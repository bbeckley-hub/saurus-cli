#!/usr/bin/env python3
"""Curate the SAURUS gene-annotation tables for data release v1.1.0.

Reads data/gene_annotation/{amr,vfdb,plasmid}_all.tsv.gz and
*_gene_freq.tsv.gz, applies the peer-review curation decisions
(dropped AMR contamination entries, clinically-relevant VFDB panel,
staphylococcal-only plasmid replicons), regenerates both files, and
writes a manifest of everything removed.

Matching is done on the normalized base name (lowercase, any allele or
plasmid-reference suffix stripped: 'blaZ_138' -> 'blaz',
'rep7c_1_rep(MSSA476)' -> 'rep7c', 'Col(BS512)_1' -> 'col(bs512)'), so
the lists also work against rebuilt tables with different allele counts.

Freq-table conventions match data release v1.0.0 exactly: denominators are
the PRE-curation module-annotated genome counts and num_occurrences equals
num_genomes, so untouched genes keep identical statistics.

Usage:
  python scripts/curate_gene_tables.py                       # dry run
  python scripts/curate_gene_tables.py --write               # in place
  python scripts/curate_gene_tables.py --write --backup      # keep .bak copies
  python scripts/curate_gene_tables.py --write --data-version v1.1.0
"""

import argparse
import gzip
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

MASTER_REL = "mrsa/mrsa_all.tsv.gz"
MODULES = ["amr", "vfdb", "plasmid"]

AMR_DROP_BASES = {
    "blaoxa-72", "blaoxa-2", "blaoxa-181", "blakpc-2", "blactx-m-14",
    "blashv-187", "blatem-116", "blatem-1a", "blatem-181", "blatem-171",
    "blatem-229", "blatem-1b", "blatem-219", "qnrb19", "qnrd1",
    "qnrd3", "vanhax", "nara", "narb", "mecb",
    "tet(a)", "tet(c)", "tet(39)", "tet(w)", "tet(o)", "tet(s)",
    "cata1", "cata2", "catb2", "cmla1", "aph(3'')-ib", "aada5", "aada9",
    "ant(2'')-ia", "ant(3'')-ia", "dfra8", "dfra14", "dfra16", "dfra17",
    "sul1", "sul2", "sal(a)", "msr(c)", "erm(47)", "erm(x)",
}

VFDB_KEEP_BASES = {
    "sea", "seb", "sec", "seh", "selk", "selq", "sell", "tsst-1",
    "luks-pv", "lukf-pv", "eta", "etb",
    "cna", "fnba", "fnbb", "clfa", "clfb", "sdrc", "sdrd", "sdre",
    "eap/map", "scn", "sak", "chp", "coa", "vwbp",
}

PLASMID_KEEP_EXACT = {"col(phad28)"}   # the one Col type native to S. aureus
PLASMID_REF_TOKENS = [
    "(ptef1", "(ptef3", "(pvef1", "(pvef3", "(pbee99", "aus0085p5",
    "aus0085p6", "aus0004p3", "(pjs33", "(pvf22", "(pciz2", "(pgdh442",
    "(pvsw2", "(pvsw4", "(pad1", "(pri1", "(psm19035",
]

def norm_base(name):
    s = str(name).strip().lower()
    return s.split("_", 1)[0].strip()

def plasmid_is_dropped(full_name):
    s = str(full_name).strip().lower()
    base = norm_base(s)
    if base.startswith("inc"):
        return True
    if base.startswith("col") and base not in PLASMID_KEEP_EXACT:
        return True
    if any(tok in s for tok in PLASMID_REF_TOKENS):
        return True
    return False

def read_gz_tsv(path):
    with gzip.open(path, "rt") as f:
        return pd.read_csv(f, sep="\t", dtype=str)

def write_gz_tsv(df, path):
    with gzip.open(path, "wt", compresslevel=9) as f:
        df.to_csv(f, sep="\t", index=False, lineterminator="\n")

def master_size(data_dir):
    with gzip.open(data_dir / MASTER_REL, "rt") as f:
        return sum(1 for _ in f) - 1

