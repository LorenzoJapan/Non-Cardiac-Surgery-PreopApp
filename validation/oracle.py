"""Reference oracle: 2026 AHA/ACC perioperative guideline, Figure 1 (stepwise approach).

Written from the guideline text only (not from the app's code). Each rule cites its source.
Input: cohort_200.json (raw clinical facts). Output: expected_200.json.

Usage:  python3 oracle.py
"""
import json

# Table 5 (Hlatky 1989) DASI weights
DASI_W = {"self_care": 2.75, "walk_indoors": 1.75, "walk_1_2_blocks": 2.75, "climb_stairs_or_hill": 5.5,
          "run_short_distance": 8, "light_housework": 2.7, "moderate_housework": 3.5, "heavy_housework": 8,
          "yardwork": 4.5, "sexual_relations": 5.25, "moderate_recreation": 6, "strenuous_sports": 7.5}


def has_cv_disease(p):
    h = p["history"]
    return any([h["ischemic_heart_disease"], h["prior_pci_or_cabg"], h["heart_failure"],
                h["stroke_or_tia_months_ago"] is not None, h["cied"], h["valve_disease"],
                h["pulmonary_hypertension"], h["congenital_heart_disease"], h["atrial_fibrillation"],
                h["peripheral_artery_disease"], p["acute"]["acs"], p["acute"]["decompensated_hf"],
                p["acute"]["unstable_arrhythmia"]])


def has_cv_risk_factor(p):
    """Fig 1 footnote *: HTN, smoking, high cholesterol, diabetes, women >65 y, men >55 y, obesity, FHx premature CAD."""
    rf = p["risk_factors"]
    return any([rf["hypertension"], rf["smoking"], rf["hyperlipidemia"], rf["diabetes"] is not None,
                rf["bmi"] >= 30,  # obesity = BMI >= 30 kg/m2 (standard definition)
                rf["family_history_premature_cad"],
                p["sex"] == "F" and p["age"] > 65, p["sex"] == "M" and p["age"] > 55])


def timing(p):
    """Table 2: emergency typically <2 h; urgent >=2 to <24 h; time-sensitive up to 3 mo; elective."""
    h = p["surgery"]["time_to_surgery_hours"]
    if h is not None:
        return "emergency" if h < 2 else "urgent" if h < 24 else "time-sensitive"
    return "time-sensitive" if p["surgery"]["can_be_delayed"] == "up to 3 months" else "elective"


def frail_score(p):
    return sum(p["frail_items"].values())  # Table 6 FRAIL: 0 nonfrail, 1-2 intermediate, 3-5 frail


def risk_modifiers(p):
    """Fig 1 risk modifiers."""
    h, mods = p["history"], []
    if h["valve_disease"] and h["valve_disease"]["severity"] == "severe": mods.append("severe VHD (§6.4)")
    if h["pulmonary_hypertension"] == "severe": mods.append("severe pulmonary hypertension (§6.3.2)")
    if h["congenital_heart_disease"] and h["congenital_heart_disease"]["complexity"] != "simple":
        mods.append("elevated-risk CHD (§6.3.3, Table 11)")
    if h["prior_pci_or_cabg"]: mods.append("prior coronary stents/CABG")
    m = h["stroke_or_tia_months_ago"]
    if m is not None and m < 3: mods.append("recent stroke (<3 mo, §6.7)")
    if h["cied"]: mods.append("CIED")
    if frail_score(p) >= 3: mods.append("frailty (§3.3)")
    return mods


def rcri_table4(p):
    """Table 4 RCRI criteria, 1 point each; elevated risk threshold RCRI >1 (Table 2 footnote, Fig 1 †)."""
    h = p["history"]
    pts = {
        "ischemic_heart_disease": bool(h["ischemic_heart_disease"] or h["prior_pci_or_cabg"]),
        "cerebrovascular_disease": h["stroke_or_tia_months_ago"] is not None,
        "history_of_hf": bool(h["heart_failure"]),
        "insulin_for_diabetes": p["risk_factors"]["diabetes"] == "insulin",
        "creatinine_ge_2": p["creatinine_mg_dl"] >= 2.0,  # Table 4 prints "serum creatinine >=2.0 mg/dL"
        "high_risk_procedure": p["surgery"]["category"] in
            ("intraperitoneal", "intrathoracic", "suprainguinal_vascular", "infrainguinal_vascular"),  # Table 4: "vascular surgery"
    }
    return sum(pts.values()), pts


def dasi(p):
    return round(sum(DASI_W[k] for k in p["dasi_activities_can_do"]), 2)


def biomarker_abnormal(p):
    """Fig 1 §: troponin >99th percentile URL; BNP >92 ng/L; NT-proBNP >=300 ng/L."""
    b = p["biomarkers"]
    return any([b["bnp_ng_l"] is not None and b["bnp_ng_l"] > 92,
                b["nt_probnp_ng_l"] is not None and b["nt_probnp_ng_l"] >= 300,
                b["troponin_ng_l"] is not None and b["troponin_ng_l"] > b["troponin_url_ng_l"]])


