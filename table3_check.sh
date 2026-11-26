#!/usr/bin/env bash
# table3_check.sh — verify every remaining Table 3 query on the v1.1.0 bundle
set -u
CLI="${SAURUS_CLI:-python3 saurus_cli.py}"
OUT="table3_results.txt"
echo "SAURUS Table 3 check — $(date)" > "$OUT"
PASS=0; DIFF=0; FAIL=0

chk(){
  local name="$1" want="$2"; shift 2
  local got; got=$($CLI "$@" --count -q 2>/dev/null | tail -1)
  local gotn wantn
  gotn=$(printf '%s' "$got" | tr -d ','); wantn=$(printf '%s' "$want" | tr -d ',')
  if [ "$gotn" = "$wantn" ]; then
    printf '  PASS  %-52s %s\n' "$name" "$got" | tee -a "$OUT"; PASS=$((PASS+1))
  elif [ -z "$got" ]; then
    printf '  FAIL  %-52s (no output)\n' "$name" | tee -a "$OUT"; FAIL=$((FAIL+1))
  else
    printf '  DIFF  %-52s got %s, expected %s\n' "$name" "$got" "$want" | tee -a "$OUT"; DIFF=$((DIFF+1))
  fi
  echo "COUNT|$name|$got" >> "$OUT"
}

chk "--amr mecA --vfdb lukS-PV --any"  NEW --amr mecA --vfdb lukS-PV --any
chk "--amr mecA,tetM (ALL)"            8060  --amr mecA,tetM
chk "--vfdb lukF-PV"                   53293 --vfdb lukF-PV
chk "--lineage EMRSA-15 (global)"      1209  --lineage EMRSA-15
chk "--spa t032"                       1294  --spa t032
chk "--sccmec IV"                      48018 --sccmec IV
chk "--agr I"                          75123 --agr I
chk "--capsule 5"                      84006 --capsule 5
chk "--mssa"                           53940 --mssa
chk "--year 2020"                      10636 --year 2020
chk "--st 5 --agr I --capsule 8 (0)"   0     --st 5 --agr I --capsule 8

printf '\n  PASS %d   DIFF %d   FAIL %d\n' "$PASS" "$DIFF" "$FAIL" | tee -a "$OUT"
printf 'Full log: %s\n' "$OUT"
