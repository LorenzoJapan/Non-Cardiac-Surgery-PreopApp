/* Drives ../index.html through its UI for every patient in cohort_200.json.
 *
 * Acts like a clinician reading the screen: answers are decided from the app's OWN on-screen
 * labels/hints (thresholds, lists) applied to the raw patient facts, never from the app's code
 * or from the oracle. RCRI, DASI and FRAIL are entered through the app's calculators.
 *
 * Mode "reset": one page, the Reset button between patients (real-world use).
 * Mode "fresh": a new page per patient (detects state leaking between patients).
 *
 * Usage:  npm i jsdom && node run_app.js   ->  app_results_200.json
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(process.env.APP_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');
const OUT = process.env.OUT_JSON || path.join(__dirname, 'app_results_200.json');
const cohort = JSON.parse(fs.readFileSync(path.join(__dirname, 'cohort_200.json'), 'utf8'));

function makePage() {
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously', pretendToBeVisual: true,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {} });
      Object.defineProperty(w.navigator, 'clipboard', {
        value: { writeText: (t) => { w.__copied = t; return Promise.resolve(); } }
      });
    }
  });
  return dom.window;
}

const txt = (el) => (el ? el.textContent.replace(/\s+/g, ' ').trim() : '');
const click = (el) => { if (!el) throw new Error('missing element'); el.click(); };
const low = (s) => s.toLowerCase();

function buttonByLabel(w, label) {
  const b = [...w.document.querySelectorAll('.row.active .seg button')]
    .find((x) => txt(x.querySelector('span')) === label);
  if (!b) throw new Error(`no button "${label}"`);
  return b;
}

/* ---------- clinician interpretation of each on-screen question ---------- */

function cvRiskAnswer(w, p) {
  const hint = low(txt(w.document.querySelector('.row.active .rhint')));
  const rf = p.risk_factors, yes = [];
  if (/htn|hypertension/.test(hint) && rf.hypertension) yes.push('HTN');
  if (/smok/.test(hint) && rf.smoking) yes.push('smoking');
  if (/cholesterol|lipid/.test(hint) && rf.hyperlipidemia) yes.push('cholesterol');
  if (/diabetes/.test(hint) && rf.diabetes) yes.push('diabetes');
  if (/obes/.test(hint) && rf.bmi >= 30) yes.push('obesity');
  if (/family history/.test(hint) && rf.family_history_premature_cad) yes.push('FHx');
  const wm = hint.match(/women\s*>\s*(\d+)/), mm = hint.match(/men\s*>\s*(\d+)/g);
  const menT = mm ? +mm.map((s) => s.match(/(\d+)/)[1]).pop() : null;
  if (wm && p.sex === 'F' && p.age > +wm[1]) yes.push('age');
  if (menT && p.sex === 'M' && p.age > menT) yes.push('age');
  const title = low(txt(w.document.querySelector('.row.active .rtitle')));
  const h = p.history, a = p.acute;
  const disease = h.ischemic_heart_disease || h.prior_pci_or_cabg || h.heart_failure || h.stroke_or_tia_months_ago !== null ||
    h.cied || h.valve_disease || h.pulmonary_hypertension || h.congenital_heart_disease || h.atrial_fibrillation ||
    h.peripheral_artery_disease || a.acs || a.decompensated_hf || a.unstable_arrhythmia;
  if (/disease/.test(title) && disease) yes.push('disease');
  if (/symptom/.test(title) && p.cv_symptoms.length) yes.push('symptoms');
  return yes.length ? 'Yes' : 'No';
}

function urgencyButton(w, p) {
  const btns = [...w.document.querySelectorAll('.row.active .seg button')];
  const hrs = p.surgery.time_to_surgery_hours;
  for (const b of btns) {
    const tl = txt(b.querySelector('.tl'));
    if (hrs !== null) {
      let m;
      if ((m = tl.match(/^<\s*([\d.]+)h$/)) && hrs < +m[1]) return b;
      if ((m = tl.match(/^([\d.]+)\s*[–-]\s*([\d.]+)h$/)) && hrs >= +m[1] && hrs < +m[2]) return b;
    } else {
      if (p.surgery.can_be_delayed === 'up to 3 months' && /3mo/.test(tl)) return b;
      if (p.surgery.can_be_delayed === 'indefinitely' && /planned/.test(tl)) return b;
    }
  }
  throw new Error('no urgency match for ' + JSON.stringify(p.surgery));
}

