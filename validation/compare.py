"""Score the app against the oracle.

Primary endpoint: final recommendation (Figure 1 outcome) matches the oracle.
Secondary: recommendation content/COR labels, branch-specific preliminary-step hint,
RCRI / DASI / FRAIL calculator agreement, copied chart note, Reset-vs-fresh consistency.

Usage:  python3 compare.py   ->  results_200.csv (+ printed summary)
"""
import csv, json
from collections import Counter

cohort = {p["id"]: p for p in json.load(open("cohort_200.json"))}
exp = {e["id"]: e for e in json.load(open("expected_200.json"))}
runs = json.load(open("app_results_200.json"))
app = {r["id"]: r for r in runs["reset"]}
fresh = {r["id"]: r for r in runs["fresh"]}
URG = {"emergency": "Emergency", "urgent": "Urgent", "time-sensitive": "Time-sens", "elective": "Elective"}


def content_failures(e, a):
    blob = " ".join([a.get("title", ""), a.get("text", ""), a.get("label", "")]).lower()
    f = [f"missing '{m}'" for m in e["content"]["must"] if m not in blob]
    f += [f"contains '{m}'" for m in e["content"]["must_not"] if m in blob]
    cor, label = e["content"]["cor"], a.get("label", "")
    if cor is None and "COR" in label: f.append(f"unsupported COR label '{label}'")
    if cor is not None and f"COR {cor}" not in label: f.append(f"expected COR {cor}, label '{label}'")
    return f


def fc_hint_failures(e, a):
    if e["fc_branch"] is None or "fc_hint" not in a: return []
    h = a["fc_hint"].lower()
    if e["fc_branch"] == "modifier":
        need = ["team consultation", "(2a)", "tte"]
        return [f"modifier hint missing '{n}'" for n in need if n not in h]
    f = [f"no-modifier hint missing '{n}'" for n in ["(2b)", "gdmt"] if n not in h]
    if "tte" in h: f.append("no-modifier hint mentions TTE")
    return f


def note_failures(e, a, p):
    n = a.get("copied_note") or ""
    f = []
    if "2026;88(13):1543-1643" not in n: f.append("note lacks 2026 citation")
    if a.get("title") and a["title"] not in n: f.append("note lacks recommendation title")
    if "CV risk factors, disease, or symptoms" not in n: f.append("note lacks CV-risk line")
    if e["outcome"] != "NO_RISK" and f"Surgical urgency: {URG[e['timing']]}" not in n and e["timing"] in ("emergency", "urgent"):
        f.append("note urgency mismatch")
    if e["fc_branch"] and not p["functional_capacity_assessable"] and e["outcome"] != "ADEQ":
        if "Functional capacity: Unknown" not in n: f.append("note does not record unknown functional capacity")
        if "DASI 0" in n: f.append("note reports DASI 0 for unknown capacity")
    return f


