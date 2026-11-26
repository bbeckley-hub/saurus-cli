#!/usr/bin/env python3
"""
🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 
                                                                        🦖 
saurus_cli.py — Command-line interface for SAURUS.                        🦖 
                                                                            🦖 
Query the SAURUS Staphylococcus aureus genomic surveillance database from    🦖 
the terminal. The full dataset (134K genomes, 11 modules) ships bundled       🦖 
inside pip / conda / Docker distributions. `saurus init` is provided for      🦖 
users who want to refresh the data independently.                              🦖 
                                                                              🦖 
Author:      Brown Beckley  <brownbeckley94@gmail.com>                        🦖 
Affiliation: University of Ghana Medical School, Accra, Ghana               🦖 
License:     MIT                                                           🦖 
                                                                          🦖 
🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 🦖 
"""    

import argparse
import gzip
import hashlib
import json
import os
import random
import re
import signal
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd

if sys.platform != "win32" and hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

__version__ = "0.4.0"
__author__ = "Brown Beckley"
__affiliation__ = "University of Ghana Medical School, Accra, Ghana"
__license__ = "MIT"

DATA_REPO = "bbeckley-hub/argus-data"
DATA_ASSET_NAME = "saurus_data.zip"
DATA_TAG_PREFIX = "saurus-data-"


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

def _supports_color(stream):
    """Return True if the stream can render ANSI color codes."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


class _Palette:
    CODES = {
        "RESET": "\033[0m", "BOLD": "\033[1m", "DIM": "\033[2m",
        "ITALIC": "\033[3m", "UNDER": "\033[4m",
        "RED": "\033[91m", "GREEN": "\033[92m", "YELLOW": "\033[93m",
        "BLUE": "\033[94m", "MAGENTA": "\033[95m", "CYAN": "\033[96m",
        "WHITE": "\033[97m", "GOLD": "\033[33m", "GRAY": "\033[90m",
    }

    def __init__(self, enabled):
        self._on = enabled

    def __getattr__(self, name):
        return self.CODES.get(name, "") if self._on else ""


C = _Palette(_supports_color(sys.stderr))
CO = _Palette(_supports_color(sys.stdout))


SAURUS_ASCII = r"""
  ####    ##   #    # #####  #    #  ####  
 #      #    # #    # #    # #    # #      
  ####  ###### #    # #####  #    #  ####  
     ## #    # #    # #   #  #    #     ## 
  ####  #    #  ####  #   #   ####   ####  
"""


def print_banner(quiet=False):
    """Print the SAURUS-CLI banner to stderr (skipped in quiet mode)."""
    if quiet or not _supports_color(sys.stderr):
        return
    print(f"{C.GOLD}{C.BOLD}{SAURUS_ASCII}{C.RESET}", file=sys.stderr)
    print(
        f"{C.CYAN}                 🦖  CLI  ·  Command-Line Interface  ·  v{__version__}{C.RESET}",
        file=sys.stderr,
    )
    print(
        f"{C.DIM}  Staphylococcus aureus Unified Resource for Universal Surveillance{C.RESET}",
        file=sys.stderr,
    )
    print(
        f"{C.DIM}  University of Ghana Medical School  ·  MIT License{C.RESET}",
        file=sys.stderr,
    )
    print("", file=sys.stderr)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LINEAGE_SIGNATURES = {
    "USA100": {"st": "5", "spa": "t002", "sccmec": "II", "agr": "II", "capsule": "5"},
    "USA300": {"st": "8", "spa": "t008", "sccmec": "IV", "agr": "I", "capsule": "5"},
    "USA400": {"st": "1", "spa": "t128", "sccmec": "IV", "agr": "III", "capsule": "8"},
    "USA500": {"st": "8", "spa": "t064", "sccmec": "IV", "agr": "I", "capsule": "5"},
    "USA700": {"st": "72", "spa": "t324", "sccmec": "IV", "agr": "I", "capsule": "5"},
    "USA800": {"st": "5", "spa": "t688", "sccmec": "IV", "agr": "II", "capsule": "5"},
    "EMRSA-15": {"st": "22", "spa": "t032", "sccmec": "IV", "agr": "I", "capsule": "5"},
    "EMRSA-16": {"st": "36", "spa": "t018", "sccmec": "II", "agr": "III", "capsule": "8"},
    "BENGAL BAY": {"st": "772", "spa": "t657", "sccmec": "V", "agr": "II", "capsule": "5"},
    "ST152": {"st": "152", "spa": "t355", "sccmec": "V", "agr": "I", "capsule": "5"},
}

SCIENCE_QUOTES = [
    ("The pure culture is the foundation for all research on infectious disease.", "Robert Koch"),
    ("In the fields of observation chance favors only the prepared mind.", "Louis Pasteur"),
    ("Nothing in biology makes sense except in the light of evolution.", "Theodosius Dobzhansky"),
    ("Science and everyday life cannot and should not be separated.", "Rosalind Franklin"),
    ("It is the lone worker who makes the first advance in a subject.", "Alexander Fleming"),
    ("Nothing in life is to be feared, it is only to be understood.", "Marie Curie"),
    ("Somewhere, something incredible is waiting to be known.", "Carl Sagan"),
    ("Antimicrobial resistance is a slow-moving pandemic — but it is moving.", "Sally Davies (adapted)"),
    ("The ultimate scientific goal is to construct a quantitative, predictive, and unified view of the entire biological world.", "Carl Woese"),
    ("In the end, we will conserve only what we love, we will love only what we understand, and we will understand only what we are taught.", "Baba Dioum"),
    ("Progress in science depends on new techniques, new discoveries and new ideas, probably in that order.", "Sydney Brenner"),
    ("The greatest obstacle to discovery is not ignorance — it is the illusion of knowledge.", "Daniel Boorstin"),
]

EXT_MAP = {
    "tsv": ".tsv",
    "csv": ".csv",
    "json": ".json",
    "accession": ".txt",
    "sra": "_sra_runs.txt",
    "biosample": "_biosamples.txt",
    "bioproject": "_bioprojects.txt",
}
VALID_FORMATS = set(EXT_MAP.keys())
SRA_FORMATS = {"sra", "biosample", "bioproject"}


# ---------------------------------------------------------------------------
# Data directory resolution
# ---------------------------------------------------------------------------

def _xdg_data_home() -> Optional[Path]:
    """Return the platform-appropriate user data directory.

    Linux:   $XDG_DATA_HOME/saurus  (default ~/.local/share/saurus)
    macOS:   ~/Library/Application Support/saurus
    Windows: %LOCALAPPDATA%\\saurus
    """
    if sys.platform == "win32":
        ad = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return Path(ad) / "saurus" if ad else None
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "saurus"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "saurus"
    return Path.home() / ".local" / "share" / "saurus"


def _get_data_dir_candidates(explicit: Optional[str] = None) -> list[Path]:
    """Return candidate data directories in priority order (highest first)."""
    candidates: list[Path] = []

    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())

    env_dir = os.environ.get("SAURUS_DATA_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser().resolve())

    xdg = _xdg_data_home()
    if xdg:
        candidates.append(xdg)

    candidates.append(Path.home() / ".saurus" / "data")
    candidates.append(Path.cwd() / "data")
    candidates.append(Path(sys.prefix) / "share" / "saurus" / "data")

    if sys.platform == "win32":
        try:
            import site
            for sp in site.getsitepackages():
                candidates.append(Path(sp).parent / "share" / "saurus" / "data")
        except Exception:
            pass

    return candidates


def find_data_dir(explicit: Optional[str] = None) -> Optional[Path]:
    """Return the first candidate directory that contains SAURUS data."""
    for c in _get_data_dir_candidates(explicit):
        try:
            if (c / "mrsa").is_dir() or \
               (c / "mrsa_all.tsv").exists() or \
               (c / "mrsa_all.tsv.gz").exists():
                return c
        except (OSError, PermissionError):
            continue
    return None


def find_data_file(data_dir: Path, *rel_paths: str) -> Optional[Path]:
    """Return the first existing path from rel_paths, supporting .gz fallback."""
    for rel in rel_paths:
        p = data_dir / rel
        if p.exists():
            return p
        gz = p.with_suffix(p.suffix + ".gz")
        if gz.exists():
            return gz
    return None


def _resolve_init_target(output: Optional[str]) -> Path:
    """Decide where `saurus init` should write.

    Prefers an existing writable data directory (so updates overwrite in
    place). Read-only locations such as pipx or uv-managed venv data are
    skipped, falling through to the XDG default.
    """
    if output:
        return Path(output).expanduser().resolve()

    env_dir = os.environ.get("SAURUS_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    for candidate in _get_data_dir_candidates():
        try:
            has_data = (
                (candidate / "mrsa").is_dir()
                or (candidate / "mrsa_all.tsv").exists()
                or (candidate / "mrsa_all.tsv.gz").exists()
            )
            if has_data and os.access(candidate, os.W_OK):
                return candidate
        except (OSError, PermissionError):
            continue

    xdg = _xdg_data_home()
    if xdg:
        return xdg

    return Path.home() / ".saurus" / "data"


def read_tsv(path: Path, **kwargs) -> pd.DataFrame:
    """Read a TSV file, transparently handling gzip compression."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            f"  Hint: reinstall saurus-cli, or run: saurus init"
        )
    if path.suffix == ".gz":
        return pd.read_csv(path, sep="\t", dtype=str, compression="gzip", **kwargs)
    return pd.read_csv(path, sep="\t", dtype=str, **kwargs)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log_loading(msg):
    print(f"{C.CYAN}🔍  {msg}{C.RESET}", file=sys.stderr)


