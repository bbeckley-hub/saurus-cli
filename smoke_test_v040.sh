#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# smoke_test_v040.sh — run EVERY SAURUS-CLI v0.4.0 example, export path,
# error path, and rendering check, and verify counts against the v1.1.0
# data release (argus-data, saurus-data-v1.1.0).
#
# Usage:
#   cd ~/saurus-cli
#   bash smoke_test_v040.sh                 # expect Data version: v1.1.0
#   bash smoke_test_v040.sh --allow-stale   # run anyway (goldens will DIFF)
#   SAURUS_CLI="saurus" bash smoke_test_v040.sh     # test the installed CLI
#
# Full results (including every recorded count) are written to smoke_results.txt
# — paste that file back for the paper's Table 3 / reviewer evidence.
# ---------------------------------------------------------------------------
set -u

CLI="${SAURUS_CLI:-python3 saurus_cli.py}"
ALLOW_STALE=0
[ "${1:-}" = "--allow-stale" ] && ALLOW_STALE=1

WORK="$(mktemp -d /tmp/saurus_smoke.XXXXXX)"
RESULTS="smoke_results.txt"
PASS=0; DIFF=0; FAIL=0; OK=0

hr(){ printf '%s\n' "────────────────────────────────────────────────────────────────" | tee -a "$RESULTS"; }
section(){ echo | tee -a "$RESULTS"; hr; printf '%s\n' "$1" | tee -a "$RESULTS"; hr; }

# ---- helpers ---------------------------------------------------------------
# cnt <args...>  -> echoes "COUNT" on success (stdout only, quiet)
cnt(){ $CLI "$@" --count -q 2>/dev/null | tail -1; }

# expect <name> <expected-count> <args...>
expect(){
  local name="$1" want="$2"; shift 2
  local got gotn wantn
  got=$(cnt "$@")
  gotn=$(printf '%s' "$got" | tr -d ',')
  wantn=$(printf '%s' "$want" | tr -d ',')
  if   [ "$gotn" = "$wantn" ]; then
    printf '  PASS  %-58s %s\n' "$name" "$got" | tee -a "$RESULTS"; PASS=$((PASS+1))
  elif [ -z "$got" ]; then
    printf '  FAIL  %-58s (no output, rc!=0)\n' "$name" | tee -a "$RESULTS"; FAIL=$((FAIL+1))
  else
    printf '  DIFF  %-58s got %s, expected %s\n' "$name" "$got" "$want" | tee -a "$RESULTS"; DIFF=$((DIFF+1))
  fi
  echo "COUNT|$name|$got" >> "$WORK/counts.txt"
}

# record <name> <args...>   (no golden — just prove it runs and log the count)
record(){
  local name="$1"; shift
  local got; got=$(cnt "$@")
  if [ -n "$got" ]; then
    printf '  OK    %-58s %s\n' "$name" "$got" | tee -a "$RESULTS"; OK=$((OK+1))
  else
    printf '  FAIL  %-58s (no output, rc!=0)\n' "$name" | tee -a "$RESULTS"; FAIL=$((FAIL+1))
  fi
  echo "COUNT|$name|$got" >> "$WORK/counts.txt"
}

# err <name> <expected-rc> <grep-pattern-or-''> <args...>
err(){
  local name="$1" want_rc="$2" pattern="$3"; shift 3
  local out rc
  out=$($CLI "$@" 2>&1 >/dev/null); rc=$?
  local grep_ok=1
  [ -n "$pattern" ] && ! grep -qi "$pattern" <<<"$out" && grep_ok=0
  if [ "$rc" -eq "$want_rc" ] && [ "$grep_ok" -eq 1 ]; then
    printf '  PASS  %-58s rc=%s\n' "$name" "$rc" | tee -a "$RESULTS"; PASS=$((PASS+1))
  else
    printf '  FAIL  %-58s rc=%s (want %s) grep=%s\n' "$name" "$rc" "$want_rc" "$grep_ok" | tee -a "$RESULTS"
    printf '        stderr: %s\n' "$(head -2 <<<"$out" | tr '\n' ' ' | cut -c1-120)" | tee -a "$RESULTS"
    FAIL=$((FAIL+1))
  fi
}

