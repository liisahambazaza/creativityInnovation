/* Reads the visitor's saved settings and applies them before the page is drawn.
   Loaded without "defer" on purpose, so text size is right from the first paint. */
(function () {
  'use strict';

  var KEY = 'kanjian.prefs';
  var choices = {
    voice: ['on', 'off'],              // built-in voice, or silent for screen-reader users
    rate: ['normal', 'slow', 'fast'],
    text: ['standard', 'large', 'xlarge'],
    verifiedOnly: [false, true],       // skip everything that is not verified
    auto: [true, false]                // continue to the next part without waiting
  };

  var saved = {};
  try {
    saved = JSON.parse(window.localStorage.getItem(KEY) || '{}') || {};
  } catch (error) {
    saved = {};
  }

  var values = {};
  Object.keys(choices).forEach(function (name) {
    values[name] = choices[name].indexOf(saved[name]) >= 0 ? saved[name] : choices[name][0];
  });

  function apply() {
    var root = document.documentElement;
    root.setAttribute('data-voice', values.voice);
    root.setAttribute('data-text', values.text);
    if (values.verifiedOnly) {
      root.setAttribute('data-verified-only', '');
    } else {
      root.removeAttribute('data-verified-only');
    }
  }

  function save() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(values));
    } catch (error) {
      /* private browsing: the settings simply last for this page */
    }
  }

  window.KanjianPrefs = { values: values, choices: choices, apply: apply, save: save };
  apply();
})();