def log_lineage(msg):
    print(f"{C.MAGENTA}🧬  {msg}{C.RESET}", file=sys.stderr)


def log_found(n):
    print(f"{C.GREEN}{C.BOLD}✨  Found {n:,} matching genomes{C.RESET}", file=sys.stderr)


def log_debug(msg):
    print(f"{C.GRAY}    [debug] {msg}{C.RESET}", file=sys.stderr)


def log_error(msg):
    print(f"{C.RED}{C.BOLD}❌  {msg}{C.RESET}", file=sys.stderr)


def log_warn(msg):
    print(f"{C.YELLOW}⚠️   {msg}{C.RESET}", file=sys.stderr)


def log_info(msg):
    print(f"{C.CYAN}ℹ️   {msg}{C.RESET}", file=sys.stderr)


def log_write(path, rows, fmt):
    print(
        f"{C.GREEN}💾{C.RESET}  {C.CYAN}{path}{C.RESET}  "
        f"{C.DIM}({rows:,} rows · {fmt.upper()}){C.RESET}",
        file=sys.stderr,
    )


def log_zero():
    print(f"{C.YELLOW}{C.BOLD}⚠️   Found 0 matching genomes{C.RESET}", file=sys.stderr)
    print(
        f"{C.GRAY}    💡  Not every genotype combination exists in nature.{C.RESET}",
        file=sys.stderr,
    )
    print(
        f"{C.GRAY}        Try removing a filter, or run with {C.BOLD}--debug{C.RESET}"
        f"{C.GRAY} to see where the count drops.{C.RESET}",
        file=sys.stderr,
    )


def print_footer(quiet=False, count_mode=False):
    """Print the closing quote and links footer."""
    if quiet:
        return
    quote, author = random.choice(SCIENCE_QUOTES)
    line = f"{C.GRAY}{'─' * 76}{C.RESET}"

    print("", file=sys.stderr)
    print(line, file=sys.stderr)

    if count_mode:
        print(f"{C.ITALIC}{C.GOLD}  💭  \"{quote}\"  — {author}{C.RESET}", file=sys.stderr)
        print(
            f"{C.CYAN}  🦖  {C.UNDER}https://saurus-db.org/{C.RESET}"
            f"{C.GRAY}  ·  {C.RESET}{C.CYAN}saurus --about{C.RESET}"
            f"{C.GRAY}  ·  {C.RESET}{C.CYAN}saurus --help{C.RESET}",
            file=sys.stderr,
        )
    else:
        print(f"{C.ITALIC}{C.GOLD}  💭  \"{quote}\"{C.RESET}", file=sys.stderr)
        print(f"{C.GRAY}       — {author}{C.RESET}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            f"{C.GOLD}{C.BOLD}  🦖  SAURUS-CLI{C.RESET}  "
            f"{C.DIM}·  {__affiliation__}{C.RESET}",
            file=sys.stderr,
        )
        print(file=sys.stderr)
        print(f"{C.CYAN}  🌐  Web UI     {C.RESET}{C.UNDER}https://saurus-db.org/{C.RESET}", file=sys.stderr)
        print(f"{C.GOLD}  ⭐  Star us    {C.RESET}{C.UNDER}https://github.com/bbeckley-hub/saurus{C.RESET}", file=sys.stderr)
        print(f"{C.RED}  🐛  Bugs       {C.RESET}{C.UNDER}https://github.com/bbeckley-hub/saurus/issues{C.RESET}", file=sys.stderr)
        print(f"{C.CYAN}  📚  Docs       {C.RESET}saurus --examples  ·  saurus --about  ·  saurus --help", file=sys.stderr)

    print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# Help, examples, about text
# ---------------------------------------------------------------------------

HELP_EPILOG = f"""
{CO.GOLD}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}
{CO.GOLD}{CO.BOLD}  ⚡  QUICK EXAMPLES{CO.RESET}
{CO.GOLD}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}

{CO.CYAN}  Count USA300 genomes globally:{CO.RESET}
    $ saurus --lineage USA300 --count

{CO.CYAN}  USA100 bloodstream isolates in the USA:{CO.RESET}
    $ saurus --lineage USA100 --country USA --source blood -o usa100.txt

{CO.CYAN}  Export BOTH a metadata table AND an accession list in one run:{CO.RESET}
    $ saurus --lineage USA300 --format tsv,accession -o usa300_results

{CO.CYAN}  Get SRA raw-read accessions (22,322 genomes have them):{CO.RESET}
    $ saurus --lineage USA300 --format sra -o usa300_runs
    $ saurus --lineage USA300 --format biosample -o usa300_samples

{CO.CYAN}  Reproducible query via JSON config:{CO.RESET}
    $ saurus --config my_query.json

{CO.GOLD}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}
{CO.GOLD}{CO.BOLD}  📚  MORE INFORMATION{CO.RESET}
{CO.GOLD}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}

    saurus --examples      Full gallery of example queries
    saurus --about         Author, affiliation, citations, and links
    saurus --version       Version number
    saurus init            Refresh the data bundle (optional; data is bundled)

{CO.CYAN}  Manual:       {CO.RESET}https://saurus-db.org/manual.html
{CO.CYAN}  Report bugs:  {CO.RESET}https://github.com/bbeckley-hub/saurus/issues
"""

