/* Kànjiàn: settings, sound cues, built-in voice and the work-page player.

   The server renders every description as ordinary text, so the page reads
   correctly with a screen reader, or with this script switched off. This file
   adds the audio guide on top. */
(function () {
  'use strict';

  var prefs = window.KanjianPrefs;
  var root = document.documentElement;
  var pageLang = root.getAttribute('data-lang') === 'zh' ? 'zh-CN' : 'en-US';
  var S = JSON.parse(document.getElementById('kj-strings').textContent);

  var RATES = { slow: 0.8, normal: 1, fast: 1.3 };
  // AI descriptions are spoken slightly lower than verified content.
  var PITCH = { verified: 1, inferred: 0.85 };

  /* ---------- sound cues ---------------------------------------------------
     verified: one clear high tone.  inferred: two soft falling tones.
     stop: a short tick as a new part begins.  end: a layer is finished. */
  var Cues = (function () {
    var patterns = {
      verified: [[880, 0, 0.16, 'sine']],
      inferred: [[392, 0, 0.11, 'triangle'], [311, 0.13, 0.15, 'triangle']],
      stop: [[660, 0, 0.06, 'sine']],
      end: [[523, 0, 0.1, 'sine'], [392, 0.12, 0.2, 'sine']]
    };
    var context = null;

    function play(name) {
      var AudioCtx = window.AudioContext || window.webkitAudioContext;
      var pattern = patterns[name];
      if (!AudioCtx || !pattern) { return 0; }
      try {
        if (!context) { context = new AudioCtx(); }
        if (context.state === 'suspended') { context.resume(); }
        var now = context.currentTime + 0.02;
        var length = 0;
        pattern.forEach(function (note) {
          var osc = context.createOscillator();
          var gain = context.createGain();
          var start = now + note[1];
          osc.type = note[3];
          osc.frequency.value = note[0];
          gain.gain.setValueAtTime(0.0001, start);
          gain.gain.exponentialRampToValueAtTime(0.22, start + 0.015);
          gain.gain.exponentialRampToValueAtTime(0.0001, start + note[2]);
          osc.connect(gain);
          gain.connect(context.destination);
          osc.start(start);
          osc.stop(start + note[2] + 0.02);
          length = Math.max(length, note[1] + note[2]);
        });
        return Math.round(length * 1000) + 90;   // milliseconds until speech may follow
      } catch (error) {
        return 0;
      }
    }
    return { play: play };
  })();

  /* ---------- built-in voice ------------------------------------------------ */
  var Speech = (function () {
    var synth = window.speechSynthesis;
    var supported = !!(synth && window.SpeechSynthesisUtterance);
    var voices = [];
    var token = 0;        // changes whenever speech is stopped; late callbacks check it
    var timer = null;
    var watchdog = null;
    var keep = [];        // Chrome drops "end" events of utterances that were garbage-collected
    var unlocked = false;

    function loadVoices() { voices = synth.getVoices() || []; }
    if (supported) {
      loadVoices();
      if (synth.addEventListener) { synth.addEventListener('voiceschanged', loadVoices); }
    }

    function voiceFor(lang) {
      var wanted = lang.toLowerCase();
      var family = wanted.split('-')[0];
      var best = null;
      var bestScore = 0;
      voices.forEach(function (voice) {
        var tag = (voice.lang || '').replace('_', '-').toLowerCase();
        var score = 0;
        if (tag === wanted) { score = 4; }
        else if (family === 'zh' && (tag === 'zh' || tag.indexOf('zh-hans') === 0 || tag === 'cmn-cn')) { score = 3; }
        else if (family === 'zh' && (tag === 'zh-sg' || tag === 'zh-tw')) { score = 2; }   // Mandarin; never Cantonese (zh-HK)
        else if (family === 'en' && tag.split('-')[0] === 'en') { score = 2; }
        if (score && voice.localService) { score += 0.5; }
        if (score > bestScore) { best = voice; bestScore = score; }
      });
      return best;
    }

    function stop() {
      token += 1;
      window.clearTimeout(timer);
      window.clearTimeout(watchdog);
      keep = [];
      if (supported) { synth.cancel(); }
    }

    // Mobile browsers only allow speech that begins inside a tap. Call this in the click handler.
    function unlock() {
      if (!supported || unlocked) { return; }
      unlocked = true;
      var silent = new window.SpeechSynthesisUtterance(' ');
      silent.volume = 0;
      synth.speak(silent);
    }

    /* items: [{ parts: [{text, lang}], cue, pitch, onstart, onend }]
       done() runs after the last item; failed() if the browser never starts speaking. */
    function say(items, done, failed) {
      stop();
      var mine = token;
      var index = 0;

      function nextItem() {
        if (mine !== token) { return; }
        if (index >= items.length) { if (done) { done(); } return; }
        var item = items[index];
        index += 1;
        var wait = item.cue ? Cues.play(item.cue) : 0;
        timer = window.setTimeout(function () {
          if (mine !== token) { return; }
          if (item.onstart) { item.onstart(); }
          speakPart(item, 0);
        }, wait);
      }

      function speakPart(item, p) {
        if (mine !== token) { return; }
        if (p >= item.parts.length) {
          if (item.onend) { item.onend(); }
          nextItem();
          return;
        }
        var part = item.parts[p];
        var utterance = new window.SpeechSynthesisUtterance(part.text);
        var voice = voiceFor(part.lang);
        var settled = false;
        utterance.lang = part.lang;
        if (voice) { utterance.voice = voice; }
        utterance.rate = RATES[prefs.values.rate] || 1;
        utterance.pitch = item.pitch || 1;
        function finish() {
          if (settled || mine !== token) { return; }
          settled = true;
          window.clearTimeout(watchdog);
          speakPart(item, p + 1);
        }
        utterance.onstart = function () { window.clearTimeout(watchdog); };
        utterance.onend = finish;
        utterance.onerror = finish;
        keep.push(utterance);
        watchdog = window.setTimeout(function () {
          if (settled || mine !== token) { return; }
          stop();
          if (failed) { failed(); }
        }, 8000);
        synth.speak(utterance);
      }

      nextItem();
    }

    return { supported: supported, say: say, stop: stop, unlock: unlock };
  })();

  /* Text of an element as runs of one language each. The server wraps Chinese
     inside English in <span lang="zh-CN">, so those runs get a Mandarin voice. */
  function partsOf(element) {
    var parts = [];
    if (!element) { return parts; }
    element.childNodes.forEach(function (node) {
      var text = (node.textContent || '').replace(/\s+/g, ' ').trim();
      if (!text || !/[\p{L}\p{N}]/u.test(text)) { return; }   // nothing to say in bare punctuation
      var lang = node.nodeType === 1 && node.getAttribute('lang') ? node.getAttribute('lang') : pageLang;
      parts.push({ text: text, lang: lang });
    });
    return parts;
  }

  function plain(text) { return [{ text: text, lang: pageLang }]; }

  function notifyPrefs() { document.dispatchEvent(new CustomEvent('kanjian:prefs')); }

  /* ---------- settings form ---------------------------------------------------- */
  (function initSettings() {
    var form = document.getElementById('settings-form');
    if (!form) { return; }
    Array.prototype.forEach.call(form.elements, function (input) {
      if (!input.name || !(input.name in prefs.values)) { return; }
      if (input.type === 'checkbox') { input.checked = prefs.values[input.name]; }
      else if (input.type === 'radio') { input.checked = input.value === prefs.values[input.name]; }
    });
    form.addEventListener('change', function (event) {
      var input = event.target;
      if (!input.name || !(input.name in prefs.values)) { return; }
      prefs.values[input.name] = input.type === 'checkbox' ? input.checked : input.value;
      prefs.save();
      prefs.apply();
      notifyPrefs();
    });
    form.addEventListener('submit', function (event) { event.preventDefault(); });
  })();

  /* ---------- small page behaviours ---------------------------------------------- */
  document.querySelectorAll('[data-cue]').forEach(function (button) {
    button.hidden = false;
    button.addEventListener('click', function () {
      var name = button.getAttribute('data-cue');
      if (Speech.supported && prefs.values.voice === 'on') {
        Speech.unlock();
        Speech.say([{ cue: name, pitch: PITCH[name], parts: plain(S['say_' + name]) }]);
      } else {
        Cues.play(name);
      }
    });
  });

  document.querySelectorAll('[data-action="print"]').forEach(function (button) {
    button.hidden = false;
    button.addEventListener('click', function () { window.print(); });
  });

  window.addEventListener('pagehide', function () { Speech.stop(); });

  /* ---------- work page ------------------------------------------------------------ */
  var article = document.querySelector('.work');
  if (!article) { return; }

  var player = document.getElementById('player');
  var statusLine = document.getElementById('player-status');
  var notice = document.getElementById('player-notice');
  var progressBar = document.getElementById('player-progress-bar');
  var playButton = document.getElementById('btn-play');
  var playText = document.getElementById('btn-play-text');
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var layers = [];
  var stops = [];
  var state = { current: 0, playing: false, heard: false };

  function voiceOn() { return Speech.supported && prefs.values.voice === 'on'; }

  // --- the image viewer pans to the part of the work being described
  var viewer = (function () {
    var element = article.querySelector('[data-viewer]');
    var dataBlock = document.getElementById('kj-work');
    var images = dataBlock ? JSON.parse(dataBlock.textContent).images : {};
    if (!element) { return { show: function () {}, layout: function () {} }; }
    var frame = element.querySelector('.viewer-frame');
    var image = element.querySelector('.viewer-image');
    var key = Object.keys(images).filter(function (k) { return images[k].src === image.getAttribute('src'); })[0];
    var region = [0, 0, 1, 1];
    element.classList.add('is-live');

    function layout() {
      var meta = images[key];
      var width = frame.clientWidth;
      if (!meta || !width) { return; }
      var tallest = Math.max(150, Math.min(window.innerHeight * 0.34, 420));
      var regionWidth = (region[2] - region[0]) * meta.width;
      var regionHeight = (region[3] - region[1]) * meta.height;
      var scale = Math.min(width / regionWidth, tallest / regionHeight);
      // a wide strip gets a low frame, so a handscroll is not shown inside empty bars
      var height = Math.round(Math.max(80, Math.min(tallest, regionHeight * scale)));
      var x = (width - regionWidth * scale) / 2 - region[0] * meta.width * scale;
      var y = (height - regionHeight * scale) / 2 - region[1] * meta.height * scale;
      frame.style.height = height + 'px';
      image.style.width = meta.width + 'px';
      image.style.height = meta.height + 'px';
      image.style.transform = 'translate(' + x.toFixed(1) + 'px, ' + y.toFixed(1) + 'px) scale(' + scale.toFixed(5) + ')';
    }

    function show(stop) {
      var wanted = stop.element.getAttribute('data-image') || key;
      if (wanted !== key && images[wanted]) {
        key = wanted;
        image.src = images[key].src;
        image.alt = images[key].alt;
      }
      region = (stop.element.getAttribute('data-region') || '0,0,1,1').split(',').map(Number);
      layout();
    }

    window.addEventListener('resize', layout);
    return { show: show, layout: layout, element: element };
  })();

  // Keep keyboard focus and scrolled-to content clear of the pinned viewer and player bar.
  function setScrollPadding() {
    var top = viewer.element ? viewer.element.offsetHeight + 16 : 16;
    root.style.scrollPaddingTop = top + 'px';
    root.style.scrollPaddingBottom = (player.offsetHeight + 16) + 'px';
  }

  // --- read the page structure
  article.querySelectorAll('.layer').forEach(function (element, layerIndex) {
    var layer = {
      element: element,
      n: layerIndex + 1,
      body: element.querySelector('.layer-body'),
      heading: element.querySelector('.layer-heading'),
      button: null,
      stops: []
    };
    element.querySelectorAll('[data-stop]').forEach(function (stopElement) {
      var stop = {
        element: stopElement,
        layer: layer,
        index: stops.length,
        inLayer: layer.stops.length,
        heading: stopElement.querySelector('.stop-heading'),
        empty: stopElement.querySelector('.stop-empty'),
        segments: Array.prototype.map.call(stopElement.querySelectorAll('.seg'), function (seg) {
          return { element: seg, status: seg.getAttribute('data-status'), text: seg.querySelector('.seg-text') };
        })
      };
      stops.push(stop);
      layer.stops.push(stop);
    });
    layers.push(layer);
  });
  if (!stops.length) { return; }

  // --- each layer heading becomes a button that opens and closes its layer
  function setOpen(layer, open) {
    layer.button.setAttribute('aria-expanded', open ? 'true' : 'false');
    layer.body.hidden = !open;
  }

  layers.forEach(function (layer) {
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'layer-toggle';
    button.setAttribute('aria-controls', layer.body.id);
    while (layer.heading.firstChild) { button.appendChild(layer.heading.firstChild); }
    layer.heading.appendChild(button);
    layer.button = button;
    setOpen(layer, layer.n === 1);
    button.addEventListener('click', function () {
      var open = button.getAttribute('aria-expanded') !== 'true';
      setOpen(layer, open);
      if (!open) { return; }
      // Opening a layer moves the guide to its first part.
      var wasPlaying = state.playing;
      select(layer.stops[0].index, { scroll: false });
      if (wasPlaying) { speakCurrent(); }
    });
  });

  function refreshEmptyNotes() {
    stops.forEach(function (stop) {
      var hasVerified = stop.segments.some(function (seg) { return seg.status === 'verified'; });
      stop.empty.hidden = !(prefs.values.verifiedOnly && !hasVerified);
    });
  }

  function setPlaying(playing) {
    state.playing = playing;
    player.setAttribute('data-state', playing ? 'playing' : 'paused');
    playText.textContent = playing ? S.btn_pause : S.btn_play;
    if (!playing) { clearSpeaking(); }
  }

  function clearSpeaking() {
    article.querySelectorAll('.seg.is-speaking').forEach(function (seg) { seg.classList.remove('is-speaking'); });
  }

  function select(index, options) {
    options = options || {};
    var stop = stops[index];
    state.current = index;
    state.heard = false;
    layers.forEach(function (layer) { layer.element.classList.toggle('is-current', layer === stop.layer); });
    stops.forEach(function (other) { other.element.classList.toggle('is-current', other === stop); });
    setOpen(stop.layer, true);
    var position = stop.heading && stop.heading.querySelector('.stop-pos');
    statusLine.textContent = stop.layer.element.getAttribute('data-status') +
      (position ? ' · ' + position.textContent.trim() : '');
    // the bar shows how far along a layer with several parts the listener is
    progressBar.parentNode.hidden = stop.layer.stops.length < 2;
    progressBar.style.width = Math.round((stop.inLayer + 1) / stop.layer.stops.length * 100) + '%';
    viewer.show(stop);
    setScrollPadding();
    if (options.scroll !== false) {
      (stop.heading || stop.layer.heading).scrollIntoView({ block: 'start', behavior: reducedMotion ? 'auto' : 'smooth' });
    }
  }

  // With the built-in voice off, move focus instead, so a screen reader announces the new part.
  function focusCurrent() {
    var stop = stops[state.current];
    (stop.heading || stop.layer.button).focus({ preventScroll: true });
  }

  function itemsFor(stop) {
    var items = [];
    if (stop.inLayer === 0) {
      items.push({ parts: plain(stop.layer.element.getAttribute('data-announce')) });
    }
    if (stop.heading) {
      var position = stop.heading.querySelector('.stop-pos');
      var parts = position ? plain(position.textContent.trim() + '.') : [];
      items.push({ cue: 'stop', parts: parts.concat(partsOf(stop.heading.querySelector('.stop-label'))) });
    }
    var last = null;
    var spoken = 0;
    stop.segments.forEach(function (seg) {
      if (prefs.values.verifiedOnly && seg.status !== 'verified') { return; }
      if (seg.status !== last) {
        // say which kind of statement follows, every time the kind changes
        items.push({ cue: seg.status, pitch: PITCH[seg.status], parts: plain(S['say_' + seg.status]) });
      }
      items.push({
        pitch: PITCH[seg.status],
        parts: partsOf(seg.text),
        onstart: function () {
          clearSpeaking();
          seg.element.classList.add('is-speaking');
          seg.element.scrollIntoView({ block: 'nearest', behavior: reducedMotion ? 'auto' : 'smooth' });
        }
      });
      last = seg.status;
      spoken += 1;
    });
    if (!spoken) { items.push({ parts: plain(S.say_none_verified) }); }
    return items;
  }

  function speechFailed() {
    setPlaying(false);
    notice.textContent = S.no_speech;
    notice.hidden = false;
    setScrollPadding();
  }

  function speakCurrent() {
    setPlaying(true);
    Speech.say(itemsFor(stops[state.current]), stopFinished, speechFailed);
  }

  function sayEnding(layer) {
    setPlaying(true);
    Speech.say([{ cue: 'end', parts: plain(layer.element.getAttribute('data-ending')) }], function () {
      setPlaying(false);
    }, speechFailed);
  }

  function stopFinished() {
    var stop = stops[state.current];
    var next = stops[state.current + 1];
    clearSpeaking();
    state.heard = true;
    if (next && next.layer === stop.layer) {
      if (prefs.values.auto) {
        select(next.index);
        speakCurrent();
      } else {
        setPlaying(false);          // the listener decides when to move on
      }
      return;
    }
    // End of a layer: say what lies deeper, then wait. Depth is the listener's choice.
    sayEnding(stop.layer);
  }

  function move(step) {
    var target = state.current + step;
    Speech.unlock();
    if (target < 0) { target = 0; }
    if (target >= stops.length) {
      if (voiceOn()) { sayEnding(stops[state.current].layer); }
      return;
    }
    select(target);
    if (voiceOn()) { speakCurrent(); } else { focusCurrent(); }
  }

  playButton.addEventListener('click', function () {
    if (state.playing) {
      Speech.stop();
      setPlaying(false);
      return;
    }
    Speech.unlock();
    if (state.heard && stops[state.current + 1]) { select(state.current + 1); }
    speakCurrent();
  });
  document.getElementById('btn-next').addEventListener('click', function () { move(1); });
  document.getElementById('btn-prev').addEventListener('click', function () { move(-1); });

  document.addEventListener('kanjian:prefs', function () {
    refreshEmptyNotes();
    if (!voiceOn()) {
      Speech.stop();
      setPlaying(false);
      statusLine.textContent = S.status_silent;
    } else if (state.playing) {
      speakCurrent();               // pick up the new speed or filter straight away
    }
    setScrollPadding();
  });

  // --- start
  player.hidden = false;
  if (!Speech.supported) {
    root.setAttribute('data-voice', 'off');
    notice.textContent = S.no_speech;
    notice.hidden = false;
  }
  setPlaying(false);
  refreshEmptyNotes();
  select(0, { scroll: false });
  statusLine.textContent = voiceOn() ? S.status_ready : S.status_silent;
  setScrollPadding();
  root.setAttribute('data-player', 'ready');
})();
