# SAURUS-CLI

**Command-line access to the SAURUS *Staphylococcus aureus* genomic surveillance database.**

[![PyPI](https://img.shields.io/pypi/v/saurus-cli.svg)](https://pypi.org/project/saurus-cli/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/saurus-cli.svg)](https://pypi.org/project/saurus-cli/)
[![Docker Hub](https://img.shields.io/docker/v/bbeckleyhub/saurus-cli?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/bbeckleyhub/saurus-cli)
[![Conda](https://img.shields.io/conda/vn/bioconda/saurus-cli?label=bioconda&logo=anaconda)](https://anaconda.org/bioconda/saurus-cli)
[![DOI](https://img.shields.io/badge/DOI-10.1186%2Fs12864--026--12609--x-blue)]( https://doi.org/10.5281/zenodo.24084554)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SAURUS-CLI lets you query 134,160 *S. aureus* genomes by MLST, spa, SCCmec, agr, capsule, AMR genes, virulence factors, and epidemiological metadata directly from your terminal. It is designed for reproducible surveillance and seamless integration into bioinformatics pipelines (Nextflow, Snakemake, Bash).

The full dataset is bundled inside every distribution. After installation, queries run locally with no downloads, no API keys, and no network access.

---

## Installation

Choose whichever fits your workflow. All four methods deliver the same CLI and the same bundled data.

### pip

```bash
pip install saurus-cli
```

### uv (fastest)

```bash
uv tool install saurus-cli
```

### pipx (isolated environment)

```bash
pipx install saurus-cli
```

### conda (Bioconda, after merge)

```bash
conda install -c bioconda saurus-cli
```

### Docker

```bash
docker pull bbeckleyhub/saurus-cli:latest
docker run --rm bbeckleyhub/saurus-cli:latest --version
```

After installation, the `saurus` command is available globally. Verify with:

```bash
saurus --version
saurus --lineage USA300 --count
```

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

### Query flags

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
| `--country` | Country of origin (searches both `country` and `country_raw`) | `--country USA` |
| `--source` | Isolation source (searches both `source` and `source_raw`) | `--source blood` |
| `--host` | Host species | `--host "Homo sapiens"` |
| `--year` | Collection year or range | `--year 2019` or `--year 2015-2023` |
| `--amr` | AMR gene(s), comma-separated | `--amr mecA,tetM` |
| `--vfdb` | Virulence gene(s), comma-separated | `--vfdb pvl,tst` |
| `--plasmid` | Plasmid replicon(s), comma-separated | `--plasmid rep5a` |
| `--any` | Match ANY gene (default is ALL) | `--amr mecA,tetM --any` |

### Output options

| Flag | Description | Default |
|---|---|---|
| `--count` | Print only the number of matching genomes | Off |
| `--format` | Output format(s): `accession`, `tsv`, `csv`, `json` (comma-separated) | `accession` |
| `--output`, `-o` | Output base path (extension added per format) | `stdout` |
| `--quiet`, `-q` | Suppress banner and footer (useful for scripts) | Off |
| `--debug` | Show row counts after each filter | Off |

### Pre-defined lineage signatures

Use `--lineage` to apply a curated signature without typing every flag.

| Lineage | Signature |
|---|---|
| `USA100` | ST5, t002, SCCmec II, agr II, capsule 5 |
| `USA300` | ST8, t008, SCCmec IV, agr I, capsule 5 |
| `USA400` | ST1, t128, SCCmec IV, agr III, capsule 8 |
| `USA500` | ST8, t064, SCCmec IV, agr I, capsule 5 |
| `USA700` | ST72, t324, SCCmec IV, agr I, capsule 5 |
| `USA800` | ST5, t688, SCCmec IV, agr II, capsule 5 |
| `EMRSA-15` | ST22, t032, SCCmec IV, agr I, capsule 5 |
| `EMRSA-16` | ST36, t018, SCCmec II, agr III, capsule 8 |
| `Bengal Bay` | ST772, t657, SCCmec V, agr II, capsule 5 |
| `ST152` | ST152, SCCmec V, agr III, capsule 5 |

> **Note:** Any flag you pass alongside `--lineage` overrides the signature. For example, `--lineage USA300 --country Japan` uses the USA300 signature but restricts results to Japan.

---

## Reproducible Queries with Config Files

For recurring surveillance tasks, save your query as a JSON file.

**`usa100_surveillance.json`**

```json
{
  "lineage": "USA100",
  "country": "United States",
  "source": "blood",
  "mrsa": true,
  "year": "2020-2025",
  "format": "tsv,accession",
  "output": "usa100_blood_2020_2025"
}
```

Run it with:

```bash
saurus --config usa100_surveillance.json
```

The output is two files (`usa100_blood_2020_2025.tsv` and `usa100_blood_2020_2025.txt`). Any command-line flag overrides the corresponding config value, so you can reuse a config file with a one-off change:

```bash
saurus --config usa100_surveillance.json --country Japan
```

---

## Examples Gallery

### Example 1: The classic USA100 query

```bash
saurus --st 5 --sccmec II --agr II --capsule 5 --spa t002 --source blood --country USA
```

Expected result: approximately 297 genomes (blood isolates in the USA).

### Example 2: USA300 bloodstream infections (2005-2015)

```bash
saurus --lineage USA300 --source blood --year 2005-2015 -o usa300_blood_2005_2015.txt
```

### Example 3: Livestock-associated MRSA (CC398) in Denmark

```bash
saurus --cc 398 --mrsa --country Denmark --host "Sus scrofa" --count
```

### Example 4: PVL-positive ST8 genomes

```bash
saurus --st 8 --vfdb lukS-PV --count
```

### Example 5: Multi-drug resistant genomes (mecA + tetM + ermB)

```bash
saurus --amr mecA,tetM,ermB --any --count
```

### Example 6: Multi-format export in one run

```bash
saurus --lineage USA300 --country USA --source blood \
    --format tsv,json,accession -o usa300_blood
```

Produces three files: `usa300_blood.tsv`, `usa300_blood.json`, and `usa300_blood.txt`.

### Example 7: Pipeline integration

```bash
# Pipe directly into NCBI datasets (no intermediate file)
saurus --lineage EMRSA-15 --country "United Kingdom" | \
  datasets download genome accession --inputfile /dev/stdin --filename emrsa15_uk.zip
```

### Example 8: Debugging a query that returns zero

```bash
saurus --st 5 --agr I --capsule 8 --debug --count
```

The `--debug` output shows the row count after each filter, so you can see exactly where a query collapsed:

```
[debug] Initial load: 134,299 rows
[debug] --st 5:        14,930 rows
[debug] --agr I:            0 rows    ← the culprit
```

Run `saurus --examples` for the full gallery inside your terminal.

---

## Docker usage

The Docker image bundles the full dataset and the NCBI `datasets` CLI, so you can fetch genomes without installing anything on your host.

```bash
# Count genomes
docker run --rm bbeckleyhub/saurus-cli:latest --lineage USA300 --count

# Export to host directory
docker run --rm -v "$PWD:/work" bbeckleyhub/saurus-cli:latest \
    --lineage USA300 --country USA --source blood \
    --format tsv,accession -o usa300_blood
```

Full Docker Hub README: https://hub.docker.com/r/bbeckleyhub/saurus-cli

---

## Data requirements

If you clone the repository and install in editable mode, SAURUS-CLI expects a `data/` directory with the following structure. All files are gzip-compressed (`*.tsv.gz`) in the distributed package, and the CLI reads both compressed and uncompressed files transparently.

```
data/
├── mrsa/
│   └── mrsa_all.tsv.gz          # Master TSV (all typing + metadata)
├── mlst/
│   ├── mlst_all.tsv.gz
│   └── cc.txt.gz
├── spa/
│   └── spa_all.tsv.gz
├── sccmec/
│   ├── sccmec_cge_all.tsv.gz
│   └── sccmec_rpet_all.tsv.gz
├── agr/
│   └── agr_all.tsv.gz
├── capsule/
│   └── capsule_all.tsv.gz
├── metadata/
│   └── metadata.tsv.gz
└── gene_annotation/
    ├── amr_all.tsv.gz
    ├── vfdb_all.tsv.gz
    └── plasmid_all.tsv.gz
```

The CLI searches four locations in priority order:

1. An explicit `--data-dir` argument
2. `~/.saurus/data/` (populated by `saurus init`)
3. `./data/` (for source checkouts)
4. `<sys.prefix>/share/saurus/data/` (the bundled install location)

To regenerate the master TSV from individual modules:

```bash
python scripts/build_master_tsv.py
```

---

## Built-in commands

| Command | Purpose |
|---|---|
| `saurus --examples` | Full gallery of example queries |
| `saurus --about` | Author, affiliation, citations, and links |
| `saurus --version` | Version number |
| `saurus --help` | Full flag reference |
| `saurus init` | Refresh the data bundle (optional; data is bundled) |

---

## Citation

If you use SAURUS-CLI in your research, please cite:

> Beckley B. SAURUS-CLI: a reproducible command-line interface for typing-based genome retrieval in *Staphylococcus aureus*. DOI: https://doi.org/10.5281/zenodo.24084554. 2026.

> Beckley B. SAURUS-CLI: a reproducible command-line interface for typing-based genome retrieval in *Staphylococcus aureus*. *BMC Bioinformatics* [under review]. 2026.

The underlying typing pipeline:

> Beckley B, Amarh V. StaphScope: a species-optimized computational pipeline for rapid and accessible *Staphylococcus aureus* genotyping and surveillance. *BMC Genomics*. 2026;27:261. doi:10.1186/s12864-026-12609-x

The source gene dataset:

> Shelenkov A, Slavokhotova A, Yunusova M, et al. Genomic typing, antimicrobial resistance gene, virulence factor and plasmid replicon database for the important pathogenic bacteria *Staphylococcus aureus*. *BMC Genom Data*. 2025;26:65. doi:10.1186/s12863-025-01363-w

---

## Part of ARGUS

SAURUS-CLI is the second release in the ARGUS initiative, a family of open genomic surveillance tools covering the WHO priority ESKAPE pathogens.

- ARGUS umbrella: https://argus-db.org/
- SAURUS web resource: https://saurus-db.org/
- Full CLI manual: https://saurus-db.org/manual.html

---

## Contributing

Bug reports and feature requests: https://github.com/bbeckley-hub/saurus/issues

---

## License

MIT License. See [LICENSE](LICENSE) for details.
