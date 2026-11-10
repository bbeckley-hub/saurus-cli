# SAURUS-CLI

**Command-line access to the SAURUS *Staphylococcus aureus* genomic surveillance database.**

[![PyPI](https://img.shields.io/pypi/v/saurus-cli.svg)](https://pypi.org/project/saurus-cli/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/saurus-cli.svg)](https://pypi.org/project/saurus-cli/)
[![Docker Hub](https://img.shields.io/docker/v/bbeckleyhub/saurus-cli?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/bbeckleyhub/saurus-cli)
[![Conda](https://img.shields.io/conda/vn/bioconda/saurus-cli?label=bioconda&logo=anaconda)](https://anaconda.org/bioconda/saurus-cli)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.24084554-blue)](https://doi.org/10.5281/zenodo.24084554)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SAURUS-CLI lets you query 134,160 *S. aureus* genomes by MLST, spa, SCCmec, agr, capsule, AMR genes, virulence factors, and epidemiological metadata directly from your terminal. It exports accessions in four namespaces (assembly, BioSample, SRA run, BioProject) for direct integration with NCBI `datasets` and `fastq-dl`.

The full dataset ships bundled inside every distribution. After installation, queries run locally with no downloads, no API keys, and no network access.

---

## What's new in v0.3.0

- **SRA raw-read export** via `--format sra`, feeding directly into `fastq-dl` for read-level reanalysis
- **BioSample and BioProject export** for metadata and study-level provenance
- **`--has-sra`** filter for the 22,322 genomes with retrievable raw reads
- **`saurus init` rewritten**: `--from-file <zip>`, `--version <tag>`, `-o <path>`, SHA256 verification, progress bar
- **`SAURUS_DATA_DIR`** environment variable and XDG data home support for Docker, HPC, pipx, and uv
- **Docker volume support**: `-v saurus_data:/data` persists data across container restarts
- **`--version` now reports the data version** alongside the CLI version
- **Separate code and data versioning**: upgrade the CLI and the data independently

Full changelog: [CHANGELOG.md](CHANGELOG.md)

---

## Installation

Choose whichever fits your workflow. All methods deliver the same CLI and the same bundled data.

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

Verify the installation:

```bash
saurus --version
saurus --lineage USA300 --count
# Expected: 10,448
```

---

## Quick Start

The most common workflows are **filter → export → download**, for either assemblies or raw reads.

### Assemblies workflow

```bash
# 1. Filter
saurus --lineage USA300 --country USA --source blood --count

# 2. Export accessions
saurus --lineage USA300 --country USA --source blood -o usa300_blood.txt

# 3. Download from NCBI
datasets download genome accession --inputfile usa300_blood.txt --filename usa300_blood.zip
```

### Raw reads workflow (v0.3.0)

```bash
# 1. Filter for genomes with retrievable raw reads
saurus --lineage USA300 --has-sra --count

# 2. Export SRA run accessions
saurus --lineage USA300 --format sra -o usa300_runs

# 3. Fetch FASTQ files with fastq-dl
fastq-dl --accession-list usa300_runs_sra_runs.txt
```

The SRA export handles genomes with multiple runs per BioSample, so the output is a deduplicated list of `SRR`/`ERR`/`DRR` accessions ready for any SRA client.

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
| `--has-sra` | Filter only genomes with retrievable SRA raw reads | `--has-sra` |
| `--country` | Country of origin (searches `country` and `country_raw`) | `--country USA` |
| `--source` | Isolation source (searches `source` and `source_raw`) | `--source blood` |
| `--host` | Host species | `--host "Homo sapiens"` |
| `--year` | Collection year or range | `--year 2019` or `--year 2015-2023` |
| `--amr` | AMR gene(s), comma-separated | `--amr mecA,tetM` |
| `--vfdb` | Virulence gene(s), comma-separated | `--vfdb lukS-PV` |
| `--plasmid` | Plasmid replicon(s), comma-separated | `--plasmid rep5a` |
| `--any` | Match ANY gene (default is ALL) | `--amr mecA,tetM --any` |

### Output formats

| Format | Extension | Feeds into |
|---|---|---|
| `accession` | `.txt` | NCBI `datasets download genome accession` |
| `sra` | `_sra_runs.txt` | `fastq-dl --accession-list`, `prefetch` |
| `biosample` | `_biosamples.txt` | `fastq-dl --group-by-sample`, metadata lookups |
| `bioproject` | `_bioprojects.txt` | Study-level bulk downloads |
| `tsv` | `.tsv` | Excel, R, pandas |
| `csv` | `.csv` | Collaborators, MS Access |
| `json` | `.json` | Web apps, `jq`, archival |

Request multiple formats in one command:

```bash
saurus --lineage USA300 --format tsv,accession,sra,biosample -o usa300
```

This writes four files: `usa300.tsv`, `usa300.txt`, `usa300_sra_runs.txt`, `usa300_biosamples.txt`.

### Output options

| Flag | Description | Default |
|---|---|---|
| `--count` | Print only the number of matching genomes | Off |
| `--format` | Output format(s), comma-separated | `accession` |
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
| `ST152` | ST152, SCCmec V, agr I, capsule 5 |

Any flag passed alongside `--lineage` overrides the signature. For example, `--lineage USA300 --country Japan` uses the USA300 signature but restricts results to Japan.

---

## Updating the data

The CLI and the data are versioned independently. The wheel bundles a snapshot of the data at build time. `saurus init` upgrades the data without touching the code.

```bash
# Install the latest data release
saurus init

# Pin to a specific data version for reproducibility
saurus init --version v1.0.0

# Install from a local zip (offline, air-gapped HPC)
saurus init --from-file saurus_data.zip

# Install to a custom location
saurus init -o /shared/saurus_data

# Force overwrite existing data
saurus init --force
```

`saurus init` verifies the SHA256 checksum of every download and writes a `DATA_VERSION` file. `saurus --version` reports which data release is active:

```
🦖SAURUS-CLI v0.3.0 — University of Ghana Medical School, Accra, Ghana
 Data version: v1.0.0  (/home/user/.local/share/saurus)
```

### Where the data lives

The CLI searches the following locations in priority order (highest wins):

| Priority | Location | Use case |
|---|---|---|
| 1 | `--data-dir <path>` | Per-command override |
| 2 | `$SAURUS_DATA_DIR` | Docker volumes, HPC scratch, shared cluster installs |
| 3 | `$XDG_DATA_HOME/saurus` (default `~/.local/share/saurus`) | Standard user install |
| 4 | `~/.saurus/data` | Legacy path (still supported) |
| 5 | `./data` | Development checkouts |
| 6 | `sys.prefix/share/saurus/data` | Bundled inside pip/conda/Docker |

To point the CLI at a specific data directory:

```bash
# Environment variable (Docker, HPC, CI)
export SAURUS_DATA_DIR=/scratch/saurus
saurus --lineage USA300 --count

# Per-command flag (highest priority)
saurus --data-dir /pinned/saurus-v1.0.0 --lineage USA300 --count
```

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

Any command-line flag overrides the corresponding config value, so you can reuse a config file with a one-off change:

```bash
saurus --config usa100_surveillance.json --country Japan
```

For strict reproducibility, pin both the data version and the config file:

```bash
SAURUS_DATA_DIR=/pinned/saurus-v1.0.0 saurus --config usa100_surveillance.json
```

---

## Examples Gallery

### Example 1: USA100 hospital clone

```bash
saurus --st 5 --sccmec II --agr II --capsule 5 --spa t002 --source blood --country USA
```

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

### Example 5: Multi-drug resistant genomes

```bash
saurus --amr mecA,tetM,ermB --any --count
```

### Example 6: Genomes with raw reads only

```bash
saurus --lineage EMRSA-15 --has-sra --format sra -o emrsa15_runs
fastq-dl --accession-list emrsa15_runs_sra_runs.txt
```

### Example 7: Multi-format export in one run

```bash
saurus --lineage USA300 --country USA --source blood \
    --format tsv,json,accession,sra,biosample -o usa300_blood
```

Produces five files, each ready for its downstream tool.

### Example 8: Pipeline integration

```bash
# Pipe directly into NCBI datasets (no intermediate file)
saurus --lineage EMRSA-15 --country "United Kingdom" | \
  datasets download genome accession --inputfile /dev/stdin --filename emrsa15_uk.zip
```

### Example 9: Debugging a query that returns zero

```bash
saurus --st 5 --agr I --capsule 8 --debug --count
```

The `--debug` output shows the row count after each filter, so you can see exactly where a query collapsed:

```
[debug] Initial load: 134,160 rows
[debug] --st 5:        14,930 rows
[debug] --agr I:            0 rows    ← the culprit
```

Run `saurus --examples` for the full gallery inside your terminal.

---

## Docker Usage

The Docker image bundles the full dataset and the NCBI `datasets` CLI.

```bash
# Count genomes (zero setup, uses bundled data)
docker run --rm bbeckleyhub/saurus-cli:latest --lineage USA300 --count

# Export to host directory
docker run --rm -v "$PWD:/work" bbeckleyhub/saurus-cli:latest \
    --lineage USA300 --country USA --source blood -o usa300_blood
```

### Persistent data with a volume (v0.3.0)

Use a named volume to persist `saurus init` updates across container restarts:

```bash
# First run: entrypoint seeds /data from the bundled dataset
docker run --rm -v saurus_data:/data bbeckleyhub/saurus-cli:latest --lineage USA300 --count

# Update the data in the same volume
docker run --rm -v saurus_data:/data bbeckleyhub/saurus-cli:latest init --force

# Subsequent runs use the updated data
docker run --rm -v saurus_data:/data bbeckleyhub/saurus-cli:latest --version
```

The entrypoint automatically sets `SAURUS_DATA_DIR=/data` when a volume is mounted, so all queries and updates use the persistent location.

Full Docker Hub README: https://hub.docker.com/r/bbeckleyhub/saurus-cli

---

## HPC Deployment

For clusters where users share a read-only data directory, install once and export the path:

```bash
# Admin: install to shared scratch (once)
sudo mkdir -p /scratch/saurus
SAURUS_DATA_DIR=/scratch/saurus saurus init
sudo chmod -R a+r /scratch/saurus

# Users: point at the shared copy
export SAURUS_DATA_DIR=/scratch/saurus
saurus --lineage USA300 --count
```

Zero duplication. If the admin updates the shared copy, all users pick up the change on the next query.

---

## Data Requirements (Development)

If you clone the repository and install in editable mode (`pip install -e .`), the CLI reads from `./data/`. The distributed package bundles this directory under `share/saurus/data/`.

```
data/
├── DATA_VERSION                 # Release tag (e.g., v1.0.0)
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

To regenerate the master TSV from individual modules:

```bash
python scripts/build_master_tsv.py
```

To build a release-ready data bundle for `saurus init`:

```bash
bash scripts/package_data.sh v1.0.0
```

---

## Built-in Commands

| Command | Purpose |
|---|---|
| `saurus --examples` | Full gallery of example queries |
| `saurus --about` | Author, affiliation, citations, and links |
| `saurus --version` | CLI version and data version |
| `saurus --help` | Full flag reference |
| `saurus init` | Install or refresh the data bundle |
| `saurus init --help` | Options for data installation |

---

## Citation

If you use SAURUS-CLI in your research, please cite:

> Beckley B. SAURUS-CLI: a reproducible command-line interface for typing-based genome retrieval in *Staphylococcus aureus*. Zenodo. 2026. doi:10.5281/zenodo.24084554

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