EXAMPLES_GALLERY = f"""
{CO.CYAN}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}
{CO.CYAN}{CO.BOLD}  🦖  SAURUS CLI — Example Queries{CO.RESET}
{CO.DIM}      Copy-paste these into your terminal.{CO.RESET}
{CO.CYAN}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}

{CO.GOLD}{CO.BOLD}  📊  Counting genomes{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --lineage USA300 --count{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA100 --country USA --source blood --count{CO.RESET}
    {CO.CYAN}$ saurus --st 5 --sccmec II --agr II --mrsa --count{CO.RESET}

{CO.GOLD}{CO.BOLD}  📤  Exporting accessions{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --lineage USA300 -o usa300.txt{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --format tsv,accession -o usa300_results{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --format csv,json,accession -o usa300_results{CO.RESET}

{CO.GOLD}{CO.BOLD}  📥  SRA raw reads{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --has-sra --count{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --format sra -o usa300_runs{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --format biosample -o usa300_samples{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --format bioproject -o usa300_projects{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --format tsv,accession,sra,biosample -o usa300{CO.RESET}

{CO.GOLD}{CO.BOLD}  🧬  Genotype queries{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --st 8 --vfdb lukS-PV --count{CO.RESET}
    {CO.CYAN}$ saurus --amr mecA,tetM --any --count{CO.RESET}
    {CO.CYAN}$ saurus --amr mecA,ermB --count{CO.RESET}

{CO.GRAY}    Gene queries are standalone: gene annotation is a static, GCA-keyed{CO.RESET}
{CO.GRAY}    snapshot (Shelenkov et al. 2025) that covers a subset of the{CO.RESET}
{CO.GRAY}    collection (AMR ~90K, VFDB ~99K, plasmid ~86K of 134K genomes).{CO.RESET}
{CO.GRAY}      • Base names match their numbered alleles (mecA → mecA_1…mecA_9).{CO.RESET}
{CO.GRAY}      • Unknown gene names are rejected, with the catalogue listing hint.{CO.RESET}
{CO.GRAY}      • A gene + typing/metadata combo can return 0 because the annotated{CO.RESET}
{CO.GRAY}        genomes lack that metadata — run the gene query alone first,{CO.RESET}
{CO.GRAY}        then add filters step by step (--debug shows where it drops).{CO.RESET}
{CO.GRAY}      • On genomes without annotation, a gene is UNKNOWN, not absent.{CO.RESET}

{CO.GOLD}{CO.BOLD}  🌍  Metadata queries{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --cc 398 --mrsa --country Denmark --count{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 --source blood --year 2005-2015 -o usa300_2005_2015.txt{CO.RESET}
    {CO.CYAN}$ saurus --mrsa --country Ghana --count{CO.RESET}

{CO.GOLD}{CO.BOLD}  🔁  Reproducible workflows{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --config my_query.json{CO.RESET}
    {CO.CYAN}$ saurus --lineage USA300 | datasets download genome accession \\{CO.RESET}
    {CO.CYAN}      --inputfile /dev/stdin --filename usa300.zip{CO.RESET}

{CO.GOLD}{CO.BOLD}  🐞  Diagnostics{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}$ saurus --st 5 --agr I --debug --count{CO.RESET}

{CO.GOLD}{CO.BOLD}  🏷   Lineage shortcuts{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    USA100 · USA300 · USA400 · USA500 · USA700 · USA800
    EMRSA-15 · EMRSA-16 · Bengal Bay · ST152

    {CO.CYAN}$ saurus --lineage EMRSA-15 --country "United Kingdom" --count{CO.RESET}

{CO.GRAY}    Lineage signatures are deliberately narrow: they match the canonical{CO.RESET}
{CO.GRAY}    combination (ST + spa + SCCmec + agr + capsule), not every genome of{CO.RESET}
{CO.GRAY}    that ST. For a broader query use --st directly:{CO.RESET}
{CO.GRAY}      saurus --lineage ST152   →  canonical ST152 only (16 genomes){CO.RESET}
{CO.GRAY}      saurus --st 152         →  all ST152 genomes (749 genomes){CO.RESET}

{CO.CYAN}  Full manual:  {CO.RESET}https://saurus-db.org/manual.html
"""

