"""Generate 200 synthetic preoperative patients as RAW clinical facts.

Records contain no expected outcome and no app inputs: only what a clinician
would know (demographics, history, labs, surgery, activities the patient can do).
Coverage is stratified by scenario template plus explicit boundary/edge cases,
but the expected answer is computed separately by oracle.py.

Usage:  python3 generate_cohort.py   ->  cohort_200.json
"""
import json, random
from itertools import combinations

rng = random.Random(2026)

SURGERY = {
    "intraperitoneal": ["Laparoscopic cholecystectomy", "Open sigmoid colectomy", "Pancreaticoduodenectomy (Whipple)",
                        "Exploratory laparotomy", "Laparoscopic right hemicolectomy"],
    "intrathoracic": ["VATS lobectomy", "Esophagectomy", "Thoracotomy with decortication"],
    "suprainguinal_vascular": ["Open AAA repair", "Aortobifemoral bypass"],
    "infrainguinal_vascular": ["Femoral-popliteal bypass", "Femoral-tibial bypass"],
    "orthopedic": ["Total knee arthroplasty", "Total hip arthroplasty", "ORIF distal radius"],
    "spine": ["Lumbar laminectomy", "Posterior lumbar fusion"],
    "urologic": ["Transurethral resection of prostate", "Cystoscopy with stent"],
    "endocrine": ["Total thyroidectomy", "Parathyroidectomy"],
    "breast": ["Lumpectomy with sentinel node biopsy", "Simple mastectomy"],
    "ophthalmologic": ["Cataract extraction"],
    "extraperitoneal_hernia": ["Open inguinal hernia repair"],
}
HIGH_RISK_CATS = ["intraperitoneal", "intrathoracic", "suprainguinal_vascular"]
LOW_RISK_CATS = ["orthopedic", "spine", "urologic", "endocrine", "breast", "ophthalmologic", "extraperitoneal_hernia"]

DASI_KEYS = ["self_care", "walk_indoors", "walk_1_2_blocks", "climb_stairs_or_hill", "run_short_distance",
             "light_housework", "moderate_housework", "heavy_housework", "yardwork", "sexual_relations",
             "moderate_recreation", "strenuous_sports"]
# Typical ladder of activity (easier activities retained as capacity increases)
LADDER = [
    [],
    ["self_care", "walk_indoors"],
    ["self_care", "walk_indoors", "walk_1_2_blocks", "light_housework"],
    ["self_care", "walk_indoors", "walk_1_2_blocks", "light_housework", "moderate_housework"],
    ["self_care", "walk_indoors", "walk_1_2_blocks", "light_housework", "moderate_housework", "climb_stairs_or_hill"],
    ["self_care", "walk_indoors", "walk_1_2_blocks", "light_housework", "moderate_housework", "climb_stairs_or_hill",
     "yardwork", "sexual_relations"],
    ["self_care", "walk_indoors", "walk_1_2_blocks", "light_housework", "moderate_housework", "climb_stairs_or_hill",
     "yardwork", "sexual_relations", "moderate_recreation"],
    ["self_care", "walk_indoors", "walk_1_2_blocks", "light_housework", "moderate_housework", "climb_stairs_or_hill",
     "yardwork", "sexual_relations", "moderate_recreation", "heavy_housework"],
    DASI_KEYS[:],
]
POOR_LEVELS, ADEQ_LEVELS = [0, 1, 2, 3, 4, 5], [6, 7, 8]

# Exact-boundary DASI profiles, found by search over Table 5 weights (in hundredths)
_W = dict(zip(DASI_KEYS, [275, 175, 275, 550, 800, 270, 350, 800, 450, 525, 600, 750]))
def _subsets_summing(target):
    out = []
    for r in range(1, 13):
        for c in combinations(DASI_KEYS, r):
            if sum(_W[k] for k in c) == target:
                out.append(list(c))
    return out
EXACT_34 = _subsets_summing(3400)
JUST_ABOVE = next(s for t in range(3401, 3500) for s in _subsets_summing(t))

