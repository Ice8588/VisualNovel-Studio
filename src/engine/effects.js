/* VisualNovel Studio — Canvas 視覺特效 */

var VNEffects = (function () {
  var canvas = null;
  var ctx = null;
  var container = null;
  var animId = null;
  var currentEffect = null;
  var particles = [];

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

  function setEffect(name) {
    stop();
    if (!name || name === "" || name === "(無)") return;
    currentEffect = name;

    switch (name) {
      case "rain":
        _startRain();
        break;
      case "snow":
        _startSnow();
        break;
      case "crt":
        _startCrt();
        break;
      case "pixel_dark":
        _startPixelDark();
        break;
    }
  }

  function stop() {
    if (animId) {
      cancelAnimationFrame(animId);
      animId = null;
    }
    currentEffect = null;
    particles = [];
    if (ctx && canvas) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    // 移除 CSS 特效
    if (container) {
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
    if (currentEffect !== "rain") return;
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
    if (currentEffect !== "snow") return;
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
    if (currentEffect !== "crt") return;
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

  /* ── Pixel Dark ── */

  function _startPixelDark() {
    if (container) {
      container.style.filter = "brightness(0.6)";
      container.style.imageRendering = "pixelated";
    }
    // pixel_dark 不需要 animation loop
  }

  return {
    init: init,
    setEffect: setEffect,
    stop: stop
  };
})();