# renders <name> <grep-pattern> <args...>
renders(){
  local name="$1" pattern="$2"; shift 2
  local out rc
  out=$($CLI "$@" 2>/dev/null); rc=$?
  if [ "$rc" -eq 0 ] && grep -q "$pattern" <<<"$out"; then
    printf '  PASS  %-58s renders\n' "$name" | tee -a "$RESULTS"; PASS=$((PASS+1))
  else
    printf '  FAIL  %-58s rc=%s or missing %r\n' "$name" "$rc" "$pattern" | tee -a "$RESULTS"; FAIL=$((FAIL+1))
  fi
}

# export_ok <name> <file> <min-lines>
export_ok(){
  local name="$1" file="$2" minlines="$3"
  if [ -s "$file" ]; then
    local n; n=$(wc -l < "$file")
    if [ "$n" -ge "$minlines" ]; then
      printf '  PASS  %-58s %s lines\n' "$name" "$n" | tee -a "$RESULTS"; PASS=$((PASS+1)); return
    fi
    printf '  FAIL  %-58s only %s lines (want >= %s)\n' "$name" "$n" "$minlines" | tee -a "$RESULTS"
  else
    printf '  FAIL  %-58s file missing/empty: %s\n' "$name" "$file" | tee -a "$RESULTS"
  fi
  FAIL=$((FAIL+1))
}

# ---- preflight -------------------------------------------------------------
echo "SAURUS-CLI smoke test — $(date)" > "$RESULTS"
echo "CLI: $CLI" >> "$RESULTS"

section "0 · Preflight"
VER_OUT=$($CLI --version 2>/dev/null)
CLI_VER=$(grep -o 'v[0-9][0-9.]*' <<<"$VER_OUT" | head -1)
DATA_VER=$(grep -o 'Data version: [^ ]*' <<<"$VER_OUT" | awk '{print $3}')
DATA_DIR=$(grep -o '(.*)' <<<"$VER_OUT" | tr -d '()')
printf '  CLI version  : %s\n  Data version : %s  (%s)\n' "$CLI_VER" "$DATA_VER" "$DATA_DIR" | tee -a "$RESULTS"
[ "$CLI_VER" != "v0.4.0" ] && printf '  FAIL  CLI version is %s, want v0.4.0\n' "$CLI_VER" | tee -a "$RESULTS" && FAIL=$((FAIL+1))
if [ "$DATA_VER" != "v1.1.0" ] && [ "$ALLOW_STALE" -eq 0 ]; then
  printf '  FAIL  Data version is %s, want v1.1.0 — gene goldens will be wrong.\n' "$DATA_VER" | tee -a "$RESULTS"
  printf '  >> Fix: cd ~/argus-data/saurus-data && zip -r ../saurus_data.zip . -x "*.bak"\n'
  printf '  >>      %s init -f ~/argus-data/saurus_data.zip --force\n' "${CLI%% *}"
  printf '  >> Or:  export SAURUS_DATA_DIR=~/saurus-cli/data\n'
  printf '  >> Then re-run, or pass --allow-stale to record stale-bundle values.\n' | tee -a "$RESULTS"
  FAIL=$((FAIL+1))
  STALE=1
else
  STALE=0
fi
echo "DATA|$DATA_VER|$DATA_DIR" >> "$WORK/counts.txt"

# ---- 1 · Info / help commands ----------------------------------------------
section "1 · Info & help"
renders "--version"          "SAURUS-CLI" --version
renders "--help"             "QUICK EXAMPLES" --help
renders "--examples"         "Example Queries" --examples
renders "--examples gene note" "Gene queries are standalone" --examples
renders "--about"            "Citation" --about
renders "--about argus"      "argus" --about
renders "init --help"        "from-file" init --help

# ---- 2 · Gallery: counting genomes ------------------------------------------
section "2 · Gallery — counting genomes"
expect "--lineage USA300" 10448 --lineage USA300
expect "--lineage USA100 --country USA --source blood" 341 --lineage USA100 --country USA --source blood
expect "--st 5 --sccmec II --agr II --mrsa" 7133 --st 5 --sccmec II --agr II --mrsa

