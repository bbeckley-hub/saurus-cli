# --- v0.2.x strain+year (master) ---
#!/usr/bin/env python3
"""
generate_mrsa.py — Build the interactive MRSA analysis page for SAURUS.

Reads:   mlst_all.tsv, spa_all.tsv, sccmec_cge_all.tsv,
         sccmec_rpet_all.tsv, capsule_all.tsv, agr_all.tsv
         cc.txt (ST → CC lookup)
Writes:  mrsa.html

Author: Brown Beckley <brownbeckley94@gmail.com>
"""

import csv
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

import saurus_common

# =========================================================================
# CONFIG
# =========================================================================
MODULE_KEY      = "mrsa"
MODULE_TITLE    = "MRSA Analysis"
MODULE_SUBTITLE = "Methicillin-Resistant Staphylococcus aureus — Comprehensive View"
MODULE_ACCENT   = "#dc2626"
CC_LOOKUP_FILE  = "cc.txt"


# ---------------------------------------------------------------------------
# Metadata (v0.2)
# ---------------------------------------------------------------------------
METADATA_FILE = "metadata.tsv"
META = saurus_common.load_metadata(METADATA_FILE)

INPUTS = {
    "mlst":  "mlst_all.tsv",
    "spa":   "spa_all.tsv",
    "cge":   "sccmec_cge_all.tsv",
    "rpet":  "sccmec_rpet_all.tsv",
    "capsule": "capsule_all.tsv",
    "agr":   "agr_all.tsv",
}

MRSA_VALUES = {"MRSA", "MSSA"}

MASTER_COLUMNS = [
    {"key": "accession",         "label": "Accession",       "type": "string", "default_visible": True},
    {"key": "mrsa_final",        "label": "MRSA Status",     "type": "string", "default_visible": True},
    {"key": "mlst_st",           "label": "MLST",            "type": "string", "default_visible": True},
    {"key": "mlst_cc",           "label": "CC",              "type": "string", "default_visible": True},
    {"key": "spa_type",          "label": "spa Type",        "type": "string", "default_visible": True},
    {"key": "rpet_sccmec_type",  "label": "SCCmec (RPet)",   "type": "string", "default_visible": True},
    {"key": "rpet_subtype",      "label": "Subtype",         "type": "string", "default_visible": True},
    {"key": "agr_type",          "label": "agr",             "type": "string", "default_visible": True},
    {"key": "cap_type",          "label": "Capsule",         "type": "string", "default_visible": True},
    {"key": "cge_sccmec_type",   "label": "SCCmec (CGE)",    "type": "string", "default_visible": False},
    {"key": "cge_confidence",    "label": "CGE Confidence",  "type": "string", "default_visible": False},
    {"key": "rpet_mec_class",    "label": "mec Class",       "type": "string", "default_visible": False},
    {"key": "mlst_status",       "label": "MLST Status",     "type": "string", "default_visible": False},
    {"key": "strain", "label": "Strain",          "type": "string", "default_visible": False},
    {"key": "year",   "label": "Collection Year", "type": "string", "default_visible": True},
]
MASTER_COLUMNS += saurus_common.META_MASTER_COLUMNS

FILTER_DEFS = [
    ("mrsa_final",        "MRSA Status"),
    ("mlst_cc",           "Clonal Complex"),
    ("mlst_st",           "MLST"),
    ("rpet_sccmec_type",  "SCCmec (RPet)"),
    ("cge_sccmec_type",   "SCCmec (CGE)"),
    ("agr_type",          "agr"),
    ("cap_type",          "Capsule"),
    ("year",    "Collection Year"),
]
FILTER_DEFS += saurus_common.META_FILTER_DEFS

CROSS_TAB_FIELDS = [
    ("mlst_cc",           "Clonal Complex"),
    ("mlst_st",           "MLST Sequence Type"),
    ("spa_type",          "spa Type"),
    ("rpet_sccmec_type",  "SCCmec Type (RPet)"),
    ("rpet_subtype",      "SCCmec Subtype"),
    ("agr_type",          "agr Type"),
    ("cap_type",          "Capsule Type"),
]
CROSS_TAB_FIELDS += saurus_common.META_CROSS_TAB_FIELDS
# =========================================================================


# ---------------------------------------------------------------------------
# ST → CC lookup
# ---------------------------------------------------------------------------
def load_st_to_cc(path: Path) -> dict:
    """Build {ST_display: CC} by majority vote from cc.txt.

    ST → CC is deterministic and stable, so we ignore the accession column
    entirely (avoids GCF/GCA prefix mismatch and incomplete overlap).
    """
    if not path.exists():
        print(f"⚠️  {path} not found — CC column will be empty")
        return {}

    votes = defaultdict(Counter)

    with open(path, encoding="utf-8") as f:
        first = f.readline()
        if not first.startswith("#"):
            f.seek(0)
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            cc = parts[1].strip()
            st = parts[2].strip()
            if not cc or not st or cc == "NA":
                continue
            if not st.startswith("ST"):
                st = f"ST{st}"
            votes[st][cc] += 1

    lookup = {}
    for st, cc_counter in votes.items():
        lookup[st] = cc_counter.most_common(1)[0][0]

    print(f"   ST→CC lookup: {len(lookup)} unique STs mapped")
    return lookup


# ---------------------------------------------------------------------------
# Cleaning helpers
# ---------------------------------------------------------------------------
def normalize_acc(raw):
    if not raw:
        return ""
    s = str(raw).strip()
    for ext in (".fna", ".fasta", ".fa"):
        if s.endswith(ext):
            s = s[: -len(ext)]
    return s


def clean_mrsa(raw):
    s = str(raw or "").strip().upper()
    return s if s in MRSA_VALUES else "Unknown"


def clean_type(raw, na="Not Assigned"):
    s = str(raw or "").strip()
    if not s or s in ("-", "ND", "Not Assigned", "None", "nan", "NA", "N/A"):
        return na
    return s


def clean_st(raw):
    s = clean_type(raw)
    if s == "Not Assigned":
        return "Not Assigned"
    m = re.match(r"^ST\s*(\d+)$", s, re.IGNORECASE)
    if m:
        return f"ST{m.group(1)}"
    if re.match(r"^\d+$", s):
        return f"ST{s}"
    return s


def clean_spa(raw):
    s = clean_type(raw)
    if s == "Not Assigned":
        return "Not Assigned"
    if re.match(r"^t\d+$", s, re.IGNORECASE):
        return s.lower()
    return "Not Assigned"


def clean_agr(raw):
    s = clean_type(raw).upper()
    if s in {"I", "II", "III", "IV"}:
        return s
    return "Not Assigned"


def clean_cap(raw):
    s = clean_type(raw)
    low = s.lower().replace("type", "").strip()
    if low == "5":
        return "Type 5"
    if low == "8":
        return "Type 8"
    return "Not Assigned"


def clean_completeness(raw):
    s = str(raw or "").strip()
    if not s:
        return "—"
    low = s.lower()
    if "complete" in low and "incomplete" not in low:
        return "Complete"
    if "partial" in low:
        return "Partial"
    if "fragment" in low:
        return "Fragment"
    if "missing" in low or "none" in low:
        return "Missing"
    return s


