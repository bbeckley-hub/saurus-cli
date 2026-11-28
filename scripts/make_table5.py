#!/usr/bin/env python3
"""Regenerate manuscript Table 5 (per-module coverage) directly from the
shipped SAURUS data bundle. Every cell is computed from the bundle; the
only inputs are the data directory and the layout. Usage:
    python3 make_table5.py [DATA_DIR]   # default: bundled data
"""
import glob
import os
import sys
import pandas as pd

data = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data")
dv = open(os.path.join(data, "DATA_VERSION")).read().strip()

master = pd.read_csv(f"{data}/mrsa/mrsa_all.tsv.gz", sep="\t",
                     dtype=str, keep_default_na=False, na_values=[])
meta = pd.read_csv(f"{data}/metadata/metadata.tsv.gz", sep="\t",
                   dtype=str, keep_default_na=False, na_values=[])
n = len(master)
typed = master[master["mrsa_status"].isin(["MRSA", "MSSA"])]
t = len(typed)
mm = len(meta)

def pct(c, d):
    v = 100.0 * c / d
    if v >= 99.99995: return "100%"
    if v > 99.9: return ">99.9%"
    return f"{v:.1f}%"

def calls(series, placeholders):
    return int((~series.isin(placeholders)).sum()), int(series.isin(placeholders).sum())

# typing panel (denominator: typed genomes)
rows_typ = []
c, nc = calls(typed["mlst_st"], {"", "-"})
rows_typ.append((f"MLST sequence type ({typed.loc[~typed['mlst_st'].isin(['','-']),'mlst_st'].nunique():,} STs)",
                 c, pct(c, t), f'{nc:,} "-"'))
cc = typed["mlst_cc"]
c, nc = calls(cc, {"NA"})
rows_typ.append((f"Clonal complex, derived from MLST CC map ({cc[cc != 'NA'].nunique():,} CCs)",
                 c, pct(c, t), f"{nc:,} NA"))
rx = r"^t\d+$"
sp = typed["spa_type"]
named = int(sp.str.match(rx).sum())
novel = int(((~sp.str.match(rx)) & (sp != "") & (sp != "No_spa_type_detected")).sum())
nodet = int((sp == "No_spa_type_detected").sum())
nores = int((sp == "").sum())
rows_typ.append((f"spa type, named tNNN ({sp[sp.str.match(rx)].nunique():,} types)",
                 named, pct(named, t),
                 f"{novel:,} novel pattern, {nodet:,} no type detected, {nores:,} no result"))
for col, label in [("sccmec_cge", "SCCmec, CGE caller"), ("sccmec_rpet", "SCCmec, RPet caller")]:
    ph = {"", "Not-Assigned", "Not Assigned"}
    c, _ = calls(typed[col], ph)
    na = int(master[col].isin(["Not-Assigned", "Not Assigned"]).sum())
    emp = int((master[col] == "").sum())
    rows_typ.append((label, c, pct(c, t), f"{na:,} Not Assigned, {emp:,} empty"))
c, _ = calls(typed["agr_type"], {""})
rows_typ.append(("agr type", c, pct(c, t), f'{int((master["agr_type"] == "").sum()):,} empty'))
c, _ = calls(typed["capsule_type"], {"", "Not Assigned", "Not-Assigned"})
na = int(master["capsule_type"].isin(["Not Assigned", "Not-Assigned"]).sum())
emp = int((master["capsule_type"] == "").sum())
rows_typ.append(("Capsule serotype "
                 f'(Type 5: {int((master["capsule_type"] == "Type 5").sum()):,}; '
                 f'Type 8: {int((master["capsule_type"] == "Type 8").sum()):,})',
                 c, pct(c, t), f"{na:,} Not Assigned, {emp:,} empty"))
mrsa = int((master["mrsa_status"] == "MRSA").sum())
mssa = int((master["mrsa_status"] == "MSSA").sum())
rows_typ.append(("MRSA/MSSA status", t, "100% of typed panel", f"{mrsa:,} MRSA, {mssa:,} MSSA"))

# metadata panel (denominator: metadata-layer assemblies)
HM = {"country": {"", "not determined"}, "source": {"", "unavailable"},
      "host": {"", "missing", "not applicable", "not provided", "not collected",
               "-", "not available: not collected"},
      "year": {""}, "biosample": {""}, "sra_run": {"NA"}}
labels = {"country": "Country (normalised)", "source": "Isolation source",
          "host": "Host species", "year": "Collection year",
          "biosample": "BioSample accession", "sra_run": "SRA run linkage"}
rows_meta = []
for col in ["country", "source", "host", "year", "biosample", "sra_run"]:
    c, nc = calls(meta[col], HM[col])
    rows_meta.append((labels[col], c, pct(c, mm), f"{nc:,} no call"))

# gene panel (denominator: master rows; annotation-space totals alongside)
rows_gene = []
for mod, label in [("vfdb", "VFDB"), ("plasmid", "Plasmid replicons"), ("amr", "AMR")]:
    g = pd.read_csv(glob.glob(f"{data}/gene_annotation/{mod}_all.tsv.gz")[0],
                    sep="\t", dtype=str, usecols=[0])
    ann = int(g.iloc[:, 0].nunique())
    inm = len(set(g.iloc[:, 0]) & set(master["accession"]))
    freq = pd.read_csv(f"{data}/gene_annotation/{mod}_gene_freq.tsv.gz",
                       sep="\t", dtype=str)
    rows_gene.append((label, ann, inm, pct(inm, n), ann - inm, len(freq)))

print(f"# Generated from data release {dv} "
      f"(master {n:,} rows; typed {t:,}; metadata layer {mm:,}; "
      f"master-only typed {len(set(master['accession']) - set(meta['accession'])):,})")
print()
print("Panel / field | Genomes with a call | Coverage | No call")
print(f"Typing (n = {t:,} typed genomes)")
for r in rows_typ:
    print(r[0], "|", f"{r[1]:,}", "|", r[2], "|", r[3])
print(f"Metadata (n = {mm:,} assemblies with a metadata-layer entry)")
for r in rows_meta:
    print(r[0], "|", f"{r[1]:,}", "|", r[2], "|", r[3])
print(f"Gene module (static, GCA-keyed; coverage of the {n:,} master rows)")
print("Module | Annotated (annotation space) | In master table | "
      "Master-table coverage | Outside master | Curated determinants")
for r in rows_gene:
    print(r[0], "|", f"{r[1]:,}", "|", f"{r[2]:,}", "|", r[3], "|", f"{r[4]:,}", "|", r[5])
