# Changelog

All notable changes to SAURUS-CLI are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
- Multi-format output via `--format tsv,json,accession` (writes multiple files at once)
- ASCII art banner on `--examples`, `--about`, and bare invocation
- ANSI colors (respects `NO_COLOR`, `FORCE_COLOR`, and TTY detection)
- Automatic `~/.saurus/data` search when `./data` is absent

### Fixed
- `BrokenPipeError` when piping output to `head` or `less`
- SCCmec filter previously matched `II` against `III` — now uses proper roman-numeral extraction
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
