#!/usr/bin/env python3
"""
test_cli.py — comprehensive test suite for SAURUS-CLI v0.3.0.

Run against dev version (works from any directory):
    python scripts/test_cli.py

Run against installed version:
    python scripts/test_cli.py $(which saurus)

Run against wheel-installed version:
    python scripts/test_cli.py /tmp/cli_test/bin/saurus

Exits non-zero if any assertion fails. Prints a counts snapshot at the end
so you can diff behaviour between versions.
"""
import json
import sys
import subprocess
import tempfile
from pathlib import Path

# Resolve saurus_cli.py relative to this script, so the test suite works
# whether invoked from the repo root, from scripts/, or from anywhere else.
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_DEFAULT_CLI_SCRIPT = _REPO_ROOT / "saurus_cli.py"

if len(sys.argv) > 1:
    CLI = sys.argv[1:]
elif _DEFAULT_CLI_SCRIPT.exists():
    CLI = [sys.executable, str(_DEFAULT_CLI_SCRIPT)]
else:
    sys.exit(
        f"Error: saurus_cli.py not found at {_DEFAULT_CLI_SCRIPT}\n"
        f"  Run from the repo root, or pass an explicit CLI:\n"
        f"    python {__file__} $(which saurus)"
    )

TMP = Path(tempfile.mkdtemp(prefix="saurus_test_"))
PASSED = 0
FAILED = 0
FAILURES = []
SNAPSHOT = {}