rows, fails = [], Counter()
for pid, e in exp.items():
    a, p, fr = app[pid], cohort[pid], fresh[pid]
    match = a["outcome"] == e["outcome"]
    cf = content_failures(e, a) if match else []
    hf = fc_hint_failures(e, a)
    nf = note_failures(e, a, p)
    rcri_ok = None if "rcri_score" not in a else a["rcri_score"] == e["rcri"]
    dasi_ok = None if "dasi_score" not in a else abs(a["dasi_score"] - e["dasi"]) < 0.051  # app displays 1 decimal
    dasi_flag_ok = None if "dasi_flag" not in a else (a["dasi_flag"] == ("POOR" if e["dasi"] <= 34 else "ADEQUATE"))
    frail_cat = "FRAIL" if e["frail_score"] >= 3 else "PREFRAIL" if e["frail_score"] >= 1 else "NONFRAIL"
    frail_ok = a.get("frail_score") == e["frail_score"] and a.get("frail_category") == frail_cat
    if "frail_inflow" in a: frail_ok = frail_ok and a["frail_inflow"] == f"{e['frail_score']} {frail_cat}"
    consistent = all(fr.get(k) == a.get(k) for k in ("outcome", "title", "text", "label", "copied_note", "rcri_score", "dasi_score"))
    banner_vs_internal = {"ACS_DEFER": "ACUTE_DEFER"}.get(a.get("internal_terminal"), a.get("internal_terminal")) == a["outcome"]
    progress_ok = "of 8" in a.get("progress_label", "of 8")
    cause = ""
    if not match:
        pts = e["rcri_points"]
        if rcri_ok is False and any(t.startswith("rcri_def") for t in p["edge_tags"]):
            diff = []
            if pts["high_risk_procedure"] and p["surgery"]["category"] == "infrainguinal_vascular": diff.append("infrainguinal vascular surgery")
            if pts["creatinine_ge_2"] and p["creatinine_mg_dl"] == 2.0: diff.append("creatinine exactly 2.0")
            cause = "RCRI definition: app label (Lee 1999) vs guideline Table 4 - " + ", ".join(diff)
        else:
            cause = "LOGIC"
    for k, v in [("outcome", match), ("content", not cf), ("fc_hint", not hf), ("note", not nf),
                 ("rcri", rcri_ok is not False), ("dasi", dasi_ok is not False), ("dasi_flag", dasi_flag_ok is not False),
                 ("frail", frail_ok), ("reset_vs_fresh", consistent), ("banner_vs_internal", banner_vs_internal), ("progress", progress_ok)]:
        if not v: fails[k] += 1
    rows.append({
        "id": pid, "edge_tags": ";".join(p["edge_tags"]), "procedure": p["surgery"]["procedure"],
        "oracle_timing": e["timing"], "oracle_modifiers": "; ".join(e["modifiers"]),
        "oracle_rcri_table4": e["rcri"], "app_rcri": a.get("rcri_score", ""),
        "oracle_dasi": e["dasi"] if e["fc_branch"] else "", "app_dasi": a.get("dasi_score", ""), "app_dasi_flag": a.get("dasi_flag", ""),
        "oracle_frail": e["frail_score"], "app_frail": f"{a.get('frail_score')} {a.get('frail_category')}",
        "oracle_outcome": e["outcome"], "app_outcome": a["outcome"], "outcome_match": match,
        "app_recommendation": a.get("title", ""), "app_label": a.get("label", ""),
        "content_failures": "; ".join(cf), "fc_hint_failures": "; ".join(hf), "note_failures": "; ".join(nf),
        "reset_vs_fresh_consistent": consistent, "discordance_cause": cause,
    })

with open("results_200.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

n = len(rows); m = sum(r["outcome_match"] for r in rows)
defn = [r for r in rows if r["discordance_cause"].startswith("RCRI definition")]
logic = [r for r in rows if r["discordance_cause"] == "LOGIC"]
print(f"PRIMARY  outcome concordance: {m}/{n} = {100*m/n:.1f}%")
print(f"         discordant: {n-m}  (RCRI-definition: {len(defn)}, logic: {len(logic)})")
if n - len(defn):
    print(f"         concordance excluding RCRI-definition cases: {m}/{n-len(defn)} = {100*m/(n-len(defn)):.1f}%")
print("PER-OUTCOME (oracle): ")
for o in ["NO_RISK", "EMERGENT", "ACUTE_DEFER", "LOW", "ADEQ", "NO_IMPACT", "BIOMARKER_OK", "BIOMARKER_HIGH"]:
    rs = [r for r in rows if r["oracle_outcome"] == o]
    print(f"   {o:15s} {sum(r['outcome_match'] for r in rs):3d}/{len(rs)}")
print("SECONDARY check failures:", dict(fails) if fails else "none")
for r in defn + logic:
    print(f"   {r['id']} {r['edge_tags'] or '-'}: oracle {r['oracle_outcome']} (RCRI {r['oracle_rcri_table4']}) vs app {r['app_outcome']} (RCRI {r['app_rcri']}) :: {r['discordance_cause']}")
for r in rows:
    for k in ("content_failures", "fc_hint_failures", "note_failures"):
        if r[k]: print(f"   {r['id']} {k}: {r[k]}")
