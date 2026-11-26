#!/usr/bin/env bash
# r2_regression_test.sh — re-runs every test Reviewer 2 performed on saurus-cli 0.3.0
# against the corrected release pair (CLI v0.4.0 + data v1.1.0).
# Usage:
#   bash r2_regression_test.sh                    # offline checks
#   RUN_ONLINE=1 bash r2_regression_test.sh       # also re-download data v1.1.0
set -u
cd "$(dirname "$0")"

CLI="${SAURUS_CLI:-python3 saurus_cli.py}"
D="${SAURUS_DATA_DIR:-$HOME/.saurus/data}"
OUT="r2_regression_results.txt"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0

hdr() { printf '\n%s\n%s\n%s\n' "────────────────────────────────────────" "$1" "────────────────────────────────────────" | tee -a "$OUT"; }
ok()  { printf '  PASS  %-52s %s\n' "$1" "$2" | tee -a "$OUT"; PASS=$((PASS+1)); }
bad() { printf '  FAIL  %-52s %s\n' "$1" "$2" | tee -a "$OUT"; FAIL=$((FAIL+1)); }
note(){ printf '  note  %-52s %s\n' "$1" "$2" | tee -a "$OUT"; }

expect() { # label expected query...
  local label="$1" exp="$2"; shift 2
  local got; got=$($CLI "$@" --count -q 2>/dev/null | tail -1 | tr -d ',')
  if [ "$got" = "$exp" ]; then ok "$label" "$got"; else bad "$label" "got ${got:-<none>}, expected $exp"; fi
}

rc_nonzero() { # label query...
  local label="$1"; shift
  $CLI "$@" >/dev/null 2>&1
  local rc=$?
  if [ "$rc" -ne 0 ]; then ok "$label" "rc=$rc (loud failure)"; else bad "$label" "rc=0, expected non-zero"; fi
}

echo "SAURUS-CLI R2 regression test — $(date)" > "$OUT"
echo "CLI: $CLI" >> "$OUT"

hdr "0 · Preflight (R2 baseline: CLI 0.3.0, data v1.0.0)"
VER=$($CLI --version 2>/dev/null)
echo "$VER" | tee -a "$OUT"
echo "$VER" | grep -q "v0.4.0" && ok "CLI version v0.4.0" "renders" || bad "CLI version v0.4.0" "$VER"
echo "$VER" | grep -q "Data version: v1.1.0" && ok "Data version v1.1.0" "renders" || bad "Data version v1.1.0" "not reported"

hdr "1 · Dataset integrity (R2 §1: damaged, incomplete virulence layer)"

# R2: vfdb_all.tsv.gz stopped mid-record at exactly 1,048,576 lines (Excel cap),
# covering only 13,978 genomes.
LINES=$(zcat "$D/gene_annotation/vfdb_all.tsv.gz" | wc -l)
[ "$LINES" -gt 1048576 ] && ok "vfdb table exceeds Excel row cap" "$LINES lines" || bad "vfdb table exceeds Excel row cap" "$LINES lines (cap 1,048,576)"
H=$(zcat "$D/gene_annotation/vfdb_all.tsv.gz" | head -1 | awk -F'\t' '{print NF}')
Tl=$(zcat "$D/gene_annotation/vfdb_all.tsv.gz" | tail -1 | awk -F'\t' '{print NF}')
[ "$H" = "$Tl" ] && [ "$H" -ge 2 ] && ok "last vfdb record is complete" "$Tl/$H fields" || bad "last vfdb record is complete" "header $H vs last $Tl fields"

# R2: freq table (isdI = 98,915) contradicted the virulence table (13,978 genomes).
VACC=$(zcat "$D/gene_annotation/vfdb_all.tsv.gz" | tail -n +2 | cut -f1 | sed 's/\.fna$//' | sort -u | wc -l)
FMAX=$(zcat "$D/gene_annotation/vfdb_gene_freq.tsv.gz" | tail -n +2 | cut -f3 | sort -n | tail -1)
[ "$VACC" = "98948" ] && ok "vfdb annotated universe" "$VACC accessions (was 13,978)" || bad "vfdb annotated universe" "got $VACC, expected 98948"
if [ -n "$FMAX" ] && [ "$FMAX" -le "$VACC" ]; then ok "freq table consistent with vfdb table" "max freq $FMAX <= $VACC"; else bad "freq table consistent with vfdb table" "max freq ${FMAX:-none} vs $VACC"; fi