# ---- 3 · Gallery: SRA --------------------------------------------------------
section "3 · Gallery — SRA raw reads"
expect "--has-sra" 22322 --has-sra

# ---- 4 · Gallery: metadata ---------------------------------------------------
section "4 · Gallery — metadata queries"
expect "--cc 398 --mrsa --country Denmark" 328 --cc 398 --mrsa --country Denmark
expect "--lineage USA300 --source blood --year 2005-2015" 483 --lineage USA300 --source blood --year 2005-2015
expect "--mrsa --country Ghana" 102 --mrsa --country Ghana

# ---- 5 · Gallery: genotype / gene (standalone) --------------------------------
section "5 · Gallery — genotype & gene queries"
expect "--amr mecA,tetM --any" 45915 --amr mecA,tetM --any
expect "--amr mecA,ermB" 1383 --amr mecA,ermB
if [ "$STALE" -eq 0 ]; then
  expect "--vfdb lukS-PV (master space)" 14856 --vfdb lukS-PV
  expect "--vfdb lukF-PV (master space)" 53293 --vfdb lukF-PV
# annotation-space catalogue pin (freq table covers 98,948 annotated genomes,
# including ones outside the 134K master — hence 19,002 vs 14,856 above)
FQ=$(zcat "$DATA_DIR/gene_annotation/vfdb_gene_freq.tsv.gz" 2>/dev/null \
     | awk -F'\t' '$1=="lukS-PV"{print $3}')
if [ "$FQ" = "19002" ]; then
  printf '  PASS  %-58s %s\n' "freq catalogue lukS-PV (annotation space)" "$FQ" | tee -a "$RESULTS"; PASS=$((PASS+1))
else
  printf '  FAIL  %-58s got %s, expected 19002\n' "freq catalogue lukS-PV (annotation space)" "$FQ" | tee -a "$RESULTS"; FAIL=$((FAIL+1))
fi
echo "COUNT|freq lukS-PV annotation-space|$FQ" >> "$WORK/counts.txt"
else
  record "--vfdb lukS-PV (standalone) [STALE]" --vfdb lukS-PV
fi
record "--st 8 --vfdb lukS-PV" --st 8 --vfdb lukS-PV
record "--amr mecA --lineage USA300" --amr mecA --lineage USA300
record "--plasmid rep21" --plasmid rep21

# ---- 6 · Lineage shortcuts (all 10) ------------------------------------------
section "6 · Lineage shortcuts"
expect "lineage USA300" 10448 --lineage USA300
expect "lineage USA100" 3342 --lineage USA100
record "lineage USA400" --lineage USA400
record "lineage USA500" --lineage USA500
record "lineage USA700" --lineage USA700
record "lineage USA800" --lineage USA800
expect "lineage EMRSA-15 UK" 654 --lineage EMRSA-15 --country "United Kingdom"
expect "lineage EMRSA-16 UK" 190 --lineage EMRSA-16 --country "United Kingdom"
expect "lineage Bengal Bay" 380 --lineage Bengal_Bay
expect "lineage ST152" 16 --lineage ST152
expect "--st 152 (broad)" 749 --st 152
record "lineage usa300 (lowercase)" --lineage usa300

# ---- 7 · Exports (every format) ----------------------------------------------
section "7 · Exports"
OUT="$WORK/out"
mkdir -p "$OUT"
$CLI --lineage USA300 -o "$OUT/usa300.txt" -q >/dev/null 2>&1 && export_ok "accession export" "$OUT/usa300.txt" 10000
$CLI --lineage USA300 --format tsv,accession -o "$OUT/usa300_results" -q >/dev/null 2>&1 \
  && export_ok "multi tsv,accession" "$OUT/usa300_results.tsv" 10000 \
  && export_ok "multi tsv,accession (txt)" "$OUT/usa300_results.txt" 10000
$CLI --lineage USA300 --format csv,json,accession -o "$OUT/usa300_cja" -q >/dev/null 2>&1 \
  && export_ok "csv" "$OUT/usa300_cja.csv" 10000 \
  && export_ok "json" "$OUT/usa300_cja.json" 10000 \
  && export_ok "accession" "$OUT/usa300_cja.txt" 10000
