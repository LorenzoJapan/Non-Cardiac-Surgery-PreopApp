# Preop Clearance

**Developed by MDGadgetz LLC**

A single‑file, clinician‑facing web app that implements the stepwise decision algorithm
(**Figure 1**) of the 2026 AHA/ACC guideline for **perioperative cardiovascular management of
non‑cardiac surgery**. It walks through a preoperative cardiac assessment one question at a
time and returns a guideline‑referenced recommendation.

> ⚠️ **Decision support, not a directive.** Not a validated medical device; does not replace
> clinical judgment. See the disclaimer below.

## Run it

The entire app is `index.html` — no build step and no dependencies.

- **Locally:** open `index.html` in any modern browser.
- **On an iPhone:** open the hosted URL (below) in Safari → **Share → Add to Home Screen** for a
  full‑screen, native‑feeling install.

## Host it (GitHub Pages)

Because the app lives at `index.html`, GitHub serves it directly — no workflow needed:

1. Push this repo to GitHub.
2. **Settings → Pages → Source: Deploy from a branch → `main` / root**.
3. Your app is live at `https://OWNER.github.io/REPO/`.

Hosting over HTTPS also makes the in‑app **Copy Preop Clearance Summary** clipboard action work
reliably (browsers restrict clipboard access outside a secure context). *Enabling Pages makes the
app publicly accessible; the in‑app disclaimer applies.*

## What it does

Eight‑step assessment matching guideline Figure 1: cardiovascular risk factors/disease/symptoms →
surgical urgency → acute cardiac condition → risk modifiers → RCRI‑gated MACE risk → DASI‑gated
functional capacity → will further testing impact care → biomarkers. When prior stents/CABG are ticked
at the risk‑modifier step, a stent‑timing panel (guideline §7.5) asks procedure (DES, BMS, balloon only,
CABG only), DES indication (ACS or stable CAD), time since PCI, and whether surgery requires stopping ≥1
antiplatelet agent, and shows the matching timing guidance (e.g., DES for ACS: ideally delay elective NCS
≥12 months, COR 1; any stent ≤30 days: COR 3: Harm). The stent flag appears in the result and copied
summary but does not change the Figure 1 recommendation. Built‑in RCRI, DASI, and FRAIL calculators; a one‑tap chart‑ready summary; an
About tab (scope, limits, privacy, medication timing, comorbidity notes, references); dark mode; larger‑text
toggle; WCAG‑AA contrast.

## Validation

The `validation/` folder holds a black‑box test suite. `oracle.py` encodes Figure 1 and the §7.5 stent rules
from the guideline text (not from the app's code); `run_app.js` drives `index.html` through its UI like a
clinician; `compare.py` scores the app against the oracle.

| Set | Patients | Source |
|---|---|---|
| Original stratified | 200 (P001–P200) | `generate_cohort.py` — every Figure 1 branch plus boundary cases |
| Random | 200 (R001–R200) | `generate_cohort_random.py` — randomly drawn demographics and history (seed 20261012) |
| Stent‑focused | 40 (S001–S040) | `generate_cohort_stent.py` — random demographics, each assigned a §7.5 scenario at every cut‑off |
| **Combined** | **440** | `cohort_440.json` |

Current result (combined 440): Figure 1 recommendation concordance 440/440; stent‑timing flag 52/52;
no secondary check failures (content/COR labels, calculators, chart note, Reset vs fresh page).

```bash
cd validation
npm i jsdom
# original 200 (default file names)
python3 generate_cohort.py && python3 oracle.py && node run_app.js && python3 compare.py
# combined 440
python3 generate_cohort_random.py && python3 generate_cohort_stent.py
python3 -c "import json;a=sum((json.load(open(f)) for f in ['cohort_200.json','cohort_random_200.json','cohort_stent_40.json']),[]);json.dump(a,open('cohort_440.json','w'),indent=1)"
python3 oracle.py cohort_440.json expected_440.json
COHORT_JSON=$PWD/cohort_440.json OUT_JSON=$PWD/app_results_440.json node run_app.js
COHORT_JSON=cohort_440.json EXPECTED_JSON=expected_440.json APP_JSON=app_results_440.json OUT_CSV=results_440.csv python3 compare.py
```

## Source

Thompson A, Fleischmann KE, Smilowitz NR, et al. 2026 AHA/ACC/ACS/ASNC/HRS/SCA/SCCT/SCMR/SVM
Guideline for Perioperative Cardiovascular Management for Noncardiac Surgery. *J Am Coll Cardiol.*
2026;88(13):1543-1643. doi:[10.1016/j.jacc.2026.06.017](https://doi.org/10.1016/j.jacc.2026.06.017)

The 2026 edition is a surveillance reaffirmation of the 2024 guideline
(doi:[10.1016/j.jacc.2024.06.013](https://doi.org/10.1016/j.jacc.2024.06.013)); its
recommendations, figures, and tables are unchanged.

RCRI criteria: Lee TH, Marcantonio ER, Mangione CM, et al. Derivation and prospective validation of a
simple index for prediction of cardiac risk of major noncardiac surgery. *Circulation.* 1999;100(10):1043-9.
doi:[10.1161/01.CIR.100.10.1043](https://doi.org/10.1161/01.CIR.100.10.1043) (criteria as worded in guideline Table 4)

RCRI risk estimates: Duceppe E, Parlow J, MacDonald P, et al. Canadian Cardiovascular Society guidelines on
perioperative cardiac risk assessment and management for patients who undergo noncardiac surgery.
*Can J Cardiol.* 2017;33(1):17-32. doi:[10.1016/j.cjca.2016.09.008](https://doi.org/10.1016/j.cjca.2016.09.008)

## Disclaimer

Clinical **decision support** for informational/educational use only. Not a validated or
regulatory‑cleared medical device; has not been prospectively validated in patients; must not be
the sole basis for any clinical decision. No warranty; no liability. The responsible clinician
retains full judgment over patient care.