# R2: 3,182 of 134,273 master genomes had any virulence data.
MASS=$(zcat "$D/mrsa/mrsa_all.tsv.gz" | tail -n +2 | cut -f1 | sort -u)
MASS_N=$(printf '%s\n' "$MASS" | wc -l)
[ "$MASS_N" = "134273" ] && ok "master collection size" "$MASS_N" || bad "master collection size" "got $MASS_N, expected 134273"
for m in amr vfdb plasmid; do
  zcat "$D/gene_annotation/${m}_all.tsv.gz" | tail -n +2 | cut -f1 | sed 's/\.fna$//' | sort -u > "$T/$m.txt"
done
printf '%s\n' "$MASS" | sort -u > "$T/master.txt"
IN_VF=$(comm -12 "$T/master.txt" "$T/vfdb.txt" | wc -l)
IN_AM=$(comm -12 "$T/master.txt" "$T/amr.txt" | wc -l)
OUT_AM=$(comm -23 "$T/amr.txt" "$T/master.txt" | wc -l)
OUT_VF=$(comm -23 "$T/vfdb.txt" "$T/master.txt" | wc -l)
OUT_PL=$(comm -23 "$T/plasmid.txt" "$T/master.txt" | wc -l)
[ "$IN_VF" = "75830" ] && ok "master genomes with virulence data" "$IN_VF (was 3,182)" || bad "master genomes with virulence data" "got $IN_VF, expected 75830"
[ "$IN_AM" -gt 60000 ] && ok "master genomes with AMR data" "$IN_AM (R2 saw mass GCA/GCF loss)" || bad "master genomes with AMR data" "got $IN_AM"
[ "$OUT_AM" = "20903" ] && ok "AMR-annotated outside master (documented)" "$OUT_AM" || bad "AMR-annotated outside master (documented)" "got $OUT_AM, expected 20903"
[ "$OUT_VF" = "23118" ] && ok "VFDB-annotated outside master (documented)" "$OUT_VF" || bad "VFDB-annotated outside master (documented)" "got $OUT_VF, expected 23118"
[ "$OUT_PL" = "20287" ] && ok "plasmid-annotated outside master (documented)" "$OUT_PL" || bad "plasmid-annotated outside master (documented)" "got $OUT_PL, expected 20287"

# R2's biologically implausible examples.
expect "USA300 + lukS-PV (was 165)"        4429  --lineage USA300 --vfdb lukS-PV
expect "ST8 + lukS-PV (was 258)"           6919  --st 8 --vfdb lukS-PV

hdr "2 · Filter correctness (R2 §2)"

# R2: --amr ZZZZ --any returned the entire database (134,273).
rc_nonzero "unknown gene, --any mode (was 134,273)" --amr ZZZZ --any --count
rc_nonzero "unknown gene, ALL mode"                 --amr ZZZZ --count

# R2: --cc + phenotype silently returned 0 (empty mlst_cc column).
expect "--cc 8 --mrsa (was 0)"                     24161 --cc 8 --mrsa
expect "--cc 398 --mrsa --country Denmark (was 0)"   328 --cc 398 --mrsa --country Denmark
CC398=$($CLI --cc 398 --count -q 2>/dev/null | tail -1 | tr -d ',')
[ -n "$CC398" ] && [ "$CC398" -gt 0 ] && ok "--cc 398 alone positive" "$CC398" || bad "--cc 398 alone positive" "got ${CC398:-none}"

# R2: config ignored "lineage"; CLI did not override config; numeric year crashed.
CFG="$T/usa100.json"
printf '%s\n' '{"lineage":"USA100","country":"USA","source":"blood"}' > "$CFG"
C_CFG=$($CLI --config "$CFG" --count -q 2>/dev/null | tail -1 | tr -d ',')
[ "$C_CFG" = "341" ] && ok "config honours lineage key (was ignored)" "$C_CFG" || bad "config honours lineage key (was ignored)" "got ${C_CFG:-none}, expected 341"
C_NOFMT=$($CLI --lineage USA100 --country USA --source blood --count -q 2>/dev/null | tail -1 | tr -d ',')
[ "$C_CFG" = "$C_NOFMT" ] && ok "config == equivalent CLI flags" "both $C_CFG" || bad "config == equivalent CLI flags" "config $C_CFG vs flags $C_NOFMT"
OV=$($CLI --config "$CFG" --country Japan --count -q 2>"$T/ov.err" | tail -1 | tr -d ',')
if [ -n "$OV" ] && [ "$OV" != "341" ] && grep -q "overrides config" "$T/ov.err"; then
  ok "CLI flag overrides config (was ignored)" "Japan: $OV (config: 341)"
