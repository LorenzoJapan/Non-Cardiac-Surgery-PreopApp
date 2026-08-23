# Preop Clearance

**Developed by MDGadgetz LLC**

A single‑file, clinician‑facing web app that implements the stepwise decision algorithm
(**Figure 1**) of the 2024 AHA/ACC guideline for **perioperative cardiovascular management of
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

Seven‑step assessment matching guideline Figure 1: surgical urgency → acute cardiac condition →
risk modifiers → RCRI‑gated MACE risk → DASI‑gated functional capacity → biomarkers →
testing decision. Built‑in RCRI, DASI, and FRAIL calculators; a one‑tap chart‑ready summary; a
reference tab (medication timing, comorbidity cards, source citation); dark mode; larger‑text
toggle; WCAG‑AA contrast.

## Source

Thompson A, Fleischmann KE, Smilowitz NR, et al. 2024 AHA/ACC/ACS/ASNC/HRS/SCA/SCCT/SCMR/SVM
Guideline for Perioperative Cardiovascular Management for Noncardiac Surgery. *J Am Coll Cardiol.*
2024. doi:[10.1016/j.jacc.2024.06.013](https://doi.org/10.1016/j.jacc.2024.06.013)

## Disclaimer

Clinical **decision support** for informational/educational use only. Not a validated or
regulatory‑cleared medical device; has not been prospectively validated in patients; must not be
the sole basis for any clinical decision. No warranty; no liability. The responsible clinician
retains full judgment over patient care.