ID = [0]
def new_patient(**kw):
    ID[0] += 1
    p = {
        "id": f"P{ID[0]:03d}", "age": 60, "sex": "M",
        "risk_factors": {"hypertension": False, "smoking": False, "hyperlipidemia": False, "diabetes": None,
                         "bmi": 26.0, "family_history_premature_cad": False},
        "cv_symptoms": [],
        "history": {"ischemic_heart_disease": None, "prior_pci_or_cabg": None, "heart_failure": None,
                    "stroke_or_tia_months_ago": None, "cied": None, "valve_disease": None,
                    "pulmonary_hypertension": None, "congenital_heart_disease": None, "atrial_fibrillation": None,
                    "peripheral_artery_disease": False},
        "acute": {"acs": None, "decompensated_hf": False, "unstable_arrhythmia": None},
        "creatinine_mg_dl": round(rng.uniform(0.7, 1.5), 1),
        "frail_items": {"fatigue": False, "resistance": False, "ambulation": False,
                        "illnesses_gt_5": False, "weight_loss_ge_5pct": False},
        "surgery": {"procedure": "", "category": "", "time_to_surgery_hours": None, "can_be_delayed": "indefinitely"},
        "dasi_activities_can_do": [], "functional_capacity_assessable": True,
        "further_testing_would_change_management": False,
        "biomarkers": {"bnp_ng_l": None, "nt_probnp_ng_l": None, "troponin_ng_l": None, "troponin_url_ng_l": None},
        "edge_tags": [],
    }
    for k, v in kw.items():
        p[k] = v
    return p

def set_surgery(p, cat, hours=None, delay=None):
    p["surgery"]["category"] = cat
    p["surgery"]["procedure"] = rng.choice(SURGERY[cat])
    p["surgery"]["time_to_surgery_hours"] = hours
    p["surgery"]["can_be_delayed"] = delay if delay else ("n/a" if hours is not None else rng.choice(["up to 3 months", "indefinitely"]))

def add_generic_risk(p):
    """Give >=1 guideline CV risk factor (Fig 1 footnote)."""
    rf = p["risk_factors"]
    for k in rng.sample(["hypertension", "smoking", "hyperlipidemia", "diabetes", "obesity"], rng.randint(1, 3)):
        if k == "diabetes": rf["diabetes"] = rng.choice(["diet-controlled", "oral agents"])
        elif k == "obesity": rf["bmi"] = round(rng.uniform(30.5, 41), 1)
        else: rf[k] = True
    p["age"] = rng.randint(45, 88); p["sex"] = rng.choice("MF")

def set_dasi(p, adequate):
    lvl = rng.choice(ADEQ_LEVELS if adequate else POOR_LEVELS)
    p["dasi_activities_can_do"] = LADDER[lvl][:]

def set_bnp(p, abnormal):
    if rng.random() < 0.5:
        p["biomarkers"]["bnp_ng_l"] = rng.randint(120, 900) if abnormal else rng.randint(10, 85)
    else:
        p["biomarkers"]["nt_probnp_ng_l"] = rng.randint(350, 4000) if abnormal else rng.randint(30, 280)
    if rng.random() < 0.3:  # troponin sometimes also measured (normal unless stated)
        p["biomarkers"]["troponin_url_ng_l"] = 14
        p["biomarkers"]["troponin_ng_l"] = rng.randint(3, 12)

# --- RCRI components and risk modifiers used by templates ----------------------------
def comp_ihd(p): p["history"]["ischemic_heart_disease"] = rng.choice(["prior MI 4 years ago", "stable angina on nitrates", "Q waves on ECG, remote MI"])
def comp_cvd(p): p["history"]["stroke_or_tia_months_ago"] = rng.choice([8, 14, 30, 60])
def comp_hf(p):  p["history"]["heart_failure"] = rng.choice(["compensated HFrEF (EF 35%) on GDMT", "compensated HFpEF, euvolemic"])
def comp_ins(p): p["risk_factors"]["diabetes"] = "insulin"
def comp_ren(p): p["creatinine_mg_dl"] = round(rng.uniform(2.2, 3.6), 1)
COMPONENTS = {"ihd": comp_ihd, "cvd": comp_cvd, "hf": comp_hf, "insulin": comp_ins, "renal": comp_ren}

def mod_vhd(p): p["history"]["valve_disease"] = {"lesion": rng.choice(["aortic stenosis", "mitral regurgitation"]), "severity": "severe", "symptomatic": rng.random() < 0.5}
def mod_ph(p):  p["history"]["pulmonary_hypertension"] = "severe"
def mod_chd(p): p["history"]["congenital_heart_disease"] = {"lesion": rng.choice(["Fontan circulation", "unrepaired tetralogy with cyanosis", "Eisenmenger syndrome"]), "complexity": "complex"}
def mod_pci(p):
    p["history"]["prior_pci_or_cabg"] = rng.choice(["DES-PCI 2 years ago", "CABG 6 years ago", "DES-PCI 14 months ago"])
    p["history"]["ischemic_heart_disease"] = p["history"]["ischemic_heart_disease"] or "CAD s/p revascularization"