ABOUT_TEXT = f"""
{CO.CYAN}{CO.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{CO.RESET}

  {CO.CYAN}Author:{CO.RESET}       {__author__}
  {CO.CYAN}Affiliation:{CO.RESET}  {__affiliation__}
  {CO.CYAN}License:{CO.RESET}      {__license__}
  {CO.CYAN}Version:{CO.RESET}      v{__version__}

{CO.GOLD}{CO.BOLD}  📖  Citation{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

  If you use  🦖SAURUS-CLI🦖 in your research, please cite:

    Beckley B, Amarh V. StaphScope: a species-optimized computational
    pipeline for rapid and accessible Staphylococcus aureus genotyping
    and surveillance. BMC Genomics. 2026;27:261.
    doi:10.1186/s12864-026-12609-x

  And the underlying gene annotation dataset:

    Shelenkov A, Slavokhotova A, Yunusova M, et al. Genomic typing,
    antimicrobial resistance gene, virulence factor and plasmid replicon
    database for the important pathogenic bacteria Staphylococcus aureus.
    BMC Genom Data. 2025;26:65. doi:10.1186/s12863-025-01363-w

{CO.GOLD}{CO.BOLD}  🔗  Links{CO.RESET}
{CO.GRAY}  ─────────────────────────────────────────────────────────────{CO.RESET}

    {CO.CYAN}🌐  Web platform:{CO.RESET}    https://saurus-db.org/
    {CO.CYAN}📚  CLI repo:{CO.RESET}        https://github.com/bbeckley-hub/saurus-cli
    {CO.CYAN}📖  User manual:{CO.RESET}     https://saurus-db.org/manual.html
    {CO.CYAN}🐛  Report bugs:{CO.RESET}     https://github.com/bbeckley-hub/saurus/issues
    {CO.CYAN}📦  PyPI:{CO.RESET}            https://pypi.org/project/saurus-cli/
    {CO.CYAN}🗃   Data releases:{CO.RESET}  https://github.com/bbeckley-hub/argus-data
"""


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def extract_sccmec_roman(s):
    """Extract the leading roman numeral from an SCCmec type string."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    if s in ("", "Not Assigned", "nan", "None", "NA"):
        return ""
    s = re.sub(r"^SCCmec_type_", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^Type\s+", "", s, flags=re.IGNORECASE)
    m = re.match(r"^(VIII|VII|VI|IV|IX|V|III|II|I|X)", s, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def serialize(df, fmt):
    """Serialize a dataframe to the given output format."""
    if fmt == "accession":
        return "\n".join(df["accession"].tolist())
    if fmt == "tsv":
        return df.to_csv(sep="\t", index=False)
    if fmt == "csv":
        return df.to_csv(index=False)
    if fmt == "json":
        return df.to_json(orient="records", indent=2, force_ascii=False)
    if fmt in SRA_FORMATS:
        return _serialize_list(df, fmt)
    raise ValueError(f"Unknown format: {fmt}")


def _serialize_list(df, fmt):
    """Serialize sra/biosample/bioproject columns to a deduplicated sorted list."""
    col = {"sra": "sra_run", "biosample": "biosample", "bioproject": "bioproject"}[fmt]
    if col not in df.columns:
        return ""
    seen = set()
    for val in df[col].dropna():
        for piece in str(val).split(","):
            piece = piece.strip()
            if piece and piece != "NA":
                seen.add(piece)
    if not seen:
        return ""
    return "\n".join(sorted(seen)) + "\n"


def resolve_output_paths(base_output, formats):
    """Resolve base output path plus extensions for each requested format."""
    p = Path(base_output)
    for ext in EXT_MAP.values():
        if p.suffix == ext:
            p = p.with_suffix("")
            break
    return {fmt: Path(str(p) + EXT_MAP[fmt]) for fmt in formats}


def needs_master(args):
    """Return True if the query requires the full master TSV."""
    formats = [f.strip().lower() for f in str(args.format).split(",") if f.strip()]
    if any(f in SRA_FORMATS for f in formats):
        return True
    if getattr(args, "has_sra", False):
        return True
    return False


def load_data(args, data_dir: Path):
    """Load the appropriate dataset for the given query, preferring fast paths."""
    master_tsv = find_data_file(data_dir, "mrsa/mrsa_all.tsv", "mrsa_all.tsv")
    if master_tsv is None:
        master_tsv = data_dir / "mrsa" / "mrsa_all.tsv"

    typing_filters = [args.st, args.cc, args.spa, args.sccmec, args.agr, args.capsule]
    meta_filters = [args.mrsa, args.mssa, args.country, args.source, args.host, args.year]
    gene_filters = [args.amr, args.vfdb, args.plasmid]
    active_typing = sum(1 for f in typing_filters if f)
    active_meta = sum(1 for f in meta_filters if f)

    if (active_typing == 1 and active_meta == 0 and not any(gene_filters)
            and (args.st or args.cc) and not needs_master(args)):
        log_loading("Loading MLST data...")
        mlst_tsv = find_data_file(data_dir, "mlst/mlst_all.tsv", "mlst_all.tsv")
        if mlst_tsv is None:
            mlst_tsv = master_tsv
        df = read_tsv(mlst_tsv)
        df["accession"] = df["accession"].str.replace(r"\.fna$", "", regex=True)
        df = df.rename(columns={"ST": "mlst_st"})
        cc_path = find_data_file(data_dir, "mlst/cc.txt", "cc.txt")
        if cc_path:
            df_cc = pd.read_csv(
                cc_path, sep="\t", comment="#",
                names=["assembly", "CC", "ST"], dtype=str,
            )
            df_cc["ST_clean"] = df_cc["ST"].str.replace("ST", "")
            st_to_cc = (
                df_cc.groupby("ST_clean")["CC"]
                .agg(lambda x: x.mode()[0] if not x.mode().empty else "NA")
                .to_dict()
            )
            df["mlst_cc"] = df["mlst_st"].map(st_to_cc).fillna("NA")
        return df

    if active_typing == 1 and active_meta == 0 and args.spa and not needs_master(args):
        log_loading("Loading spa data...")
        spa_tsv = find_data_file(data_dir, "spa/spa_all.tsv", "spa_all.tsv")
        if spa_tsv is None:
            spa_tsv = master_tsv
        df = read_tsv(spa_tsv)
        df["accession"] = df["accession"].str.replace(r"\.fna$", "", regex=True)
        return df.rename(columns={"spa_Type": "spa_type"})

    if not master_tsv.exists():
        log_error(f"Master file not found: {master_tsv}")
        log_info("The saurus-cli package should ship with bundled data.")
        log_info("If data is missing, run: saurus init")
        sys.exit(1)

    log_loading("Loading master SAURUS data...")
    df = read_tsv(master_tsv)
    return ensure_mlst_cc(df, data_dir)


def _gene_col(df_gene):
    for c in ["gene", "Gene", "gene_name", "Gene_Name", "AMR_Gene", "Virulence_Gene"]:
        if c in df_gene.columns:
            return c
    return None


def _norm_gene_base(name):
    """Canonical base name for catalogue matching: lowercase, brackets and
    allele suffix removed ('tet(M)_13' -> 'tetm', 'mecA_6' -> 'meca')."""
    s = re.sub(r"[()\[\]\s]", "", str(name).strip().lower())
    return re.split(r"_", s, maxsplit=1)[0]


def _gene_matches(value, request):
    """Anchored gene match: exact catalogue name, or a base name matched
    against its allele-suffixed catalogue entries (e.g. 'mecA' matches
    'mecA_6', 'tetM' matches 'tet(M)_13'). Substring matching is deliberately
    not used: it silently counts unrelated entries (e.g. 'agr' matches
    'agrB2'), which previously inflated gene-based counts."""
    v = str(value).strip().lower()
    g = str(request).strip().lower()
    return (
        v == g
        or v.startswith(g + "_")
        or v.startswith(g + "-")
        or _norm_gene_base(v) == _norm_gene_base(g)
    )


def resolve_gene_accessions(gene_file, genes, module_label):
    """Return the set of accessions carrying any of `genes` in a long-format
    gene table, and the catalogue-vocabulary match mask per gene.

    Every requested gene must be present in the module's catalogue; unknown
    names abort with an actionable error instead of silently returning an
    empty intersection (match_all) or the entire master table (--any)."""
    if not gene_file or not Path(gene_file).exists():
        return set(), []
    df_gene = read_tsv(gene_file)
    df_gene["accession"] = df_gene["accession"].str.replace(r"\.fna$", "", regex=True)
    gene_col = _gene_col(df_gene)
    if not gene_col:
        return set(), []
    gene_series = df_gene[gene_col].fillna("").astype(str)
    bases = {_norm_gene_base(v) for v in gene_series}
    unknown = [g for g in genes if _norm_gene_base(g) not in bases]
    if unknown:
        release_hint = find_data_dir()
        rel_hint = ""
        if release_hint:
            freq = Path(release_hint) / "gene_annotation" / f"{_module_freq_file(module_label)}"
            if freq.exists():
                rel_hint = f"    Run: zcat {freq} | cut -f1 | sort -u"
        log_error(
            f"Gene(s) {', '.join(unknown)} not found in the SAURUS "
            f"{module_label} catalogue."
        )
        log_info("Gene names must match the module catalogue exactly "
                 "(base names match their numbered alleles, e.g. 'mecA' -> 'mecA_6').")
        if rel_hint:
            log_info("To list valid gene names for this module:")
            print(rel_hint, file=sys.stderr)
        sys.exit(1)
    accs_by_gene = []
    for g in genes:
        mask = gene_series.map(lambda v, _g=g: _gene_matches(v, _g))
        accs_by_gene.append(set(df_gene.loc[mask, "accession"]))
    return accs_by_gene, unknown


def _module_freq_file(module_label):
    return {
        "AMR": "amr_gene_freq.tsv",
        "VFDB": "vfdb_gene_freq.tsv",
        "Plasmid": "plasmid_gene_freq.tsv",
    }.get(module_label, module_label)


def _read_tsv_row_count(path, unique_first_col=False):
    """Count rows in a (possibly gzipped) TSV without loading it fully."""
    path = Path(path)
    opener = gzip.open if str(path).endswith(".gz") else open
    seen = set()
    n = 0
    try:
        with opener(path, "rt") as fh:
            next(fh, None)
            for line in fh:
                n += 1
                if unique_first_col:
                    seen.add(line.split("\t", 1)[0])
    except OSError:
        return 0
    return len(seen) if unique_first_col else n


def _warn_gene_table_coverage(data_dir, active_labels=(), debug=False, min_coverage=0.15):
    """Warn when a gene module covers only a small fraction of the collection,
    which usually indicates a truncated build rather than genuine gene absence."""
    mlst = find_data_file(data_dir, "mlst/mlst_all.tsv", "mlst_all.tsv")
    master = find_data_file(data_dir, "mrsa/mrsa_all.tsv", "mrsa_all.tsv")
    ref_path = master or mlst
    if not ref_path:
        return
    n_ref = _read_tsv_row_count(ref_path)
    if not n_ref:
        return
    all_modules = [
        ("AMR", ["gene_annotation/amr_all.tsv", "amr_all.tsv"]),
        ("VFDB", ["gene_annotation/vfdb_all.tsv", "vfdb_all.tsv"]),
        ("Plasmid", ["gene_annotation/plasmid_all.tsv", "plasmid_all.tsv"]),
    ]
    for label, rels in all_modules:
        if active_labels and label not in active_labels:
            continue
        f = find_data_file(data_dir, *rels)
        if not f:
            continue
        n_cov = _read_tsv_row_count(f, unique_first_col=True)
        if n_cov and n_cov / n_ref < min_coverage:
            log_warn(
                f"{label} gene table covers only {n_cov:,} of {n_ref:,} genomes "
                f"({100 * n_cov / n_ref:.1f}%). This looks like a truncated data "
                "release: absent genes in the uncovered genomes are missing "
                "annotation, not confirmed absence. Run 'saurus init' for a "
                "rebuilt data release."
            )


def _st_to_cc_map(data_dir):
    """ST -> clonal-complex mapping from the mlst module's cc.txt."""
    cc_path = find_data_file(data_dir, "mlst/cc.txt", "cc.txt")
    if not cc_path:
        return {}
    try:
        df_cc = pd.read_csv(
            cc_path, sep="\t", comment="#",
            names=["assembly", "CC", "ST"], dtype=str,
        )
    except Exception:
        return {}
    df_cc["ST_clean"] = df_cc["ST"].str.replace("ST", "", regex=False)
    return {
        k: v for k, v in (
            df_cc.groupby("ST_clean")["CC"]
            .agg(lambda x: x.mode()[0] if not x.mode().empty else None)
            .to_dict()
        ).items() if v
    }


