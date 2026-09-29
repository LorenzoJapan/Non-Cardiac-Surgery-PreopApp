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
functional capacity → will further testing impact care → biomarkers. Built‑in RCRI, DASI, and FRAIL calculators; a one‑tap chart‑ready summary; an
About tab (scope, limits, privacy, medication timing, comorbidity notes, references); dark mode; larger‑text
toggle; WCAG‑AA contrast.

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