def mod_stroke(p): p["history"]["stroke_or_tia_months_ago"] = rng.choice([1, 2])
def mod_cied(p): p["history"]["cied"] = rng.choice(["dual-chamber pacemaker", "ICD"])
def mod_frail(p):
    for k in rng.sample(list(p["frail_items"]), rng.randint(3, 5)): p["frail_items"][k] = True
MODIFIERS = {"vhd": mod_vhd, "ph": mod_ph, "chd": mod_chd, "pci": mod_pci, "stroke": mod_stroke, "cied": mod_cied, "frail": mod_frail}

def distractor(p):
    """Non-acute, non-modifier findings that must NOT change the pathway."""
    d = rng.choice(["af", "mod_as", "mild_ph", "simple_chd", "prefrail", "none", "none"])
    if d == "af": p["history"]["atrial_fibrillation"] = "paroxysmal AF, rate controlled"
    elif d == "mod_as": p["history"]["valve_disease"] = {"lesion": "aortic stenosis", "severity": "moderate", "symptomatic": False}
    elif d == "mild_ph": p["history"]["pulmonary_hypertension"] = rng.choice(["mild", "moderate"])
    elif d == "simple_chd": p["history"]["congenital_heart_disease"] = {"lesion": "repaired secundum ASD, no residua", "complexity": "simple"}
    elif d == "prefrail":
        for k in rng.sample(list(p["frail_items"]), rng.randint(1, 2)): p["frail_items"][k] = True

def nonemergent_timing():
    r = rng.random()
    if r < 0.2: return rng.choice([2.5, 4, 6, 10, 18, 23]), None
    return None, None

def elevated_patient():
    """Elevated calculated risk and/or a risk modifier (never uses RCRI definitional edges)."""
    p = new_patient(); add_generic_risk(p)
    hrs, _ = nonemergent_timing()
    if rng.random() < 0.5:   # RCRI >=2, no modifiers
        comps = rng.sample(list(COMPONENTS) + ["surgery"], rng.randint(2, 3))
        for c in comps:
            if c != "surgery": COMPONENTS[c](p)
        set_surgery(p, rng.choice(HIGH_RISK_CATS if "surgery" in comps else LOW_RISK_CATS), hrs)
        if rng.random() < 0.4: distractor(p)
    else:                    # modifier present, any calculated risk
        for m in rng.sample(list(MODIFIERS), rng.randint(1, 2)): MODIFIERS[m](p)
        for c in rng.sample(list(COMPONENTS), rng.randint(0, 2)): COMPONENTS[c](p)
        set_surgery(p, rng.choice(HIGH_RISK_CATS + LOW_RISK_CATS), hrs)
    return p

cohort = []

# 1) No CV risk factors, disease, or symptoms (some emergencies: step 1 comes first)
for i in range(11):
    p = new_patient(age=rng.randint(19, 50), sex=rng.choice("MF"))
    p["risk_factors"]["bmi"] = round(rng.uniform(19, 28.5), 1)
    if i < 4: set_surgery(p, rng.choice(["intraperitoneal", "orthopedic"]), hours=rng.choice([0.5, 1, 1.5]))
    else: set_surgery(p, rng.choice(LOW_RISK_CATS + ["intraperitoneal"]))
    set_dasi(p, True); cohort.append(p)

# 2) Emergency surgery with CV risk (incl. acute conditions / modifiers that must be bypassed)
for i in range(16):
    p = elevated_patient() if i % 2 else new_patient()
    if i % 2 == 0: add_generic_risk(p)
    if i % 4 == 0: p["acute"]["acs"] = "NSTEMI 3 days ago"
    set_surgery(p, rng.choice(["intraperitoneal", "suprainguinal_vascular", "orthopedic", "intrathoracic"]),
                hours=rng.choice([0.25, 0.5, 1, 1.5]))
    set_dasi(p, rng.random() < 0.5); cohort.append(p)

