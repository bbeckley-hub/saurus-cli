"""Release gate for SAURUS-CLI data bundles.

Fails (exit 1) when a released data bundle shows any defect found during
peer review of data v1.0.0 / CLI v0.3.0, or diverges from the locked v1.1.0
curation:

  - master table missing / too small
  - mlst_cc column largely empty (--cc unreliable on the master load path)
  - mlst row count diverging from typed master rows
  - a gene module table missing, or still capped at the Excel 1,048,576-line
    artifact
  - a gene module catalogue diverging from the locked curated counts
    (AMR 174, VFDB 26, plasmid 177)
  - a gene freq table disagreeing with the per-gene genome counts recomputed
    from its own long table

    python3 scripts/verify_data_release.py /path/to/saurus/data [--expect-version v1.1.0]
"""
import argparse
import gzip
import io
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from saurus_cli import find_data_file, read_tsv  # noqa: E402

MIN_MASTER_ROWS = 100_000
MIN_CC_POPULATION = 0.50
MIN_MODULE_COVERAGE = 0.50
EXCEL_CAP_ROWS = (1 << 20) - 1

EXPECTED_NAME_COUNTS = {"amr": 174, "vfdb": 26, "plasmid": 177}

MODULES = {
    "amr": "gene_annotation/amr_all.tsv",
    "vfdb": "gene_annotation/vfdb_all.tsv",
    "plasmid": "gene_annotation/plasmid_all.tsv",
}


def open_any(path):
    if str(path).endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
    return open(path, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--expect-version", default="v1.1.0",
                    help="required DATA_VERSION (empty string skips the check)")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    failures = []

    if args.expect_version:
        vp = data_dir / "DATA_VERSION"
        have = vp.read_text().strip() if vp.exists() else "<missing>"
        print(f"DATA_VERSION           : {have}")
        if have != args.expect_version:
            failures.append(f"DATA_VERSION is {have!r}, expected "
                            f"{args.expect_version!r}")

    master_path = find_data_file(data_dir, "mrsa/mrsa_all.tsv", "mrsa_all.tsv")
    if master_path is None or not Path(master_path).exists():
        print("FAIL  master table not found")
        sys.exit(1)
    master = read_tsv(master_path)
    n_master = len(master)
    print(f"master rows            : {n_master:,}")
    if n_master < MIN_MASTER_ROWS:
        failures.append(f"master table has only {n_master:,} rows")

    mlst_path = find_data_file(data_dir, "mlst/mlst_all.tsv", "mlst_all.tsv")
    if mlst_path is not None and Path(mlst_path).exists():
        mlst = read_tsv(mlst_path)
        n_mlst = len(mlst)
        print(f"mlst rows              : {n_mlst:,}")
        if abs(n_mlst - master["mlst_st"].notna().sum()) > max(1000, 0.01 * n_mlst):
            failures.append(
                f"mlst rows ({n_mlst:,}) diverge from typed master rows")
    else:
        n_mlst = n_master

    cc = master["mlst_cc"].fillna("").astype(str).str.strip().str.upper()
    populated = int(cc.isin(["", "NA"]).eq(False).sum())
    frac = populated / n_master if n_master else 0
    print(f"master mlst_cc coverage: {populated:,} ({frac:.1%})")
    if frac < MIN_CC_POPULATION:
        failures.append(
            "mlst_cc is largely empty in the master table; --cc is unreliable "
            "on the master load path")

    for name, rel in MODULES.items():
        path = find_data_file(data_dir, rel, rel.split("/")[-1])
        if path is None or not Path(path).exists():
            failures.append(f"{name.upper()} module table missing ({rel})")
            continue
        df = read_tsv(path)
        n_rows = len(df)
        n_acc = (df["accession"].str.replace(r"\.fna$", "", regex=True)
                 .nunique())
        frac = n_acc / n_mlst if n_mlst else 0
        print(f"{name.upper():<7} rows {n_rows:>12,}  accessions {n_acc:>9,}  "
              f"({frac:.1%} of master)")
        if n_rows == EXCEL_CAP_ROWS:
            failures.append(
                f"{name} table has exactly {EXCEL_CAP_ROWS:,} rows: the "
                "Excel 1,048,576-line truncation artifact is still present")
        if frac < MIN_MODULE_COVERAGE:
            failures.append(
                f"{name} gene table covers only {n_acc:,} of {n_mlst:,} "
                f"genomes ({frac:.1%}); gene-based counts would treat missing "
                "annotation as gene absence")
        n_names = df["gene"].nunique()
        expect = EXPECTED_NAME_COUNTS.get(name)
        print(f"        catalogue    : {n_names:,} gene names "
              f"(expected {expect})")
        if expect is not None and n_names != expect:
            failures.append(
                f"{name} catalogue has {n_names} gene names, expected {expect}")

        freq_rel = f"gene_annotation/{name}_gene_freq.tsv"
        freq_path = find_data_file(data_dir, freq_rel, freq_rel.split("/")[-1])
        if freq_path is not None and Path(freq_path).exists():
            with open_any(freq_path) as f:
                header = f.readline().rstrip("\n").split("\t")
                gi, ni = header.index("gene"), header.index("num_genomes")
                shipped = {}
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) > max(gi, ni):
                        shipped[parts[gi].strip()] = int(parts[ni])
            recomputed = defaultdict(int)
            for g, grp in df.groupby("gene"):
                recomputed[g] = grp["accession"].nunique()
            bad = [(g, recomputed[g], n) for g, n in shipped.items()
                   if recomputed[g] != n]
            bad += [(g, n, "?") for g, n in recomputed.items()
                    if g not in shipped]
            if bad:
                sample = ", ".join(f"{g} (long={a}, freq={b})"
                                   for g, a, b in bad[:5])
                failures.append(
                    f"{name} freq table disagrees with its long table "
                    f"({len(bad)} genes; e.g. {sample})")
            else:
                print(f"        freq check   : OK ({len(shipped)} genes)")
        else:
            failures.append(f"{name} freq table missing ({freq_rel})")

    if failures:
        print("\nFAILED data-release audit:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nPASSED data-release audit")
    sys.exit(0)


if __name__ == "__main__":
    main()
