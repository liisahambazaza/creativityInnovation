/* Kànjiàn: handscroll viewer and read-aloud.

   Every page works without this script. It adds two things on a work page:
   - a handscroll opens at its right-hand end (where it starts) and can be dragged;
   - "Read aloud" reads the introduction and the things to look for, using Ava
     for English when it is installed and a Mandarin voice for Chinese. */
(function () {
  'use strict';

  var root = document.documentElement;
  var pageLang = root.getAttribute('data-lang') === 'zh' ? 'zh-CN' : 'en-US';
  var stringsEl = document.getElementById('kj-strings');
  var S = stringsEl ? JSON.parse(stringsEl.textContent) : {};

  /* ---------- handscroll viewer ---------------------------------------------- */
  function setUpScroll(frame) {
    // Handscrolls are read from right to left, so start at the right-hand end.
    function toStart() { frame.scrollLeft = frame.scrollWidth; }
    var img = frame.querySelector('img');
    if (img && !img.complete) { img.addEventListener('load', toStart); }
    toStart();

    // Drag with a mouse to unroll (touch and trackpads already scroll sideways).
    var startX = 0;
    var startLeft = 0;
    var dragging = false;
    frame.addEventListener('pointerdown', function (event) {
      if (event.pointerType !== 'mouse' || event.button !== 0) { return; }
      dragging = true;
      startX = event.clientX;
      startLeft = frame.scrollLeft;
      frame.classList.add('is-dragging');
      frame.setPointerCapture(event.pointerId);
      event.preventDefault();
    });
    frame.addEventListener('pointermove', function (event) {
      if (dragging) { frame.scrollLeft = startLeft - (event.clientX - startX); }
    });
    function stopDrag() { dragging = false; frame.classList.remove('is-dragging'); }
    frame.addEventListener('pointerup', stopDrag);
    frame.addEventListener('pointercancel', stopDrag);

    // Arrow keys move along the scroll when it has focus.
    frame.addEventListener('keydown', function (event) {
      var step = frame.clientWidth * 0.6;
      if (event.key === 'ArrowLeft') { frame.scrollBy({ left: -step, behavior: 'smooth' }); event.preventDefault(); }
      if (event.key === 'ArrowRight') { frame.scrollBy({ left: step, behavior: 'smooth' }); event.preventDefault(); }
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll('[data-scroll-start="right"]'), setUpScroll);

  /* ---------- read aloud ---------------------------------------------------- */
  var synth = window.speechSynthesis;
  var supported = !!(synth && window.SpeechSynthesisUtterance);
  var voices = [];
  function loadVoices() { voices = synth.getVoices() || []; }
  if (supported) {
    loadVoices();
    if (synth.addEventListener) { synth.addEventListener('voiceschanged', loadVoices); }
  }

  // Named voices to use when installed, by language family, best first: Ava for
  // English; Tingting, the standard macOS Mandarin voice, for Chinese (rather than
  // whichever novelty voice happens to be listed first). macOS lists the same voice
  // as "Ava", "Ava (Enhanced)" or "Ava (Premium)"; the better quality wins.
  var PREFERRED = { en: ['ava'], zh: ['tingting', 'meijia'] };

  function preferredBonus(voice, family) {
    var wants = PREFERRED[family] || [];
    var name = (voice.name || '').toLowerCase();
    for (var i = 0; i < wants.length; i += 1) {
      if (name === wants[i] || name.indexOf(wants[i] + ' ') === 0) {
        var bonus = 10 - i;
        if (name.indexOf('premium') !== -1) { return bonus + 0.2; }
        if (name.indexOf('enhanced') !== -1) { return bonus + 0.1; }
        return bonus;
      }
    }
    return 0;
  }

  function voiceFor(lang) {
    var wanted = lang.toLowerCase();
    var family = wanted.split('-')[0];
    if (family === 'zh' && wanted === 'zh') { wanted = 'zh-cn'; }
    var best = null;
    var bestScore = 0;
    voices.forEach(function (voice) {
      var tag = (voice.lang || '').replace('_', '-').toLowerCase();
      var score = 0;
      if (tag === wanted) { score = 4; }
      else if (family === 'zh' && (tag === 'zh' || tag.indexOf('zh-hans') === 0 || tag === 'cmn-cn')) { score = 3; }
      else if (family === 'zh' && (tag === 'zh-sg' || tag === 'zh-tw')) { score = 2; }   // Mandarin; never Cantonese (zh-HK)
      else if (family === 'en' && tag.split('-')[0] === 'en') { score = 2; }
      if (score) { score += preferredBonus(voice, family); }
      if (score && voice.localService) { score += 0.5; }
      if (score > bestScore) { best = voice; bestScore = score; }
    });
    return best;
  }

  /* An element's text as runs of one language each. Chinese inside English is
     wrapped in <span lang="zh">, so those runs get a Mandarin voice. */
  function partsOf(element) {
    var parts = [];
    element.childNodes.forEach(function (node) {
      if (node.nodeType === 1 && node.hasAttribute('data-noread')) { return; }   // citation numbers
      var text = (node.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text || !/[\p{L}\p{N}]/u.test(text)) { return; }   // nothing to say in bare punctuation
      var lang = node.nodeType === 1 && node.getAttribute('lang') ? node.getAttribute('lang') : pageLang;
      parts.push({ text: text, lang: lang, element: element });
    });
    return parts;
  }

  var button = document.getElementById('btn-read');
  if (!button) { return; }
  var label = document.getElementById('btn-read-text');
  var status = document.getElementById('read-status');
  button.parentElement.hidden = false;

  var token = 0;
  var keep = [];   // Chrome drops "end" events of utterances that were garbage-collected
  var watchdog = null;

  function setReading(on) {
    button.setAttribute('aria-pressed', on ? 'true' : 'false');
    label.textContent = on ? S.stop_reading : S.read_aloud;
    if (!on) {
      Array.prototype.forEach.call(document.querySelectorAll('.is-reading'), function (el) {
        el.classList.remove('is-reading');
      });
    }
  }

  function stop() {
    token += 1;
    keep = [];
    window.clearTimeout(watchdog);
    if (supported) { synth.cancel(); }
    setReading(false);
  }

  function readAll() {
    var heading = document.querySelector('.work-header h1');
    var items = [heading].concat(Array.prototype.slice.call(document.querySelectorAll('[data-read]')));
    var parts = [];
    items.forEach(function (el) { if (el) { parts = parts.concat(partsOf(el)); } });
    stop();
    var mine = token;
    setReading(true);

    function speak(i) {
      if (mine !== token) { return; }
      Array.prototype.forEach.call(document.querySelectorAll('.is-reading'), function (el) {
        el.classList.remove('is-reading');
      });
      if (i >= parts.length) { setReading(false); return; }
      var part = parts[i];
      part.element.classList.add('is-reading');
      var utterance = new window.SpeechSynthesisUtterance(part.text);
      var voice = voiceFor(part.lang);
      var settled = false;
      utterance.lang = voice ? voice.lang : part.lang;
      if (voice) { utterance.voice = voice; }
      function next() {
        if (settled || mine !== token) { return; }
        settled = true;
        window.clearTimeout(watchdog);
        speak(i + 1);
      }
      utterance.onstart = function () { window.clearTimeout(watchdog); };
      utterance.onend = next;
      utterance.onerror = next;
      keep.push(utterance);
      // Some browsers accept speak() but never start (no voice installed).
      watchdog = window.setTimeout(function () {
        if (settled || mine !== token) { return; }
        stop();
        status.textContent = S.no_speech;
      }, 8000);
      synth.speak(utterance);
    }
    speak(0);
  }

  button.addEventListener('click', function () {
    status.textContent = '';
    if (!supported) { status.textContent = S.no_speech; return; }
    if (button.getAttribute('aria-pressed') === 'true') { stop(); } else { readAll(); }
  });
  window.addEventListener('pagehide', stop);
})();
