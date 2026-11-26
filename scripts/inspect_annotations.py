#!/usr/bin/env python3
"""Inspect SAURUS data before gene-curation decisions.

Run from anywhere; point --data-dir at the data folder (the one holding
agr/ capsule/ gene_annotation/ ...).

  python inspect_annotations.py --data-dir ../data
  python inspect_annotations.py --data-dir ../data --module vfdb --min-genomes 100
  python inspect_annotations.py --data-dir ../data --search lukS
  python inspect_annotations.py --data-dir ../data --search "tet("

Overview mode prints, for the master and each gene module:
  - row / gene / accession counts, in-master vs out-of-master accessions
    (with GCF/GCA split, so annotation coverage choices are explicit)
  - prevalence bands (share of the master) to guide keep/drop selection
  - a 2^20-row truncation check on the VFDB table
Search mode prints every gene whose base name matches, with its genome
count and prevalence, so "which ones to keep" becomes a lookup.
"""

import argparse
import gzip
import sys
from pathlib import Path

import pandas as pd

MODULES = ["amr", "vfdb", "plasmid"]
N_BANDS = [
    ("ubiquitous  >=95% of master", 95.0, 1e9),
    ("common      50-95%", 50.0, 95.0),
    ("variable     5-50%", 5.0, 50.0),
    ("rare        <5%", 0.0, 5.0),
]


def read_tsv(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        return pd.read_csv(f, sep="\t", dtype=str)


def find(data_dir, rel):
    p = data_dir / rel
    if p.exists():
        return p
    gz = p.with_suffix(p.suffix + ".gz")
    return gz if gz.exists() else None


def strip_fna(series):
    return series.str.replace(r"\.fna$", "", regex=True)


def prefix_split(series):
    s = series.fillna("")
    gcf = int(s.str.startswith("GCF_").sum())
    gca = int(s.str.startswith("GCA_").sum())
    other = len(s) - gcf - gca
    return gcf, gca, other


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--module", choices=MODULES, help="restrict the gene listing to one module")
    ap.add_argument("--min-genomes", type=int, default=-1,
                    help="only list genes hit in >= N genomes")
    ap.add_argument("--search", help="list genes whose base name contains this substring")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        sys.exit(f"error: data dir not found: {data_dir.resolve()}")

    master_path = find(data_dir, "mrsa/mrsa_all.tsv")
    if master_path is None:
        sys.exit("error: master table not found (mrsa/mrsa_all.tsv[.gz])")
    master = read_tsv(master_path)
    master_acc = set(strip_fna(master["accession"]))
    gcf, gca, other = prefix_split(master["accession"])
    mlst_cc_filled = int((master["mlst_cc"].fillna("").str.strip() != "").sum()) \
        if "mlst_cc" in master.columns else 0

    print("=" * 74)
    print(f"MASTER  {master_path.name}")
    print(f"  rows                : {len(master):,}")
    print(f"  unique accessions   : {len(master_acc):,}")
    print(f"  GCF / GCA / other   : {gcf:,} / {gca:,} / {other:,}")
    if "mlst_cc" in master.columns:
        print(f"  mlst_cc populated   : {mlst_cc_filled:,} "
              f"({100 * mlst_cc_filled / max(len(master), 1):.1f}%)")
    print("=" * 74)

    search = args.search.lower() if args.search else None
    for mod in MODULES:
        if args.module and mod != args.module:
            continue
        all_path = find(data_dir, f"gene_annotation/{mod}_all.tsv")
        freq_path = find(data_dir, f"gene_annotation/{mod}_gene_freq.tsv")
        if all_path is None:
            print(f"\n[{mod}] table missing, skipped")
            continue

        all_df = read_tsv(all_path)
        all_df["acc"] = strip_fna(all_df["accession"])
        freq = read_tsv(freq_path) if freq_path else None

        accs = set(all_df["acc"])
        in_master = accs & master_acc
        out_master = accs - master_acc
        gcf_o, gca_o, other_o = prefix_split(
            pd.Series(sorted(out_master), dtype=str))

        rows_in_master = int(all_df["acc"].isin(master_acc).sum())
        trunc_flag = ""
        if len(all_df) == (1 << 20) - 1:
            trunc_flag = "   <= TRUNCATED at 2^20 rows"

        print(f"\n[{mod}]  {all_path.name}")
        print(f"  rows                : {len(all_df):,}{trunc_flag}")
        print(f"  unique genes        : {all_df['gene'].nunique():,}")
        print(f"  unique accessions   : {len(accs):,}")
        print(f"  in master           : {len(in_master):,} "
              f"({100 * len(in_master) / len(master_acc):.1f}% of master)   "
              f"usable rows: {rows_in_master:,}")
        print(f"  NOT in master       : {len(out_master):,}   "
              f"(GCF {gcf_o:,} / GCA {gca_o:,} / other {other_o:,})")

        if search or args.module:
            grp = all_df.groupby("gene")["acc"].nunique().rename("genomes")
            raw = all_df.groupby("gene").size().rename("rows")
            tbl = pd.concat([grp, raw], axis=1)
            tbl["base"] = tbl.index.str.lower().str.split("_").str[0]
            if freq is not None:
                f = freq.set_index("gene")["num_genomes"].astype(int)
                tbl["freq_genomes"] = f.reindex(tbl.index)
            if search:
                mask = tbl.index.str.lower().str.contains(search, regex=False) \
                    | tbl["base"].str.contains(search, regex=False)
                tbl = tbl[mask]
            if args.min_genomes >= 0:
                tbl = tbl[tbl["genomes"] >= args.min_genomes]
            tbl["pct_master"] = (tbl["genomes"] / len(master_acc) * 100).round(2)
            tbl = tbl.sort_values("genomes", ascending=False)

            if freq is not None and not search:
                bands = pd.cut(
                    tbl["pct_master"],
                    bins=[-0.01, 5, 50, 95, 1e9],
                    labels=[b[0] for b in reversed(N_BANDS)],
                )
                print("  prevalence bands (share of master):")
                for label, count in bands.value_counts().reindex(
                        [b[0] for b in N_BANDS]).items():
                    print(f"    {label} : {count} genes")

            print(f"  listing {len(tbl)} genes"
                  + (f" matching '{search}'" if search else "")
                  + ":")
            for gene, r in tbl.iterrows():
                extra = ""
                if "freq_genomes" in tbl.columns \
                        and pd.notna(r["freq_genomes"]) \
                        and int(r["freq_genomes"]) != int(r["genomes"]):
                    extra = f"  freq table: {int(r['freq_genomes']):,}"
                print(f"    {gene:<40} {int(r['genomes']):>7,} genomes  "
                      f"{r['pct_master']:>6.2f}%  ({int(r['rows']):,} rows)"
                      + extra)
        else:
            print(f"  (overview only — rerun with --module {mod} "
                  f"or --search <name> to list genes)")


if __name__ == "__main__":
    main()
