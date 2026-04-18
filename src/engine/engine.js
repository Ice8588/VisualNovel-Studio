/**
 * VisualNovel Studio — 播放引擎
 * Vanilla JS 狀態機：載入 script data → 點擊推進 → 自動播放 → 歷史紀錄
 * 支援角色顏色/位置/立繪差分、Markdown 粗斜體、視覺特效
 * 鍵盤操控符合視覺小說業界標準
 */
(function () {
  "use strict";

  // ── 常數 ──
  var TYPEWRITER_SPEED = 30;
  var SKIP_INTERVAL = 100;
  var FADE_DURATION = 500;

  // 文字效果鍵集合 — 必須與 src/core/effects.py::TEXT_EFFECTS 一致
  // （tests/test_effects_sync.py 斷言兩端 key 集合相同）
  var TEXT_EFFECTS = [
    {key: "bold",          display: "粗體"},
    {key: "italic",        display: "斜體"},
    {key: "underline",     display: "底線"},
    {key: "strikethrough", display: "刪除線"},
    {key: "shake",         display: "顫抖"},
    {key: "blink",         display: "閃爍"},
  ];
  var TEXT_EFFECT_KEYS = TEXT_EFFECTS.map(function (e) { return e.key; });

  // ── Capture Mode（影片導出用，跳過動畫/音訊） ──
  var CAPTURE_MODE = (typeof window.VN_CAPTURE_MODE !== 'undefined' && window.VN_CAPTURE_MODE);
  if (CAPTURE_MODE) {
    TYPEWRITER_SPEED = 0;
    FADE_DURATION = 0;
  }

  var ASSETS_DIR = "assets/";

  // ── 狀態 ──
  var scriptData = null;
  var charactersMap = {};
  var sceneIndex = 0;
  var dialogueIndex = 0;
  var historyEntries = [];
  var isAutoPlay = false;
  var autoPlayTimer = null;
  var currentBgm = null;
  var currentBgmFile = null;
  var isHistoryOpen = false;
  var isTransitioning = false;
  var isTyping = false;
  var typewriterTimer = null;
  var audioUnlocked = false;
  var isSkipping = false;
  var skipTimer = null;
  var isUiHidden = false;
  var _jumpedFromPython = false;  // QWebChannel：Python 主動跳轉時設為 true，避免回呼迴圈

  // ── DOM 快取 ──
  var els = {};

  // ── 初始化 ──

  function init() {
    // Capture 模式：禁用所有 CSS 動畫/轉場，避免截幀出現中間狀態
    if (CAPTURE_MODE) {
      var noTransitionStyle = document.createElement("style");
      noTransitionStyle.textContent = "* { transition: none !important; animation: none !important; }";
      document.head.appendChild(noTransitionStyle);
    }

    els.container = document.getElementById("game-container");
    els.bg = document.getElementById("background");
    els.bgNext = document.getElementById("background-next");
    els.sprite = document.getElementById("sprite");
    els.stageSprites = {
      left:   document.getElementById("sprite-left"),
      center: document.getElementById("sprite-center"),
      right:  document.getElementById("sprite-right"),
    };
    els.dialogueBox = document.getElementById("dialogue-box");
    els.namePlate = document.getElementById("name-plate");
    els.dialogueText = document.getElementById("dialogue-text");
    els.quickMenu = document.getElementById("quick-menu");
    els.btnAuto = document.getElementById("btn-auto");
    els.btnSkip = document.getElementById("btn-skip");
    els.btnLog = document.getElementById("btn-log");
    els.btnHide = document.getElementById("btn-hide");
    els.historyPanel = document.getElementById("history-panel");
    els.historyContent = document.getElementById("history-content");
    els.btnCloseHistory = document.getElementById("btn-close-history");
    els.endScreen = document.getElementById("end-screen");
    els.skipIndicator = document.getElementById("skip-indicator");
    els.autoIndicator = document.getElementById("auto-indicator");

    // 事件綁定
    els.container.addEventListener("click", onContainerClick);
    els.container.addEventListener("contextmenu", onRightClick);
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keyup", onKeyUp);
    document.addEventListener("wheel", onWheel, { passive: false });

    // Quick Menu 按鈕
    els.btnAuto.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleAutoPlay();
    });
    els.btnSkip.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleSkip();
    });
    els.btnLog.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleHistory();
    });
    els.btnHide.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleUiHide();
    });
    els.btnCloseHistory.addEventListener("click", function (e) {
      e.stopPropagation();
      closeHistory();
    });

    // 初始化特效引擎
    if (typeof VNEffects !== "undefined") {
      VNEffects.init(els.container);
    }

    // 舞台 overlay：匯出時加 capture-mode class 隱藏；預覽時啟用 overlay
    if (CAPTURE_MODE) {
      document.body.classList.add("capture-mode");
    } else {
      setupStageOverlay();
    }

    loadScript();
  }

  // ── 載入 script data ──

  function loadScript() {
    if (typeof SCRIPT_DATA !== "undefined") {
      scriptData = SCRIPT_DATA;
      buildCharactersMap();
      applyGameSettings();
      startStory();
      return;
    }
    fetch("script.json")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        scriptData = data;
        buildCharactersMap();
        applyGameSettings();
        startStory();
      })
      .catch(function () {
        els.dialogueText.textContent = "無法載入 script.json";
      });
  }

  function applyGameSettings() {
    if (!scriptData || !scriptData.game_settings) return;
    var gs = scriptData.game_settings;
    if (gs.dialogue_font_size && els.dialogueText) {
      els.dialogueText.style.fontSize = gs.dialogue_font_size + "px";
    }
    if (gs.name_font_size && els.namePlate) {
      els.namePlate.style.fontSize = gs.name_font_size + "px";
    }
    if (gs.dialogue_box_opacity != null && els.dialogueBox) {
      els.dialogueBox.style.backgroundColor =
        "rgba(20,20,40," + gs.dialogue_box_opacity + ")";
    }
  }

  function buildCharactersMap() {
    charactersMap = {};
    if (scriptData && scriptData.characters) {
      var chars = scriptData.characters;
      for (var name in chars) {
        if (chars.hasOwnProperty(name)) {
          charactersMap[name] = chars[name];
        }
      }
    }
  }

  function startStory() {
    if (!scriptData || !scriptData.scenes || scriptData.scenes.length === 0) {
      showEndScreen();
      return;
    }
    sceneIndex = 0;
    dialogueIndex = 0;
    historyEntries = [];
    enterScene(0);
  }

  // ── 場景控制 ──

  function enterScene(index) {
    var scene = scriptData.scenes[index];

    // 切換背景
    var bgFile = scene.background;
    if (bgFile) {
      var bgUrl = isDataUri(bgFile) ? bgFile : ASSETS_DIR + bgFile;
      // 檔名含空白或特殊字元時 CSS url() 需用雙引號包裹、內嵌 " 轉 %22
      var newBg = 'url("' + bgUrl.replace(/"/g, "%22") + '")';
      var currentBg = els.bg.style.backgroundImage;
      if (newBg !== currentBg) {
        if (isSkipping || CAPTURE_MODE) {
          // Skip / Capture 模式跳過轉場動畫
          els.bg.style.backgroundImage = newBg;
          els.bgNext.style.backgroundImage = newBg;
        } else {
          els.bgNext.style.backgroundImage = newBg;
          els.bg.style.opacity = "0";
          isTransitioning = true;
          setTimeout(function () {
            els.bg.style.backgroundImage = newBg;
            els.bg.style.opacity = "1";
            isTransitioning = false;
          }, FADE_DURATION);
        }
      }
    }

    // 切換 BGM
    var bgmFile = scene.bgm || null;
    if (bgmFile !== currentBgmFile) {
      if (currentBgm) {
        fadeOutAudio(currentBgm, FADE_DURATION, function () {
          currentBgm.pause();
          currentBgm = null;
          if (bgmFile) startNewBgm(bgmFile);
        });
      } else if (bgmFile) {
        startNewBgm(bgmFile);
      }
      currentBgmFile = bgmFile;
    }

    // 切換特效
    if (typeof VNEffects !== "undefined") {
      VNEffects.setEffect(scene.effect || null);
    }

    showDialogue();
  }

  function advanceScene() {
    sceneIndex++;
    if (sceneIndex >= scriptData.scenes.length) {
      showEndScreen();
      return;
    }
    dialogueIndex = 0;
    enterScene(sceneIndex);
  }

  // ── Markdown → HTML ──

  function mdToHtml(text) {
    var result = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    result = result.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    result = result.replace(/\*(.+?)\*/g, "<em>$1</em>");
    result = result.replace(/~~(.+?)~~/g, "<del>$1</del>");
    return result;
  }

  // ── 對話渲染 ──

  function showDialogue() {
    var scene = scriptData.scenes[sceneIndex];

    if (!scene.dialogues || scene.dialogues.length === 0) {
      advanceScene();
      return;
    }

    if (dialogueIndex >= scene.dialogues.length) {
      advanceScene();
      return;
    }

    var d = scene.dialogues[dialogueIndex];
    var charInfo = d.character ? (charactersMap[d.character] || null) : null;

    // 確保 UI 可見（Skip 時可能被隱藏）
    if (isUiHidden) {
      showUi();
    }

    // 名稱牌（B7：半透明背景 + 寬度貼合文字）
    if (d.character) {
      els.namePlate.textContent = d.character;
      els.namePlate.style.visibility = "visible";
      var hex = charInfo && charInfo.name_color ? charInfo.name_color : "#4682B4";
      els.namePlate.style.background = hexToRgba(hex, 0.6);
    } else {
      els.namePlate.textContent = "";
      els.namePlate.style.visibility = "hidden";
    }

    // 立繪：優先用 stage；三槽皆空時退回 legacy 單立繪
    var stage = d.stage || {left: null, center: null, right: null};
    var hasStage = stage.left || stage.center || stage.right;
    if (hasStage) {
      renderStageSlot("left",   stage.left);
      renderStageSlot("center", stage.center);
      renderStageSlot("right",  stage.right);
      els.sprite.style.display = "none";
    } else {
      hideAllStageSlots();
      renderLegacySprite(d, charInfo);
    }

    // 套用文字效果（D1 多選）：對 #dialogue-text 加 fx-{key} class
    applyTextEffects(d.effects || []);

    // Skip / Capture 模式：跳過打字機，直接顯示完整文字
    if (isSkipping || CAPTURE_MODE) {
      els.dialogueText.innerHTML = mdToHtml(d.text);
      isTyping = false;
    } else {
      typeText(els.dialogueText, d.text);
    }

    // 加入歷史
    historyEntries.push({
      character: d.character,
      text: d.text,
      nameColor: charInfo ? charInfo.name_color : null
    });

    isTransitioning = false;

    // 更新舞台 overlay 按鈕狀態（Preview 模式）
    if (!CAPTURE_MODE) {
      refreshStageOverlayButtons(d);
    }

    // 通知 Python 端當前台詞（QWebChannel，非 Capture 模式、非 Python 主動跳轉）
    if (!CAPTURE_MODE && window._bridge && !_jumpedFromPython) {
      window._bridge.on_dialogue_shown(sceneIndex, dialogueIndex);
    }
    _jumpedFromPython = false;
  }

  function resolveSpriteFile(dialogue, charInfo) {
    if (!dialogue.sprite) return null;
    if (isDataUri(dialogue.sprite)) return dialogue.sprite;
    if (charInfo && charInfo.sprites && charInfo.sprites[dialogue.sprite]) {
      return charInfo.sprites[dialogue.sprite];
    }
    return dialogue.sprite;
  }

  function setSpritePosition(position) {
    els.sprite.className = "";
    if (position === "left") {
      els.sprite.className = "sprite-left";
    } else if (position === "right") {
      els.sprite.className = "sprite-right";
    } else {
      els.sprite.className = "sprite-center";
    }
  }

  // ── 三槽位立繪輔助函數 ──

  function renderStageSlot(position, slotData) {
    var el = els.stageSprites[position];
    if (!slotData) {
      el.style.display = "none";
      return;
    }
    var charInfo = slotData.character ? (charactersMap[slotData.character] || null) : null;
    var spriteLabel = slotData.sprite || null;
    var spriteFile = null;
    if (spriteLabel) {
      if (isDataUri(spriteLabel)) {
        spriteFile = spriteLabel;
      } else if (charInfo && charInfo.sprites && charInfo.sprites[spriteLabel]) {
        spriteFile = charInfo.sprites[spriteLabel];
      } else {
        spriteFile = spriteLabel;
      }
    }
    if (!spriteFile) {
      el.style.display = "none";
      return;
    }
    var url = isDataUri(spriteFile) ? spriteFile : ASSETS_DIR + spriteFile;
    if (el.getAttribute("src") !== url) {
      el.style.opacity = "0";
      el.src = url;
      el.onload = function () {
        el.style.display = "block";
        el.style.opacity = "1";
      };
    } else {
      el.style.display = "block";
      el.style.opacity = "1";
    }
  }

  function hideAllStageSlots() {
    els.stageSprites.left.style.display   = "none";
    els.stageSprites.center.style.display = "none";
    els.stageSprites.right.style.display  = "none";
  }

  function renderLegacySprite(d, charInfo) {
    var spriteFile = resolveSpriteFile(d, charInfo);
    if (spriteFile) {
      var spriteUrl = isDataUri(spriteFile) ? spriteFile : ASSETS_DIR + spriteFile;
      if (els.sprite.getAttribute("src") !== spriteUrl) {
        els.sprite.style.opacity = "0";
        els.sprite.src = spriteUrl;
        els.sprite.onload = function () {
          els.sprite.style.display = "block";
          els.sprite.style.opacity = "1";
        };
      } else {
        els.sprite.style.display = "block";
        els.sprite.style.opacity = "1";
      }
      setSpritePosition(charInfo ? charInfo.position : "center");
    } else {
      els.sprite.style.display = "none";
    }
  }

  function isDataUri(str) {
    return str && str.indexOf("data:") === 0;
  }

  // D1：文字效果 — 依 d.effects 陣列套用 fx-{key} class；未知 key 忽略
  function applyTextEffects(effects) {
    if (!els.dialogueText) return;
    // 先清除所有現有 fx-* class
    TEXT_EFFECT_KEYS.forEach(function (k) {
      els.dialogueText.classList.remove("fx-" + k);
    });
    if (!Array.isArray(effects)) return;
    effects.forEach(function (key) {
      if (TEXT_EFFECT_KEYS.indexOf(key) >= 0) {
        els.dialogueText.classList.add("fx-" + key);
      }
    });
  }

  // 將 #RRGGBB / #RGB 轉 rgba(r, g, b, alpha)；非合法 hex 回傳預設藍色半透明
  function hexToRgba(hex, alpha) {
    if (typeof hex !== "string") return "rgba(70, 130, 180, " + alpha + ")";
    var h = hex.trim().replace(/^#/, "");
    if (h.length === 3) {
      h = h.split("").map(function (c) { return c + c; }).join("");
    }
    if (!/^[0-9a-fA-F]{6}$/.test(h)) {
      return "rgba(70, 130, 180, " + alpha + ")";
    }
    var r = parseInt(h.substring(0, 2), 16);
    var g = parseInt(h.substring(2, 4), 16);
    var b = parseInt(h.substring(4, 6), 16);
    return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")";
  }

  // ── 舞台 overlay（Preview 模式） ──

  function setupStageOverlay() {
    var positions = ["left", "center", "right"];
    positions.forEach(function (pos) {
      var ctrl = document.querySelector(".slot-control[data-position='" + pos + "']");
      if (!ctrl) return;

      var btnAdd = document.createElement("button");
      btnAdd.className = "btn-add";
      btnAdd.textContent = "+";
      btnAdd.addEventListener("click", function (e) {
        e.stopPropagation();
        if (window._bridge) {
          window._bridge.on_stage_slot_clicked(sceneIndex, dialogueIndex, pos, "add");
        }
      });

      var btnClear = document.createElement("button");
      btnClear.className = "btn-clear";
      btnClear.textContent = "✕";
      btnClear.addEventListener("click", function (e) {
        e.stopPropagation();
        if (window._bridge) {
          window._bridge.on_stage_slot_clicked(sceneIndex, dialogueIndex, pos, "clear");
        }
      });

      var btnSwap = document.createElement("button");
      btnSwap.className = "btn-swap";
      btnSwap.textContent = "▼";
      btnSwap.addEventListener("click", function (e) {
        e.stopPropagation();
        if (window._bridge) {
          window._bridge.on_stage_slot_clicked(sceneIndex, dialogueIndex, pos, "swap");
        }
      });

      ctrl.appendChild(btnAdd);
      ctrl.appendChild(btnClear);
      ctrl.appendChild(btnSwap);
    });
  }

  function refreshStageOverlayButtons(d) {
    var stage = d.stage || {left: null, center: null, right: null};
    var positions = ["left", "center", "right"];
    positions.forEach(function (pos) {
      var ctrl = document.querySelector(".slot-control[data-position='" + pos + "']");
      if (!ctrl) return;
      var btnAdd   = ctrl.querySelector(".btn-add");
      var btnClear = ctrl.querySelector(".btn-clear");
      var btnSwap  = ctrl.querySelector(".btn-swap");
      if (!btnAdd) return;
      if (stage[pos]) {
        ctrl.classList.add("filled");
        btnAdd.style.display = "none";
      } else {
        ctrl.classList.remove("filled");
        btnAdd.style.display = "";
        if (btnClear) btnClear.style.display = "none";
        if (btnSwap)  btnSwap.style.display  = "none";
      }
    });
  }

  // ── 推進 ──

  function advance() {
    if (isHistoryOpen) return;

    if (isTyping) {
      skipTypewriter();
      return;
    }

    if (isTransitioning) return;

    dialogueIndex++;
    showDialogue();
  }

  // ── 打字機效果 ──

  function typeText(element, text) {
    clearInterval(typewriterTimer);
    isTyping = true;
    var htmlText = mdToHtml(text);
    element.innerHTML = "";
    var i = 0;
    var plainText = text;
    typewriterTimer = setInterval(function () {
      i++;
      if (i >= plainText.length) {
        element.innerHTML = htmlText;
        clearInterval(typewriterTimer);
        isTyping = false;
        scheduleAutoAdvance(plainText);
      } else {
        element.innerHTML = mdToHtml(plainText.substring(0, i));
      }
    }, TYPEWRITER_SPEED);
  }

  function skipTypewriter() {
    clearInterval(typewriterTimer);
    var scene = scriptData.scenes[sceneIndex];
    if (scene && dialogueIndex < scene.dialogues.length) {
      var text = scene.dialogues[dialogueIndex].text;
      els.dialogueText.innerHTML = mdToHtml(text);
      scheduleAutoAdvance(text);
    }
    isTyping = false;
  }

  // ── Auto 模式（依字數計算延遲） ──

  function getAutoDuration(text) {
    // 最少 1.5 秒，每字加 150ms
    return Math.max(1500, 1000 + text.length * 150);
  }

  function scheduleAutoAdvance(text) {
    clearTimeout(autoPlayTimer);
    if (!isAutoPlay) return;
    var delay = getAutoDuration(text);
    autoPlayTimer = setTimeout(function () {
      if (isAutoPlay && !isTyping && !isTransitioning && !isHistoryOpen && !isSkipping) {
        advance();
      }
    }, delay);
  }

  function toggleAutoPlay() {
    if (isAutoPlay) {
      stopAutoPlay();
    } else {
      // 停止 Skip 模式
      if (isSkipping) stopSkip();
      isAutoPlay = true;
      els.btnAuto.classList.add("active");
      els.autoIndicator.style.display = "block";
      // 如果目前沒在打字，立即排程下一次推進
      if (!isTyping) {
        var scene = scriptData.scenes[sceneIndex];
        if (scene && dialogueIndex < scene.dialogues.length) {
          scheduleAutoAdvance(scene.dialogues[dialogueIndex].text);
        }
      }
    }
  }

  function stopAutoPlay() {
    isAutoPlay = false;
    clearTimeout(autoPlayTimer);
    autoPlayTimer = null;
    els.btnAuto.classList.remove("active");
    els.autoIndicator.style.display = "none";
  }

  // ── Skip 模式（Ctrl 按住 / 按鈕 toggle） ──

  function startSkip() {
    if (isSkipping) return;
    // 停止 Auto 模式
    if (isAutoPlay) stopAutoPlay();
    isSkipping = true;
    els.btnSkip.classList.add("active");
    els.skipIndicator.style.display = "block";
    skipTimer = setInterval(function () {
      if (isHistoryOpen) return;
      if (isTyping) skipTypewriter();
      advance();
    }, SKIP_INTERVAL);
  }

  function stopSkip() {
    if (!isSkipping) return;
    isSkipping = false;
    clearInterval(skipTimer);
    skipTimer = null;
    els.btnSkip.classList.remove("active");
    els.skipIndicator.style.display = "none";
  }

  function toggleSkip() {
    if (isSkipping) {
      stopSkip();
    } else {
      startSkip();
    }
  }

  // ── UI 顯示/隱藏（H 鍵 / 右鍵） ──

  function toggleUiHide() {
    if (isUiHidden) {
      showUi();
    } else {
      hideUi();
    }
  }

  function hideUi() {
    isUiHidden = true;
    els.dialogueBox.style.display = "none";
    els.quickMenu.style.display = "none";
  }

  function showUi() {
    isUiHidden = false;
    els.dialogueBox.style.display = "";
    els.quickMenu.style.display = "";
  }

  // ── 歷史紀錄 ──

  function toggleHistory() {
    if (isHistoryOpen) {
      closeHistory();
    } else {
      openHistory();
    }
  }

  function openHistory() {
    var html = "";
    for (var i = 0; i < historyEntries.length; i++) {
      var entry = historyEntries[i];
      html += '<div class="history-entry">';
      if (entry.character) {
        var colorStyle = entry.nameColor
          ? ' style="color:' + escapeHtml(entry.nameColor) + '"'
          : "";
        html += '<span class="history-character"' + colorStyle + '>'
          + escapeHtml(entry.character) + '</span>';
        html += '<span class="history-text">' + mdToHtml(entry.text) + '</span>';
      } else {
        html += '<span class="history-narration">' + mdToHtml(entry.text) + '</span>';
      }
      html += '</div>';
    }
    els.historyContent.innerHTML = html;
    els.historyPanel.style.display = "block";
    els.historyPanel.scrollTop = els.historyPanel.scrollHeight;
    isHistoryOpen = true;
  }

  function closeHistory() {
    els.historyPanel.style.display = "none";
    isHistoryOpen = false;
  }

  // ── END 畫面 ──

  function showEndScreen() {
    if (isAutoPlay) stopAutoPlay();
    if (isSkipping) stopSkip();
    if (currentBgm) {
      fadeOutAudio(currentBgm, FADE_DURATION, function () {
        currentBgm.pause();
        currentBgm = null;
      });
    }
    if (typeof VNEffects !== "undefined") {
      VNEffects.stop();
    }
    els.dialogueBox.style.display = "none";
    els.sprite.style.display = "none";
    els.quickMenu.style.display = "none";
    els.endScreen.style.display = "flex";
  }

  // ── BGM 處理 ──

  function startNewBgm(filename) {
    if (CAPTURE_MODE) return;
    var url = isDataUri(filename) ? filename : ASSETS_DIR + filename;
    currentBgm = new Audio(url);
    currentBgm.loop = true;
    currentBgm.volume = 0.5;
    currentBgm.play().catch(function () {});
  }

  function fadeOutAudio(audio, duration, callback) {
    var steps = 10;
    var stepDuration = duration / steps;
    var volumeStep = audio.volume / steps;
    var interval = setInterval(function () {
      audio.volume = Math.max(0, audio.volume - volumeStep);
      if (audio.volume <= 0.01) {
        clearInterval(interval);
        audio.volume = 0;
        if (callback) callback();
      }
    }, stepDuration);
  }

  function unlockAudio() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    if (currentBgm && currentBgm.paused) {
      currentBgm.play().catch(function () {});
    }
  }

  // ── 事件處理 ──

  function onContainerClick(e) {
    if (e.target.tagName === "BUTTON") return;
    unlockAudio();
    // 如果 UI 被隱藏，點擊恢復顯示
    if (isUiHidden) {
      showUi();
      return;
    }
    advance();
  }

  function onRightClick(e) {
    e.preventDefault();
    if (isHistoryOpen) {
      closeHistory();
      return;
    }
    toggleUiHide();
  }

  function onKeyDown(e) {
    // Ctrl 按住快進
    if (e.key === "Control" && !e.repeat) {
      startSkip();
      return;
    }

    // Space / Enter：推進
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      unlockAudio();
      if (isUiHidden) {
        showUi();
        return;
      }
      advance();
      return;
    }

    // A：切換 Auto
    if (e.key === "a" || e.key === "A") {
      toggleAutoPlay();
      return;
    }

    // H：隱藏/顯示 UI
    if (e.key === "h" || e.key === "H") {
      toggleUiHide();
      return;
    }

    // Escape：關閉歷史 / 停止 Skip / 停止 Auto
    if (e.key === "Escape") {
      if (isHistoryOpen) {
        closeHistory();
      } else if (isSkipping) {
        stopSkip();
      } else if (isAutoPlay) {
        stopAutoPlay();
      }
      return;
    }

    // Page Up：開歷史
    if (e.key === "PageUp") {
      e.preventDefault();
      if (!isHistoryOpen) openHistory();
      return;
    }

    // Page Down：推進
    if (e.key === "PageDown") {
      e.preventDefault();
      advance();
      return;
    }
  }

  function onKeyUp(e) {
    // Ctrl 放開停止快進
    if (e.key === "Control") {
      stopSkip();
    }
  }

  function onWheel(e) {
    // 滾輪上：開歷史
    if (e.deltaY < 0) {
      e.preventDefault();
      if (!isHistoryOpen) openHistory();
    }
    // 滾輪下：推進（僅在歷史面板關閉時）
    if (e.deltaY > 0 && !isHistoryOpen) {
      e.preventDefault();
      advance();
    }
  }

  // ── 工具函式 ──

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // ── 啟動 ──

  document.addEventListener("DOMContentLoaded", function () {
    init();

    // VNPreviewAPI：在預覽模式也可跳轉（保留動畫效果）
    window.VNPreviewAPI = {
      goToScene: function (sIdx) {
        _jumpedFromPython = true;
        if (!scriptData || sIdx < 0 || sIdx >= scriptData.scenes.length) return;
        sceneIndex = sIdx;
        dialogueIndex = 0;
        enterScene(sIdx);
      },
      goToDialogue: function (dIdx) {
        _jumpedFromPython = true;
        var scene = scriptData && scriptData.scenes[sceneIndex];
        if (!scene || dIdx < 0 || dIdx >= scene.dialogues.length) return;
        dialogueIndex = dIdx;
        showDialogue();
      }
    };

    // QWebChannel：在 PyQt6 WebEngine 預覽環境中初始化雙向通訊
    if (!CAPTURE_MODE && typeof QWebChannel !== "undefined") {
      new QWebChannel(qt.webChannelTransport, function (channel) {
        window._bridge = channel.objects.bridge;
      });
    }

    if (CAPTURE_MODE) {
      // 暴露截幀控制 API 給 Python 端呼叫
      window.VNCaptureAPI = {
        /** 切換到指定場景（會觸發背景/特效切換 + 顯示第一句對話） */
        goToScene: function (sIdx) {
          sceneIndex = sIdx;
          dialogueIndex = 0;
          enterScene(sIdx);
        },
        /** 切換到當前場景的指定對話（不重設背景/特效） */
        goToDialogue: function (dIdx) {
          dialogueIndex = dIdx;
          showDialogue();
        },
        /** 查詢場景資訊 */
        getInfo: function () {
          if (!scriptData) return null;
          return {
            sceneCount: scriptData.scenes.length,
            scenes: scriptData.scenes.map(function (s) {
              return {
                dialogueCount: s.dialogues ? s.dialogues.length : 0,
                effect: s.effect || null,
                background: s.background || null,
                bgm: s.bgm || null
              };
            })
          };
        }
      };
    }
  });
})();
