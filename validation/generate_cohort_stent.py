"""Generate 40 stent-focused patients for the §7.5 stent-timing panel (option 3).

Demographics, risk factors, comorbidities, frailty, functional capacity and biomarkers are drawn at random
(same model as generate_cohort_random.py). Each patient is then assigned one stent scenario from the grid
below so every rule and boundary is exercised: procedure type, DES indication, days since PCI at each
cut-off (14 d, 30 d, 3 mo = 90 d, 6 mo = 180 d, 12 mo = 365 d), urgency, and antiplatelet plan.
Three control patients (emergency surgery or an acute condition) must bypass the stent step.

The expected answer comes from oracle.py, not from this file.

Usage:  python3 generate_cohort_stent.py [seed]   ->  cohort_stent_40.json
"""
import json, sys
import generate_cohort_random as g

g.rng.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 7505)

# (type, indication, days since PCI, urgency, antiplatelet interruption)
GRID = [
    # DES for ACS, elective, interruption: 30 d harm boundary, 12 mo delay boundary
    ("DES", "ACS", 10, "elective", "yes"), ("DES", "ACS", 30, "elective", "yes"), ("DES", "ACS", 31, "elective", "yes"),
    ("DES", "ACS", 89, "elective", "yes"), ("DES", "ACS", 90, "elective", "yes"), ("DES", "ACS", 200, "elective", "yes"),
    ("DES", "ACS", 364, "elective", "yes"), ("DES", "ACS", 365, "elective", "yes"),
    # DES for stable CAD, elective: 6 mo boundary
    ("DES", "stable CAD", 45, "elective", "yes"), ("DES", "stable CAD", 179, "elective", "yes"),
    ("DES", "stable CAD", 180, "elective", "yes"),
    # DES, time-sensitive: 3 mo "may consider" boundary
    ("DES", "ACS", 60, "time-sensitive", "yes"), ("DES", "ACS", 90, "time-sensitive", "yes"),
    ("DES", "ACS", 300, "time-sensitive", "yes"), ("DES", "ACS", 400, "time-sensitive", "yes"),
    ("DES", "stable CAD", 89, "time-sensitive", "yes"), ("DES", "stable CAD", 120, "time-sensitive", "yes"),
    ("DES", "stable CAD", 200, "time-sensitive", "yes"),
    # BMS: 30 d boundary, elective and time-sensitive
    ("BMS", None, 20, "elective", "yes"), ("BMS", None, 30, "elective", "yes"), ("BMS", None, 31, "elective", "yes"),
    ("BMS", None, 15, "time-sensitive", "yes"), ("BMS", None, 45, "time-sensitive", "yes"),
    # balloon angioplasty without stent: 14 d boundary
    ("balloon only", None, 13, "elective", "yes"), ("balloon only", None, 14, "elective", "yes"),
    ("balloon only", None, 10, "time-sensitive", "yes"),
    # antiplatelets continued
    ("DES", "ACS", 20, "elective", "no"), ("BMS", None, 10, "time-sensitive", "no"),
    # antiplatelet plan unknown
    ("DES", "ACS", 100, "elective", "unknown"), ("DES", "stable CAD", 25, "elective", "unknown"),
    ("BMS", None, 200, "elective", "unknown"), ("DES", "ACS", 400, "elective", "unknown"),
    ("balloon only", None, 5, "elective", "unknown"),
    # urgent surgery
    ("DES", "ACS", 20, "urgent", "yes"), ("BMS", None, 300, "urgent", "yes"),
    # CABG only
    ("CABG", None, None, "elective", None), ("CABG", None, None, "time-sensitive", None),
    # controls that must bypass the stent step
    ("DES", "ACS", 20, "emergency", "yes"), ("DES", "stable CAD", 60, "emergency", "yes"),
    ("DES", "ACS", 40, "elective-with-acute-ACS", "yes"),
]
assert len(GRID) == 40

cohort = []
for i, (typ, ind, days, urg, stop) in enumerate(GRID, 1):
    p = g.patient(i)
    p["id"] = f"S{i:03d}"
    h = p["history"]
    p["acute"] = {"acs": None, "decompensated_hf": False, "unstable_arrhythmia": None}
    if urg == "elective-with-acute-ACS":
        p["acute"]["acs"] = "NSTEMI 5 days ago"
        urg = "elective"
    if typ == "CABG":
        h["prior_pci_or_cabg"] = f"CABG {g.rng.randint(1, 15)} years ago"
        h["pci"] = {"type": "CABG", "indication": None, "days_since": None, "antiplatelet_interruption": None}
    else:
        h["prior_pci_or_cabg"] = f"{typ}-PCI {days} days ago" + (f" for {ind}" if ind else "")
        h["pci"] = {"type": typ, "indication": ind, "days_since": days, "antiplatelet_interruption": stop}
    h["ischemic_heart_disease"] = h["ischemic_heart_disease"] or "CAD s/p revascularization"
    s = p["surgery"]
    s["time_to_surgery_hours"] = {"emergency": g.rng.choice([0.5, 1, 1.5]), "urgent": g.rng.choice([3, 6, 12, 20])}.get(urg)
    s["can_be_delayed"] = "n/a" if s["time_to_surgery_hours"] is not None else (
        "up to 3 months" if urg == "time-sensitive" else "indefinitely")
    cohort.append(p)

json.dump(cohort, open("cohort_stent_40.json", "w"), indent=1)
print("wrote 40 stent-focused patients to cohort_stent_40.json")