else
  bad "CLI flag overrides config (was ignored)" "got ${OV:-none}, override log missing"
fi
printf '%s\n' '{"lineage":"USA100","country":"USA","year":2019}' > "$T/numyear.json"
NY=$($CLI --config "$T/numyear.json" --count -q 2>/dev/null | tail -1 | tr -d ',')
[ -n "$NY" ] && [ "$NY" != "" ] && ok "numeric year value does not crash (was crash)" "rc=0, count $NY" || bad "numeric year value does not crash (was crash)" "no output"
printf '%s\n' '{"nosuchflag":true}' > "$T/badkey.json"
rc_nonzero "unknown config key is fatal (was ignored)" --config "$T/badkey.json"

# R2: substring country matching (Oman→Romania, Mali→Somalia, India→Indiana/USA).
country_clean() { # label country forbidden_substring
  local label="$1" c="$2" forbid="$3"
  $CLI --country "$c" --format tsv -o "$T/c.tsv" -q 2>/dev/null
  local n hits
  n=$(( $(wc -l < "$T/c.tsv") - 1 ))
  hits=$(tail -n +2 "$T/c.tsv" | grep -ci "$forbid" || true)
  if [ "$n" -gt 0 ] && [ "$hits" = "0" ]; then ok "$label" "$n rows, 0 '$forbid'"; else bad "$label" "$n rows, $hits '$forbid' hits"; fi
}
country_clean "--country Oman excludes Romania (was matched)" Oman  "romania"
country_clean "--country Mali excludes Somalia (was matched)" Mali  "somalia"
country_clean "--country India excludes Indiana (was matched)" India "indiana"

# R2: gene names treated as regex; tetM and tet(M) returned 0.
$CLI --amr tetM --count -q 2>/dev/null | tail -1 | tr -d ',' > "$T/t1"
$CLI --amr "tet(M)" --count -q 2>/dev/null | tail -1 | tr -d ',' > "$T/t2"
if [ -s "$T/t1" ] && [ "$(cat "$T/t1")" = "$(cat "$T/t2")" ] && [ "$(cat "$T/t1")" -gt 0 ]; then
  ok "tetM == tet(M), no regex needed (was 0/0)" "$(cat "$T/t1")"
else
  bad "tetM == tet(M), no regex needed (was 0/0)" "tetM=$(cat "$T/t1" 2>/dev/null) tet(M)=$(cat "$T/t2" 2>/dev/null)"
fi
expect "mecA master-space count"                       45432 --amr mecA
expect "mecA,tetM --any"                               45915 --amr mecA,tetM --any
expect "mecA,tetM ALL"                                  8060 --amr mecA,tetM
expect "cross-module mecA+lukS-PV --any (corrected)"   47301 --amr mecA --vfdb lukS-PV --any

hdr "3 · Reproducibility (R2 §3)"

# R2: documented data version returned HTTP 404.
if [ "${RUN_ONLINE:-0}" = "1" ]; then
  SAURUS_DATA_DIR="$T/online" $CLI init -v v1.1.0 --force > "$T/init.log" 2>&1
  if [ $? -eq 0 ] && grep -qi "checksum verified" "$T/init.log"; then
    ok "init -v v1.1.0 downloads + verifies (was 404)" "remote release resolves"
  else
    bad "init -v v1.1.0 downloads + verifies (was 404)" "see $T/init.log"
  fi
  DV=$(SAURUS_DATA_DIR="$T/online" $CLI --version -q 2>/dev/null | grep -o 'v1\.1\.0' | head -1)
  [ "$DV" = "v1.1.0" ] && ok "remote install reports v1.1.0" "$DV" || bad "remote install reports v1.1.0" "got ${DV:-none}"
  SAURUS_DATA_DIR="$T/online" $CLI init -v v1.1.0 --force > /dev/null 2>&1 \
    && ok "init -v idempotent re-run (was no-op)" "rc=0" \
    || bad "init -v idempotent re-run (was no-op)" "rc!=0"
else
  note "online checks skipped" "re-run with RUN_ONLINE=1"
fi