function acuteMatches(label, p) {
  const l = low(label), a = p.acute, v = p.history.valve_disease;
  if (/coronary syndrome|acs/.test(l)) return !!a.acs;
  if (/heart failure/.test(l)) return /decompensated/.test(l) ? a.decompensated_hf : (a.decompensated_hf || !!p.history.heart_failure);
  if (/arrhythmia/.test(l)) return !!a.unstable_arrhythmia;
  if (/valv|stenosis|\bas\b/.test(l)) return !!(v && v.severity === 'severe' && v.symptomatic);
  throw new Error('unrecognized acute item: ' + label);
}

function recentStrokeMonths(w) {
  // The app's comorbidity card defines what "recent" means (e.g. "Delay elective surgery >= 3 months")
  const card = [...w.document.querySelectorAll('#v-ref .refcard')].find((c) => /stroke/i.test(txt(c)));
  const m = card && txt(card).match(/(\d+)\s*months?/);
  return m ? +m[1] : 3;
}

function modifierMatches(label, p, ctx) {
  const l = low(label), h = p.history;
  if (/valv/.test(l)) return !!(h.valve_disease && h.valve_disease.severity === 'severe');
  if (/pulmonary hypertension/.test(l)) return (/severe/.test(l) ? h.pulmonary_hypertension === 'severe' : !!h.pulmonary_hypertension);
  if (/congenital/.test(l)) return !!(h.congenital_heart_disease && h.congenital_heart_disease.complexity !== 'simple');
  if (/stent|cabg/.test(l)) return !!h.prior_pci_or_cabg;
  if (/stroke/.test(l)) { const m = l.match(/<\s*(\d+)\s*months?/); const cut = m ? +m[1] : ctx.recentStroke;
    return h.stroke_or_tia_months_ago !== null && h.stroke_or_tia_months_ago < cut; }
  if (/cied|pacemaker|icd/.test(l)) return !!h.cied;
  if (/frail/.test(l)) return ctx.frailCategory === 'FRAIL';
  throw new Error('unrecognized modifier: ' + label);
}

function rcriItemMatches(label, p) {
  const l = low(label), h = p.history;
  if (/high-risk surgery/.test(l)) {
    const inside = (l.match(/\(([^)]*)\)/) || [, ''])[1];
    const cats = new Set();
    inside.split(/,|\bor\b/).map((s) => s.trim()).forEach((s) => {
      if (s === 'intraperitoneal') cats.add('intraperitoneal');
      else if (s === 'intrathoracic') cats.add('intrathoracic');
      else if (s === 'suprainguinal vascular') cats.add('suprainguinal_vascular');
      else if (s === 'vascular') { cats.add('suprainguinal_vascular'); cats.add('infrainguinal_vascular'); }
    });
    return cats.has(p.surgery.category);
  }
  if (/ischemic heart/.test(l)) return !!(h.ischemic_heart_disease || h.prior_pci_or_cabg);
  if (/heart failure/.test(l)) return !!h.heart_failure;
  if (/cerebrovascular|stroke/.test(l)) return h.stroke_or_tia_months_ago !== null;
  if (/insulin/.test(l)) return p.risk_factors.diabetes === 'insulin';
  if (/creatinine/.test(l)) {
    const m = label.match(/(>=|≥|>)\s*([\d.]+)/);
    return m[1] === '>' ? p.creatinine_mg_dl > +m[2] : p.creatinine_mg_dl >= +m[2];
  }
  throw new Error('unrecognized RCRI item: ' + label);
}

const DASI_KEYWORDS = [
  ['self_care', /\beat\b|\bdress\b|\bbathe\b/], ['walk_indoors', /\bindoors\b/], ['walk_1_2_blocks', /\bblocks?\b/],
  ['climb_stairs_or_hill', /\bstairs\b|\bhill\b/], ['run_short_distance', /\brun\b/], ['light_housework', /\blight\b/],
  ['moderate_housework', /\bmoderate work\b|\bvacuum\b/], ['heavy_housework', /\bheavy\b/], ['yardwork', /\byardwork\b/],
  ['sexual_relations', /\bsexual\b/], ['moderate_recreation', /\bmoderate recreation\b|\bgolf\b/], ['strenuous_sports', /\bstrenuous\b/]];
function dasiUniqueCheck(labels) {  // guard against keyword collisions: each app item must map to exactly one activity
  labels.forEach((l) => { const n = DASI_KEYWORDS.filter(([, re]) => re.test(l.toLowerCase())).length;
    if (n !== 1) throw new Error(`DASI label "${l}" matched ${n} activities`); });
}
function dasiItemKey(label) {
  const l = low(label);
  const hit = DASI_KEYWORDS.find(([, re]) => re.test(l));
  if (!hit) throw new Error('unrecognized DASI item: ' + label);
  return hit[0];
}

