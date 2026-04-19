/* VisualNovel Studio — Canvas 視覺特效。

   Phase 3 API：`VNEffects.setActive(activeList)`
     activeList = [{effect_type, params}, ...]（由 Python `state_at` 預計算）

   分類：
   - canvas 型（rain / snow / crt）：同時至多 1 個，取 activeList 第一個出現的。
   - body-class / filter 型（pixel_dark / screen_shake）：可與任何 canvas 型疊加。
   - 未知 effect_type：console.warn，不崩。

   向下相容：`VNEffects.setEffect(name)` 仍可用（內部轉成單條 active 呼叫 setActive）。
*/

var VNEffects = (function () {
  var canvas = null;
  var ctx = null;
  var container = null;
  var animId = null;
  var currentCanvasEffect = null;   // "rain" / "snow" / "crt" / null
  var particles = [];

  var CANVAS_EFFECTS = ["rain", "snow", "crt"];
  var KNOWN_EFFECTS = ["rain", "snow", "crt", "pixel_dark", "screen_shake"];

  function init(containerEl) {
    container = containerEl || document.getElementById("game-container");
    canvas = document.getElementById("effect-canvas");
    if (!canvas) return;
    ctx = canvas.getContext("2d");
    _resize();
    window.addEventListener("resize", _resize);
  }

  function _resize() {
    if (!canvas || !container) return;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
  }

  /**
   * 切換 active effects。傳入 [] 代表全部停止。
   * activeList 由 Python `state_at` 預先組裝，engine.js 只需消化。
   */
  function setActive(activeList) {
    if (!Array.isArray(activeList)) activeList = [];
    var types = activeList.map(function (e) { return e && e.effect_type; });

    // Canvas effect：至多 1 個（取 activeList 第一個 canvas 型）
    var newCanvas = null;
    for (var i = 0; i < types.length; i++) {
      if (CANVAS_EFFECTS.indexOf(types[i]) >= 0) {
        newCanvas = types[i];
        break;
      }
    }
    _setCanvasEffect(newCanvas);

    // pixel_dark：container filter
    _setPixelDark(types.indexOf("pixel_dark") >= 0);

    // screen_shake：body class（CSS keyframes；capture mode 下 animation disabled）
    if (document && document.body) {
      document.body.classList.toggle("fx-screen_shake", types.indexOf("screen_shake") >= 0);
    }

    // 未知 effect_type → warn 但不崩
    types.forEach(function (t) {
      if (t && KNOWN_EFFECTS.indexOf(t) < 0) {
        console.warn("[VNEffects] unknown effect_type:", t);
      }
    });
  }

  /** 向下相容舊 API。傳 null/"" 代表停止所有特效。 */
  function setEffect(name) {
    if (!name || name === "" || name === "(無)") {
      setActive([]);
    } else {
      setActive([{ effect_type: name, params: {} }]);
    }
  }

  function stop() {
    setActive([]);
  }

  function _setCanvasEffect(name) {
    if (name === currentCanvasEffect) return;
    // 停掉現有 canvas 動畫
    if (animId) {
      cancelAnimationFrame(animId);
      animId = null;
    }
    particles = [];
    if (ctx && canvas) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    currentCanvasEffect = name;
    if (name === "rain") _startRain();
    else if (name === "snow") _startSnow();
    else if (name === "crt") _startCrt();
  }

  function _setPixelDark(on) {
    if (!container) return;
    if (on) {
      container.style.filter = "brightness(0.6)";
      container.style.imageRendering = "pixelated";
    } else {
      container.style.filter = "";
      container.style.imageRendering = "";
    }
  }

  /* ── Rain ── */

  function _startRain() {
    var w = canvas.width;
    var h = canvas.height;
    particles = [];
    for (var i = 0; i < 120; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        speed: 4 + Math.random() * 4,
        len: 10 + Math.random() * 15
      });
    }
    _loopRain();
  }

  function _loopRain() {
    if (currentCanvasEffect !== "rain") return;
    var w = canvas.width;
    var h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "rgba(174, 194, 224, 0.5)";
    ctx.lineWidth = 1;

    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x - 1, p.y + p.len);
      ctx.stroke();

      p.y += p.speed;
      p.x -= 0.5;
      if (p.y > h) {
        p.y = -p.len;
        p.x = Math.random() * w;
      }
    }

    animId = requestAnimationFrame(_loopRain);
  }

  /* ── Snow ── */

  function _startSnow() {
    var w = canvas.width;
    var h = canvas.height;
    particles = [];
    for (var i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        r: 1.5 + Math.random() * 2.5,
        speed: 0.5 + Math.random() * 1.5,
        drift: Math.random() * Math.PI * 2
      });
    }
    _loopSnow();
  }

  function _loopSnow() {
    if (currentCanvasEffect !== "snow") return;
    var w = canvas.width;
    var h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "rgba(255, 255, 255, 0.8)";

    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();

      p.y += p.speed;
      p.drift += 0.01;
      p.x += Math.sin(p.drift) * 0.5;

      if (p.y > h + p.r) {
        p.y = -p.r;
        p.x = Math.random() * w;
      }
    }

    animId = requestAnimationFrame(_loopSnow);
  }

  /* ── CRT ── */

  function _startCrt() {
    _loopCrt();
  }

  var crtFlicker = 0;

  function _loopCrt() {
    if (currentCanvasEffect !== "crt") return;
    var w = canvas.width;
    var h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // 掃描線
    ctx.fillStyle = "rgba(0, 0, 0, 0.12)";
    for (var y = 0; y < h; y += 3) {
      ctx.fillRect(0, y, w, 1);
    }

    // 輕微閃爍
    crtFlicker += 1;
    if (crtFlicker % 8 < 2) {
      ctx.fillStyle = "rgba(0, 0, 0, 0.03)";
      ctx.fillRect(0, 0, w, h);
    }

    animId = requestAnimationFrame(_loopCrt);
  }

  return {
    init: init,
    setEffect: setEffect,     // 向下相容
    setActive: setActive,     // Phase 3 新 API
    stop: stop,
  };
})();
