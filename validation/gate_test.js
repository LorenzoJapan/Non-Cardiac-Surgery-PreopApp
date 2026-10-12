/* UI check: step 4 cannot be completed while "Prior cardiac stents / CABG" is ticked and the stent questions
 * are incomplete.  Usage:  node gate_test.js  (requires jsdom) */
const fs = require('fs'), path = require('path'), { JSDOM } = require('jsdom');
const HTML = fs.readFileSync(process.env.APP_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');
const w = new JSDOM(HTML, { runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(w) { w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} }); } }).window;
const d = w.document, txt = (e) => e.textContent.replace(/\s+/g, ' ').trim();
const btn = () => d.querySelector('.row.active .qcontinue');
const chip = (t) => [...d.querySelectorAll('#stentQ .schip')].find((c) => txt(c) === t).click();
const step = () => w.eval('evalFlow().activeIdx');
let fail = 0; const check = (name, ok) => { console.log((ok ? 'PASS ' : 'FAIL ') + name); if (!ok) fail++; };

[...d.querySelectorAll('#rows button')].find((b) => /Begin/.test(txt(b))).click();
[...d.querySelectorAll('.row.active .seg button')].find((b) => txt(b.querySelector('span')) === 'Yes').click();
[...d.querySelectorAll('.row.active .seg button')].find((b) => txt(b.querySelector('span')) === 'Elective').click();
btn().click();                                                    // acute: none
check('at step 4', step() === 3);
check('no modifiers: continue enabled', !btn().disabled);
const stentBox = [...d.querySelectorAll('.row.active .qchk')].find((q) => /stents/i.test(txt(q)));
stentBox.click();
check('stent ticked, unanswered: continue disabled', btn().disabled && /stent questions/.test(txt(btn())));
w.eval("confirmCond('modifiers')"); check('forced confirm does not advance', step() === 3);
chip('DES'); check('procedure only: still disabled', btn().disabled);
chip('ACS'); chip('14–30 d'); check('no antiplatelet answer: still disabled', btn().disabled);
chip('Yes'); check('all answered: enabled', !btn().disabled && /present/.test(txt(btn())));
chip('BMS'); check('switched to BMS (time + antiplatelet kept): enabled, BMS ≤30 d = Defer', !btn().disabled && d.querySelector('.stentflag').classList.contains('harm'));
chip('Balloon only'); chip('DES'); check('switched back to DES: indication cleared, disabled', btn().disabled);
chip('ACS');
chip('CABG only'); check('CABG only: enabled', !btn().disabled);
stentBox.click(); check('stent unticked: enabled', !btn().disabled);
stentBox.click(); chip('DES'); chip('ACS'); chip('14–30 d'); chip('Yes');
btn().click(); check('completed stent questions: advances', step() > 3);
d.querySelector('.appbar .reset').click();
check('Reset clears stent answers', w.eval('stentD.type===null && stentD.stop===null'));
console.log(fail ? `${fail} FAILED` : 'all gate checks pass'); process.exit(fail ? 1 : 0);