# 3) Acute cardiac conditions (elective / time-sensitive / urgent)
acute_kinds = ["acs"] * 7 + ["dhf"] * 7 + ["arr"] * 7
for i, k in enumerate(acute_kinds):
    p = new_patient(); add_generic_risk(p)
    if k == "acs": p["acute"]["acs"] = rng.choice(["NSTEMI 5 days ago", "unstable angina this week", "STEMI 2 weeks ago, not revascularized"])
    elif k == "dhf": p["acute"]["decompensated_hf"] = True; p["history"]["heart_failure"] = "HFrEF, currently volume overloaded"
    else: p["acute"]["unstable_arrhythmia"] = rng.choice(["AF with RVR 150 bpm, hypotensive", "sustained VT", "symptomatic complete heart block"])
    hrs = rng.choice([3, 8, 20]) if i % 3 == 0 else None
    set_surgery(p, rng.choice(HIGH_RISK_CATS + LOW_RISK_CATS), hours=hrs)
    set_dasi(p, rng.random() < 0.5); cohort.append(p)

# 4) Low calculated risk, no modifiers (RCRI <=1 by Table 4), incl. urgent and distractors
for i in range(23):
    p = new_patient(); add_generic_risk(p)
    comps = rng.sample(list(COMPONENTS) + ["surgery", None, None], 1)
    c = comps[0]
    if c in COMPONENTS: COMPONENTS[c](p)
    set_surgery(p, rng.choice(HIGH_RISK_CATS) if c == "surgery" else rng.choice(LOW_RISK_CATS),
                hours=rng.choice([2.5, 6, 12, 22]) if i % 5 == 0 else None)
    if rng.random() < 0.6: distractor(p)
    set_dasi(p, rng.random() < 0.5); cohort.append(p)

# 5) Elevated risk / modifiers -> adequate functional capacity
for _ in range(21):
    p = elevated_patient(); set_dasi(p, True); cohort.append(p)

# 6) Poor/unknown FC, further testing would NOT change management
for i in range(21):
    p = elevated_patient(); set_dasi(p, False)
    if i % 7 == 0: p["dasi_activities_can_do"] = []; p["functional_capacity_assessable"] = False
    set_bnp(p, rng.random() < 0.5); cohort.append(p)

# 7) Poor/unknown FC, testing would change management, normal biomarkers
for i in range(20):
    p = elevated_patient(); set_dasi(p, False); p["further_testing_would_change_management"] = True
    if i % 7 == 0: p["dasi_activities_can_do"] = []; p["functional_capacity_assessable"] = False
    set_bnp(p, False); cohort.append(p)

# 8) Poor/unknown FC, testing would change management, abnormal biomarkers
for i in range(24):
    p = elevated_patient(); set_dasi(p, False); p["further_testing_would_change_management"] = True
    if i % 8 == 0: p["dasi_activities_can_do"] = []; p["functional_capacity_assessable"] = False
    set_bnp(p, True)
    if i % 6 == 0:  # abnormal troponin with normal natriuretic peptide
        p["biomarkers"] = {"bnp_ng_l": rng.randint(20, 80), "nt_probnp_ng_l": None, "troponin_ng_l": rng.randint(20, 60), "troponin_url_ng_l": 14}
    cohort.append(p)

# --- Explicit boundary / edge cases -----------------------------------------------------
def edge(tag, build):
    p = new_patient(); p["edge_tags"].append(tag); build(p); cohort.append(p)

def only_low_surgery(p): set_surgery(p, "orthopedic"); set_dasi(p, True)
edge("age_boundary_man_55_no_risk", lambda p: (p.update(age=55, sex="M"), only_low_surgery(p)))
edge("age_boundary_woman_65_no_risk", lambda p: (p.update(age=65, sex="F"), only_low_surgery(p)))
edge("age_boundary_man_56_risk", lambda p: (p.update(age=56, sex="M"), only_low_surgery(p)))
edge("age_boundary_woman_66_risk", lambda p: (p.update(age=66, sex="F"), only_low_surgery(p)))
edge("bmi_29_9_no_risk", lambda p: (p.update(age=40, sex="F"), p["risk_factors"].update(bmi=29.9), only_low_surgery(p)))
edge("bmi_30_0_obesity", lambda p: (p.update(age=40, sex="F"), p["risk_factors"].update(bmi=30.0), only_low_surgery(p)))
edge("symptoms_only", lambda p: (p.update(age=38, sex="M"), p.update(cv_symptoms=["exertional chest pressure"]), only_low_surgery(p)))
edge("hours_1_9_emergency", lambda p: (p["risk_factors"].update(hypertension=True), set_surgery(p, "intraperitoneal", hours=1.9), set_dasi(p, True)))
edge("hours_2_0_urgent_low_risk", lambda p: (p["risk_factors"].update(hypertension=True), set_surgery(p, "orthopedic", hours=2.0), set_dasi(p, True)))
edge("hours_2_0_urgent_with_acs", lambda p: (p["risk_factors"].update(hypertension=True), p["acute"].update(acs="NSTEMI 2 days ago"), set_surgery(p, "orthopedic", hours=2.0)))
edge("emergency_with_acs", lambda p: (p["risk_factors"].update(smoking=True), p["acute"].update(acs="STEMI today"), set_surgery(p, "intraperitoneal", hours=0.5)))
edge("severe_symptomatic_AS_not_acute_poor_fc_test_high_bnp", lambda p: (p["risk_factors"].update(hypertension=True), p.update(age=79),
     p["history"].update(valve_disease={"lesion": "aortic stenosis", "severity": "severe", "symptomatic": True}),
     set_surgery(p, "orthopedic"), set_dasi(p, False), p.update(further_testing_would_change_management=True), p["biomarkers"].update(nt_probnp_ng_l=1800)))