# R2: checksum verification skipped when sidecar missing; --from-file unverified.
cp "$HOME/argus-data/saurus_data.zip" "$T/nochecksum.zip"
SAURUS_DATA_DIR="$T/x1" $CLI init -f "$T/nochecksum.zip" --force >/dev/null 2>&1
[ $? -ne 0 ] && ok "from-file without sidecar refused" "rc!=0" || bad "from-file without sidecar refused" "installed without verification"
SAURUS_DATA_DIR="$T/x1b" $CLI init -f "$T/nochecksum.zip" --force --allow-unverified > "$T/x1b.log" 2>&1
if [ $? -eq 0 ] && grep -q "allow-unverified" "$T/x1b.log"; then
  ok "from-file + --allow-unverified proceeds" "rc=0 (explicit opt-out)"
else
  bad "from-file + --allow-unverified proceeds" "see $T/x1b.log"
fi
cp "$HOME/argus-data/saurus_data.zip" "$T/tamper.zip"
printf 'deadbeef%s  %s\n' "$(head -c 48 /dev/zero | tr '\0' '0')" "$T/tamper.zip" > "$T/tamper.zip.sha256"
SAURUS_DATA_DIR="$T/x2" $CLI init -f "$T/tamper.zip" --force >/dev/null 2>&1
[ $? -ne 0 ] && ok "wrong checksum refused" "rc!=0" || bad "wrong checksum refused" "bad checksum accepted"
if [ -f "$HOME/argus-data/saurus_data.zip.sha256" ]; then
  SAURUS_DATA_DIR="$T/x3" $CLI init -f "$HOME/argus-data/saurus_data.zip" --force > "$T/good.log" 2>&1
  if [ $? -eq 0 ] && grep -qi "checksum verified" "$T/good.log"; then
    ok "valid sidecar installs + verifies" "$(cat "$T/x3/DATA_VERSION" 2>/dev/null)"
  else
    bad "valid sidecar installs + verifies" "see $T/good.log"
  fi
else
  note "valid-sidecar install check skipped" "$HOME/argus-data/saurus_data.zip.sha256 not found"
fi

hdr "4 · Manuscript claims (R2 §4)"

NCOL=$(zcat "$D/mrsa/mrsa_all.tsv.gz" | head -1 | awk -F'\t' '{print NF}')
[ "$NCOL" = "20" ] && ok "master table has 20 columns" "$NCOL" || bad "master table has 20 columns" "got $NCOL"
GZ=$(stat -c%s "$D/mrsa/mrsa_all.tsv.gz")
[ "$GZ" -ge 1500000 ] && [ "$GZ" -le 3000000 ] && ok "master table gz ~2.1 MB" "$((GZ/1024/1024)) MB" || bad "master table gz ~2.1 MB" "$GZ bytes"
UNC=$(zcat "$D/mrsa/mrsa_all.tsv.gz" | wc -c)
[ "$UNC" -ge 18000000 ] && [ "$UNC" -le 28000000 ] && ok "master table uncompressed ~22.5 MB" "$((UNC/1024/1024)) MB" || bad "master table uncompressed ~22.5 MB" "$UNC bytes"
DATAV=$(cat "$D/DATA_VERSION" 2>/dev/null)
[ "$DATAV" = "v1.1.0" ] && ok "DATA_VERSION marker" "$DATAV" || bad "DATA_VERSION marker" "got ${DATAV:-none}"
note "six-tier search honours SAURUS_DATA_DIR" "resolved: $D"
for f in tsv csv json accession sra biosample bioproject; do
  $CLI --lineage USA300 --format "$f" -o "$T/f_$f" -q >/dev/null 2>&1
  [ -s "$T/f_$f"* ] 2>/dev/null && ok "format $f produces output" "non-empty" || bad "format $f produces output" "missing/empty"
done
FCSV=$(cat "$T/f_sra_sra_runs.txt" 2>/dev/null | wc -l)
[ "$FCSV" = "1821" ] && ok "SRA export for USA300" "$FCSV lines (was undocumented)" || bad "SRA export for USA300" "got $FCSV, expected 1821"
hdr "5 · Rebuild scripts (R2 §5)"
for s in build_master_tsv.py curate_gene_tables.py verify_data_release.py package_data.sh inspect_annotations.py generate_mrsa.py; do
  [ -f "scripts/$s" ] && ok "scripts/$s present" "found" || bad "scripts/$s present" "missing"
done

hdr "SUMMARY"
printf '  PASS %d   FAIL %d\n' "$PASS" "$FAIL" | tee -a "$OUT"
[ "$FAIL" = "0" ] && echo "R2 REGRESSION: ALL CHECKS PASS" | tee -a "$OUT" || echo "R2 REGRESSION: FAILURES PRESENT" | tee -a "$OUT"
echo "Full log: $OUT"
exit "$FAIL"