def curate_module(name, data_dir, out_dir, write=False, backup=False):
    all_path = data_dir / "gene_annotation" / f"{name}_all.tsv.gz"
    freq_path = data_dir / "gene_annotation" / f"{name}_gene_freq.tsv.gz"
    df = read_gz_tsv(all_path)
    n0_acc = df["accession"].nunique()

    if name == "amr":
        keep_mask = ~df["gene"].map(norm_base).isin(AMR_DROP_BASES)
    elif name == "vfdb":
        keep_mask = df["gene"].map(norm_base).isin(VFDB_KEEP_BASES)
    else:
        keep_mask = ~df["gene"].map(plasmid_is_dropped)

    kept = df[keep_mask].copy()
    kept["accession"] = kept["accession"].str.replace(r"\.fna$", "", regex=True)
    dropped = df[~keep_mask]
    n1_acc = kept["accession"].nunique()
    n_genes = kept["gene"].nunique()

    print(f"\n[{name}] rows {len(df):,} -> {len(kept):,}   "
          f"names {df['gene'].nunique()} -> {n_genes}   "
          f"genomes with a hit: {n0_acc:,} -> {n1_acc:,}")

    if len(dropped):
        drop_stat = (dropped.groupby("gene")["accession"].nunique()
                     .rename("genomes").reset_index()
                     .sort_values("genomes", ascending=False))
        print("  dropped genes (top 15 by genome count):")
        for _, r in drop_stat.head(15).iterrows():
            print(f"    {r['gene']}  ({int(r['genomes']):,} genomes)")
        if len(drop_stat) > 15:
            print(f"    ... and {len(drop_stat) - 15} more")

    if not write:
        return {"module": name, "rows_before": int(len(df)),
                "rows_after": int(len(kept)), "names_after": int(n_genes),
                "genomes_before": int(n0_acc), "genomes_after": int(n1_acc)}

    if backup:
        for p in (all_path, freq_path):
            if p.exists():
                shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))

    out_dir.mkdir(parents=True, exist_ok=True)
    write_gz_tsv(kept, out_dir / f"{name}_all.tsv.gz")

    denom = n0_acc if n0_acc else 1
    freq = (kept.groupby("gene")
            .agg(num_genomes=("accession", "nunique"))
            .reset_index()
            .sort_values("num_genomes", ascending=False))
    freq["database"] = {"amr": "AMR", "vfdb": "VFDB",
                        "plasmid": "Plasmid"}[name]
    freq["num_occurrences"] = freq["num_genomes"]
    freq["prevalence_pct"] = (freq["num_genomes"] / denom * 100).round(2)
    freq = freq[["gene", "database", "num_genomes", "prevalence_pct",
                 "num_occurrences"]]
    write_gz_tsv(freq, out_dir / f"{name}_gene_freq.tsv.gz")
    print(f"  wrote {out_dir}/{name}_all.tsv.gz and {name}_gene_freq.tsv.gz")
    return {"module": name, "rows_before": int(len(df)),
            "rows_after": int(len(kept)), "names_after": int(n_genes),
            "genomes_before": int(n0_acc), "genomes_after": int(n1_acc)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default=None,
                    help="output dir (default: <data-dir>/gene_annotation)")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--bump-data-version", metavar="V",
                    help="update DATA_VERSION (e.g. v1.1.0)")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not (data_dir / "gene_annotation").is_dir():
        sys.exit(f"error: {data_dir}/gene_annotation not found")
    out_dir = Path(args.out) if args.out else data_dir / "gene_annotation"

    print(f"master table: {master_size(data_dir):,} genomes")
    print("mode: " + ("WRITE" if args.write else "DRY RUN (pass --write)"))

    results = [curate_module(m, data_dir, out_dir, args.write, args.backup)
               for m in MODULES]
    results.append({"master_genomes": master_size(data_dir)})

    if args.bump_data_version:
        vp = data_dir / "DATA_VERSION"
        if args.write:
            old = vp.read_text().strip() if vp.exists() else "?"
            vp.write_text(args.bump_data_version + "\n")
            print(f"\nDATA_VERSION: {old} -> {args.bump_data_version}")
        else:
            print(f"\n(dry run) DATA_VERSION would become {args.bump_data_version}")

    print(json.dumps(results, indent=2))
    if not args.write:
        print("\nDry run complete. Re-run with --write to apply.")

if __name__ == "__main__":
    main()