$CLI --lineage USA300 --format sra -o "$OUT/usa300_runs" -q >/dev/null 2>&1 && export_ok "sra" "$OUT/usa300_runs_sra_runs.txt" 1
$CLI --lineage USA300 --format biosample -o "$OUT/usa300_samples" -q >/dev/null 2>&1 && export_ok "biosample" "$OUT/usa300_samples_biosamples.txt" 1
$CLI --lineage USA300 --format bioproject -o "$OUT/usa300_projects" -q >/dev/null 2>&1 && export_ok "bioproject" "$OUT/usa300_projects_bioprojects.txt" 1
$CLI --lineage USA300 --format tsv,accession,sra,biosample -o "$OUT/usa300_all" -q >/dev/null 2>&1 \
  && export_ok "4-format tsv" "$OUT/usa300_all.tsv" 10000 \
  && export_ok "4-format sra" "$OUT/usa300_all_sra_runs.txt" 1
# header sanity for the TSV export
head -1 "$OUT/usa300_results.tsv" 2>/dev/null | grep -q "accession" \
  && printf '  PASS  %-58s\n' "tsv header contains 'accession'" | tee -a "$RESULTS" && PASS=$((PASS+1)) \
  || { printf '  FAIL  tsv header\n' | tee -a "$RESULTS"; FAIL=$((FAIL+1)); }

# ---- 8 · Reproducible workflow (config) ---------------------------------------
section "8 · Reproducible workflow (config)"
cat > "$WORK/q.json" <<'EOF'
{"lineage": "USA100", "country": "USA", "source": "blood"}
EOF
A=$(cnt --config "$WORK/q.json"); B=$(cnt --lineage USA100 --country USA --source blood)
if [ -n "$A" ] && [ "$A" = "$B" ]; then
  printf '  PASS  %-58s %s\n' "config == equivalent CLI flags" "$A" | tee -a "$RESULTS"; PASS=$((PASS+1))
else
  printf '  FAIL  config=%s cli=%s\n' "$A" "$B" | tee -a "$RESULTS"; FAIL=$((FAIL+1))
fi
echo "COUNT|config≡CLI|$A" >> "$WORK/counts.txt"

# ---- 9 · Diagnostics ----------------------------------------------------------
section "9 · Diagnostics"
DBG=$($CLI --st 5 --agr I --debug --count -q 2>&1 >/dev/null | grep -c "rows")
[ "${DBG:-0}" -ge 2 ] \
  && printf '  PASS  %-58s (%s debug steps)\n' "--debug shows per-filter counts" "$DBG" | tee -a "$RESULTS" && PASS=$((PASS+1)) \
  || { printf '  FAIL  --debug steps=%s\n' "$DBG" | tee -a "$RESULTS"; FAIL=$((FAIL+1)); }

# ---- 10 · Error paths ----------------------------------------------------------
section "10 · Error paths"
err   "unknown lineage"              1 "Unknown lineage"        --lineage NOPE --count
err   "unknown format"               1 "Unknown format"         --lineage USA300 --format bogus --count
err   "unknown AMR gene (fatal)"     1 "not found in the SAURUS" --amr NOT_A_REAL_GENE_XYZ --count
err   "unknown VFDB gene (fatal)"    1 "not found in the SAURUS" --vfdb NOT_A_REAL_GENE --count
err   "missing config file"          1 "not found"              --config "$WORK/missing.json" --count
err   "multi-format without -o"      1 "specify --output"       --lineage USA300 --format tsv,accession
echo '{"bogus_key": 1}' > "$WORK/badkey.json"
err   "unknown config key (fatal)"    1 "Unknown config key"    --config "$WORK/badkey.json" --count

# ---- summary -------------------------------------------------------------------
section "SUMMARY"
printf '  PASS %d   OK(recorded) %d   DIFF %d   FAIL %d\n' "$PASS" "$OK" "$DIFF" "$FAIL" | tee -a "$RESULTS"
cat "$WORK/counts.txt" >> "$RESULTS"
printf '\nFull value log: %s\n' "$RESULTS"
rm -rf "$WORK"
[ "$FAIL" -eq 0 ]