def ensure_mlst_cc(df, data_dir):
    """Guarantee a populated mlst_cc column.

    The v0.3.0 master table shipped the mlst_cc column entirely empty, which
    made every --cc query issued together with a metadata or phenotype filter
    (the master-table load path) return zero rows. If the column is missing or
    empty it is recomputed here from the mlst module's cc.txt, so --cc behaves
    identically on both load paths. Genome sets with no CC assignment remain
    excluded, but the exclusion is now reported by the --cc warning.
    """
    if "mlst_st" not in df.columns:
        return df
    if "mlst_cc" not in df.columns:
        df["mlst_cc"] = None
    vals = df["mlst_cc"].fillna("").astype(str).str.strip().str.upper()
    n_missing = int(vals.isin(["", "NA"]).sum())
    if n_missing == 0:
        return df
    st_to_cc = _st_to_cc_map(data_dir)
    if st_to_cc:
        st_plain = df["mlst_st"].fillna("").astype(str).str.replace("ST", "", regex=False)
        mapped = st_plain.map(st_to_cc)
        keep = df["mlst_cc"].fillna("").astype(str).str.strip().str.upper().ne("NA")
        keep &= df["mlst_cc"].fillna("").astype(str).str.strip().ne("")
        df["mlst_cc"] = df["mlst_cc"].where(keep, mapped)
    return df


def filter_by_gene(df, gene_file, genes, match_all=True, module_label="gene"):
    """Filter a dataframe by presence of one or more gene names.

    With match_all=False (--any), the return set is the union of the genes
    requested within this module only, intersected with the current
    dataframe, so an unmatched gene can never widen the result."""
    if not gene_file or not Path(gene_file).exists():
        return df
    accs_by_gene, _ = resolve_gene_accessions(gene_file, genes, module_label)
    if not accs_by_gene:
        return df
    valid_accs = set(df["accession"])
    if match_all:
        for accs in accs_by_gene:
            valid_accs = valid_accs.intersection(accs)
    else:
        union_accs = set()
        for accs in accs_by_gene:
            union_accs = union_accs.union(accs)
        valid_accs = valid_accs.intersection(union_accs)
    return df[df["accession"].isin(valid_accs)]


def debug_step(label, df, enabled):
    """Print a debug trace line for the current filter step."""
    if enabled:
        log_debug(f"{label}: {len(df):,} rows")


# ---------------------------------------------------------------------------
# `saurus init` subcommand
# ---------------------------------------------------------------------------

def _download_with_progress(url: str, dest: Path) -> None:
    """Download a URL to dest, printing a progress bar to stderr."""
    print(f"{C.CYAN}📥{C.RESET}  Downloading...", file=sys.stderr)
    last_pct = -1

    def _hook(blocks, block_size, total_size):
        nonlocal last_pct
        if total_size <= 0:
            return
        downloaded = blocks * block_size
        pct = int(100 * downloaded / total_size)
        if pct != last_pct and pct % 5 == 0:
            mb_done = downloaded / 1_048_576
            mb_total = total_size / 1_048_576
            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(
                f"    {C.CYAN}{bar}{C.RESET}  {pct:3d}%  ({mb_done:.1f}/{mb_total:.1f} MB)",
                file=sys.stderr,
                end="\r",
            )
            last_pct = pct

    urllib.request.urlretrieve(url, str(dest), reporthook=_hook)
    print("", file=sys.stderr)


def _sha256(path: Path) -> str:
    """Return the hex SHA256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _latest_data_tag() -> Optional[str]:
    """Return the newest release tag belonging to this CLI's data product.

    The argus-data repo hosts data releases for several products, so the
    repo-wide 'latest' release is not necessarily a SAURUS one; products are
    namespaced by tag prefix (e.g. 'saurus-data-v1.1.0')."""
    url = f"https://api.github.com/repos/{DATA_REPO}/releases?per_page=100"
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            releases = json.load(r)
    except Exception:
        return None
    for rel in releases:
        tag = rel.get("tag_name", "")
        if tag.startswith(DATA_TAG_PREFIX):
            return tag
    return None


def _resolve_data_url(version: Optional[str]) -> tuple[str, str]:
    """Return (zip_url, sha256_url) for the requested data version."""
    if version and version.lower() not in ("latest", "main"):
        tag = version.strip()
        if not tag.startswith("v") and not tag.startswith(DATA_TAG_PREFIX):
            tag = "v" + tag
        if not tag.startswith(DATA_TAG_PREFIX):
            tag = DATA_TAG_PREFIX + tag
        base = f"https://github.com/{DATA_REPO}/releases/download/{tag}/{DATA_ASSET_NAME}"
        return base, f"{base}.sha256"
    tag = _latest_data_tag()
    if tag:
        base = f"https://github.com/{DATA_REPO}/releases/download/{tag}/{DATA_ASSET_NAME}"
        return base, f"{base}.sha256"
    base = f"https://github.com/{DATA_REPO}/releases/latest/download/{DATA_ASSET_NAME}"
    return base, f"{base}.sha256"


def cmd_init(argv):
    """Handle the `saurus init` subcommand."""
    output: Optional[str] = None
    version: Optional[str] = None
    force = False
    from_file: Optional[Path] = None
    quiet = False
    allow_unverified = "--allow-unverified" in argv

    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-o", "--output", "--path", "--data-dir"):
            output = argv[i + 1]
            i += 2
        elif a in ("-v", "--version"):
            version = argv[i + 1]
            i += 2
        elif a in ("-f", "--from-file"):
            from_file = Path(argv[i + 1]).expanduser()
            i += 2
        elif a in ("--force", "--allow-unverified"):
            if a == "--force":
                force = True
            i += 1
        elif a in ("-q", "--quiet"):
            quiet = True
            i += 1
        elif a in ("-h", "--help"):
            print("""Usage: saurus init [OPTIONS]

Download or refresh the SAURUS data bundle.

Where does it write?
  1. --output <path>
  2. $SAURUS_DATA_DIR
  3. Existing writable data location
  4. $XDG_DATA_HOME/saurus (default for new installs)
  5. ~/.saurus/data (fallback)

Options:
  -o, --output PATH       Install to PATH (default: auto)
  -v, --version VERSION   Specific data version (default: latest); re-downloads
                          even when data is already installed
  -f, --from-file ZIP     Install from a local zip. The companion ZIP.sha256
                          must exist and match, otherwise the install is
                          refused.
  --force                 Overwrite without asking
  --allow-unverified      Proceed without checksum verification when the
                          checksum file is missing or cannot be downloaded
                          (checksum mismatch is always fatal)
  -q, --quiet             Suppress banner
