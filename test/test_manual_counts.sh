#!/usr/bin/env bash
#
# test_manual_counts.sh — Run all CLI manual examples to get exact counts.
#

echo "=================================================="
echo " SAURUS CLI - Manual Example Counts"
echo "=================================================="
echo ""

echo "--- 1. Counting Genomes ---"
echo -n "USA300 globally:               "; saurus --lineage USA300 --count -q 2>/dev/null
echo -n "USA100 blood USA:              "; saurus --lineage USA100 --country USA --source blood --count -q 2>/dev/null
echo -n "ST5 SCCmec II agr II MRSA:     "; saurus --st 5 --sccmec II --agr II --mrsa --count -q 2>/dev/null
echo -n "CC398 MRSA Denmark (Sus):      "; saurus --cc 398 --mrsa --country Denmark --host "Sus scrofa" --count -q 2>/dev/null
echo -n "MRSA Ghana:                    "; saurus --mrsa --country Ghana --count -q 2>/dev/null
echo ""

echo "--- 2. SRA Raw Reads ---"
echo -n "Genomes with SRA:              "; saurus --has-sra --count -q 2>/dev/null
saurus --lineage USA300 --format sra -o /tmp/test_usa300_sra -q 2>/dev/null
echo "USA300 SRA runs exported:       $(wc -l < /tmp/test_usa300_sra_sra_runs.txt 2>/dev/null || echo "0 (file not generated)")"
rm -f /tmp/test_usa300_sra_sra_runs.txt
echo ""

echo "--- 3. Genotype Queries ---"
echo -n "ST8 PVL-positive (lukS-PV):    "; saurus --st 8 --vfdb lukS-PV --count -q 2>/dev/null
echo -n "MRSA mecA AND ermB:            "; saurus --amr mecA,ermB --count -q 2>/dev/null
echo -n "MRSA mecA OR tetM (--any):     "; saurus --amr mecA,tetM --any --count -q 2>/dev/null
echo -n "Plasmid rep5a:                 "; saurus --plasmid rep5a --count -q 2>/dev/null
echo ""

echo "--- 4. Metadata Queries ---"
saurus --lineage USA300 --source blood --year 2005-2015 -o /tmp/test_usa300_2005 -q 2>/dev/null
echo "USA300 blood 2005-2015:         $(wc -l < /tmp/test_usa300_2005.txt 2>/dev/null || echo "0 (file not generated)")"
rm -f /tmp/test_usa300_2005.txt
echo -n "EMRSA-15 UK:                   "; saurus --lineage EMRSA-15 --country "United Kingdom" --count -q 2>/dev/null
echo -n "Bengal Bay India:              "; saurus --lineage "Bengal Bay" --country India --count -q 2>/dev/null
echo -n "EMRSA-16 UK 2020-2025:         "; saurus --lineage EMRSA-16 --country "United Kingdom" --count -q 2>/dev/null
echo ""

echo "--- 5. Lineages ---"
echo -n "USA300 Japan:                  "; saurus --lineage USA300 --country Japan --count -q 2>/dev/null
echo -n "ST152 Ghana:                   "; saurus --st ST152 --count 
 -q 2>/dev/null
echo ""

echo "--- 6. Diagnostics (should be 0) ---"
echo -n "ST5 agr I capsule 8:           "; saurus --st 5 --agr I --capsule 8 --count -q 2>/dev/null || true
echo ""

echo "=================================================="
echo " Done. Please copy the output above."
echo "=================================================="
