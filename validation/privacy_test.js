/* Privacy check: the app must not collect, store, or transmit anything.
 *
 * Static:  Content-Security-Policy present and locked down; no free-text fields; no external scripts,
 *          stylesheets, fonts or images (only <a> links to guideline DOIs).
 * Runtime: completes a full assessment (FRAIL, stent panel, RCRI, DASI, copy summary, all tabs) with every
 *          network and storage API instrumented; fails if any is called or if the copied note contains a date.
 *
 * jsdom does not enforce CSP, so the runtime part catches code that *tries* to send or store data.
 * Usage:  node privacy_test.js   (requires jsdom)
 */
const fs = require('fs'), path = require('path'), { JSDOM } = require('jsdom');
const HTML = fs.readFileSync(process.env.APP_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');
let fail = 0; const check = (name, ok, extra) => { console.log((ok ? 'PASS ' : 'FAIL ') + name + (ok || !extra ? '' : ' :: ' + extra)); if (!ok) fail++; };

/* ---------- static ---------- */
const csp = (HTML.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)"/) || [])[1] || '';
const dir = Object.fromEntries(csp.split(';').map((d) => d.trim().split(/\s+/)).filter((d) => d[0]).map(([k, ...v]) => [k, v.join(' ')]));
check('CSP meta tag present', !!csp);
check("CSP default-src 'none'", dir['default-src'] === "'none'", dir['default-src']);
check("CSP connect-src 'none' (no fetch/XHR/beacon/WebSocket)", dir['connect-src'] === "'none'", dir['connect-src']);
check("CSP script-src allows no external origin", dir['script-src'] === "'unsafe-inline'", dir['script-src']);
check("CSP style-src allows no external origin", dir['style-src'] === "'unsafe-inline'", dir['style-src']);
check('CSP img-src data: only', dir['img-src'] === 'data:', dir['img-src']);
check("CSP form-action 'none'", dir['form-action'] === "'none'", dir['form-action']);
const freeText = HTML.match(/<(input|textarea|select)\b|contenteditable/gi) || [];
check('no free-text / form fields', freeText.length === 0, freeText.join(','));
const external = [...HTML.matchAll(/<(script|link|img|iframe|source|video|audio|object|embed)\b[^>]*\b(src|href)=["'](?!data:)[^"']+["']/gi)].map((m) => m[0].slice(0, 80));
check('no external scripts/stylesheets/images/frames', external.length === 0, external.join(' | '));
const anchors = [...HTML.matchAll(/<a\b[^>]*href=["']([^"']+)["']/gi)].map((m) => m[1]);
check('only outbound links are guideline DOIs', anchors.every((u) => /^https:\/\/doi\.org\//.test(u)), anchors.join(', '));

/* ---------- runtime ---------- */
const calls = [];
const w = new JSDOM(HTML, {
  runScripts: 'dangerously', pretendToBeVisual: true, url: 'https://example.github.io/preop/',
  beforeParse(w) {
    w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
    const trap = (name) => function () { calls.push(name); throw new Error(name + ' blocked by test'); };
    w.fetch = trap('fetch'); w.XMLHttpRequest = trap('XMLHttpRequest'); w.WebSocket = trap('WebSocket'); w.EventSource = trap('EventSource');
    Object.defineProperty(w.navigator, 'sendBeacon', { value: trap('sendBeacon') });
    Object.defineProperty(w.navigator, 'clipboard', { value: { writeText: (t) => { w.__copied = t; return Promise.resolve(); } } });
    for (const m of ['setItem', 'getItem', 'removeItem', 'clear', 'key']) {   // patch the prototype: own props on Storage become items
      const o = w.Storage.prototype[m];
      w.Storage.prototype[m] = function (...a) { calls.push('storage.' + m); return o.apply(this, a); };
    }
    Object.defineProperty(w.document, 'cookie', { get() { calls.push('cookie read'); return ''; }, set() { calls.push('cookie write'); } });
    if (w.indexedDB) w.indexedDB.open = trap('indexedDB.open');
  },
}).window;
const d = w.document, txt = (e) => e.textContent.replace(/\s+/g, ' ').trim();
const segBtn = (label) => [...d.querySelectorAll('.row.active .seg button')].find((b) => txt(b.querySelector('span')) === label).click();
const chip = (t) => [...d.querySelectorAll('#stentQ .schip')].find((c) => txt(c) === t).click();
const sheetTickAll = () => d.querySelectorAll('#sheet-list .chk').forEach((c) => c.click());

d.querySelector('.tab[data-tab="calc"]').click();
[...d.querySelectorAll('#v-calc button')].find((b) => /FRAIL/.test(txt(b))).click(); sheetTickAll(); d.querySelector('#sheet-foot button').click();
d.querySelector('.tab[data-tab="assess"]').click();
[...d.querySelectorAll('#rows button')].find((b) => /Begin/.test(txt(b))).click();
segBtn('Yes'); segBtn('Elective'); d.querySelector('.row.active .qcontinue').click();
[...d.querySelectorAll('.row.active .qchk')].find((q) => /stents/i.test(txt(q))).click();
['DES', 'ACS', '6 – < 12 mo', 'Yes'].forEach(chip);
d.querySelector('.row.active .qcontinue').click();                       // opens RCRI
sheetTickAll(); d.querySelector('#sheet-foot button').click();
d.querySelector('.row.active .rmini').click(); d.querySelector('#sheet-foot button').click();   // DASI, nothing ticked -> poor
segBtn('Yes'); segBtn('Elevated');
const reached = !d.getElementById('result').classList.contains('pending');
d.getElementById('copyBtn').click();
d.querySelector('.tab[data-tab="ref"]').click(); d.querySelector('.appbar .reset').click();

check('full assessment reached a recommendation', reached);
check('no network or storage API was called', calls.length === 0, calls.join(', '));
check('localStorage and sessionStorage empty', w.localStorage.length === 0 && w.sessionStorage.length === 0);
const note = w.__copied || '';
check('summary was copied', /^PREOPERATIVE CARDIAC CLEARANCE/.test(note));
const datey = note.match(/\b\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4}\b|\b(19|20)\d{2}-\d{2}-\d{2}\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2}\b/gi) || [];
check('copied summary contains no calendar dates', datey.length === 0, datey.join(', '));

console.log(fail ? `${fail} FAILED` : 'all privacy checks pass'); process.exit(fail ? 1 : 0);