""")
            return 0
        else:
            i += 1

    target = _resolve_init_target(output)

    if not quiet:
        print_banner(quiet=False)

    version_file = target / "DATA_VERSION"
    master_tsv = target / "mrsa" / "mrsa_all.tsv"
    master_gz = target / "mrsa" / "mrsa_all.tsv.gz"
    has_data = master_tsv.exists() or master_gz.exists()

    if has_data and not force and from_file is None and version is None:
        installed = version_file.read_text().strip() if version_file.exists() else "unknown"
        print(f"{C.GREEN}✓{C.RESET}  Data already installed at {target}", file=sys.stderr)
        print(f"    Installed version: {installed}", file=sys.stderr)
        print(
            f"    Use {C.CYAN}--force{C.RESET} to reinstall, "
            f"or {C.CYAN}-v <version>{C.RESET} to install a specific version.",
            file=sys.stderr,
        )
        print_footer(quiet, count_mode=True)
        return 0

    target.mkdir(parents=True, exist_ok=True)
    tmp_zip: Optional[Path] = None

    try:
        if from_file is not None:
            if not from_file.exists():
                log_error(f"Local zip not found: {from_file}")
                return 1
            zip_path = from_file
            print(f"{C.CYAN}📦{C.RESET}  Installing from local file: {zip_path}", file=sys.stderr)
            sidecar = Path(str(from_file) + ".sha256")
            if sidecar.exists():
                expected = sidecar.read_text().split()[0].strip()
                actual = _sha256(zip_path)
                if expected.lower() != actual.lower():
                    log_error("Checksum mismatch — file may be corrupted")
                    return 1
                print(f"{C.GREEN}✓{C.RESET}  Checksum verified", file=sys.stderr)
            elif allow_unverified:
                log_warn(
                    f"No checksum sidecar ({sidecar.name}) — proceeding "
                    "without verification (--allow-unverified)"
                )
            else:
                log_error(f"No checksum sidecar ({sidecar.name}) — refusing to install")
                print(
                    f"    Create it with: {C.CYAN}sha256sum {zip_path} > {sidecar}{C.RESET}",
                    file=sys.stderr,
                )
                print(
                    f"    Or re-run with {C.CYAN}--allow-unverified{C.RESET} "
                    "to install without verification.",
                    file=sys.stderr,
                )
                return 1
        else:
            zip_url, sha_url = _resolve_data_url(version)
            print(f"{C.CYAN}📥{C.RESET}  Downloading SAURUS data", file=sys.stderr)
            print(f"    {C.DIM}URL:    {zip_url}{C.RESET}", file=sys.stderr)
            print(f"    {C.DIM}Target: {target}{C.RESET}", file=sys.stderr)
            print("", file=sys.stderr)

            tmp_dir = Path(tempfile.mkdtemp(prefix="saurus-init-"))
            zip_path = tmp_dir / DATA_ASSET_NAME

            try:
                _download_with_progress(zip_url, zip_path)
            except urllib.error.HTTPError as e:
                log_error(f"Download failed: HTTP {e.code}")
                if e.code == 404:
                    print("    The release or asset does not exist.", file=sys.stderr)
                    print(f"    Check: https://github.com/{DATA_REPO}/releases", file=sys.stderr)
                return 1
            except Exception as e:
                log_error(f"Download failed: {e}")
                return 1

            try:
                with urllib.request.urlopen(sha_url, timeout=30) as r:
                    expected = r.read().decode().split()[0].strip()
                actual = _sha256(zip_path)
                if expected.lower() != actual.lower():
                    log_error("Checksum mismatch — download may be corrupted")
                    return 1
                print(f"{C.GREEN}✓{C.RESET}  Checksum verified", file=sys.stderr)
            except Exception:
                if allow_unverified:
                    log_warn("Checksum not available — proceeding (--allow-unverified)")
                else:
                    log_error("Checksum file could not be downloaded — aborting")
                    print(
                        f"    Re-run with {C.CYAN}--allow-unverified{C.RESET} "
                        f"to skip checksum verification.",
                        file=sys.stderr,
                    )
                    return 1

            tmp_zip = zip_path

        print(f"{C.CYAN}📂{C.RESET}  Extracting...", file=sys.stderr)
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            z.extractall(target)

        version_file = target / "DATA_VERSION"
        if version_file.exists():
            installed_version = version_file.read_text().strip()
        else:
            installed_version = version or "latest"

        master = target / "mrsa" / "mrsa_all.tsv"
        master_gz = target / "mrsa" / "mrsa_all.tsv.gz"
        if not master.exists() and not master_gz.exists():
            log_error("Zip extracted, but mrsa/mrsa_all.tsv is missing")
            return 1

        n_files = len([n for n in names if not n.endswith("/")])
        total_bytes = sum((target / n).stat().st_size for n in names if (target / n).is_file())
        total_mb = total_bytes / 1_048_576

        print(
            f"{C.GREEN}✓{C.RESET}  Data installed → {target}\n"
            f"    Version: {installed_version}\n"
            f"    Files:   {n_files}\n"
            f"    Size:    {total_mb:.1f} MB",
            file=sys.stderr,
        )
        print_footer(quiet, count_mode=True)
        return 0

    except zipfile.BadZipFile:
        log_error("Downloaded file is not a valid zip")
        return 1
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        return 1
    finally:
        if tmp_zip and tmp_zip.exists():
            try:
                tmp_zip.unlink()
                tmp_zip.parent.rmdir()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _version_str():
    """Return the --version output string, including the data version if available."""
    base = f" 🦖SAURUS-CLI v{__version__} — {__affiliation__}"
    try:
        d = find_data_dir()
        if d and (d / "DATA_VERSION").exists():
            dv = (d / "DATA_VERSION").read_text().strip()
            base += f"\n Data version: {dv}  ({d})"
    except Exception:
        pass
    return base


CONFIG_KEY_ALIASES = {"sra": "has_sra"}


def _config_attr(key, args, valid_keys):
    """Map a JSON config key onto its argparse destination.

    Keys are matched to argument names before aliasing, so both the flag
    spelling (`sccmec`) and the field spelling (`SCCmec`) resolve; anything
    else is rejected instead of being dropped with a warning, which is how
    silently wrong counts previously slipped in."""
    norm = key.strip().lower().replace("-", "_")
    if hasattr(args, norm):
        return norm
    for cand in valid_keys:
        if norm == cand.lower().replace("-", "_"):
            return cand
    norm2 = re.sub(r"[^a-z0-9_]+", "", key.strip().lower())
    for cand in valid_keys:
        if norm2 == re.sub(r"[^a-z0-9_]+", "", cand.lower()):
            return cand
    return CONFIG_KEY_ALIASES.get(norm) if CONFIG_KEY_ALIASES.get(norm) in valid_keys else None


STRING_FILTER_KEYS = {
    "st", "cc", "spa", "sccmec", "agr", "capsule", "country", "source",
    "host", "year", "amr", "vfdb", "plasmid", "lineage", "format",
}


def _coerce_config_value(attr, v):
    """Coerce JSON values to the types the filter code expects."""
    if attr in STRING_FILTER_KEYS:
        if isinstance(v, list):
            return ",".join(str(x).strip() for x in v)
        return str(v).strip()
    return v


def _cli_given_dests(argv, parser):
    """Return the set of argparse dests that were set explicitly on the CLI."""
    flag_map = {}
    for a in parser._actions:
        if a.dest == "help":
            continue
        for opt in a.option_strings:
            flag_map[opt.split("=", 1)[0]] = a.dest
    given = set()
    for tok in argv or []:
        base = tok.split("=", 1)[0]
        if base in flag_map:
            given.add(flag_map[base])
    return given


def _apply_config(config_data, args, parser, cli_override=None):
    valid_keys = [a.dest for a in parser._actions if a.dest not in ("help",)]
    cli_override = cli_override or set()
    for k, v in config_data.items():
        attr = _config_attr(k, args, valid_keys)
        if attr is None:
            log_error(
                f"Unknown config key '{k}'. Valid keys are the CLI flags without "
                f"'--': {', '.join(sorted(valid_keys))}"
            )
            sys.exit(1)
        if attr in cli_override:
            log_info(f"CLI flag overrides config for '{k}'")
            continue
        if attr == "any" and not v:
            continue
        setattr(args, attr, _coerce_config_value(attr, v))
    formats = [f.strip().lower() for f in str(args.format).split(",") if f.strip()]
    for f in formats:
        if f not in VALID_FORMATS:
            log_error(f"Unknown format '{f}' in config. Valid: {', '.join(sorted(VALID_FORMATS))}")
            sys.exit(1)
    if not formats:
        formats = ["accession"]
    args._formats = formats


def main(argv=None):
    """Entry point for the SAURUS CLI."""
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] in ("init", "setup"):
        sys.exit(cmd_init(argv[1:]))

    parser = argparse.ArgumentParser(
        description="🦖 SAURUS CLI — query 134K S. aureus genomes from your terminal. 🦖",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--config", "-c", help="JSON config file with query parameters.")
    parser.add_argument(
        "--data-dir", default=None,
        help="Path to SAURUS data directory\n"
             "(default: searches $SAURUS_DATA_DIR, XDG paths, ~/.saurus/data, "
             "./data, and bundled install)",
    )
    parser.add_argument("--debug", action="store_true", help="Show row counts after each filter.")
    parser.add_argument(
        "--lineage",
        help="Pre-defined lineage signature (USA100, USA300, EMRSA-15, Bengal Bay, ST152, etc.)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress the footer and banner (useful for scripting).",
    )
    parser.add_argument(
        "--examples", action="store_true",
        help="Print a gallery of example queries and exit.",
    )
    parser.add_argument(
        "--about", action="store_true",
        help="Print author, affiliation, and citation information and exit.",
    )
    parser.add_argument("--version", action="version", version=_version_str())

    grp_type = parser.add_argument_group("Typing filters")
    grp_type.add_argument("--st", help="MLST Sequence Type (e.g., 5)")
    grp_type.add_argument("--cc", help="Clonal Complex (e.g., 398)")
    grp_type.add_argument("--spa", help="spa Type (e.g., t002)")
    grp_type.add_argument("--sccmec", help="SCCmec Type (e.g., II, IV)")
    grp_type.add_argument("--agr", help="agr Type (e.g., I, II)")
    grp_type.add_argument("--capsule", help="Capsule Type (e.g., 5, 8)")

    grp_pheno = parser.add_argument_group("Phenotype")
    grp_pheno.add_argument("--mrsa", action="store_true", help="Filter only MRSA isolates")
    grp_pheno.add_argument("--mssa", action="store_true", help="Filter only MSSA isolates")
    grp_pheno.add_argument(
        "--has-sra", action="store_true",
        help="Filter only genomes with retrievable SRA raw reads",
    )

    grp_meta = parser.add_argument_group("Epidemiological metadata")
    grp_meta.add_argument("--country", help="Country of origin (matches country and country_raw)")
    grp_meta.add_argument("--source", help="Isolation source (e.g., blood, nasal)")
    grp_meta.add_argument("--host", help="Host species (e.g., 'Homo sapiens')")
    grp_meta.add_argument("--year", help="Collection year (e.g., 2019 or 2015-2023)")

    grp_gene = parser.add_argument_group("Gene content")
    gene_help_note = (
        "Standalone static snapshot, GCA-keyed (see 'saurus --examples'). "
        "Base names match their alleles (mecA -> mecA_6)."
    )
    grp_gene.add_argument(
        "--amr", help=f"AMR gene(s), comma-separated (e.g., mecA,tetM). {gene_help_note}"
    )
    grp_gene.add_argument(
        "--vfdb", help=f"Virulence gene(s), comma-separated. {gene_help_note}"
    )
    grp_gene.add_argument(
        "--plasmid", help=f"Plasmid replicon(s), comma-separated. {gene_help_note}"
    )
    grp_gene.add_argument(
        "--any", action="store_true",
        help="Match ANY of the given genes (default: ALL)",
    )

    grp_out = parser.add_argument_group("Output options")
    grp_out.add_argument(
        "--format", "-f", default="accession",
        help="Output format(s), comma-separated: tsv, csv, json, accession, "
             "sra, biosample, bioproject\n"
             "Examples: '--format tsv,accession' writes both a TSV and an accession list.\n"
             "Default: accession",
    )
    grp_out.add_argument("--output", "-o", default="stdout",
                         help="Output base path (extension added per format)")
    grp_out.add_argument("--count", action="store_true",
                         help="Only print the number of matching genomes")

    args = parser.parse_args(argv)
    if "_formats" in args.__dict__:
        del args.__dict__["_formats"]

    if args.examples:
        print_banner(quiet=args.quiet)
        print(EXAMPLES_GALLERY)
        print_footer(args.quiet, count_mode=True)
        sys.exit(0)
    if args.about:
        print_banner(quiet=args.quiet)
        print(ABOUT_TEXT)
        print_footer(args.quiet, count_mode=True)
        sys.exit(0)

    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            log_error(f"Config file {config_path} not found.")
            sys.exit(1)
        with open(config_path, "r") as f:
            config_data = json.load(f)
        log_info(f"Loaded config from {config_path}")
        _apply_config(config_data, args, parser,
                      cli_override=_cli_given_dests(argv, parser))
        formats = list(args._formats)
    else:
        formats = [f.strip().lower() for f in str(args.format).split(",") if f.strip()]
        for f in formats:
            if f not in VALID_FORMATS:
                log_error(f"Unknown format '{f}'. Valid: {', '.join(sorted(VALID_FORMATS))}")
                sys.exit(1)
        if not formats:
            formats = ["accession"]

    if args.lineage:
        key = args.lineage.upper().replace("-", " ").replace("_", " ").strip()
        sig = None
        for k, v in LINEAGE_SIGNATURES.items():
            if k.upper().replace("-", " ") == key or k.upper() == args.lineage.upper():
                sig = v
                break
        if sig is None:
            log_error(f"Unknown lineage '{args.lineage}'.")
            print(f"    Available: {', '.join(LINEAGE_SIGNATURES.keys())}", file=sys.stderr)
            sys.exit(1)
        log_lineage(f"Applying lineage signature: {args.lineage}")
        if not args.st and "st" in sig:
            args.st = sig["st"]
        if not args.cc and "cc" in sig:
            args.cc = sig["cc"]
        if not args.spa and "spa" in sig:
            args.spa = sig["spa"]
        if not args.sccmec and "sccmec" in sig:
            args.sccmec = sig["sccmec"]
        if not args.agr and "agr" in sig:
            args.agr = sig["agr"]
        if not args.capsule and "capsule" in sig:
            args.capsule = sig["capsule"]

    has_any_filter = any([
        args.st, args.cc, args.spa, args.sccmec, args.agr, args.capsule,
        args.mrsa, args.mssa, args.country, args.source, args.host, args.year,
        args.amr, args.vfdb, args.plasmid, args.lineage, args.config,
        args.has_sra,
    ])
    if not has_any_filter and not args.count and args.output == "stdout":
        print_banner(quiet=args.quiet)
        print(parser.format_help())
        print(f"\n{C.YELLOW}💡  Add a filter to query the database, e.g.:{C.RESET}", file=sys.stderr)
        print(f"      {C.CYAN}saurus --lineage USA300 --count{C.RESET}", file=sys.stderr)
        print(f"      {C.CYAN}saurus --st 5 --mrsa --country USA{C.RESET}", file=sys.stderr)
        print(f"\n   {C.CYAN}saurus --examples{C.RESET} for a full gallery.\n", file=sys.stderr)
        sys.exit(0)

    data_dir = find_data_dir(args.data_dir)
    if data_dir is None:
        log_error("SAURUS data not found.")
        print("    Searched:", file=sys.stderr)
        for c in _get_data_dir_candidates(args.data_dir):
            print(f"      • {c}", file=sys.stderr)
        print("", file=sys.stderr)
        print("    Fix one of these ways:", file=sys.stderr)
        print(f"      {C.CYAN}saurus init{C.RESET}                        (download to default location)", file=sys.stderr)
        print(f"      {C.CYAN}pip install --force-reinstall saurus-cli{C.RESET}  (restore bundled data)", file=sys.stderr)
        print(f"      {C.CYAN}saurus --data-dir /path/to/data ...{C.RESET}      (use custom location)", file=sys.stderr)
        print(f"      {C.CYAN}export SAURUS_DATA_DIR=/path/to/data{C.RESET}   (env var)", file=sys.stderr)
        sys.exit(1)
    if args.debug:
        log_debug(f"data_dir = {data_dir}")

    if not args.quiet and _supports_color(sys.stderr):
        print_banner(quiet=False)

    df = load_data(args, data_dir)
    debug_step("Initial load", df, args.debug)

    if args.st:
        t = str(args.st).strip()
        if t.upper().startswith("ST"):
            t = t[2:]
        df = df[df["mlst_st"].fillna("").astype(str).str.strip() == t]
        debug_step(f"--st {t}", df, args.debug)

    if args.cc:
        t = str(args.cc).strip().upper()
        if not t.startswith("CC"):
            t = "CC" + t
        cc_vals = df["mlst_cc"].fillna("").astype(str).str.strip().str.upper()
        n_unmapped = int(((cc_vals == "") | (cc_vals == "NA") | (cc_vals == "CCNA")).sum())
        if n_unmapped:
            log_warn(
                f"{n_unmapped:,} of {len(df):,} selected genomes have no clonal-complex "
                "assignment in this data release (missing CC mapping, not membership "
                "of a different CC); they are excluded by --cc."
            )
        df = df[cc_vals == t]
        debug_step(f"--cc {t}", df, args.debug)

    if args.spa:
        t = str(args.spa).strip().lower()
        if not t.startswith("t"):
            t = "t" + t
        df = df[df["spa_type"].fillna("").str.lower() == t]
        debug_step(f"--spa {t}", df, args.debug)

    if args.sccmec:
        t = str(args.sccmec).strip().upper()
        t = re.sub(r"^(SCCMEC_TYPE_|TYPE\s+|SCCMEC_)", "", t)
        df = df[
            (df["sccmec_cge"].apply(extract_sccmec_roman) == t)
            | (df["sccmec_rpet"].apply(extract_sccmec_roman) == t)
        ]
        debug_step(f"--sccmec {t}", df, args.debug)

    if args.agr:
        t = str(args.agr).strip().upper()
        t = re.sub(r"^(AGR_?TYPE_?|AGR_?|TYPE_)", "", t)
        df = df[df["agr_type"].fillna("").str.strip().str.upper() == t]
        debug_step(f"--agr {t}", df, args.debug)

    if args.capsule:
        t = str(args.capsule).strip()
        t = re.sub(r"^(Type\s*|TYPE\s*)", "", t, flags=re.IGNORECASE)
        df = df[df["capsule_type"].fillna("").str.contains(f"Type {t}", case=False, na=False)]
        debug_step(f"--capsule Type {t}", df, args.debug)

    if args.mrsa:
        df = df[df["mrsa_status"] == "MRSA"]
        debug_step("--mrsa", df, args.debug)
    if args.mssa:
        df = df[df["mrsa_status"] == "MSSA"]
        debug_step("--mssa", df, args.debug)

    if getattr(args, "has_sra", False):
        if "sra_run" not in df.columns:
            log_warn("Column 'sra_run' not in data — rebuild master TSV to use --has-sra")
        else:
            sra_mask = df["sra_run"].fillna("").astype(str).str.strip()
            df = df[(sra_mask != "") & (sra_mask != "NA")]
        debug_step("--has-sra", df, args.debug)

    if args.country:
        c = args.country.strip().lower()
        col_a = df["country"].fillna("").str.lower().str.strip()
        col_b = df["country_raw"].fillna("").str.lower() if "country_raw" in df.columns else col_a
        df = df[
            (col_a == c)
            | (col_b == c)
            | col_b.str.startswith(c + ":")
            | col_b.str.startswith(c + ",")
        ]
        debug_step(f"--country '{args.country}'", df, args.debug)

    if args.source:
        s = args.source.strip().lower()
        col_a = df["source"].fillna("").str.lower()
        col_b = df["source_raw"].fillna("").str.lower() if "source_raw" in df.columns else col_a
        df = df[col_a.str.contains(s, na=False) | col_b.str.contains(s, na=False)]
        debug_step(f"--source '{args.source}'", df, args.debug)

    if args.host:
        h = args.host.strip()
        df = df[df["host"].fillna("").str.contains(h, case=False, na=False)]
        debug_step(f"--host '{h}'", df, args.debug)

    if args.year:
        yc = df["year"].fillna("").astype(str).str[:4]
        if "-" in args.year:
            a, b = args.year.split("-")
            df = df[(yc >= a.strip()) & (yc <= b.strip())]
            debug_step(f"--year {a}-{b}", df, args.debug)
        else:
            df = df[yc == str(args.year).strip()]
            debug_step(f"--year {args.year}", df, args.debug)

    GENE_MODULES = [
        ("amr", "AMR", ["gene_annotation/amr_all.tsv", "amr_all.tsv"]),
        ("vfdb", "VFDB", ["gene_annotation/vfdb_all.tsv", "vfdb_all.tsv"]),
        ("plasmid", "Plasmid", ["gene_annotation/plasmid_all.tsv", "plasmid_all.tsv"]),
    ]
    active_gene_modules = [
        (attr, label, rels)
        for attr, label, rels in GENE_MODULES
        if getattr(args, attr)
    ]
    if active_gene_modules:
        _warn_gene_table_coverage(
            data_dir, active_labels={label for _, label, _ in active_gene_modules},
            debug=args.debug,
        )
        if args.any and len(active_gene_modules) > 1:
            any_accs = set()
            for attr, label, rels in active_gene_modules:
                f = find_data_file(data_dir, *rels)
                if not f:
                    continue
                accs_by_gene, _ = resolve_gene_accessions(
                    f, [g.strip() for g in getattr(args, attr).split(",")], label
                )
                module_accs = set().union(*accs_by_gene) if accs_by_gene else set()
                any_accs = any_accs.union(module_accs)
                if args.debug:
                    log_debug(
                        f"--{attr} {getattr(args, attr)} (--any): "
                        f"{len(set(df['accession']) & module_accs):,} rows"
                    )
            df = df[df["accession"].isin(any_accs)]
            debug_step("--any gene union across modules", df, args.debug)
        else:
            for attr, label, rels in active_gene_modules:
                f = find_data_file(data_dir, *rels)
                if not f:
                    continue
                df = filter_by_gene(
                    df, f, [g.strip() for g in getattr(args, attr).split(",")],
                    match_all=not args.any, module_label=label,
                )
                debug_step(f"--{attr} {getattr(args, attr)}", df, args.debug)

    if args.count:
        print(f"{len(df):,}", flush=True)
        print_footer(args.quiet, count_mode=True)
        sys.exit(0)

    if len(df) == 0:
        log_zero()
        print_footer(args.quiet, count_mode=True)
        sys.exit(0)

    log_found(len(df))

    if args.output == "stdout" and len(formats) > 1:
        log_error("Please specify --output (-o) when requesting multiple formats.")
        sys.exit(1)

    if args.output == "stdout":
        print(serialize(df, formats[0]))
        if not args.quiet:
            print(
                f"{C.GRAY}    (streamed {len(df):,} rows to stdout · {formats[0]}){C.RESET}",
                file=sys.stderr,
            )
    else:
        paths = resolve_output_paths(args.output, formats)
        for fmt, path in paths.items():
            content = serialize(df, fmt)
            if fmt in SRA_FORMATS:
                if not content.strip():
                    log_warn(f"Skipping '{path}' — 0 {fmt} accessions in the selected rows")
                    continue
                count = len(content.strip().split("\n"))
            else:
                count = len(df)
            path.write_text(content)
            log_write(path, count, fmt)

    print_footer(args.quiet, count_mode=False)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}⚠️   Interrupted.{C.RESET}", file=sys.stderr)
        sys.exit(130)