edge("severe_AS_rcri0_adequate_fc", lambda p: (p["risk_factors"].update(hypertension=True),
     p["history"].update(valve_disease={"lesion": "aortic stenosis", "severity": "severe", "symptomatic": False}), set_surgery(p, "breast"), set_dasi(p, True)))
edge("recent_stroke_2mo_adequate", lambda p: (p["risk_factors"].update(hypertension=True), p["history"].update(stroke_or_tia_months_ago=2), set_surgery(p, "spine"), set_dasi(p, True)))
edge("stroke_exactly_3mo_not_recent", lambda p: (p["risk_factors"].update(hypertension=True), p["history"].update(stroke_or_tia_months_ago=3), set_surgery(p, "spine"), set_dasi(p, True)))
edge("frail_3_only_modifier_no_impact", lambda p: (p.update(age=84, sex="F"), [p["frail_items"].update({k: True}) for k in ["fatigue", "resistance", "ambulation"]],
     set_surgery(p, "orthopedic"), set_dasi(p, False)))
edge("prefrail_2_low", lambda p: (p.update(age=80, sex="F"), [p["frail_items"].update({k: True}) for k in ["fatigue", "resistance"]], set_surgery(p, "orthopedic"), set_dasi(p, True)))
for j, prof in enumerate(EXACT_34[:2]):
    edge(f"dasi_exactly_34_{j+1}", lambda p, prof=prof: (p["risk_factors"].update(hypertension=True), comp_ihd(p), comp_ins(p), set_surgery(p, "orthopedic"),
         p.update(dasi_activities_can_do=prof)))
edge("dasi_just_above_34", lambda p: (p["risk_factors"].update(hypertension=True), comp_ihd(p), comp_ins(p), set_surgery(p, "orthopedic"), p.update(dasi_activities_can_do=JUST_ABOVE)))
edge("fc_unknown_wheelchair_test_normal_bnp", lambda p: (p["risk_factors"].update(hypertension=True), comp_ihd(p), comp_hf(p), set_surgery(p, "urologic"),
     p.update(dasi_activities_can_do=[], functional_capacity_assessable=False, further_testing_would_change_management=True), p["biomarkers"].update(bnp_ng_l=60)))
def bio_edge(tag, **bm):
    edge(tag, lambda p: (p["risk_factors"].update(hypertension=True), comp_ihd(p), comp_hf(p), set_surgery(p, "orthopedic"), set_dasi(p, False),
         p.update(further_testing_would_change_management=True), p["biomarkers"].update(**bm)))
bio_edge("bnp_92_normal", bnp_ng_l=92)
bio_edge("bnp_93_abnormal", bnp_ng_l=93)
bio_edge("ntprobnp_299_normal", nt_probnp_ng_l=299)
bio_edge("ntprobnp_300_abnormal", nt_probnp_ng_l=300)
bio_edge("troponin_equal_url_normal", bnp_ng_l=40, troponin_ng_l=14, troponin_url_ng_l=14)
bio_edge("troponin_above_url_abnormal", bnp_ng_l=40, troponin_ng_l=15, troponin_url_ng_l=14)
# RCRI definitional edges: guideline Table 4 ("vascular surgery", "creatinine >=2.0") vs original Lee wording
edge("rcri_def_infrainguinal_vascular_plus_ihd_adequate", lambda p: (p["risk_factors"].update(smoking=True), p["history"].update(peripheral_artery_disease=True), comp_ihd(p),
     set_surgery(p, "infrainguinal_vascular"), set_dasi(p, True)))