const FRAIL_KEYWORDS = [['fatigue', /fatigue/], ['resistance', /resistance/], ['ambulation', /ambulation/],
  ['illnesses_gt_5', /illness/], ['weight_loss_ge_5pct', /weight/]];

function biomarkerAnswer(w, p) {
  const hint = txt(w.document.querySelector('.row.active .rhint'));
  const b = p.biomarkers;
  const cmp = (v, op, t) => (op === '>' ? v > t : v >= t);
  let m, abn = false;
  if (b.bnp_ng_l != null && (m = hint.match(/(?<!-)BNP\s*(>=|≥|>)\s*(\d+)/))) abn = abn || cmp(b.bnp_ng_l, m[1], +m[2]);
  if (b.nt_probnp_ng_l != null && (m = hint.match(/NT-proBNP\s*(>=|≥|>)\s*(\d+)/))) abn = abn || cmp(b.nt_probnp_ng_l, m[1], +m[2]);
  if (b.troponin_ng_l != null && /troponin\s*>\s*URL/i.test(hint)) abn = abn || b.troponin_ng_l > b.troponin_url_ng_l;
  return abn ? 'Elevated' : 'Normal';
}

/* ---------- sheet (calculator) helpers ---------- */
function tickSheet(w, matcher) {  // set each item to its desired state (calculators remember prior ticks)
  const items = [...w.document.querySelectorAll('#sheet-list .chk')];
  items.forEach((it) => { if (!!matcher(txt(it.querySelector('.lbl'))) !== it.classList.contains('on')) click(it); });
}
function sheetOpen(w) { return w.document.getElementById('sheet').classList.contains('open'); }
function sheetButton(w) { return w.document.querySelector('#sheet-foot button'); }