def shorten_sccmec(raw):
    """SCCmec_type_IV(2B) -> IV(2B)  (for compact display in stat cards)."""
    s = str(raw or "").strip()
    if not s or s in ("-", "Not Assigned"):
        return s or "-"
    return re.sub(r"^SCCmec_type_", "", s)


# ---------------------------------------------------------------------------
# Per-module loaders
# ---------------------------------------------------------------------------
def load_mlst(path, st_cc):
    data = {}
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return data
    hit = miss = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = normalize_acc(row.get("accession", ""))
            if not acc:
                continue
            st = clean_st(row.get("ST", ""))
            cc = st_cc.get(st, "") if st != "Not Assigned" else ""
            if cc:
                hit += 1
            else:
                miss += 1
            data[acc] = {
                "mlst_st":     st,
                "mlst_cc":     cc if cc else "NA",
                "mlst_status": clean_type(row.get("MLST_Status", "")),
            }
    total = hit + miss
    cov = round(hit / total * 100, 1) if total else 0
    print(f"   ST→CC coverage: {hit:,}/{total:,} ({cov}%)")
    return data


def load_spa(path):
    data = {}
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = normalize_acc(row.get("accession", ""))
            if not acc:
                continue
            data[acc] = {"spa_type": clean_spa(row.get("spa_Type", ""))}
    return data


def load_cge(path):
    data = {}
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = normalize_acc(row.get("accession", ""))
            if not acc:
                continue
            data[acc] = {
                "cge_sccmec_type": clean_type(row.get("SCCmec_Type", "")),
                "cge_mrsa_status": clean_mrsa(row.get("MRSA_Status", "")),
                "cge_confidence":  clean_type(row.get("Confidence", ""), "—"),
                "cge_method":      clean_type(row.get("Prediction_Method", ""), "—"),
            }
    return data


def load_rpet(path):
    data = {}
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = normalize_acc(row.get("accession", ""))
            if not acc:
                continue
            data[acc] = {
                "rpet_sccmec_type": clean_type(row.get("sccmec_type", "")),
                "rpet_subtype":     clean_type(row.get("sccmec_subtype", "")),
                "rpet_mrsa_status": clean_mrsa(row.get("mrsa_status", "")),
                "rpet_mec_class":   clean_type(row.get("mec_class", ""), "—"),
            }
    return data


def load_capsule(path):
    data = {}
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = normalize_acc(row.get("accession", ""))
            if not acc:
                continue
            data[acc] = {
                "cap_type":         clean_cap(row.get("cap_type", "")),
                "cap_completeness": clean_completeness(row.get("cap_completeness", "")),
            }
    return data


def load_agr(path):
    data = {}
    if not path.exists():
        print(f"⚠️  {path.name} not found")
        return data
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            acc = normalize_acc(row.get("accession", ""))
            if not acc:
                continue
            data[acc] = {
                "agr_type":  clean_agr(row.get("agr_Type", "")),
                "agr_group": clean_type(row.get("agr_Group", ""), "—"),
            }
    return data


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------
def merge_all(mlst, spa, cge, rpet, capsule, agr):
    all_acc = sorted(set(mlst) | set(spa) | set(cge) | set(rpet) | set(capsule) | set(agr))
    rows = []
    for acc in all_acc:
        c = cge.get(acc, {})
        r = rpet.get(acc, {})
        rpet_mrsa = r.get("rpet_mrsa_status", "Unknown")
        cge_mrsa  = c.get("cge_mrsa_status", "Unknown")

        if cge_mrsa in MRSA_VALUES:
            mrsa_final = cge_mrsa
        elif rpet_mrsa in MRSA_VALUES:
            mrsa_final = rpet_mrsa
        else:
            mrsa_final = "Unknown"

        row = {"accession": acc, "mrsa_final": mrsa_final}
        row.update(mlst.get(acc, {}))
        row.update(spa.get(acc, {}))
        row.update(c)
        row.update(r)
        row.update(capsule.get(acc, {}))
        row.update(agr.get(acc, {}))

        for col in MASTER_COLUMNS:
            row.setdefault(col["key"], "—")
        saurus_common.attach_metadata(row, META)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Stats + cross-tabs
# ---------------------------------------------------------------------------

def _build_filter_values(rows):
    """Populate a dropdown option-list for EVERY key in FILTER_DEFS.
    Normalizes float-like years (2015.0 -> 2015) and sorts numerically."""
    exclude = {"", "—", "nan", "NaN", "None", "None ", "NA", "N/A", "Not Assigned"}
    preferred = {
        "mrsa_final": ["MRSA", "MSSA", "Unknown"],
    }
    out = {}
    for key, _label in FILTER_DEFS:
        if key in preferred:
            out[key] = preferred[key]
            continue

        seen, vals = set(), []
        for r in rows:
            v = str(r.get(key, "")).strip()
            if not v or v in exclude:
                continue
            if key == "year":
                try:
                    v = str(int(float(v)))
                except (ValueError, TypeError):
                    pass
            if v not in seen:
                seen.add(v)
                vals.append(v)

        def _sort(v):
            try:
                return (0, float(v))
            except ValueError:
                return (1, v)
        vals.sort(key=_sort)
        out[key] = vals
    return out