edge("rcri_def_infrainguinal_vascular_plus_ihd_poor_test_high", lambda p: (p["risk_factors"].update(smoking=True), p["history"].update(peripheral_artery_disease=True), comp_ihd(p),
     set_surgery(p, "infrainguinal_vascular"), set_dasi(p, False), p.update(further_testing_would_change_management=True), p["biomarkers"].update(bnp_ng_l=240)))
edge("rcri_def_creatinine_2_0_plus_ihd", lambda p: (p["risk_factors"].update(hypertension=True), comp_ihd(p), p.update(creatinine_mg_dl=2.0), set_surgery(p, "orthopedic"), set_dasi(p, True)))
edge("rcri_control_creatinine_2_1_plus_ihd", lambda p: (p["risk_factors"].update(hypertension=True), comp_ihd(p), p.update(creatinine_mg_dl=2.1), set_surgery(p, "orthopedic"), set_dasi(p, True)))
edge("rcri_control_suprainguinal_plus_ihd", lambda p: (p["risk_factors"].update(smoking=True), comp_ihd(p), set_surgery(p, "suprainguinal_vascular"), set_dasi(p, True)))
edge("oral_dm_plus_ihd_low", lambda p: (p["risk_factors"].update(diabetes="oral agents"), comp_ihd(p), set_surgery(p, "endocrine"), set_dasi(p, True)))
edge("insulin_plus_ihd_elevated", lambda p: (p["risk_factors"].update(diabetes="insulin"), comp_ihd(p), set_surgery(p, "endocrine"), set_dasi(p, True)))
edge("rate_controlled_af_low", lambda p: (p["risk_factors"].update(hypertension=True), p["history"].update(atrial_fibrillation="persistent AF, rate controlled"), set_surgery(p, "urologic"), set_dasi(p, False)))
edge("moderate_ph_low", lambda p: (p["risk_factors"].update(hypertension=True), p["history"].update(pulmonary_hypertension="moderate"), set_surgery(p, "breast"), set_dasi(p, False)))
edge("severe_ph_modifier", lambda p: (p["risk_factors"].update(hypertension=True), p["history"].update(pulmonary_hypertension="severe"), set_surgery(p, "breast"), set_dasi(p, True)))
edge("simple_repaired_asd_low", lambda p: (p.update(age=35, sex="F"), p["history"].update(congenital_heart_disease={"lesion": "repaired secundum ASD, no residua", "complexity": "simple"}),
     set_surgery(p, "breast"), set_dasi(p, True)))
edge("fontan_modifier", lambda p: (p.update(age=29, sex="M"), p["history"].update(congenital_heart_disease={"lesion": "Fontan circulation", "complexity": "complex"}),
     set_surgery(p, "orthopedic"), set_dasi(p, False)))
edge("pacemaker_only_modifier", lambda p: (p["risk_factors"].update(hypertension=True), p["history"].update(cied="single-chamber pacemaker"), set_surgery(p, "ophthalmologic"), set_dasi(p, True)))
edge("prior_pci_modifier", lambda p: (p["risk_factors"].update(hyperlipidemia=True), mod_pci(p), set_surgery(p, "orthopedic"), set_dasi(p, True)))
edge("rcri2_no_modifier_poor_no_impact", lambda p: (p["risk_factors"].update(hypertension=True), comp_ihd(p), comp_ren(p), set_surgery(p, "urologic"), set_dasi(p, False)))
edge("compensated_hf_plus_insulin_elevated", lambda p: (p["risk_factors"].update(hypertension=True), comp_hf(p), comp_ins(p), set_surgery(p, "spine"), set_dasi(p, True)))

assert len(cohort) == 200, len(cohort)
for p in cohort:  # every patient has a biomarker value available in case the pathway needs it
    b = p["biomarkers"]
    if b["bnp_ng_l"] is None and b["nt_probnp_ng_l"] is None:
        b["bnp_ng_l"] = rng.randint(15, 80)
json.dump(cohort, open("cohort_200.json", "w"), indent=1)
print(f"wrote {len(cohort)} patients; exact-34 DASI profiles found: {len(EXACT_34)}; just-above sum: {sum(_W[k] for k in JUST_ABOVE)/100}")