/* ---------- one patient ---------- */
function runPatient(w, p) {
  const d = w.document, rec = { id: p.id, answers: {}, errors: [] };
  // FRAIL via Calculators tab first (clinician screens frailty before the modifier step)
  click(d.querySelector('.tab[data-tab="calc"]'));
  const frailBtn = [...d.querySelectorAll('#v-calc button')].find((b) => /FRAIL/i.test(txt(b)));
  click(frailBtn);
  tickSheet(w, (lbl) => FRAIL_KEYWORDS.some(([k, re]) => re.test(low(lbl)) && p.frail_items[k]));
  rec.frail_score = +txt(d.querySelector('#sheet-foot .num'));
  rec.frail_category = txt(d.querySelector('#sheet-foot .flag'));
  click(sheetButton(w));
  click(d.querySelector('.tab[data-tab="assess"]'));
  const ctx = { frailCategory: rec.frail_category, recentStroke: recentStrokeMonths(w) };

  click([...d.querySelectorAll('#rows button')].find((b) => /Begin/.test(txt(b))));
  for (let guard = 0; guard < 20; guard++) {
    const res = d.getElementById('result');
    if (!res.classList.contains('pending')) break;
    const row = d.querySelector('.row.active');
    if (!row) throw new Error('no active row and no result');
    const title = txt(row.querySelector('.rtitle'));
    rec.progress_label = txt(d.querySelector('#progress .plabel'));
    if (/CV risk factors/.test(title)) { const a = cvRiskAnswer(w, p); rec.answers.cvrisk = a; click(buttonByLabel(w, a)); }
    else if (/Surgical urgency/.test(title)) { const b = urgencyButton(w, p); rec.answers.urgency = txt(b.querySelector('span')); click(b); }
    else if (/Acute cardiac/.test(title)) {
      const picked = [];
      [...row.querySelectorAll('.qchk')].forEach((q) => { const l = txt(q.querySelector('.lbl')); if (acuteMatches(l, p)) { picked.push(l); click(q); } });
      rec.answers.acute = picked; click(row.querySelector('.qcontinue'));
    } else if (/Risk modifiers/.test(title)) {
      const frailQ = [...row.querySelectorAll('.qchk')].find((q) => /frail/i.test(txt(q.querySelector('.lbl'))));
      const frailBtn = frailQ && frailQ.querySelector('button');
      if (frailBtn) {                       // in-assessment FRAIL calculator
        click(frailBtn);
        tickSheet(w, (lbl) => FRAIL_KEYWORDS.some(([k, re]) => re.test(low(lbl)) && p.frail_items[k]));
        rec.frail_inflow = `${txt(d.querySelector('#sheet-foot .num'))} ${txt(d.querySelector('#sheet-foot .flag'))}`;
        click(sheetButton(w));
      }
      const picked = [];
      const cur = d.querySelector('.row.active');   // re-query: applying FRAIL re-renders the step
      [...cur.querySelectorAll('.qchk')].forEach((q) => {
        const l = txt(q.querySelector('.lbl'));
        if (frailBtn && /frail/i.test(l)) { if (q.classList.contains('on')) picked.push(l); return; }  // set by the app
        if (modifierMatches(l, p, ctx)) { picked.push(l); click(q); }
      });
      rec.answers.modifiers = picked; click(cur.querySelector('.qcontinue'));
    } else if (/Risk of MACE/.test(title)) {
      if (!sheetOpen(w)) click(row.querySelector('.rmini'));
      tickSheet(w, (lbl) => rcriItemMatches(lbl, p));
      rec.rcri_score = +txt(d.querySelector('#sheet-foot .num'));
      rec.rcri_flag = txt(d.querySelector('#sheet-foot .flag'));
      click(sheetButton(w));
    } else if (/Functional capacity/.test(title)) {
      rec.fc_hint = txt(row.querySelector('.rhint'));
      const unk = [...row.querySelectorAll('.seg button')].find((b) => txt(b.querySelector('span')) === 'Unknown');
      if (!p.functional_capacity_assessable && unk) { rec.answers.func = 'Unknown'; click(unk); continue; }
      click(row.querySelector('.rmini'));
      dasiUniqueCheck([...d.querySelectorAll('#sheet-list .chk .lbl')].map(txt));
      tickSheet(w, (lbl) => p.dasi_activities_can_do.includes(dasiItemKey(lbl)));  // unknown FC -> nothing ticked
      rec.dasi_score = +txt(d.querySelector('#sheet-foot .num'));
      rec.dasi_flag = txt(d.querySelector('#sheet-foot .flag'));
      click(sheetButton(w));
    } else if (/further testing|cardiac testing change/i.test(title)) {
      const a = p.further_testing_would_change_management ? 'Yes' : 'No'; rec.answers.test = a; click(buttonByLabel(w, a));
    } else if (/Biomarkers/.test(title)) { const a = biomarkerAnswer(w, p); rec.answers.biomarkers = a; click(buttonByLabel(w, a)); }
    else throw new Error('unrecognized step: ' + title);
  }
  const res = d.getElementById('result');
  if (res.classList.contains('pending')) throw new Error('no recommendation reached');
  rec.banner_class = res.className;
  rec.title = txt(d.getElementById('rtitle'));
  rec.text = txt(d.getElementById('rtext'));
  rec.label = txt(d.getElementById('rnote'));
  w.__copied = null; click(d.getElementById('copyBtn')); rec.copied_note = w.__copied;
  rec.internal_terminal = w.eval('evalFlow().terminal');  // cross-check only; not used for scoring
  rec.outcome = classifyBanner(rec);
  return rec;
}

/* Black-box classification from what the clinician sees */
function classifyBanner(r) {
  const t = low(r.title), x = low(r.text);
  if (/no cardiovascular risk factors/.test(x)) return 'NO_RISK';
  if (/emergency/.test(x)) return 'EMERGENT';
  if (/hold on surgery/.test(t)) return 'ACUTE_DEFER';
  if (/predicted mace < 1%/.test(x)) return 'LOW';
  if (/≥ 4 mets/.test(x)) return 'ADEQ';
  if (/would not impact/.test(x)) return 'NO_IMPACT';
  if (/normal biomarkers/.test(t)) return 'BIOMARKER_OK';
  if (/abnormal biomarkers/.test(x)) return 'BIOMARKER_HIGH';
  return 'UNRECOGNIZED';
}

const out = { reset: [], fresh: [] };
let w = makePage();
for (const p of cohort) {
  click(w.document.querySelector('.appbar .reset'));
  try { out.reset.push(runPatient(w, p)); } catch (e) { out.reset.push({ id: p.id, outcome: 'ERROR', error: String(e) }); }
}
for (const p of cohort) {
  const fw = makePage();
  try { out.fresh.push(runPatient(fw, p)); } catch (e) { out.fresh.push({ id: p.id, outcome: 'ERROR', error: String(e) }); }
  fw.close();
}
fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log('reset-mode outcomes:', out.reset.map((r) => r.outcome).reduce((a, o) => ((a[o] = (a[o] || 0) + 1), a), {}));