def compute_stats(rows):
    total = len(rows)
    mrsa    = sum(1 for r in rows if r["mrsa_final"] == "MRSA")
    mssa    = sum(1 for r in rows if r["mrsa_final"] == "MSSA")
    unknown = total - mrsa - mssa
    mrsa_rate = round(mrsa / total * 100, 1) if total else 0

    # Overall ST / CC counters
    all_st_counter = Counter(
        r["mlst_st"] for r in rows
        if r["mlst_st"] not in ("Not Assigned", "—", "")
    )
    all_cc_counter = Counter(
        r["mlst_cc"] for r in rows
        if r.get("mlst_cc") and r["mlst_cc"] not in ("", "NA")
    )
    unique_sts = len(all_st_counter)
    unique_ccs = len(all_cc_counter)

    # MRSA-only top counters
    mrsa_st_counter = Counter(
        r["mlst_st"] for r in rows
        if r["mrsa_final"] == "MRSA" and r["mlst_st"] not in ("Not Assigned", "—", "")
    )
    mrsa_cc_counter = Counter(
        r["mlst_cc"] for r in rows
        if r["mrsa_final"] == "MRSA" and r.get("mlst_cc") and r["mlst_cc"] not in ("", "NA")
    )
    top_st  = mrsa_st_counter.most_common(1)[0] if mrsa_st_counter else ("—", 0)
    top_cc  = mrsa_cc_counter.most_common(1)[0] if mrsa_cc_counter else ("—", 0)

    mrsa_rpet_counter = Counter(
        r["rpet_sccmec_type"] for r in rows
        if r["mrsa_final"] == "MRSA"
        and r["rpet_sccmec_type"] not in ("Not Assigned", "—", "")
    )
    top_scc_rpet = mrsa_rpet_counter.most_common(1)[0] if mrsa_rpet_counter else ("—", 0)

    mrsa_cge_counter = Counter(
        r["cge_sccmec_type"] for r in rows
        if r["mrsa_final"] == "MRSA"
        and r["cge_sccmec_type"] not in ("Not Assigned", "—", "")
    )
    top_scc_cge = mrsa_cge_counter.most_common(1)[0] if mrsa_cge_counter else ("—", 0)

    def uniq(field, exclude_empty=True):
        c = Counter(r.get(field, "") for r in rows)
        vals = [v for v in c if v and v != "—"]
        if exclude_empty:
            vals = [v for v in vals if v not in ("", "Not Assigned", "Unknown", "NA")]
        return sorted(vals, key=lambda v: (-c[v], v))

    return {
        "total": total,
        "mrsa": mrsa, "mssa": mssa, "unknown": unknown,
        "mrsa_rate": mrsa_rate,
        "unique_sts": unique_sts,
        "unique_ccs": unique_ccs,
        "top_st":  top_st[0],  "top_st_count":  top_st[1],
        "top_cc":  top_cc[0],  "top_cc_count":  top_cc[1],
        "top_scc_rpet":         top_scc_rpet[0],
        "top_scc_rpet_count":   top_scc_rpet[1],
        "top_scc_cge":          shorten_sccmec(top_scc_cge[0]),
        "top_scc_cge_count":    top_scc_cge[1],
        "filter_values": _build_filter_values(rows),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def compute_cross_tabs(rows):
    result = {}
    for field, label in CROSS_TAB_FIELDS:
        agg = defaultdict(lambda: {"MRSA": 0, "MSSA": 0, "Unknown": 0})
        for r in rows:
            v = r.get(field, "—")
            if v in ("—", "Not Assigned", "", "NA"):
                continue
            status = r["mrsa_final"]
            if status not in agg[v]:
                agg[v][status] = 0
            agg[v][status] += 1

        table = []
        for value, counts in agg.items():
            total = counts["MRSA"] + counts["MSSA"] + counts["Unknown"]
            typed = counts["MRSA"] + counts["MSSA"]
            mrsa_pct = round(counts["MRSA"] / typed * 100, 1) if typed else 0
            table.append({
                "value": value,
                "mrsa": counts["MRSA"],
                "mssa": counts["MSSA"],
                "unknown": counts["Unknown"],
                "total": total,
                "mrsa_pct": mrsa_pct,
            })
        table.sort(key=lambda x: -x["total"])
        result[field] = {"label": label, "rows": table}
    return result


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
CSS = """
:root {
    --gold: #d4af37; --navy: #0a1628; --accent: __ACCENT__;
    --bg: #f8fafc; --card: #fff; --text: #1e293b;
    --muted: #64748b; --border: #e2e8f0;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5; }

.saurus-nav {
    background: var(--navy); color: #fff; padding: 20px 32px;
    display: flex; align-items: center; justify-content: space-between;
    gap: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    position: sticky; top: 0; z-index: 100;
}
.saurus-nav .brand { display: flex; align-items: center; gap: 20px; text-decoration: none; flex-shrink: 0; }
.saurus-nav .brand-emoji { font-size: 5.6em; line-height: 1; flex-shrink: 0; }
.saurus-nav .brand-text { display: flex; flex-direction: column; gap: 3px; }
.saurus-nav .brand-name { font-weight: 800; font-size: 3.45em; letter-spacing: 1px; color: var(--gold); line-height: 1; }
.saurus-nav .brand-tagline { font-size: 1.0em; font-weight: 400; color: #94a3b8; line-height: 1.15; max-width: 520px; }
.saurus-nav .links { display: flex; gap: 2px; align-items: center; flex-wrap: wrap; }
.saurus-nav .links a {
    color: #cbd5e1; text-decoration: none; padding: 6px 10px;
    border-radius: 6px; font-size: 0.85em; font-weight: 500;
    transition: all 0.15s; white-space: nowrap;
}
.saurus-nav .links a:hover { background: rgba(255,255,255,0.08); color: white; }
.saurus-nav .links a.active { background: var(--gold); color: var(--navy); font-weight: 600; }

.page-header {
    background: linear-gradient(135deg, #7f1d1d 0%, var(--navy) 100%);
    color: white; padding: 40px 32px 32px;
}
.page-header h1 { font-size: 2.2em; margin-bottom: 6px; font-weight: 700; }
.page-header .subtitle { color: #fca5a5; font-size: 1.05em; margin-bottom: 24px; }
.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; max-width: 1400px; }
.stat-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px; padding: 16px 18px;
    backdrop-filter: blur(8px);
}
.stat-card.mrsa { background: rgba(220,38,38,0.18); border-color: rgba(220,38,38,0.35); }
.stat-card.mssa { background: rgba(59,130,246,0.15); border-color: rgba(59,130,246,0.3); }
.stat-card.cc   { background: rgba(139,92,246,0.15); border-color: rgba(139,92,246,0.3); }
.stat-card .value { font-size: 1.9em; font-weight: 800; color: var(--gold); line-height: 1.1; }
.stat-card.mrsa .value { color: #fca5a5; }
.stat-card.mssa .value { color: #93c5fd; }
.stat-card.cc .value { color: #c4b5fd; }
.stat-card .label { font-size: 0.82em; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

main { max-width: 1400px; margin: 0 auto; padding: 28px 32px 60px; }

.tabs {
    display: flex; gap: 6px; margin-bottom: 18px;
    background: var(--card); padding: 8px;
    border-radius: 12px; border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    width: fit-content;
}
.tab-btn {
    padding: 10px 22px; border: none; border-radius: 8px;
    background: transparent; color: var(--muted);
    font-size: 0.92em; font-weight: 700;
    cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.tab-btn:hover { background: #f1f5f9; color: var(--text); }
.tab-btn.active { background: var(--accent); color: white; box-shadow: 0 3px 10px __ACCENT__55; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }

.controls {
    background: var(--card); border-radius: 12px; padding: 16px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    margin-bottom: 20px;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
}
.search-wrapper { position: relative; flex: 1; min-width: 260px; }
.search-wrapper input {
    width: 100%; padding: 10px 14px 10px 40px;
    border: 2px solid var(--border); border-radius: 8px;
    font-size: 0.95em; font-family: inherit; outline: none;
    transition: border 0.15s;
}
.search-wrapper input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px __ACCENT__22; }
.search-wrapper::before {
    content: '🔍'; position: absolute; left: 14px; top: 50%;
    transform: translateY(-50%); font-size: 14px; opacity: 0.6;
}
.search-hint { font-size: 0.72em; color: var(--muted); margin-top: 4px; padding-left: 4px; }
.search-hint code { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; }

.filter-label {
    display: flex; flex-direction: column; gap: 4px;
    font-size: 0.78em; color: var(--muted); font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.3px;
}
.filter-select {
    padding: 9px 12px; border: 2px solid var(--border); border-radius: 8px;
    background: white; font-size: 0.9em; font-family: inherit;
    color: var(--text); min-width: 130px; cursor: pointer; outline: none;
    transition: border 0.15s;
}
.filter-select:focus { border-color: var(--accent); }

.col-toggle-wrap { position: relative; }
.col-toggle-btn {
    padding: 9px 14px; border: 2px solid var(--border); border-radius: 8px;
    background: white; font-family: inherit; font-size: 0.88em; font-weight: 700;
    color: var(--muted); cursor: pointer; transition: all 0.15s;
}
.col-toggle-btn:hover { border-color: var(--accent); color: var(--accent); }
.col-panel {
    position: absolute; right: 0; top: calc(100% + 6px);
    background: white; border: 1px solid var(--border); border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.12);
    padding: 10px 14px; min-width: 220px; max-height: 320px; overflow-y: auto;
    z-index: 50; display: none;
}
.col-panel.open { display: block; }
.col-panel label { display: flex; align-items: center; gap: 8px; padding: 6px 4px; font-size: 0.88em; cursor: pointer; border-radius: 4px; }
.col-panel label:hover { background: #f8fafc; }

.export-bar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-left: auto; }
.scope-select {
    padding: 8px 12px; border: 2px solid var(--border); border-radius: 8px;
    background: white; font-size: 0.88em; font-family: inherit;
    cursor: pointer; font-weight: 600; color: var(--muted);
}
.export-btn {
    padding: 9px 16px; border: none; border-radius: 8px;
    font-size: 0.88em; font-weight: 600; cursor: pointer;
    transition: all 0.15s; color: white; background: var(--accent); font-family: inherit;
}
.export-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px __ACCENT__55; }
.export-btn.secondary { background: #64748b; }
.sel-counter {
    padding: 6px 12px; background: #fee2e2; color: #991b1b;
    border-radius: 20px; font-size: 0.82em; font-weight: 700; white-space: nowrap;
}

.table-wrap {
    background: var(--card); border-radius: 12px; border: 1px solid var(--border);
    overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.table-scroll { max-height: 70vh; overflow: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
thead th {
    background: #f1f5f9; padding: 12px 14px; text-align: left;
    font-weight: 700; color: #334155; font-size: 0.85em;
    text-transform: uppercase; letter-spacing: 0.3px;
    position: sticky; top: 0; z-index: 5;
    cursor: pointer; user-select: none;
    border-bottom: 2px solid var(--border); white-space: nowrap;
}
thead th:hover { background: #e2e8f0; }
thead th.sortable::after { content: ' ⇅'; opacity: 0.35; font-size: 0.85em; }
thead th.sorted-asc::after { content: ' ▲'; opacity: 1; color: var(--accent); }
thead th.sorted-desc::after { content: ' ▼'; opacity: 1; color: var(--accent); }
thead th.checkbox-col, tbody td.checkbox-col { width: 40px; text-align: center; padding: 8px; }
tbody td { padding: 11px 14px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
tbody tr:hover td { background: #fef2f2; }
tbody tr.selected td { background: #fee2e2 !important; }
tbody tr.is-mrsa td:first-child { border-left: 3px solid #dc2626; }
tbody tr.is-mssa td:first-child { border-left: 3px solid #3b82f6; }

.mrsa-pill { display: inline-block; padding: 3px 12px; border-radius: 12px; font-weight: 800; font-size: 0.82em; }
.mrsa-positive { background: #fee2e2; color: #991b1b; }
.mrsa-negative { background: #dbeafe; color: #1e40af; }
.mrsa-unknown  { background: #f1f5f9; color: #64748b; font-style: italic; font-weight: 600; }

.st-pill { display: inline-block; padding: 3px 10px; border-radius: 12px; background: #dbeafe; color: #1e40af; font-weight: 700; font-size: 0.85em; font-family: 'SF Mono', Monaco, monospace; }
.cc-pill { display: inline-block; padding: 3px 10px; border-radius: 12px; background: #ede9fe; color: #6d28d9; font-weight: 700; font-size: 0.85em; font-family: 'SF Mono', Monaco, monospace; }
.cc-na { color: #94a3b8; font-style: italic; font-size: 0.9em; }
.spa-pill { display: inline-block; padding: 3px 10px; border-radius: 12px; background: #d1fae5; color: #065f46; font-weight: 700; font-size: 0.85em; font-family: 'SF Mono', Monaco, monospace; }
.agr-pill { display: inline-block; padding: 3px 12px; border-radius: 12px; font-weight: 800; font-size: 0.82em; font-family: 'SF Mono', Monaco, monospace; }
.agr-I   { background: #d1fae5; color: #065f46; }
.agr-II  { background: #dbeafe; color: #1e40af; }
.agr-III { background: #fef3c7; color: #92400e; }
.agr-IV  { background: #fee2e2; color: #991b1b; }
.agr-NA  { background: #f1f5f9; color: #94a3b8; font-style: italic; font-weight: 600; }
.cap-Type5 { display: inline-block; padding: 3px 12px; border-radius: 12px; background: #d1fae5; color: #065f46; font-weight: 700; font-size: 0.82em; }
.cap-Type8 { display: inline-block; padding: 3px 12px; border-radius: 12px; background: #fee2e2; color: #991b1b; font-weight: 700; font-size: 0.82em; }
.cap-NA    { color: #94a3b8; font-style: italic; font-size: 0.9em; }
.sccmec-pill { display: inline-block; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.82em; font-family: 'SF Mono', Monaco, monospace; white-space: nowrap; }
.sccmec-I    { background: #dbeafe; color: #1e40af; }
.sccmec-II   { background: #d1fae5; color: #065f46; }
.sccmec-III  { background: #fef3c7; color: #92400e; }
.sccmec-IV   { background: #fee2e2; color: #991b1b; }
.sccmec-V    { background: #f3e8ff; color: #6b21a8; }
.sccmec-VI   { background: #ccfbf1; color: #115e59; }
.sccmec-VII  { background: #fce7f3; color: #9f1239; }
.sccmec-VIII { background: #ffedd5; color: #9a3412; }
.sccmec-X    { background: #f1f5f9; color: #475569; }
.sccmec-NA   { color: #94a3b8; font-style: italic; font-size: 0.9em; }
.subtype-pill { display: inline-block; padding: 3px 10px; border-radius: 12px; background: #ffedd5; color: #9a3412; font-weight: 700; font-size: 0.85em; font-family: 'SF Mono', Monaco, monospace; }
.subtype-NA { color: #94a3b8; font-style: italic; font-size: 0.9em; }
.conf-high { color: #15803d; font-weight: 700; }
.conf-med  { color: #b45309; font-weight: 700; }
.conf-low  { color: #b91c1c; font-weight: 700; }
.mono-field { font-family: 'SF Mono', Monaco, monospace; font-size: 0.85em; color: #475569; }
.dim { color: #94a3b8; font-style: italic; }

.breakdown-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(520px, 1fr)); gap: 20px; }
.breakdown-card {
    background: var(--card); border-radius: 12px; border: 1px solid var(--border);
    overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.breakdown-card h3 {
    padding: 14px 18px; background: #f8fafc; color: #334155;
    border-bottom: 1px solid var(--border); font-size: 1.05em;
    font-weight: 700; display: flex; align-items: center; justify-content: space-between;
}
.breakdown-card h3 .count-badge {
    background: #e2e8f0; color: #475569;
    padding: 2px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 700;
}
.breakdown-scroll { max-height: 500px; overflow-y: auto; }
.breakdown-card table { font-size: 0.85em; }
.breakdown-card thead th { padding: 10px 12px; font-size: 0.78em; background: #f1f5f9; }
.breakdown-card tbody td { padding: 8px 12px; }
.mrsa-bar { height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-top: 3px; min-width: 80px; }
.mrsa-bar-fill { height: 100%; background: #dc2626; border-radius: 4px; }
.pct-cell { display: flex; flex-direction: column; gap: 2px; }
.pct-value { font-weight: 700; font-size: 0.9em; }
.ct-value { font-family: 'SF Mono', Monaco, monospace; font-weight: 700; color: #334155; font-size: 0.88em; }

.pagination {
    display: flex; gap: 12px; align-items: center; justify-content: center;
    padding: 14px 18px; background: #f8fafc;
    border-top: 1px solid var(--border); font-size: 0.88em; flex-wrap: wrap;
}
.pagination button {
    padding: 7px 14px; border: 1px solid var(--border); background: white;
    border-radius: 6px; cursor: pointer; font-weight: 600;
    color: var(--text); font-family: inherit;
}
.pagination button:hover:not(:disabled) { background: var(--accent); color: white; border-color: var(--accent); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.pagination .page-info { color: var(--muted); font-weight: 600; }
.page-size-label { display: flex; align-items: center; gap: 6px; font-size: 0.85em; color: var(--muted); font-weight: 600; margin-left: auto; white-space: nowrap; }
.page-size-label select { padding: 5px 8px; border: 1px solid var(--border); border-radius: 6px; background: white; font-family: inherit; font-size: 1em; cursor: pointer; font-weight: 700; color: var(--text); }

.empty-state { text-align: center; padding: 60px 20px; color: var(--muted); }
.empty-state .icon { font-size: 3em; opacity: 0.4; margin-bottom: 12px; }

.saurus-footer {
    background: var(--navy); color: #94a3b8; padding: 32px;
    text-align: center; font-size: 0.88em; margin-top: 60px;
}
.saurus-footer a { color: var(--gold); text-decoration: none; }
.saurus-footer a:hover { text-decoration: underline; }
.saurus-footer .footer-line { margin: 6px 0; }
.saurus-footer .full-name { color: #cbd5e1; font-size: 0.95em; letter-spacing: 0.2px; }

@media (max-width: 900px) {
    .saurus-nav { flex-direction: column; align-items: flex-start; gap: 12px; }
    .saurus-nav .brand-tagline { max-width: 100%; }
    .saurus-nav .brand-emoji { font-size: 3.6em; }
    .saurus-nav .brand-name { font-size: 2.2em; }
    .breakdown-grid { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
    .controls { flex-direction: column; align-items: stretch; }
    .export-bar { margin-left: 0; }
    .page-header { padding: 28px 20px 24px; }
    main { padding: 20px 16px 40px; }
    .saurus-nav { padding: 14px 16px; }
    .page-size-label { margin-left: 0; }
    .tabs { width: 100%; flex-direction: column; }
}
"""


# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------
JS = """
const DATA = __DATA__;
const STATS = __STATS__;
const COLUMNS = __COLUMNS__;
const CROSS_TABS = __CROSS_TABS__;
const ACCENT = "__ACCENT__";

let filtered = DATA.slice();
let currentPage = 1;
let pageSize = 100;
let sortKey = null;
let sortAsc = true;
const selected = new Set();

const tbody = document.getElementById('table-body');
const thead = document.getElementById('table-head');
const searchInput = document.getElementById('search');
const paginationEl = document.getElementById('pagination');
const selCounter = document.getElementById('sel-counter');
const statRow = document.getElementById('stat-row');
const colPanel = document.getElementById('col-panel');
const colToggleBtn = document.getElementById('col-toggle-btn');

function renderStats() {
    const cards = [
        { value: STATS.total.toLocaleString(), label: 'Total Samples', cls: '' },
        { value: STATS.mrsa.toLocaleString(),  label: 'MRSA',           cls: 'mrsa' },
        { value: STATS.mssa.toLocaleString(),  label: 'MSSA',           cls: 'mssa' },
        { value: STATS.mrsa_rate + '%',        label: 'MRSA Rate',      cls: 'mrsa' },
        { value: STATS.unique_ccs.toLocaleString(), label: 'Unique CCs', cls: 'cc' },
        { value: STATS.unique_sts.toLocaleString(), label: 'Unique STs', cls: '' },
        { value: STATS.top_cc,                 label: 'Top MRSA CC',    cls: 'cc' },
        { value: STATS.top_st,                 label: 'Top MRSA ST',    cls: '' },
        { value: STATS.top_scc_rpet,           label: 'Top SCCmec (RPet)', cls: '' },
        { value: STATS.top_scc_cge,            label: 'Top SCCmec (CGE)',  cls: '' },
    ];
    statRow.innerHTML = cards.map(c =>
        '<div class="stat-card ' + c.cls + '"><div class="value">' + c.value + '</div><div class="label">' + c.label + '</div></div>'
    ).join('');
    document.getElementById('generated-at').textContent = STATS.generated;
}

function getColumnState() {
    const key = 'saurus_mrsa_cols';
    const saved = localStorage.getItem(key);
    if (saved) {
        try {
            const arr = JSON.parse(saved);
            if (Array.isArray(arr) && arr.length === COLUMNS.length) return arr;
        } catch (e) {}
    }
    return COLUMNS.map(c => c.default_visible);
}
function saveColumnState(state) { localStorage.setItem('saurus_mrsa_cols', JSON.stringify(state)); }
function getVisibleColumns() {
    const state = getColumnState();
    return COLUMNS.filter((c, i) => state[i]);
}

function renderHead() {
    const cols = getVisibleColumns();
    let html = '<tr><th class="checkbox-col"><input type="checkbox" id="select-all"></th>';
    for (const col of cols) {
        html += '<th class="sortable" data-key="' + col.key + '" data-type="' + col.type + '">' + col.label + '</th>';
    }
    html += '</tr>';
    thead.innerHTML = html;

    thead.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const key = th.dataset.key;
            if (sortKey === key) sortAsc = !sortAsc;
            else { sortKey = key; sortAsc = true; }
            applySort(); renderBody();
        });
    });
    document.getElementById('select-all').addEventListener('change', e => {
        if (e.target.checked) filtered.forEach(r => selected.add(r.accession));
        else filtered.forEach(r => selected.delete(r.accession));
        renderBody();
    });
}

function esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function extractRoman(s) {
    const m = String(s).match(/(XIII|XII|XI|VIII|VII|VI|IV|IX|X|V|III|II|I)/);
    return m ? m[1] : 'X';
}

function rowMatches(row, term) {
    if (!term) return true;
    const tokens = term.toLowerCase().trim().split(/\\s+/).filter(Boolean);
    for (const tok of tokens) {
        // exact ST/CC match
        if (/^(st|cc)\\d+$/.test(tok)) {
            const found = String(row.mlst_st || '').toLowerCase() === tok
                       || String(row.mlst_cc || '').toLowerCase() === tok;
            if (!found) return false;
            continue;
        }
        let found = false;
        for (const k in row) {
            if (String(row[k] == null ? '' : row[k]).toLowerCase().includes(tok)) {
                found = true; break;
            }
        }
        if (!found) return false;
    }
    return true;
}

function applySort() {
    if (!sortKey) return;
    filtered.sort((a, b) => {
        const av = a[sortKey] == null ? '' : a[sortKey];
        const bv = b[sortKey] == null ? '' : b[sortKey];
        const an = parseFloat(String(av).replace(/[^0-9.\\-]/g, ''));
        const bn = parseFloat(String(bv).replace(/[^0-9.\\-]/g, ''));
        if (!isNaN(an) && !isNaN(bn)) return sortAsc ? an - bn : bn - an;
        return sortAsc
            ? String(av).localeCompare(String(bv))
            : String(bv).localeCompare(String(av));
    });
}

function applyFilters() {
    const term = searchInput.value.trim();
    const activeFilters = {};
    document.querySelectorAll('.filter-select').forEach(sel => {
        if (sel.value) activeFilters[sel.dataset.filterKey] = sel.value;
    });
    filtered = DATA.filter(row => {
        if (!rowMatches(row, term)) return false;
        for (const k in activeFilters) {
            if (String(row[k] == null ? '' : row[k]) !== activeFilters[k]) return false;
        }
        return true;
    });
    applySort();
    currentPage = 1;
    renderBody();
    renderPagination();
}

function getVisibleRows() {
    const start = (currentPage - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
}

function renderBody() {
    const cols = getVisibleColumns();
    const rows = getVisibleRows();
    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="' + (cols.length + 1) + '"><div class="empty-state"><div class="icon">🔍</div><div>No matching rows</div></div></td></tr>';
        updateSelCounter(); updateSelectAll(); return;
    }
    tbody.innerHTML = rows.map(row => {
        const isSel = selected.has(row.accession);
        const status = row.mrsa_final;
        let rowCls = isSel ? 'selected ' : '';
        if (status === 'MRSA') rowCls += 'is-mrsa';
        else if (status === 'MSSA') rowCls += 'is-mssa';

        let cells = '<td class="checkbox-col"><input type="checkbox" class="row-check" data-acc="' + esc(row.accession) + '"' + (isSel ? ' checked' : '') + '></td>';
        for (const col of cols) {
            cells += '<td>' + formatCell(col.key, row[col.key]) + '</td>';
        }
        return '<tr class="' + rowCls.trim() + '" data-acc="' + esc(row.accession) + '">' + cells + '</tr>';
    }).join('');

    tbody.querySelectorAll('.row-check').forEach(cb => {
        cb.addEventListener('change', e => {
            const acc = e.target.dataset.acc;
            if (e.target.checked) selected.add(acc);
            else selected.delete(acc);
            e.target.closest('tr').classList.toggle('selected', e.target.checked);
            updateSelCounter(); updateSelectAll();
        });
    });
    updateSelCounter(); updateSelectAll();
}

function updateSelectAll() {
    const cb = document.getElementById('select-all');
    if (!cb) return;
    const allSel = filtered.length > 0 && filtered.every(r => selected.has(r.accession));
    const anySel = filtered.some(r => selected.has(r.accession));
    cb.checked = allSel;
    cb.indeterminate = anySel && !allSel;
}

function formatCell(key, val) {
    const v = val == null ? '' : String(val);

    if (key === 'mrsa_final') {
        const u = v.toUpperCase();
        let cls = 'mrsa-unknown';
        if (u === 'MRSA') cls = 'mrsa-positive';
        else if (u === 'MSSA') cls = 'mrsa-negative';
        return '<span class="mrsa-pill ' + cls + '">' + esc(v || '—') + '</span>';
    }
    if (key === 'mlst_st') {
        if (!v || v === 'Not Assigned') return '<span class="dim">—</span>';
        return '<span class="st-pill">' + esc(v) + '</span>';
    }
    if (key === 'mlst_cc') {
        if (!v || v === 'NA' || v === '—') return '<span class="cc-na">—</span>';
        return '<span class="cc-pill">' + esc(v) + '</span>';
    }
    if (key === 'spa_type') {
        if (!v || v === 'Not Assigned') return '<span class="dim">—</span>';
        return '<span class="spa-pill">' + esc(v) + '</span>';
    }
    if (key === 'agr_type') {
        const u = v.toUpperCase();
        let cls = 'agr-NA';
        if (u === 'I' || u === 'II' || u === 'III' || u === 'IV') cls = 'agr-' + u;
        return '<span class="agr-pill ' + cls + '">' + esc(v || '—') + '</span>';
    }
    if (key === 'cap_type') {
        if (v === 'Type 5') return '<span class="cap-Type5">Type 5</span>';
        if (v === 'Type 8') return '<span class="cap-Type8">Type 8</span>';
        return '<span class="cap-NA">—</span>';
    }
    if (key === 'rpet_sccmec_type' || key === 'cge_sccmec_type') {
        if (v === 'Not Assigned' || !v || v === '—') {
            return '<span class="sccmec-NA">Not Assigned</span>';
        }
        const roman = extractRoman(v);
        return '<span class="sccmec-pill sccmec-' + roman + '">' + esc(v) + '</span>';
    }
    if (key === 'rpet_subtype') {
        if (v === 'Not Assigned' || !v || v === '—') return '<span class="subtype-NA">—</span>';
        return '<span class="subtype-pill">' + esc(v) + '</span>';
    }
    if (key === 'cge_confidence') {
        const u = v.toUpperCase();
        let cls = '';
        if (u.indexOf('VERY') !== -1 || u === 'HIGH') cls = 'conf-high';
        else if (u.indexOf('MEDIUM') !== -1 || u.indexOf('MODERATE') !== -1) cls = 'conf-med';
        else if (u.indexOf('LOW') !== -1) cls = 'conf-low';
        return cls ? '<span class="' + cls + '">' + esc(v) + '</span>' : esc(v);
    }
    if (key === 'mlst_status') {
        const ok = v === 'Assigned';
        return '<span style="color:' + (ok ? '#15803d' : '#b91c1c') + ';font-weight:600;">' + esc(v || '—') + '</span>';
    }
    if (key === 'rpet_mec_class') {
        if (!v || v === '—') return '<span class="dim">—</span>';
        return '<span class="mono-field">' + esc(v) + '</span>';
    }
    return esc(v);
}

function renderPagination() {
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    paginationEl.innerHTML =
        '<button id="prev-page"' + (currentPage === 1 ? ' disabled' : '') + '>← Prev</button>' +
        '<span class="page-info">Page ' + currentPage + ' / ' + totalPages + ' · ' + filtered.length.toLocaleString() + ' rows</span>' +
        '<button id="next-page"' + (currentPage === totalPages ? ' disabled' : '') + '>Next →</button>' +
        '<label class="page-size-label">Show <select id="page-size">' +
        '<option value="20"' + (pageSize === 20 ? ' selected' : '') + '>20</option>' +
        '<option value="50"' + (pageSize === 50 ? ' selected' : '') + '>50</option>' +
        '<option value="100"' + (pageSize === 100 ? ' selected' : '') + '>100</option>' +
        '</select> per page</label>';
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) { currentPage--; renderBody(); renderPagination(); }
    });
    document.getElementById('next-page').addEventListener('click', () => {
        if (currentPage < totalPages) { currentPage++; renderBody(); renderPagination(); }
    });
    document.getElementById('page-size').addEventListener('change', e => {
        pageSize = parseInt(e.target.value);
        currentPage = 1;
        renderBody(); renderPagination();
    });
}

function updateSelCounter() { selCounter.textContent = selected.size.toLocaleString() + ' selected'; }

function renderColumnPanel() {
    const state = getColumnState();
    colPanel.innerHTML = COLUMNS.map((col, i) =>
        '<label><input type="checkbox" data-col-idx="' + i + '"' + (state[i] ? ' checked' : '') + '><span>' + col.label + '</span></label>'
    ).join('');
    colPanel.querySelectorAll('input[type=checkbox]').forEach(cb => {
        cb.addEventListener('change', e => {
            const idx = parseInt(e.target.dataset.colIdx);
            const newState = getColumnState();
            newState[idx] = e.target.checked;
            saveColumnState(newState);
            renderHead(); renderBody();
        });
    });
}
colToggleBtn.addEventListener('click', e => { e.stopPropagation(); colPanel.classList.toggle('open'); });
document.addEventListener('click', e => {
    if (!colPanel.contains(e.target) && e.target !== colToggleBtn) colPanel.classList.remove('open');
});

function renderCrossTabs() {
    const container = document.getElementById('breakdown-grid');
    const html = Object.keys(CROSS_TABS).map(field => {
        const tab = CROSS_TABS[field];
        const rowsHtml = tab.rows.map(r => {
            const barWidth = Math.max(2, r.mrsa_pct);
            return '<tr>' +
                '<td><strong>' + esc(r.value) + '</strong></td>' +
                '<td style="color:#991b1b;font-weight:700;">' + r.mrsa + '</td>' +
                '<td style="color:#1e40af;font-weight:700;">' + r.mssa + '</td>' +
                '<td style="color:#64748b;">' + r.unknown + '</td>' +
                '<td>' + r.total + '</td>' +
                '<td><div class="pct-cell"><span class="pct-value">' + r.mrsa_pct.toFixed(1) + '%</span>' +
                '<div class="mrsa-bar"><div class="mrsa-bar-fill" style="width:' + barWidth + '%;"></div></div></div></td>' +
                '</tr>';
        }).join('');
        return '<div class="breakdown-card">' +
            '<h3><span>' + tab.label + '</span><span class="count-badge">' + tab.rows.length + ' unique</span></h3>' +
            '<div class="breakdown-scroll"><table>' +
            '<thead><tr>' +
            '<th>' + tab.label + '</th>' +
            '<th>MRSA</th><th>MSSA</th><th>Unknown</th><th>Total</th><th>% MRSA</th>' +
            '</tr></thead><tbody>' + rowsHtml + '</tbody></table></div></div>';
    }).join('');
    container.innerHTML = html;
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

function getExportRows() {
    const scope = document.getElementById('export-scope').value;
    if (scope === 'selected') return DATA.filter(r => selected.has(r.accession));
    return filtered;
}
function download(filename, content, mime) {
    const blob = new Blob([content], { type: mime + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
}
document.querySelectorAll('.export-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const fmt = btn.dataset.fmt;
        const rows = getExportRows();
        const stamp = new Date().toISOString().slice(0, 10);
        const base = 'saurus_mrsa_' + stamp;
        const cols = getVisibleColumns();

        if (fmt === 'tsv' || fmt === 'csv') {
            const sep = fmt === 'tsv' ? '\\t' : ',';
            const quote = fmt === 'csv';
            const hdr = cols.map(c => quote ? '"' + c.label + '"' : c.label).join(sep);
            const lines = [hdr];
            for (const r of rows) {
                const vals = cols.map(c => {
                    const v = String(r[c.key] == null ? '' : r[c.key]);
                    if (quote) return '"' + v.replace(/"/g, '""') + '"';
                    return v.replace(/\\t/g, ' ');
                });
                lines.push(vals.join(sep));
            }
            download(base + '.' + fmt, lines.join('\\n'), fmt === 'tsv' ? 'text/tab-separated-values' : 'text/csv');
        } else if (fmt === 'json') {
            const out = rows.map(r => {
                const o = {};
                for (const c of cols) o[c.key] = r[c.key];
                return o;
            });
            download(base + '.json', JSON.stringify(out, null, 2), 'application/json');
        } else if (fmt === 'accessions') {
            download(base + '_accessions.txt', rows.map(r => r.accession).join('\\n'), 'text/plain');
        }
    });
});

searchInput.addEventListener('input', () => {
    clearTimeout(window._searchTimer);
    window._searchTimer = setTimeout(applyFilters, 180);
});
document.querySelectorAll('.filter-select').forEach(sel => sel.addEventListener('change', applyFilters));

renderStats();
renderHead();
applyFilters();
renderColumnPanel();
renderCrossTabs();
"""


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------
def build_html(rows, stats, cross_tabs):
    keys = [c["key"] for c in MASTER_COLUMNS]
    slim_rows = [{k: r.get(k, "") for k in keys} for r in rows]

    data_json = json.dumps(slim_rows, ensure_ascii=False)
    stats_json = json.dumps(stats, ensure_ascii=False)
    columns_json = json.dumps(MASTER_COLUMNS, ensure_ascii=False)
    cross_tabs_json = json.dumps(cross_tabs, ensure_ascii=False)

    filter_html = ""
    for key, label in FILTER_DEFS:
        opts = "".join(
            f'<option value="{v}">{v}</option>'
            for v in stats["filter_values"].get(key, [])
        )
        filter_html += f'''
        <label class="filter-label">
            <span>{label}</span>
            <select class="filter-select" data-filter-key="{key}">
                <option value="">All</option>
                {opts}
            </select>
        </label>'''

    css = CSS.replace("__ACCENT__", MODULE_ACCENT)
    js = (JS.replace("__DATA__", data_json)
            .replace("__STATS__", stats_json)
            .replace("__COLUMNS__", columns_json)
            .replace("__CROSS_TABS__", cross_tabs_json)
            .replace("__ACCENT__", MODULE_ACCENT))

    # Final nav
    nav = [
        ("../index.html", "Home", False),
        ("mlst.html", "MLST", False),
        ("spa.html", "spa", False),
        ("sccmec.html", "SCCmec", False),
        ("capsule.html", "Capsule", False),
        ("agr.html", "agr", False),
        ("mrsa.html", "MRSA", True),
        ("amr.html", "AMR", False),
        ("vfdb.html", "Virulence", False),
        ("plasmid.html", "Plasmid", False),
        ("../statistics.html", "Statistics", False),
        ("../lineages.html", "Lineages", False),
        ("../downloads.html", "Downloads", False),
        ("../about.html", "About", False),
    ]
    nav_html = "".join(
        f'<a href="{href}"{" class=\'active\'" if active else ""}>{label}</a>'
        for href, label, active in nav
    )

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{MODULE_TITLE} — SAURUS</title>
<style>
{css}
</style>
</head>
<body>

<nav class="saurus-nav">
    <a class="brand" href="../index.html">
        <span class="brand-emoji">🦖</span>
        <span class="brand-text">
            <span class="brand-name">SAURUS</span>
            <span class="brand-tagline">Staphylococcus aureus Unified Resource for Universal Surveillance</span>
        </span>
    </a>
    <div class="links">
        <a href="../index.html">Home</a>
        <a href="pages/mlst.html">MLST</a>
        <a href="pages/spa.html">spa</a>
        <a href="pages/sccmec.html">SCCmec</a>
        <a href="pages/capsule.html">Capsule</a>
        <a href="pages/agr.html">agr</a>
        <a href="pages/mrsa.html" class="active">MRSA</a>
        <a href="pages/amr.html">AMR</a>
        <a href="pages/vfdb.html">Virulence</a>
        <a href="pages/plasmid.html">Plasmid</a>
        <a href="../statistics.html">Statistics</a>
        <a href="../geography.html">Geography</a>
        <a href="../trends.html">Trends</a>
        <a href="../compare.html">Compare</a>
        <a href="../lineages.html">Lineages</a>
        <a href="../downloads.html">Downloads</a>
        <a href="../about.html">About</a>
    </div>
</nav>

<header class="page-header">
    <h1>{MODULE_TITLE}</h1>
    <div class="subtitle">{MODULE_SUBTITLE}</div>
    <div class="stat-row" id="stat-row"></div>
</header>

<main>
    <div class="tabs">
        <button class="tab-btn active" data-tab="master">Master Table</button>
        <button class="tab-btn" data-tab="breakdown">MRSA Breakdown</button>
    </div>

    <div class="tab-panel active" id="tab-master">
        <div class="controls">
            <div style="flex:1;min-width:260px;">
                <div class="search-wrapper">
                    <input type="text" id="search" placeholder="Search accession, ST, CC, spa, SCCmec...">
                </div>
                <div class="search-hint">
                    Tip: type <code>CC5</code> for clonal complex, <code>ST5</code> for exact ST
                </div>
            </div>
            {filter_html}
            <div class="col-toggle-wrap">
                <button class="col-toggle-btn" id="col-toggle-btn">⚙ Columns</button>
                <div class="col-panel" id="col-panel"></div>
            </div>
            <div class="export-bar">
                <span class="sel-counter" id="sel-counter">0 selected</span>
                <select class="scope-select" id="export-scope">
                    <option value="visible">Visible rows</option>
                    <option value="selected">Selected rows</option>
                </select>
                <button class="export-btn" data-fmt="tsv">⬇ TSV</button>
                <button class="export-btn" data-fmt="csv">⬇ CSV</button>
                <button class="export-btn" data-fmt="json">⬇ JSON</button>
                <button class="export-btn secondary" data-fmt="accessions">🧬 Accessions</button>
            </div>
        </div>

        <div class="table-wrap">
            <div class="table-scroll">
                <table id="data-table">
                    <thead id="table-head"></thead>
                    <tbody id="table-body"></tbody>
                </table>
            </div>
            <div class="pagination" id="pagination"></div>
        </div>
    </div>

    <div class="tab-panel" id="tab-breakdown">
        <div style="margin-bottom:20px;padding:16px 20px;background:#fef2f2;border-left:5px solid #dc2626;border-radius:8px;">
            <strong style="color:#991b1b;">🔬 How to read these tables</strong>
            <p style="margin-top:6px;color:#475569;font-size:0.92em;">
                Each table shows how a typing field (CC, ST, spa, SCCmec, agr, capsule) is distributed
                across <strong style="color:#991b1b;">MRSA</strong>,
                <strong style="color:#1e40af;">MSSA</strong>, and
                <strong style="color:#64748b;">Unknown</strong> samples.
                The <strong>% MRSA</strong> column (with red bar) shows how methicillin-resistant each value is.
            </p>
        </div>
        <div class="breakdown-grid" id="breakdown-grid"></div>
    </div>
</main>

<footer class="saurus-footer">
    <div class="footer-line full-name">
        <strong style="color:#d4af37;">SAURUS</strong> — Staphylococcus aureus Unified Resource for Universal Surveillance
    </div>
    <div class="footer-line">
        University of Ghana Medical School · MIT License · Data updated <span id="generated-at"></span>
    </div>
    <div class="footer-line">
        <a href="https://github.com/bbeckley-hub/saurus">GitHub</a> ·
        <a href="../about.html">About</a> ·
        <a href="mailto:brownbeckley94@gmail.com">Contact</a>
    </div>
</footer>

<script>
{js}
</script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate the MRSA page for SAURUS")
    parser.add_argument("--mlst",    default=INPUTS["mlst"])
    parser.add_argument("--spa",     default=INPUTS["spa"])
    parser.add_argument("--cge",     default=INPUTS["cge"])
    parser.add_argument("--rpet",    default=INPUTS["rpet"])
    parser.add_argument("--capsule", default=INPUTS["capsule"])
    parser.add_argument("--agr",     default=INPUTS["agr"])
    parser.add_argument("--cc",      default=CC_LOOKUP_FILE,
                        help=f"ST → CC lookup (default: {CC_LOOKUP_FILE})")
    parser.add_argument("-o", "--output", default="mrsa.html")
    args = parser.parse_args()

    out_path = Path(args.output)
    cc_path  = Path(args.cc)

    print(f"📖 Building ST→CC lookup from {cc_path}")
    st_cc = load_st_to_cc(cc_path)

    print("📖 Loading all typing modules...")
    mlst    = load_mlst(Path(args.mlst), st_cc)
    print(f"   MLST:    {len(mlst):,} rows")
    spa     = load_spa(Path(args.spa))
    print(f"   spa:     {len(spa):,} rows")
    cge     = load_cge(Path(args.cge))
    print(f"   CGE:     {len(cge):,} rows")
    rpet    = load_rpet(Path(args.rpet))
    print(f"   RPet:    {len(rpet):,} rows")
    capsule = load_capsule(Path(args.capsule))
    print(f"   Capsule: {len(capsule):,} rows")
    agr     = load_agr(Path(args.agr))
    print(f"   agr:     {len(agr):,} rows")

    print("🔗 Merging into master view...")
    rows = merge_all(mlst, spa, cge, rpet, capsule, agr)
    print(f"   {len(rows):,} unique accessions")

    stats = compute_stats(rows)
    print(f"   MRSA: {stats['mrsa']:,}  MSSA: {stats['mssa']:,}  Unknown: {stats['unknown']:,}")
    print(f"   MRSA rate: {stats['mrsa_rate']}%")
    print(f"   Unique STs: {stats['unique_sts']} · Unique CCs: {stats['unique_ccs']}")
    print(f"   Top MRSA CC: {stats['top_cc']} ({stats['top_cc_count']:,})")
    print(f"   Top MRSA ST: {stats['top_st']} ({stats['top_st_count']:,})")

    print("📊 Building cross-tabs...")
    cross_tabs = compute_cross_tabs(rows)
    for field, data in cross_tabs.items():
        print(f"   {data['label']}: {len(data['rows'])} unique values")

    print("🎨 Building HTML...")
    html = build_html(rows, stats, cross_tabs)
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ Written: {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()