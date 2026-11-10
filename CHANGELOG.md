# Changelog

All notable changes to SAURUS-CLI are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] — 2026-11-10

### Added
- **`saurus init --from-file <zip>`** — install data from a local zip (offline
  installs, air-gapped HPC, CI/CD cached artifacts)
- **`saurus init --version <tag>`** — pin to a specific data release
  (e.g. `saurus init -v v1.0.0`) for reproducible methods sections
- **`saurus init -o <path>`** — install data to a custom directory
- **`$SAURUS_DATA_DIR` environment variable** — controls where the CLI reads
  and where `saurus init` writes, in priority order above all other defaults
- **XDG data home support** — `~/.local/share/saurus` on Linux,
  `~/Library/Application Support/saurus` on macOS,
  `%LOCALAPPDATA%\saurus` on Windows, and `$XDG_DATA_HOME/saurus` if set
- **Progress bar** during `saurus init` download
- **SHA256 checksum verification** — `saurus init` fetches a `.sha256` sibling
  and refuses to extract on mismatch
- **`DATA_VERSION` file** — bundled in pip/conda/Docker packages and in the
  release zip; `saurus --version` now prints it
- **Docker entrypoint** — auto-seeds `/data` volume from bundled data on first
  run, redirects writes to `/data` for `saurus init` updates
- **`VOLUME ["/data"]`** in the Dockerfile for persistence across container
  restarts and upgrades
- **`--from-file` help text** documenting all `saurus init` options
- **HPC shared-directory pattern** — install once under `/opt/saurus`, export
  `SAURUS_DATA_DIR=/opt/saurus`, all users read the same copy

### Changed
- **Data directory resolution rewritten** — `find_data_dir()` now searches
  `--data-dir`, `$SAURUS_DATA_DIR`, XDG, `~/.saurus/data`, `./data`, and
  `sys.prefix/share/saurus/data` in strict priority order
- **`saurus init` target resolution rewritten** — `_resolve_init_target()`
  overwrites existing writable data in place, otherwise falls back to XDG
  default; **skips read-only locations** (pipx/uv bundled venv data) so
  `saurus init` never fails with `PermissionError`
- **`--version` output** — now shows both CLI version and data version,
  e.g. `Data version: v1.0.0  (/home/user/.local/share/saurus)`
- **Default `--data-dir`** — no longer hardcoded to `./data`; the flag is now
  optional and the search order above is used when omitted
- **Data release URL** — points to `saurus-cli` release assets instead of the
  web repo (`github.com/bbeckley-hub/saurus-cli/releases`), separating code
  releases from data releases
- **CHANGELOG structure** — added `[Unreleased]` section for future work

### Fixed
- **`sarus init` typos** in the "data not found" error message
- **Stale data warning** — `saurus --version` now clearly shows which data
  directory is active, so users can spot stale installs
- **Cross-platform data paths** — Windows `LOCALAPPDATA` and macOS
  `Application Support` are handled explicitly rather than assuming Linux
  conventions
- **`DATA_VERSION` not bundled** — added to `pyproject.toml` `data-files` and
  to the release zip; `--version` no longer reports `unknown` for packaged
  installs

### Removed
- **Dead `include-package-data` and `package-data`** entries in `pyproject.toml`
  — no-ops for `py-modules`-only packages
- **Hardcoded `~/.saurus/data`** as the sole init target

### Verified
- `pip install` → `saurus --lineage USA300 --count` returns 10,448 without
  running `saurus init` (data bundled in wheel)
- `pipx install` → `saurus init` writes to XDG instead of the read-only pipx
  venv, and subsequent queries pick up the new data
- Docker `--rm` fresh run → 10,448 genomes, zero setup
- Docker `-v saurus_data:/data` → volume persists across `docker rm`, updates
  via `saurus init --force`
- `SAURUS_DATA_DIR=/shared/saurus saurus init` → installs to shared location,
  all users read the same copy
- `saurus init --from-file dist/saurus_data.zip` → offline install works with
  checksum verification

## [0.2.0] — 2026-11-05

### Updated
- SAURUS data now covers **134,160 typed genomes** with a 134,184-record
  metadata layer (previous release shipped only the RefSeq subset)
- General improvements across page generation and CLI startup
- Reference counts in `--examples` and `--about` updated to match the
  full collection

### Added
- `--format sra`, `--format biosample`, `--format bioproject` — export SRA
  raw-read accessions, BioSample IDs, and BioProject IDs directly
- `--has-sra` flag — filter to genomes with at least one retrievable SRA run
- `_serialize_list()` helper for deduplicating and sorting SRA/BioSample/
  BioProject outputs (handles comma-separated multi-run cells)

### Fixed
- `--lineage ST152` was matching only the canonical genotype; documented the
  narrower scope in `--examples` and pointed users to `--st 152` for the full
  set

## [0.1.0] — 2026-10-28

### Added
- `saurus init` command to download the SAURUS data bundle to `~/.saurus/data`
- Rotating science quotes in the footer (12 quotes, random per run)
- `--examples` — full gallery of example queries in the terminal
- `--about` — author, affiliation, citations, and links
- `--version` — clean version output
- `--quiet` / `-q` — silent mode for pipelines
- `--debug` — per-filter row-count tracing
- `--lineage` — pre-defined clonal signatures (USA100, USA300, EMRSA-15, etc.)
- Multi-format output via `--format tsv,json,accession` (writes multiple files
  at once)
- ASCII art banner on `--examples`, `--about`, and bare invocation
- ANSI colors (respects `NO_COLOR`, `FORCE_COLOR`, and TTY detection)
- Automatic `~/.saurus/data` search when `./data` is absent

### Fixed
- `BrokenPipeError` when piping output to `head` or `less`
- SCCmec filter previously matched `II` against `III` — now uses proper
  roman-numeral extraction
- Country and source filters now search both normalized and raw columns

### Changed
- Default `--data-dir` falls back through `./data` → `~/.saurus/data`

## [0.0.0] — 2026-10-15

### Added
- Initial release
- Query by MLST, spa, SCCmec (CGE + RPet), agr, capsule
- Metadata filters: country, source, host, collection year
- Gene filters: AMR, virulence, plasmid
- JSON config file support (`--config`)
- Accession-first export model

[Unreleased]: https://github.com/bbeckley-hub/saurus-cli/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/bbeckley-hub/saurus-cli/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bbeckley-hub/saurus-cli/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bbeckley-hub/saurus-cli/compare/v0.0.0...v0.1.0
[0.0.0]: https://github.com/bbeckley-hub/saurus-cli/releases/tag/v0.0.0
