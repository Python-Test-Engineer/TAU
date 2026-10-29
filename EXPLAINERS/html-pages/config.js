// OpenRouter configuration LOADER.
//
// This file is committed to git and contains NO secrets. The live API key and
// model are read at runtime from OPENROUTER.txt (which is git-ignored), then
// exposed as OPENROUTER_API_KEY / OPENROUTER_MODEL.
//
// IMPORTANT: the browser cannot read a local file from a file:// page, so the
// demos must be served over http(s) - e.g. VS Code "Live Server" (right-click
// the html page > "Open with Live Server"). Double-clicking the html file will
// NOT load the key.
//
// Usage from a page:  await window.openRouterReady;  then read the globals.

const OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions';

// Path to OPENROUTER.txt, relative to the HTML-PAGES/*.html pages.
const OPENROUTER_CONFIG_PATH = '../OPENROUTER.txt';

// Optional attribution headers recommended by OpenRouter (not required)
const OPENROUTER_HEADERS = {
   'HTTP-Referer': window.location.href,
   'X-Title': 'Brighton Web Dev Meetup'
};

// Populated from OPENROUTER.txt once it has loaded (see window.openRouterReady).
var OPENROUTER_API_KEY = '';
var OPENROUTER_MODEL = '';

// Parses the simple KEY=VALUE format of OPENROUTER.txt (quotes optional, # = comment).
function parseOpenRouterConfig(text) {
   const cfg = {};
   for (const raw of text.split(/\r?\n/)) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      const eq = line.indexOf('=');
      if (eq === -1) continue;
      const key = line.slice(0, eq).trim();
      let value = line.slice(eq + 1).trim();
      if (value.length >= 2 &&
         ((value.startsWith('"') && value.endsWith('"')) ||
          (value.startsWith("'") && value.endsWith("'")))) {
         value = value.slice(1, -1);
      }
      cfg[key] = value;
   }
   return cfg;
}

// Await this before using OPENROUTER_API_KEY / OPENROUTER_MODEL:
//     await window.openRouterReady;
window.openRouterReady = fetch(OPENROUTER_CONFIG_PATH)
   .then(response => {
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      return response.text();
   })
   .then(text => {
      const cfg = parseOpenRouterConfig(text);
      OPENROUTER_API_KEY = cfg.OPENROUTER_API_KEY || '';
      OPENROUTER_MODEL = cfg.MODEL || cfg.OPENROUTER_MODEL || '';

      if (!OPENROUTER_API_KEY) {
         console.warn('config.js: no OPENROUTER_API_KEY found in ' + OPENROUTER_CONFIG_PATH);
      }
      if (OPENROUTER_MODEL && !OPENROUTER_MODEL.includes('/')) {
         console.warn(`config.js: MODEL "${OPENROUTER_MODEL}" has no provider prefix; ` +
            'OpenRouter model ids look like "deepseek/deepseek-v4.1-flash"');
      }

      // Pre-fill the API key field so the demo works out of the box.
      const input = document.getElementById('apiKey');
      if (input && OPENROUTER_API_KEY) input.value = OPENROUTER_API_KEY;

      return { apiKey: OPENROUTER_API_KEY, model: OPENROUTER_MODEL };
   })
   .catch(error => {
      console.error(`config.js: could not load ${OPENROUTER_CONFIG_PATH} - ` +
         'are you serving this over http (e.g. Live Server) rather than opening the file directly?', error);
      window.openRouterConfigError = error.message;
      return { apiKey: '', model: '' };
   });
