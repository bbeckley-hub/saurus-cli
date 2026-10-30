# SAURUS-CLI

**Command-line access to the SAURUS *Staphylococcus aureus* genomic surveillance database.**

[![DOI](https://img.shields.io/badge/DOI-10.1186%2Fs12864--026--12609--x-blue)](https://doi.org/10.1186/s12864-026-12609-x)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SAURUS-CLI lets you query 139,257 *S. aureus* genomes by MLST, spa, SCCmec, agr, capsule, AMR genes, virulence factors, and epidemiological metadata—directly from your terminal. It is designed for reproducible surveillance and seamless integration into bioinformatics pipelines (Nextflow, Snakemake, Bash).

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/bbeckley-hub/saurus-cli.git
cd saurus-cli

# 2. Install in editable mode (recommended for development)
pip install -e .
```

After installation, the `saurus` command is available globally.

---

## Quick Start

The most common workflow is: **filter → export → download**.

### 1. Filter by lineage

```bash
# Find all USA300 (ST8, t008, SCCmec IV, agr I) genomes
saurus --lineage USA300 --count
```

### 2. Combine genotype and geography

```bash
# USA300 bloodstream isolates from the United States
saurus --lineage USA300 --country USA --source blood --count
```

### 3. Export accessions

```bash
# Save the matching genome accessions to a text file
saurus --lineage USA300 --country USA --source blood -o usa300_blood.txt
```

### 4. Download genomes from NCBI

```bash
# Feed the accession list to NCBI datasets
datasets download genome accession --inputfile usa300_blood.txt --filename usa300_blood.zip
```

---

## Core Usage

### Query Flags

| Flag | Description | Example |
|---|---|---|
| `--st` | MLST Sequence Type | `--st 5` or `--st ST5` |
| `--cc` | Clonal Complex | `--cc 398` or `--cc CC398` |
| `--spa` | spa Type | `--spa t002` |
| `--sccmec` | SCCmec Type | `--sccmec II` |
| `--agr` | agr Type | `--agr I` |
| `--capsule` | Capsule Serotype | `--capsule 5` or `--capsule 8` |
| `--mrsa` | Filter only MRSA | `--mrsa` |
| `--mssa` | Filter only MSSA | `--mssa` |
| `--country` | Country of origin (searches both `country` and `country_raw`) | `--country USA` or `--country "United States"` |
| `--source` | Isolation source (searches both `source` and `source_raw`) | `--source blood` or `--source nasal` |
| `--host` | Host species | `--host "Homo sapiens"` |
| `--year` | Collection year or range | `--year 2019` or `--year 2015-2023` |
| `--amr` | AMR gene(s), comma-separated | `--amr mecA,tetM` |
| `--vfdb` | Virulence gene(s), comma-separated | `--vfdb pvl,tst` |
| `--plasmid` | Plasmid replicon(s), comma-separated | `--plasmid rep5a` |
| `--any` | Match ANY gene (default is ALL) | `--amr mecA,tetM --any` |

### Output Options

| Flag | Description | Default |
|---|---|---|
| `--count` | Print only the number of matching genomes | Off |
| `--format` | Output format: `accession`, `tsv`, `csv` | `accession` |
| `--output`, `-o` | Output file path | `stdout` |
| `--debug` | Show row counts after each filter | Off |

### Pre-defined Lineage Signatures

Use `--lineage` to apply a curated signature without typing every flag.

| Lineage | Signature |
|---|---|
| `USA100` | ST5, t002, SCCmec II, agr II, capsule 5 |
| `USA300` | ST8, t008, SCCmec IV, agr I, capsule 5 |
| `USA400` | ST1, t128, SCCmec IV, agr III, capsule 8 |
| `USA500` | ST8, t064, SCCmec IV, agr I, capsule 5 |
| `EMRSA-15` | ST22, t032, SCCmec IV, agr I, capsule 5 |
| `EMRSA-16` | ST36, t018, SCCmec II, agr III, capsule 8 |
| `Bengal Bay` | ST772, t657, SCCmec V, agr II, capsule 5 |
| `ST152` | ST152, SCCmec V, agr III, capsule 5 |

> **Note:** Any flag you pass alongside `--lineage` overrides the signature. For example, `--lineage USA300 --country Japan` will use the USA300 signature but restrict results to Japan.

---

## Reproducible Queries with Config Files

For recurring surveillance tasks, save your query as a JSON file.

**`usa100_surveillance.json`**
```json
{
  "st": "5",
  "sccmec": "II",
  "agr": "II",
  "capsule": "5",
  "spa": "t002",
  "source": "blood",
  "country": "USA",
  "format": "tsv",
  "output": "usa100_blood.tsv"
}
```

Run it with:
```bash
saurus --config usa100_surveillance.json
```

---

## Examples Gallery

### Example 1: The "Classic" USA100 Query
```bash
saurus --st 5 --sccmec II --agr II --capsule 5 --spa t002 --source blood --country USA
```
**Expected result:** ~297 genomes (blood isolates in the USA).

### Example 2: USA300 Bloodstream Infections (2005–2015)
```bash
saurus --lineage USA300 --source blood --year 2005-2015 -o usa300_blood_2005_2015.txt
```

### Example 3: Livestock-Associated MRSA (CC398) in Denmark
```bash
saurus --cc 398 --mrsa --country Denmark --host "Sus scrofa" --count
```

### Example 4: PVL-Positive ST8 Genomes
```bash
saurus --st 8 --vfdb lukS-PV --count
```

### Example 5: Multi-Drug Resistant Genomes (mecA + tetM + ermB)
```bash
saurus --amr mecA,tetM,ermB --any --count
```

### Example 6: Pipeline Integration
```bash
# Pipe directly into NCBI datasets (no intermediate file)
saurus --lineage EMRSA-15 --country "United Kingdom" | \
  datasets download genome accession --inputfile /dev/stdin --filename emrsa15_uk.zip
```

---

## Data Requirements

SAURUS-CLI expects a `data/` directory with the following structure:

```
data/
├── mrsa/
│   └── mrsa_all.tsv          # Master TSV (all typing + metadata)
├── mlst/
│   ├── mlst_all.tsv
│   └── cc.txt
├── spa/
│   └── spa_all.tsv
├── sccmec/
│   ├── sccmec_cge_all.tsv
│   └── sccmec_rpet_all.tsv
├── agr/
│   └── agr_all.tsv
├── capsule/
│   └── capsule_all.tsv
├── metadata/
│   └── metadata.tsv
└── gene_annotation/
    ├── amr_all.tsv
    ├── vfdb_all.tsv
    └── plasmid_all.tsv
```

To regenerate the master TSV from individual modules:
```bash
python scripts/build_master_tsv.py
```

---

## Citation

If you use SAURUS-CLI in your research, please cite:

> Beckley B, Amarh V. StaphScope: a species-optimized computational pipeline for rapid and accessible *Staphylococcus aureus* genotyping and surveillance. *BMC Genomics*. 2026;27:261. doi:10.1186/s12864-026-12609-x

And the underlying gene dataset:

> Shelenkov A, Slavokhotova A, Yunusova M, et al. Genomic typing, antimicrobial resistance gene, virulence factor and plasmid replicon database for the important pathogenic bacteria *Staphylococcus aureus*. *BMC Genom Data*. 2025;26:65. doi:10.1186/s12863-025-01363-w

---

## License

MIT License. See [LICENSE](LICENSE) for details.

