"""Generate N synthetic preoperative patients with RANDOMLY drawn features (no scenario templates).

Unlike generate_cohort.py (stratified by Figure 1 branch), every feature here is drawn independently
from plausible prevalences, with age/sex shaping risk factors, comorbidity and frailty. Patients with
prior PCI also get random stent details (type, indication, days since PCI, antiplatelet plan) so the
§7.5 stent-timing panel (option 3 preview) is exercised.

Records hold raw clinical facts only; the expected answer comes from oracle.py.

Usage:  python3 generate_cohort_random.py [seed] [n]   ->  cohort_random_<n>.json
"""
import json, random, sys

SEED = int(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else 20261012
N = int(sys.argv[2]) if __name__ == "__main__" and len(sys.argv) > 2 else 200
rng = random.Random(SEED)

SURGERY = {  # category: (procedures, relative frequency)
    "intraperitoneal": (["Laparoscopic cholecystectomy", "Open sigmoid colectomy", "Pancreaticoduodenectomy (Whipple)",
                         "Exploratory laparotomy", "Laparoscopic right hemicolectomy"], 18),
    "intrathoracic": (["VATS lobectomy", "Esophagectomy", "Thoracotomy with decortication"], 6),
    "suprainguinal_vascular": (["Open AAA repair", "Aortobifemoral bypass"], 4),
    "infrainguinal_vascular": (["Femoral-popliteal bypass", "Femoral-tibial bypass"], 4),
    "orthopedic": (["Total knee arthroplasty", "Total hip arthroplasty", "ORIF distal radius", "Hip fracture repair"], 22),
    "spine": (["Lumbar laminectomy", "Posterior lumbar fusion"], 8),
    "urologic": (["Transurethral resection of prostate", "Cystoscopy with stent"], 10),
    "endocrine": (["Total thyroidectomy", "Parathyroidectomy"], 5),
    "breast": (["Lumpectomy with sentinel node biopsy", "Simple mastectomy"], 8),
    "ophthalmologic": (["Cataract extraction"], 8),
    "extraperitoneal_hernia": (["Open inguinal hernia repair"], 7),
}
DASI_KEYS = ["self_care", "walk_indoors", "walk_1_2_blocks", "climb_stairs_or_hill", "run_short_distance",
             "light_housework", "moderate_housework", "heavy_housework", "yardwork", "sexual_relations",
             "moderate_recreation", "strenuous_sports"]
# probability a "fully able" patient can do each activity (harder items rarer)
DASI_BASE = dict(zip(DASI_KEYS, [.99, .98, .93, .85, .45, .95, .85, .5, .65, .7, .7, .3]))


def p(x):
    return rng.random() < x


def age_draw():
    # adult surgical population, skewed older
    return max(18, min(95, int(rng.gauss(62, 15))))


def patient(i):
    age, sex = age_draw(), rng.choice("MF")
    old = max(0.0, (age - 40) / 50)                       # 0 at 40, 1 at 90
    rf = {"hypertension": p(.15 + .5 * old), "smoking": p(.18), "hyperlipidemia": p(.12 + .4 * old),
          "diabetes": None, "bmi": round(min(55, max(16.5, rng.gauss(28.5, 6))), 1),
          "family_history_premature_cad": p(.07)}
    if p(.08 + .2 * old):
        rf["diabetes"] = rng.choices(["diet-controlled", "oral agents", "insulin"], [2, 5, 3])[0]

    h = {"ischemic_heart_disease": None, "prior_pci_or_cabg": None, "heart_failure": None,
         "stroke_or_tia_months_ago": None, "cied": None, "valve_disease": None,
         "pulmonary_hypertension": None, "congenital_heart_disease": None, "atrial_fibrillation": None,
         "peripheral_artery_disease": p(.03 + .1 * old), "pci": None}
    if p(.04 + .22 * old):
        h["ischemic_heart_disease"] = rng.choice(["prior MI", "stable angina on nitrates", "Q waves on ECG, remote MI"])
    if p(.03 + .14 * old):                                # revascularized: PCI (~80%) or CABG
        if p(.8):
            stent = rng.choices(["DES", "BMS", "balloon only"], [8, 1.5, .5])[0]
            ind = rng.choice(["ACS", "stable CAD"]) if stent == "DES" else None
            # spread across all timing windows, with extra weight near the 14 d/30 d/3/6/12 mo cut-offs
            days = rng.choice([rng.randint(1, 13), rng.randint(14, 30), rng.randint(31, 89), rng.randint(90, 179),
                               rng.randint(180, 364), rng.randint(365, 3650), rng.randint(365, 3650),
                               rng.choice([13, 14, 30, 31, 89, 90, 179, 180, 364, 365])])
            h["prior_pci_or_cabg"] = f"{stent}-PCI {days} days ago"
            h["pci"] = {"type": stent, "indication": ind, "days_since": days,
                        "antiplatelet_interruption": rng.choices(["yes", "no", "unknown"], [5, 3, 2])[0]}
        else:
            h["prior_pci_or_cabg"] = f"CABG {rng.randint(1, 15)} years ago"
            h["pci"] = {"type": "CABG", "indication": None, "days_since": None, "antiplatelet_interruption": None}
        h["ischemic_heart_disease"] = h["ischemic_heart_disease"] or "CAD s/p revascularization"
    if p(.02 + .12 * old):
        h["heart_failure"] = rng.choice(["compensated HFrEF on GDMT", "compensated HFpEF, euvolemic"])
    if p(.02 + .08 * old):
        h["stroke_or_tia_months_ago"] = rng.choice([1, 2, 3, 4, 6, 12, 24, 60])
    if p(.01 + .06 * old):
        h["cied"] = rng.choice(["dual-chamber pacemaker", "single-chamber pacemaker", "ICD"])
    if p(.02 + .1 * old):
        h["valve_disease"] = {"lesion": rng.choice(["aortic stenosis", "mitral regurgitation"]),
                              "severity": rng.choices(["mild", "moderate", "severe"], [4, 3, 2])[0], "symptomatic": p(.3)}
    if p(.03):
        h["pulmonary_hypertension"] = rng.choices(["mild", "moderate", "severe"], [4, 3, 1])[0]
    if p(.02):
        h["congenital_heart_disease"] = rng.choice([
            {"lesion": "repaired secundum ASD, no residua", "complexity": "simple"},
            {"lesion": "repaired tetralogy of Fallot", "complexity": "moderate"},
            {"lesion": "Fontan circulation", "complexity": "complex"}])
    if p(.02 + .12 * old):
        h["atrial_fibrillation"] = rng.choice(["paroxysmal AF, rate controlled", "persistent AF, rate controlled"])

    acute = {"acs": None, "decompensated_hf": False, "unstable_arrhythmia": None}
    if p(.03):
        acute["acs"] = rng.choice(["NSTEMI 4 days ago", "unstable angina this week", "STEMI 10 days ago, not revascularized"])
    if p(.025):
        acute["decompensated_hf"] = True
        h["heart_failure"] = h["heart_failure"] or "HFrEF, currently volume overloaded"
    if p(.02):
        acute["unstable_arrhythmia"] = rng.choice(["AF with RVR 150 bpm, hypotensive", "sustained VT", "symptomatic complete heart block"])

    symptoms = ["exertional chest pressure"] if p(.04) else []
    frail = {k: p(.04 + .35 * old ** 2) for k in ["fatigue", "resistance", "ambulation", "illnesses_gt_5", "weight_loss_ge_5pct"]}

    cat = rng.choices(list(SURGERY), [v[1] for v in SURGERY.values()])[0]
    u = rng.choices(["emergency", "urgent", "time-sensitive", "elective"], [8, 10, 22, 60])[0]
    hours = {"emergency": rng.choice([0.25, 0.5, 1, 1.5, 1.9]), "urgent": rng.choice([2, 2.5, 4, 8, 12, 20, 23.5])}.get(u)
    delay = "n/a" if hours is not None else ("up to 3 months" if u == "time-sensitive" else "indefinitely")

    # functional capacity: worse with age, frailty, HF
    capacity = max(0.0, 1 - .55 * old - .15 * sum(frail.values()) - (.25 if h["heart_failure"] else 0) + rng.gauss(0, .25))
    assessable = not p(.05)
    dasi = [k for k in DASI_KEYS if assessable and rng.random() < DASI_BASE[k] * min(1, capacity * 1.3)]

    bio = {"bnp_ng_l": None, "nt_probnp_ng_l": None, "troponin_ng_l": None, "troponin_url_ng_l": None}
    np_level = rng.lognormvariate(3.6 + 1.2 * old + (1 if h["heart_failure"] else 0), .9)
    if p(.5):
        bio["bnp_ng_l"] = int(np_level)
    else:
        bio["nt_probnp_ng_l"] = int(np_level * 3.5)
    if p(.35):
        bio["troponin_url_ng_l"] = 14
        bio["troponin_ng_l"] = int(rng.lognormvariate(1.8 + .6 * old, .6))

    return {
        "id": f"R{i:03d}", "age": age, "sex": sex, "risk_factors": rf, "cv_symptoms": symptoms, "history": h,
        "acute": acute, "creatinine_mg_dl": round(min(5.5, max(.5, rng.lognormvariate(0, .3) * (1 + .3 * old))), 1),
        "frail_items": frail,
        "surgery": {"procedure": rng.choice(SURGERY[cat][0]), "category": cat, "time_to_surgery_hours": hours,
                    "can_be_delayed": delay},
        "dasi_activities_can_do": dasi, "functional_capacity_assessable": assessable,
        "further_testing_would_change_management": p(.5), "biomarkers": bio, "edge_tags": [],
    }


if __name__ == "__main__":
    cohort = [patient(i + 1) for i in range(N)]
    out = f"cohort_random_{N}.json"
    json.dump(cohort, open(out, "w"), indent=1)
    print(f"wrote {N} patients to {out} (seed {SEED})")