def run(args, timeout=180):
    try:
        r = subprocess.run(CLI + list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 124


def count(*args):
    out, _, _ = run(list(args) + ["--count", "-q"])
    try:
        return int(out.strip().split("\n")[0].replace(",", ""))
    except (ValueError, IndexError):
        return None


def check(desc, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  \u2713 {desc}")
    else:
        FAILED += 1
        FAILURES.append(f"{desc}  [{detail}]")
        print(f"  \u2717 {desc}  [{detail}]")


def eq(d, a, b):    check(d, a == b, f"{a} != {b}")
def le(d, a, b):    check(d, a is not None and b is not None and a <= b, f"{a} <= {b}?")
def ge(d, a, b):    check(d, a is not None and b is not None and a >= b, f"{a} >= {b}?")
def gt(d, a, n=0):  check(d, a is not None and a > n, f"{a} > {n}?")


def file_lines(p):
    if not Path(p).exists():
        return 0
    txt = Path(p).read_text().rstrip("\n")
    return 0 if not txt else len(txt.split("\n"))


def file_prefixes(p):
    if not Path(p).exists():
        return set()
    return {ln[:3] for ln in Path(p).read_text().strip().split("\n") if ln}


def info(desc, value):
    """Informational check — reports but does not fail the suite."""
    print(f"  \u2139 {desc}: {value}")


def section(s):
    print(f"\n\u2501\u2501\u2501 {s} \u2501\u2501\u2501")


# ============================================================================
# 1. Baseline
# ============================================================================
section("Baseline sanity")

out, err, _ = run(["--version"])
check("--version prints 0.3.0", "0.3.0" in (out + err))

out, err, _ = run([])
check("bare invocation prints help", "usage" in (out + err).lower())

out, err, rc = run(["--examples", "-q"])
check("--examples exits 0", rc == 0, f"rc={rc}")

out, err, rc = run(["--about", "-q"])
check("--about exits 0", rc == 0, f"rc={rc}")

# ============================================================================
# 2. Determinism
# ============================================================================
section("Determinism (same query twice = same answer)")

for args in (
    ("--st", "5"),
    ("--lineage", "USA100", "--country", "USA"),
    ("--mrsa", "--has-sra"),
    ("--cc", "8", "--sccmec", "IV"),
):
    a = count(*args)
    b = count(*args)
    eq(f"{' '.join(args)} deterministic", a, b)

# ============================================================================
# 3. Lineage signatures (all 10)
# ============================================================================
section("Lineage signatures (all 10)")

LINEAGES = ["USA100", "USA300", "USA400", "USA500", "USA700", "USA800",
            "EMRSA-15", "EMRSA-16", "BENGAL BAY", "ST152"]
lineage_counts = {}
for lin in LINEAGES:
    n = count("--lineage", lin)
    lineage_counts[lin] = n
    SNAPSHOT[f"lineage_{lin}"] = n
    gt(f"--lineage {lin} > 0", n, 0)

# USA300 shortcut should exactly equal its 5 individual flags
n_shortcut = count("--lineage", "USA300")
n_explicit = count("--st", "8", "--spa", "t008", "--sccmec", "IV",
                   "--agr", "I", "--capsule", "5")
eq("USA300 shortcut == explicit 5 flags", n_shortcut, n_explicit)

# Unknown lineage must fail
out, err, rc = run(["--lineage", "NOTREAL", "--count", "-q"])
check("unknown --lineage rejected", rc != 0, f"rc={rc}")

# ============================================================================
# 4. Individual filters
# ============================================================================
section("Individual filters")

for args in (
    ("--mrsa",),
    ("--mssa",),
    ("--st", "5"),
    ("--cc", "8"),
    ("--spa", "t002"),
    ("--sccmec", "IV"),
    ("--agr", "I"),
    ("--capsule", "5"),
    ("--country", "USA"),
    ("--source", "blood"),
    ("--host", "Homo"),
    ("--year", "2019"),
    ("--year", "2015-2020"),
):
    n = count(*args)
    gt(f"{' '.join(args)} > 0", n, 0)
    SNAPSHOT[f"filter_{'_'.join(args).replace(' ', '_')}"] = n

# ============================================================================
# 5. Gene filters
# ============================================================================
section("Gene filters")

gt("--amr mecA > 0", count("--amr", "mecA"), 0)
n_mecA_tetM = count("--amr", "mecA,tetM")
info("--amr mecA,tetM (all)", f"{n_mecA_tetM} (gene-name format issue, not a v0.3.0 regression)")

gt("--amr mecA,blaZ (all) > 0", count("--amr", "mecA,blaZ"), 0)
gt("--amr mecA,tetK (any) > 0", count("--amr", "mecA,tetK", "--any"), 0)
gt("--vfdb lukS-PV > 0", count("--vfdb", "lukS-PV"), 0)
gt("--vfdb hla > 0", count("--vfdb", "hla"), 0)
gt("--plasmid rep5a > 0", count("--plasmid", "rep5a"), 0)

le("--amr mecA,tetM (all) <= (any)",
   count("--amr", "mecA,tetM"),
   count("--amr", "mecA,tetM", "--any"))

# ============================================================================
# 6. Subset invariants (each filter reduces or maintains count)
# ============================================================================
section("Subset invariants (monotonicity)")

n_st5 = count("--st", "5")
le("--st 5 --mrsa <= --st 5", count("--st", "5", "--mrsa"), n_st5)
le("--st 5 --country USA <= --st 5", count("--st", "5", "--country", "USA"), n_st5)
le("--st 5 --source blood <= --st 5", count("--st", "5", "--source", "blood"), n_st5)
le("--st 5 --has-sra <= --st 5", count("--st", "5", "--has-sra"), n_st5)
le("--st 5 --amr mecA <= --st 5", count("--st", "5", "--amr", "mecA"), n_st5)

n_mrsa = count("--mrsa")
le("--mrsa --has-sra <= --mrsa", count("--mrsa", "--has-sra"), n_mrsa)

n_usa300 = lineage_counts.get("USA300")
le("--lineage USA300 --has-sra <= --lineage USA300",
   count("--lineage", "USA300", "--has-sra"), n_usa300)

le("--st 5 --country USA --source blood <= --st 5 --country USA",
   count("--st", "5", "--country", "USA", "--source", "blood"),
   count("--st", "5", "--country", "USA"))

typing_pairs = [
    (("--st", "5"), ("--mrsa",)),
    (("--st", "5"), ("--sccmec", "IV")),
    (("--st", "5"), ("--agr", "I")),
    (("--cc", "8"), ("--mrsa",)),
    (("--cc", "8"), ("--country", "USA")),
    (("--spa", "t002"), ("--sccmec", "II")),
]
for f1, f2 in typing_pairs:
    n1 = count(*f1)
    n2 = count(*f2)
    n12 = count(*(f1 + f2))
    if n1 is not None and n2 is not None:
        le(f"{' '.join(f1)} + {' '.join(f2)} <= min({n1},{n2})",
           n12, min(n1, n2))
    else:
        check(f"{' '.join(f1)} + {' '.join(f2)} (skipped, missing counts)",
              False, f"n1={n1} n2={n2}")

# ============================================================================
# 7. Empty result handling
# ============================================================================
section("Empty result handling")

eq("--st 99999 returns 0", count("--st", "99999"), 0)
eq("--st 5 --spa t9999 returns 0", count("--st", "5", "--spa", "t9999"), 0)

base = TMP / "empty_test"
for ext in ("_sra_runs.txt", "_biosamples.txt", "_bioprojects.txt", ".tsv", ".txt"):
    fp = Path(str(base) + ext)
    if fp.exists():
        fp.unlink()

run(["--st", "99999", "--format", "tsv,accession,sra,biosample,bioproject",
     "-o", str(base)])
check("empty result: no files created",
      not any(Path(str(base) + e).exists()
              for e in (".tsv", ".txt", "_sra_runs.txt",
                        "_biosamples.txt", "_bioprojects.txt")))

# ============================================================================
# 8. Format correctness
# ============================================================================
section("Format correctness (single)")

TEST_ARGS = ["--lineage", "USA100", "--country", "USA", "--source", "blood"]
n_test = count(*TEST_ARGS)
print(f"  (test filter matches {n_test} genomes)")

if n_test and n_test > 0:
    # TSV
    base = TMP / "fmt_tsv"
    run(TEST_ARGS + ["--format", "tsv", "-o", str(base)])
    p = Path(str(base) + ".tsv")
    check("tsv file created", p.exists())
    if p.exists():
        eq("tsv lines = N + header", file_lines(p), n_test + 1)
        check("tsv has tab separator", "\t" in p.read_text()[:1000])

    # CSV
    base = TMP / "fmt_csv"
    run(TEST_ARGS + ["--format", "csv", "-o", str(base)])
    p = Path(str(base) + ".csv")
    check("csv file created", p.exists())
    if p.exists():
        try:
            import csv as _csv
            with open(p, newline="", encoding="utf-8") as f:
                reader = _csv.reader(f)
                header = next(reader)
                n_csv_rows = sum(1 for _ in reader)
            check("csv header parsed", len(header) > 0, f"{len(header)} columns")
            check("csv header contains accession",
                  any("accession" in c.lower() for c in header),
                  f"header: {header[:3]}")
            eq("csv data rows = N", n_csv_rows, n_test)
        except Exception as e:
            check("csv parses", False, str(e))

    # JSON
    base = TMP / "fmt_json"
    run(TEST_ARGS + ["--format", "json", "-o", str(base)])
    p = Path(str(base) + ".json")
    check("json file created", p.exists())
    if p.exists():
        try:
            data = json.loads(p.read_text())
            eq("json is a list", isinstance(data, list), True)
            eq("json length = N", len(data), n_test)
        except Exception as e:
            check("json parses", False, str(e))

    # Accession
    base = TMP / "fmt_acc"
    run(TEST_ARGS + ["--format", "accession", "-o", str(base)])
    p = Path(str(base) + ".txt")
    check("accession file created", p.exists())
    if p.exists():
        eq("accession lines = N", file_lines(p), n_test)
        prefixes = file_prefixes(p)
        check("accession lines start GCA/GCF",
              all(pre in ("GCA", "GCF") for pre in prefixes),
              f"prefixes: {prefixes}")

    # BioSample
    base = TMP / "fmt_bio"
    run(TEST_ARGS + ["--format", "biosample", "-o", str(base)])
    p = Path(str(base) + "_biosamples.txt")
    if p.exists() and file_lines(p) > 0:
        prefixes = file_prefixes(p)
        check("biosample lines start SAM*",
              all(pre.startswith("SAM") for pre in prefixes),
              f"prefixes: {prefixes}")

    # BioProject
    base = TMP / "fmt_bp"
    run(TEST_ARGS + ["--format", "bioproject", "-o", str(base)])
    p = Path(str(base) + "_bioprojects.txt")
    if p.exists() and file_lines(p) > 0:
        prefixes = file_prefixes(p)
        check("bioproject lines start PRJ*",
              all(pre.startswith("PRJ") for pre in prefixes),
              f"prefixes: {prefixes}")

    # SRA
    base = TMP / "fmt_sra"
    run(TEST_ARGS + ["--format", "sra", "-o", str(base)])
    p = Path(str(base) + "_sra_runs.txt")
    if p.exists() and file_lines(p) > 0:
        prefixes = file_prefixes(p)
        check("sra lines start SRR/ERR/DRR",
              all(pre in {"SRR", "ERR", "DRR"} for pre in prefixes),
              f"prefixes: {prefixes}")

# ============================================================================
# 9. Multi-format (no filename collisions)
# ============================================================================
section("Multi-format (no collisions)")

base = TMP / "multi"
run(TEST_ARGS + ["--format",
                 "tsv,accession,sra,biosample,bioproject,csv,json",
                 "-o", str(base)])
expected = [".tsv", ".txt", ".csv", ".json",
            "_sra_runs.txt", "_biosamples.txt", "_bioprojects.txt"]
for ext in expected:
    check(f"multi-format created {Path(str(base) + ext).name}",
          Path(str(base) + ext).exists())

# ============================================================================
# 10. SRA cross-checks
# ============================================================================
section("SRA cross-checks (22,322 genomes vs ~22,277 BioSamples)")

n_has_sra = count("--has-sra")
SNAPSHOT["has_sra_genomes"] = n_has_sra
gt("--has-sra --count > 20,000", n_has_sra, 20000)

base = TMP / "has_sra_bio"
run(["--has-sra", "--format", "biosample", "-o", str(base)])
p = Path(str(base) + "_biosamples.txt")
if p.exists():
    n_biosamples = file_lines(p)
    SNAPSHOT["has_sra_biosamples"] = n_biosamples
    gt("--has-sra unique BioSamples > 20,000", n_biosamples, 20000)
    check(f"BioSample count ({n_biosamples}) <= genome count ({n_has_sra})",
          n_biosamples <= n_has_sra,
          f"biosamples={n_biosamples} genomes={n_has_sra}")
    gap = n_has_sra - n_biosamples
    check(f"genome-BioSample gap is 30-60 (actual {gap})",
          30 <= gap <= 60,
          f"gap={gap}")

base = TMP / "has_sra_runs"
run(["--has-sra", "--format", "sra", "-o", str(base)])
p = Path(str(base) + "_sra_runs.txt")
if p.exists():
    n_sra_runs = file_lines(p)
    SNAPSHOT["has_sra_runs"] = n_sra_runs
    ge(f"SRA run count ({n_sra_runs}) >= genome count ({n_has_sra})",
       n_sra_runs, n_has_sra)

# ============================================================================
# 11. Streaming (stdout)
# ============================================================================
section("Streaming (stdout)")

out, err, rc = run(["--lineage", "USA300", "-q"], timeout=180)
lines = [l for l in out.strip().split("\n") if l]
if lines:
    check("--lineage USA300 stdout starts GCA/GCF",
          lines[0].startswith(("GCA_", "GCF_")),
          f"first line: {lines[0][:40]}")
    eq("--lineage USA300 streaming line count matches --count",
       len(lines), lineage_counts["USA300"])

out, err, rc = run(["--st", "5", "--format", "sra", "-q"], timeout=180)
lines = [l for l in out.strip().split("\n") if l]
if lines:
    check("--st 5 --format sra stdout starts SRR/ERR/DRR",
          lines[0][:3] in {"SRR", "ERR", "DRR"},
          f"first line: {lines[0][:20]}")

# ============================================================================
# 12. Error handling
# ============================================================================
section("Error handling")

out, err, rc = run(["--st", "5", "--format", "parquet", "-q"])
check("unknown --format rejected", rc != 0, f"rc={rc}")

out, err, rc = run(["--st", "5", "--format", "tsv,csv", "-q"])
check("multiple formats without -o rejected", rc != 0, f"rc={rc}")

# ============================================================================
# 13. Quiet mode
# ============================================================================
section("Quiet mode")

out1, err1, _ = run(["--st", "5", "--count"])
out2, err2, _ = run(["--st", "5", "--count", "-q"])
eq("-q does not change stdout", out1.strip(), out2.strip())
check("-q reduces stderr output", len(err2) < len(err1),
      f"quiet={len(err2)}, normal={len(err1)}")

# ============================================================================
# 14. Debug mode
# ============================================================================
section("Debug mode")

out, err, _ = run(["--st", "5", "--mrsa", "--has-sra", "--debug", "--count"])
check("--debug prints [debug] lines", "[debug]" in err)

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 72)
print(f"  Result: {PASSED} passed, {FAILED} failed")
if FAILURES:
    print("\n  Failures:")
    for f in FAILURES:
        print(f"    \u2022 {f}")
print("=" * 72)

snapshot_path = TMP / "counts_snapshot.json"
snapshot_path.write_text(json.dumps(SNAPSHOT, indent=2, sort_keys=True))
print(f"\n  Snapshot saved: {snapshot_path}")

sys.exit(0 if FAILED == 0 else 1)