# Content each outcome must/must-not carry (Fig 1, §3.2, §3.4, §4.1, §4.3-4.5, §6.1.1, §9.1)
CONTENT = {
    "NO_RISK":        {"cor": None, "must": ["proceed"], "must_not": []},
    "EMERGENT":       {"cor": None, "must": ["proceed"], "must_not": ["urgent"]},
    "ACUTE_DEFER":    {"cor": None, "must": ["multidisciplinary", "deferral"], "must_not": []},
    "LOW":            {"cor": None, "must": ["proceed"], "must_not": []},
    "ADEQ":           {"cor": "2a", "must": ["proceed"], "must_not": ["obtain a baseline ecg"]},
    "NO_IMPACT":      {"cor": None, "must": ["proceed", "deferral", "palliation"], "must_not": ["troponin"]},
    "BIOMARKER_OK":   {"cor": "2a", "must": ["proceed"], "must_not": ["24 and 48", "postoperative troponin"]},
    "BIOMARKER_HIGH": {"cor": "2b", "must": ["multidisciplinary", "echocardiography", "stress", "ccta", "24 and 48"], "must_not": []},
    # §7.5 Defer/Delay is more restrictive than any Figure 1 outcome reached after step 4 -> it is the headline;
    # the Figure 1 outcome is kept as "once stent timing allows" (checked separately as fig1_outcome)
    "STENT_HOLD":     {"cor": "any", "must": ["stent timing", "once stent timing allows", "multidisciplinary"], "must_not": []},
}


def stent_level(p, timing_):
    """§7.5 (recs 2-6, 8, 10) stent-timing flag, for patients with prior PCI/CABG who reach the modifier step.
    Thresholds: balloon <14 d; any stent <=30 d (3: Harm, elective); BMS >30 d ok; DES for ACS <12 mo (365 d),
    DES for stable CAD <6 mo (180 d); time-sensitive: DES >=3 mo (90 d) may consider (2b), BMS <=30 d / DES <3 mo
    continue DAPT (rec 8). Urgent surgery: thresholds address elective/time-sensitive -> team decision ("info")."""
    s = p["history"].get("pci")
    if not s: return None
    if s["type"] == "CABG": return "ok"
    if timing_ == "urgent": return "info"
    if s["antiplatelet_interruption"] == "no": return "ok"
    d, ts = s["days_since"], timing_ == "time-sensitive"
    if s["type"] == "balloon only": return "delay" if d < 14 else "ok"
    des = s["type"] == "DES"
    if ts and (d < 90 if des else d <= 30): return "delay"
    if d <= 30: return "harm"
    if not des: return "ok"
    limit = 365 if s["indication"] == "ACS" else 180
    if d >= limit: return "ok"
    return "consider" if ts and d >= 90 else "delay"


def evaluate(p):
    r = evaluate_fig1(p)
    if r.get("stent_level") in ("harm", "delay"):
        r["fig1_outcome"], r["outcome"], r["content"] = r["outcome"], "STENT_HOLD", CONTENT["STENT_HOLD"]
    return r


def evaluate_fig1(p):
    r = {"id": p["id"], "timing": timing(p), "frail_score": frail_score(p), "modifiers": risk_modifiers(p),
         "rcri": rcri_table4(p)[0], "rcri_points": rcri_table4(p)[1], "dasi": dasi(p), "fc_branch": None}
    def done(outcome):
        r["outcome"] = outcome; r["content"] = CONTENT[outcome]; return r
    if not (has_cv_risk_factor(p) or has_cv_disease(p) or p["cv_symptoms"]):
        return done("NO_RISK")                                   # Fig 1 entry: no -> proceed
    if r["timing"] == "emergency":
        return done("EMERGENT")                                  # Fig 1: emergency -> proceed
    a = p["acute"]
    if a["acs"] or a["decompensated_hf"] or a["unstable_arrhythmia"]:
        return done("ACUTE_DEFER")                               # Fig 1 acute conditions
    r["stent_level"] = stent_level(p, r["timing"])
    if not r["modifiers"] and r["rcri"] <= 1:
        return done("LOW")                                       # low calculated risk, no modifiers
    r["fc_branch"] = "modifier" if r["modifiers"] else "no_modifier"
    poor = (not p["functional_capacity_assessable"]) or r["dasi"] <= 34   # poor or unknown: DASI <=34
    if not poor:
        return done("ADEQ")
    if not p["further_testing_would_change_management"]:
        return done("NO_IMPACT")
    return done("BIOMARKER_HIGH" if biomarker_abnormal(p) else "BIOMARKER_OK")


if __name__ == "__main__":
    import sys
    src, dst = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("cohort_200.json", "expected_200.json")
    cohort = json.load(open(src))
    out = [evaluate(p) for p in cohort]
    json.dump(out, open(dst, "w"), indent=1)
    from collections import Counter
    print(dict(Counter(o["outcome"] for o in out)))
