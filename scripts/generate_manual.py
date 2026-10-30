#!/usr/bin/env python3
"""
generate_manual.py — Build the SAURUS CLI Manual page.

Reads:   nothing (static content)
Writes:  manual.html

Author: Brown Beckley <brownbeckley94@gmail.com>
"""

import argparse
from pathlib import Path
from datetime import datetime


# =========================================================================
# CLI metadata (mirrors saurus_cli.py — update in sync)
# =========================================================================
CLI_VERSION = "0.2.0"
CLI_AUTHOR = "Brown Beckley"
CLI_AFFILIATION = "University of Ghana Medical School, Accra, Ghana"


# =========================================================================
# EXAMPLE CATEGORIES — the master example gallery
# Each item: {"title": ..., "desc": ..., "cmd": ..., "note": optional}
# =========================================================================
EXAMPLE_CATEGORIES = [
    {
        "id": "counting",
        "icon": "📊",
        "title": "Counting Genomes",
        "desc": "Get a number fast — perfect for checking how much data exists before you commit to downloading.",
        "examples": [
            {
                "title": "USA300 globally",
                "desc": "The world's most sequenced community-acquired MRSA clone.",
                "cmd": "saurus --lineage USA300 --count",
                "note": "Returns ~8,657 genomes.",
            },
            {
                "title": "USA100 bloodstream isolates in the USA",
                "desc": "The New York/Japan clone — dominant hospital MRSA in the US.",
                "cmd": "saurus --lineage USA100 --country USA --source blood --count",
                "note": "Returns ~297 genomes.",
            },
            {
                "title": "ST5 MRSA with SCCmec II and agr II",
                "desc": "The full genotype you'd expect for a USA100 hospital isolate.",
                "cmd": "saurus --st 5 --sccmec II --agr II --mrsa --count",
            },
            {
                "title": "Livestock-associated MRSA in Denmark",
                "desc": "CC398 in pigs — the classic LA-MRSA surveillance query.",
                "cmd": 'saurus --cc 398 --mrsa --country Denmark --host "Sus scrofa" --count',
            },
            {
                "title": "All MRSA from Ghana",
                "desc": "Demonstrates African surveillance coverage.",
                "cmd": "saurus --mrsa --country Ghana --count",
                "note": "Small number — the African data gap in action.",
            },
        ],
    },
    {
        "id": "export",
        "icon": "📤",
        "title": "Exporting Accessions",
        "desc": "Every query exports a clean accession list, ready for the NCBI datasets CLI. Or export the full metadata table too.",
        "examples": [
            {
                "title": "Plain-text accession list",
                "desc": "The format 95% of downstream pipelines actually consume.",
                "cmd": "saurus --lineage USA300 -o usa300.txt",
            },
            {
                "title": "Metadata table AND accession list together",
                "desc": "One command → two files. Verify the rows, then feed the list downstream.",
                "cmd": "saurus --lineage USA300 --format tsv,accession -o usa300_results",
                "note": "Produces usa300_results.tsv and usa300_results.txt.",
            },
            {
                "title": "Everything, all at once",
                "desc": "TSV + JSON + accession list — three files, one command.",
                "cmd": "saurus --lineage EMRSA-15 --format tsv,json,accession -o emrsa15_results",
            },
        ],
    },
    {
        "id": "genotype",
        "icon": "🧬",
        "title": "Genotype Queries",
        "desc": "Filter by gene content across the AMR, virulence, and plasmid modules. Match ALL (default) or ANY with --any.",
        "examples": [
            {
                "title": "PVL-positive ST8",
                "desc": "lukS-PV is the toxin marker that made USA300 famous.",
                "cmd": "saurus --st 8 --vfdb lukS-PV --count",
            },
            {
                "title": "MRSA with both mecA and erm(B)",
                "desc": "Match ALL genes — the default AND logic.",
                "cmd": "saurus --amr mecA,ermB --count",
            },
            {
                "title": "Multi-drug resistant (match ANY)",
                "desc": "mecA OR tetM — the OR logic. Returns a larger set than the AND version.",
                "cmd": "saurus --amr mecA,tetM --any --count",
            },
            {
                "title": "Plasmid replicon filter",
                "desc": "Find genomes carrying a specific plasmid replicon — useful for horizontal-gene-transfer studies.",
                "cmd": "saurus --plasmid rep5a --count",
            },
        ],
    },
    {
        "id": "metadata",
        "icon": "🌍",
        "title": "Metadata Queries",
        "desc": "Combine genotype with country, source, host, and year — the core of surveillance.",
        "examples": [
            {
                "title": "USA300 bloodstream infections, USA, 2005–2015",
                "desc": "The decade USA300 exploded across US hospitals.",
                "cmd": "saurus --lineage USA300 --source blood --year 2005-2015 -o usa300_2005_2015.txt",
            },
            {
                "title": "EMRSA-15 in the UK",
                "desc": "The UK's dominant hospital-acquired MRSA clone.",
                "cmd": 'saurus --lineage EMRSA-15 --country "United Kingdom" --count',
            },
            {
                "title": "Bengal Bay clone in India",
                "desc": "ST772 — a regional clone with global spread.",
                "cmd": 'saurus --lineage "Bengal Bay" --country India --count',
            },
            {
                "title": "Recent EMRSA-16 in the UK",
                "desc": "Combines lineage, geography, and time range.",
                "cmd": 'saurus --lineage EMRSA-16 --country "United Kingdom" --year 2020-2025 --count',
            },
        ],
    },
    {
        "id": "diagnostics",
        "icon": "🐞",
        "title": "Diagnostics",
        "desc": "When a query returns 0 genomes, --debug shows you exactly where the count dropped. The #1 time saver.",
        "examples": [
            {
                "title": "Debug an impossible genotype",
                "desc": "ST5 is never agr I / capsule 8 — the USA100 genotype is agr II / capsule 5.",
                "cmd": "saurus --st 5 --agr I --capsule 8 --debug --count",
                "note": "Shows the exact step where it drops to 0.",
            },
            {
                "title": "Quiet mode for pipelines",
                "desc": "Suppresses banner, footer, and quote — clean stdout for scripting.",
                "cmd": "saurus --lineage USA300 -q | head -5",
                "note": "Exits silently when piped — no BrokenPipeError.",
            },
        ],
    },
    {
        "id": "lineages",
        "icon": "🏷️",
        "title": "Lineage Signatures",
        "desc": "Use --lineage to apply a curated genotype signature in one flag. Override any component by passing the specific flag yourself.",
        "examples": [
            {
                "title": "USA300 override",
                "desc": "USA300 signature, but restricted to Japan instead of global.",
                "cmd": "saurus --lineage USA300 --country Japan --count",
            },
            {
                "title": "ST152 (African clone) in Ghana",
                "desc": "ST152 is prominent in West Africa and typically carries SCCmec V.",
                "cmd": "saurus --lineage ST152 --country Ghana --count",
            },
            {
                "title": "List available signatures",
                "desc": "An unknown lineage shows the full list of options.",
                "cmd": "saurus --lineage XYZ",
                "note": "Prints all available shortcuts and exits.",
            },
        ],
    },
]


# =========================================================================
# LINEAGE SIGNATURES — mirrors saurus_cli.py
# =========================================================================
LINEAGES = [
    {"name": "USA100",     "color": "#dc2626", "sig": "ST5 · t002 · SCCmec II · agr II · capsule 5"},
    {"name": "USA300",     "color": "#ea580c", "sig": "ST8 · t008 · SCCmec IV · agr I · capsule 5"},
    {"name": "USA400",     "color": "#f59e0b", "sig": "ST1 · t128 · SCCmec IV · agr III · capsule 8"},
    {"name": "USA500",     "color": "#ca8a04", "sig": "ST8 · t064 · SCCmec IV · agr I · capsule 5"},
    {"name": "USA700",     "color": "#65a30d", "sig": "ST72 · t324 · SCCmec IV · agr I · capsule 5"},
    {"name": "USA800",     "color": "#16a34a", "sig": "ST5 · t688 · SCCmec IV · agr II · capsule 5"},
    {"name": "EMRSA-15",   "color": "#0d9488", "sig": "ST22 · t032 · SCCmec IV · agr I · capsule 5"},
    {"name": "EMRSA-16",   "color": "#0891b2", "sig": "ST36 · t018 · SCCmec II · agr III · capsule 8"},
    {"name": "Bengal Bay", "color": "#7c3aed", "sig": "ST772 · t657 · SCCmec V · agr II · capsule 5"},
    {"name": "ST152",      "color": "#db2777", "sig": "ST152 · SCCmec V · agr III · capsule 5"},
]


# =========================================================================
# CORE FLAGS — reference table
# =========================================================================
FLAGS = [
    {"group": "Typing filters", "items": [
        {"flag": "--st",      "desc": "MLST Sequence Type",         "ex": "--st 5 or --st ST5"},
        {"flag": "--cc",      "desc": "Clonal Complex",             "ex": "--cc 398 or --cc CC398"},
        {"flag": "--spa",     "desc": "spa Type",                   "ex": "--spa t002"},
        {"flag": "--sccmec",  "desc": "SCCmec Type",                "ex": "--sccmec II"},
        {"flag": "--agr",     "desc": "agr Type",                   "ex": "--agr I or II"},
        {"flag": "--capsule", "desc": "Capsule Serotype",           "ex": "--capsule 5 or 8"},
    ]},
    {"group": "Phenotype", "items": [
        {"flag": "--mrsa",    "desc": "Only MRSA isolates",         "ex": "--mrsa"},
        {"flag": "--mssa",    "desc": "Only MSSA isolates",         "ex": "--mssa"},
    ]},
    {"group": "Epidemiological metadata", "items": [
        {"flag": "--country", "desc": "Country of origin",          "ex": '--country USA'},
        {"flag": "--source",  "desc": "Isolation source",           "ex": "--source blood"},
        {"flag": "--host",    "desc": "Host species",               "ex": '--host "Homo sapiens"'},
        {"flag": "--year",    "desc": "Collection year or range",   "ex": "--year 2019  or  2015-2023"},
    ]},
    {"group": "Gene content", "items": [
        {"flag": "--amr",     "desc": "AMR gene(s), comma-separated","ex": "--amr mecA,tetM"},
        {"flag": "--vfdb",    "desc": "Virulence gene(s)",           "ex": "--vfdb lukS-PV"},
        {"flag": "--plasmid", "desc": "Plasmid replicon(s)",         "ex": "--plasmid rep5a"},
        {"flag": "--any",     "desc": "Match ANY gene (default ALL)","ex": "--amr mecA,tetM --any"},
    ]},
    {"group": "Output", "items": [
        {"flag": "--format",  "desc": "One or more formats",        "ex": "--format tsv,accession"},
        {"flag": "--output",  "desc": "Output base path",           "ex": "-o usa300_results"},
        {"flag": "--count",   "desc": "Print count only",           "ex": "--count"},
        {"flag": "--quiet",   "desc": "Suppress footer (scripts)",  "ex": "-q"},
        {"flag": "--debug",   "desc": "Show row counts per filter", "ex": "--debug"},
    ]},
    {"group": "Shortcuts", "items": [
        {"flag": "--lineage", "desc": "Pre-defined signature",      "ex": "--lineage USA300"},
        {"flag": "--config",  "desc": "JSON config file",           "ex": "--config query.json"},
        {"flag": "--examples","desc": "Show example gallery",       "ex": "--examples"},
        {"flag": "--about",   "desc": "Author and citation info",   "ex": "--about"},
        {"flag": "--version", "desc": "Version number",             "ex": "--version"},
    ]},
]


# ---------------------------------------------------------------------------
# CSS — matches generate_about.py palette
# ---------------------------------------------------------------------------
CSS = """
:root {
    --gold: #d4af37;
    --gold-dark: #b8941f;
    --navy: #0a1628;
    --navy-2: #1e293b;
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #1e293b;
    --muted: #64748b;
    --border: #e2e8f0;
    --code-bg: #0f172a;
    --code-fg: #e2e8f0;
    --accent: #3b82f6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.65;
    -webkit-font-smoothing: antialiased;
}

/* ---------- Nav ---------- */
.saurus-nav {
    background: var(--navy);
    color: white;
    padding: 20px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    position: sticky;
    top: 0;
    z-index: 100;
}
.saurus-nav .brand {
    display: flex; align-items: center; gap: 20px;
    text-decoration: none; flex-shrink: 0;
}
.saurus-nav .brand-emoji { font-size: 5.6em; line-height: 1; flex-shrink: 0; }
.saurus-nav .brand-text { display: flex; flex-direction: column; gap: 3px; }
.saurus-nav .brand-name {
    font-weight: 800; font-size: 3.45em; letter-spacing: 1px;
    color: var(--gold); line-height: 1;
}
.saurus-nav .brand-tagline {
    font-size: 1.0em; font-weight: 400;
    color: #94a3b8; line-height: 1.15; max-width: 520px;
}
.saurus-nav .links {
    display: flex; gap: 2px; align-items: center; flex-wrap: wrap;
}
.saurus-nav .links a {
    color: #cbd5e1; text-decoration: none;
    padding: 6px 10px; border-radius: 6px;
    font-size: 0.85em; font-weight: 500;
    transition: all 0.15s; white-space: nowrap;
}
.saurus-nav .links a:hover { background: rgba(255,255,255,0.08); color: white; }
.saurus-nav .links a.active { background: var(--gold); color: var(--navy); font-weight: 600; }

/* ---------- Hero ---------- */
.manual-hero {
    background:
        radial-gradient(circle at 25% 30%, rgba(212, 175, 55, 0.10) 0%, transparent 55%),
        radial-gradient(circle at 75% 70%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
        linear-gradient(135deg, var(--navy) 0%, var(--navy-2) 100%);
    color: white;
    padding: 70px 32px 55px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.manual-hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: radial-gradient(circle, rgba(212,175,55,0.15) 1px, transparent 1px);
    background-size: 40px 40px;
    opacity: 0.3;
    pointer-events: none;
}
.manual-hero-inner { position: relative; max-width: 900px; margin: 0 auto; z-index: 1; }
.manual-hero h1 {
    font-size: 2.8em; font-weight: 900;
    color: var(--gold); letter-spacing: 2px;
    margin-bottom: 12px;
    text-shadow: 0 4px 24px rgba(212,175,55,0.25);
}
.manual-hero .hero-sub {
    font-size: 1.15em; color: #cbd5e1;
    margin-bottom: 14px; font-weight: 500;
}
.manual-hero .hero-tag {
    display: inline-block;
    background: rgba(212,175,55,0.15);
    color: var(--gold);
    padding: 6px 18px; border-radius: 20px;
    font-size: 0.85em; font-weight: 700;
    letter-spacing: 0.5px;
    border: 1px solid rgba(212,175,55,0.3);
}
.manual-hero .hero-cta {
    margin-top: 26px;
    display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;
}
.manual-hero .hero-cta a {
    display: inline-flex; align-items: center; gap: 10px;
    padding: 12px 24px;
    border-radius: 10px;
    text-decoration: none;
    font-weight: 800; font-size: 0.95em;
    transition: all 0.18s;
    letter-spacing: 0.3px;
}
.manual-hero .hero-cta a.primary {
    background: var(--gold); color: var(--navy);
}
.manual-hero .hero-cta a.primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(212,175,55,0.35);
}
.manual-hero .hero-cta a.secondary {
    background: rgba(212,175,55,0.15);
    color: var(--gold);
    border: 2px solid rgba(212,175,55,0.4);
}
.manual-hero .hero-cta a.secondary:hover {
    background: rgba(212,175,55,0.25);
    transform: translateY(-2px);
}

/* ---------- TOC / Sidebar ---------- */
.manual-layout {
    max-width: 1400px;
    margin: 0 auto;
    padding: 40px 32px 60px;
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 40px;
    align-items: start;
}
.toc {
    position: sticky;
    top: 100px;
    background: var(--card);
    border-radius: 12px;
    padding: 22px 20px;
    border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    max-height: calc(100vh - 130px);
    overflow-y: auto;
}
.toc .toc-title {
    font-size: 0.78em;
    font-weight: 800;
    color: var(--gold-dark);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--gold);
}
.toc ul { list-style: none; }
.toc li { margin-bottom: 4px; }
.toc a {
    display: block;
    padding: 6px 10px;
    border-radius: 6px;
    text-decoration: none;
    color: #475569;
    font-size: 0.88em;
    font-weight: 500;
    transition: all 0.12s;
}
.toc a:hover { background: #f1f5f9; color: var(--navy); }
.toc a.section-h {
    font-weight: 700;
    color: var(--navy);
    margin-top: 8px;
}
.toc a.section-h:hover { background: rgba(212,175,55,0.1); }
.toc .toc-sub { margin-left: 12px; font-size: 0.84em; }

.manual-content { min-width: 0; }

/* ---------- Manual section ---------- */
.manual-section {
    background: var(--card);
    border-radius: 14px;
    padding: 34px 40px;
    margin-bottom: 26px;
    border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    scroll-margin-top: 100px;
}
.manual-section h2 {
    font-size: 1.6em;
    color: var(--navy);
    margin-bottom: 18px;
    display: flex; align-items: center; gap: 14px;
    padding-bottom: 12px;
    border-bottom: 3px solid var(--gold);
    font-weight: 800;
}
.manual-section h3 {
    font-size: 1.15em;
    color: #334155;
    margin: 26px 0 12px;
    font-weight: 700;
}
.manual-section p {
    color: #475569;
    margin-bottom: 14px;
    font-size: 1.0em;
    line-height: 1.7;
}
.manual-section ul, .manual-section ol {
    margin: 8px 0 16px 24px;
    color: #475569;
}
.manual-section li {
    margin-bottom: 8px;
    line-height: 1.65;
}
.manual-section code {
    background: #f1f5f9;
    padding: 2px 7px;
    border-radius: 5px;
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 0.88em;
    color: #334155;
    border: 1px solid #e2e8f0;
}
.manual-section a {
    color: #1e40af;
    text-decoration: none;
    font-weight: 600;
    border-bottom: 1px dotted #1e40af;
}
.manual-section a:hover { color: var(--gold-dark); border-bottom-color: var(--gold-dark); }

.lead {
    font-size: 1.08em;
    color: #334155;
    line-height: 1.75;
    margin-bottom: 20px;
}

/* ---------- Code blocks ---------- */
.code-block {
    position: relative;
    margin: 14px 0 10px;
}
.code-block pre {
    background: var(--code-bg);
    color: var(--code-fg);
    padding: 18px 60px 18px 22px;
    border-radius: 10px;
    overflow-x: auto;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
    font-size: 0.92em;
    line-height: 1.6;
    margin: 0;
    border-left: 4px solid var(--gold);
}
.code-block pre code {
    background: transparent;
    border: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
}
.code-block .prompt { color: #64748b; user-select: none; }
.code-block .cmd    { color: #fbbf24; }
.code-block .comment { color: #64748b; font-style: italic; }
.copy-btn {
    position: absolute;
    top: 12px;
    right: 12px;
    background: rgba(255,255,255,0.08);
    color: #e2e8f0;
    border: 1px solid rgba(255,255,255,0.15);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.78em;
    font-weight: 700;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
}
.copy-btn:hover {
    background: var(--gold);
    color: var(--navy);
    border-color: var(--gold);
}
.copy-btn.copied {
    background: #10b981;
    color: white;
    border-color: #10b981;
}

/* ---------- Example cards ---------- */
.example-list { display: flex; flex-direction: column; gap: 22px; }
.example-item {
    background: #f8fafc;
    border-radius: 12px;
    padding: 22px 24px;
    border: 1px solid var(--border);
    border-left: 4px solid var(--gold);
}
.example-item .ex-title {
    font-size: 1.05em;
    font-weight: 800;
    color: var(--navy);
    margin-bottom: 6px;
}
.example-item .ex-desc {
    font-size: 0.92em;
    color: var(--muted);
    margin-bottom: 12px;
    line-height: 1.55;
}
.example-item .ex-note {
    margin-top: 8px;
    font-size: 0.85em;
    color: #92400e;
    background: #fffbeb;
    padding: 6px 12px;
    border-radius: 6px;
    display: inline-block;
    border-left: 3px solid #f59e0b;
}

/* ---------- Flags table ---------- */
.flag-table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 20px;
    font-size: 0.92em;
}
.flag-table th {
    background: var(--navy);
    color: var(--gold);
    padding: 12px 16px;
    text-align: left;
    font-weight: 700;
    font-size: 0.82em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
}
.flag-table td {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}
.flag-table tr:hover td { background: #f8fafc; }
.flag-table td code {
    background: var(--navy);
    color: var(--gold);
    padding: 3px 10px;
    border-radius: 5px;
    font-weight: 700;
    font-size: 0.88em;
    border: none;
}
.flag-table td.flag-ex code {
    background: #f1f5f9;
    color: #475569;
    font-weight: 500;
}
.flag-group-title {
    font-size: 0.78em;
    font-weight: 800;
    color: var(--gold-dark);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 22px 0 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}

/* ---------- Lineage grid ---------- */
.lineage-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
    margin-top: 16px;
}
.lineage-card {
    background: #f8fafc;
    border-radius: 10px;
    padding: 16px 18px;
    border-left: 5px solid var(--lc, var(--gold));
    border-top: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    transition: all 0.15s;
}
.lineage-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
}
.lineage-card .lc-name {
    font-size: 1.05em;
    font-weight: 900;
    color: var(--lc, var(--gold-dark));
    margin-bottom: 6px;
    letter-spacing: 0.3px;
}
.lineage-card .lc-sig {
    font-size: 0.82em;
    color: #475569;
    font-family: 'SF Mono', Monaco, monospace;
    line-height: 1.5;
}

/* ---------- Callouts ---------- */
.callout {
    padding: 16px 20px;
    border-radius: 10px;
    margin: 16px 0;
    font-size: 0.95em;
    line-height: 1.65;
}
.callout.info    { background: #eff6ff; border-left: 4px solid #3b82f6; color: #1e3a8a; }
.callout.success { background: #f0fdf4; border-left: 4px solid #10b981; color: #065f46; }
.callout.warn    { background: #fffbeb; border-left: 4px solid #f59e0b; color: #78350f; }
.callout.danger  { background: #fef2f2; border-left: 4px solid #dc2626; color: #991b1b; }
.callout strong { font-weight: 800; }

/* ---------- Feature grid ---------- */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-top: 18px;
}
.feature-card {
    background: #f8fafc;
    border-radius: 12px;
    padding: 20px 18px;
    border: 1px solid var(--border);
    transition: all 0.18s;
}
.feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 24px rgba(0,0,0,0.08);
    border-color: var(--gold);
}
.feature-card .f-icon {
    font-size: 1.8em;
    display: block;
    margin-bottom: 10px;
    line-height: 1;
}
.feature-card h4 {
    color: var(--navy);
    font-size: 1em;
    margin-bottom: 6px;
    font-weight: 700;
}
.feature-card p {
    color: var(--muted);
    font-size: 0.88em;
    margin: 0;
    line-height: 1.55;
}

/* ---------- Footer ---------- */
.saurus-footer {
    background: var(--navy);
    color: #94a3b8;
    padding: 40px 32px;
    text-align: center;
    font-size: 0.88em;
    margin-top: 40px;
}
.saurus-footer .footer-line { margin: 8px 0; }
.saurus-footer a {
    color: var(--gold);
    text-decoration: none;
    font-weight: 600;
}
.saurus-footer a:hover { text-decoration: underline; }
.saurus-footer .full-name {
    color: #cbd5e1;
    font-size: 1em;
    letter-spacing: 0.2px;
    margin-bottom: 14px;
}

/* ---------- Responsive ---------- */
@media (max-width: 1000px) {
    .manual-layout {
        grid-template-columns: 1fr;
        padding: 24px 20px 50px;
    }
    .toc { position: static; max-height: none; }
    .saurus-nav { flex-direction: column; align-items: flex-start; gap: 12px; }
    .saurus-nav .brand-tagline { max-width: 100%; }
    .saurus-nav .brand-emoji { font-size: 3.6em; }
    .saurus-nav .brand-name { font-size: 2.2em; }
    .manual-hero { padding: 50px 20px 40px; }
    .manual-hero h1 { font-size: 2.1em; }
    .manual-section { padding: 26px 22px; }
    .manual-section h2 { font-size: 1.3em; }
}
@media (max-width: 600px) {
    .saurus-nav { padding: 14px 16px; }
    .manual-hero .hero-cta { flex-direction: column; align-items: stretch; }
    .manual-hero .hero-cta a { justify-content: center; }
}
"""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
NAV_LINKS = [
    ("index.html", "Home", False),
    ("pages/mlst.html", "MLST", False),
    ("pages/spa.html", "spa", False),
    ("pages/sccmec.html", "SCCmec", False),
    ("pages/capsule.html", "Capsule", False),
    ("pages/agr.html", "agr", False),
    ("pages/mrsa.html", "MRSA", False),
    ("pages/amr.html", "AMR", False),
    ("pages/vfdb.html", "Virulence", False),
    ("pages/plasmid.html", "Plasmid", False),
    ("statistics.html", "Statistics", False),
    ("geography.html", "Geography", False),
    ("lineages.html", "Lineages", False),
    ("downloads.html", "Downloads", False),
    ("manual.html", "CLI Manual", True),
    ("about.html", "About", False),
]


def esc(s):
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def code_block(cmd, comment=None):
    """Render a copy-able shell code block."""
    inner = f'<span class="prompt">$ </span><span class="cmd">{esc(cmd)}</span>'
    if comment:
        inner += f'\n<span class="comment"># {esc(comment)}</span>'
    return (
        '<div class="code-block">'
        '<button class="copy-btn" onclick="copyCode(this)">📋 Copy</button>'
        f'<pre><code>{inner}</code></pre>'
        '</div>'
    )


def build_toc():
    sections = [
        ("quickstart",       "🚀  Quick Start"),
        ("install",          "📦  Installation"),
        ("first-query",      "🎯  Your First Query"),
        ("flags",            "🧾  Core Flags"),
        ("lineages",         "🏷️  Lineage Signatures"),
        ("examples",         "📚  Example Queries"),
        ("multi-format",     "📤  Multi-Format Output"),
        ("config",           "🔁  Reproducible Configs"),
        ("pipeline",         "⚙️  Pipeline Integration"),
        ("diagnostics",      "🐞  Troubleshooting"),
        ("cli-commands",     "💻  CLI Commands"),
    ]
    out = ['<nav class="toc"><div class="toc-title">On This Page</div><ul>']
    for anchor, label in sections:
        out.append(f'<li><a class="section-h" href="#{anchor}">{label}</a></li>')
    out.append("</ul></nav>")
    return "".join(out)


def build_example_sections():
    out = []
    for cat in EXAMPLE_CATEGORIES:
        items = []
        for ex in cat["examples"]:
            block = (
                '<div class="example-item">'
                f'<div class="ex-title">{ex["title"]}</div>'
                f'<div class="ex-desc">{ex["desc"]}</div>'
                f'{code_block(ex["cmd"])}'
            )
            if ex.get("note"):
                block += f'<div class="ex-note">💡 {ex["note"]}</div>'
            block += '</div>'
            items.append(block)
        out.append(
            f'<h3 id="ex-{cat["id"]}">{cat["icon"]} {cat["title"]}</h3>'
            f'<p>{cat["desc"]}</p>'
            f'<div class="example-list">{"".join(items)}</div>'
        )
    return "".join(out)


def build_flags_tables():
    out = []
    for grp in FLAGS:
        out.append(f'<div class="flag-group-title">{grp["group"]}</div>')
        out.append(
            '<table class="flag-table">'
            '<thead><tr><th>Flag</th><th>Description</th><th>Example</th></tr></thead>'
            '<tbody>'
        )
        for item in grp["items"]:
            out.append(
                f'<tr>'
                f'<td><code>{item["flag"]}</code></td>'
                f'<td>{item["desc"]}</td>'
                f'<td class="flag-ex"><code>{esc(item["ex"])}</code></td>'
                f'</tr>'
            )
        out.append('</tbody></table>')
    return "".join(out)


def build_lineage_grid():
    out = ['<div class="lineage-grid">']
    for l in LINEAGES:
        out.append(
            f'<div class="lineage-card" style="--lc: {l["color"]};">'
            f'<div class="lc-name">{l["name"]}</div>'
            f'<div class="lc-sig">{l["sig"]}</div>'
            '</div>'
        )
    out.append('</div>')
    return "".join(out)


# ---------------------------------------------------------------------------
# Main HTML builder
# ---------------------------------------------------------------------------
def build_html(out_path):
    generated = datetime.now().strftime("%Y-%m-%d")
    nav_html = "".join(
        f'<a href="{href}"{" class=\'active\'" if active else ""}>{label}</a>'
        for href, label, active in NAV_LINKS
    )
    toc_html = build_toc()
    flags_html = build_flags_tables()
    lineage_html = build_lineage_grid()
    examples_html = build_example_sections()

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CLI Manual — SAURUS</title>
<meta name="description" content="Complete user manual for the SAURUS command-line interface — query 139,257 S. aureus genomes from your terminal.">
<style>
{CSS}
</style>
</head>
<body>

<nav class="saurus-nav">
    <a class="brand" href="index.html">
        <span class="brand-emoji">🦖</span>
        <span class="brand-text">
            <span class="brand-name">SAURUS</span>
            <span class="brand-tagline">Staphylococcus aureus Unified Resource for Universal Surveillance</span>
        </span>
    </a>
    <div class="links">{nav_html}</div>
</nav>

<header class="manual-hero">
    <div class="manual-hero-inner">
        <h1>SAURUS CLI Manual</h1>
        <p class="hero-sub">Query 139,257 <em>S. aureus</em> genomes from your terminal.</p>
        <span class="hero-tag">v{CLI_VERSION}  ·  MIT License  ·  No installation required for the web UI</span>
        <div class="hero-cta">
            <a class="primary" href="#quickstart">🚀 Get Started</a>
            <a class="secondary" href="https://github.com/bbeckley-hub/saurus-cli" target="_blank">🐙 Clone the repo</a>
            <a class="secondary" href="#examples">📚 Browse examples</a>
        </div>
    </div>
</header>

<div class="manual-layout">

    {toc_html}

    <div class="manual-content">

        <!-- ============ QUICK START ============ -->
        <section class="manual-section" id="quickstart">
            <h2>🚀 Quick Start</h2>
            <p class="lead">
                The most common workflow is <strong>filter → verify → export</strong>. Here's the
                whole thing in four commands:
            </p>

            {code_block('saurus --lineage USA300 --count', 'Step 1: how many USA300 genomes exist globally?')}
            {code_block('saurus --lineage USA300 --country USA --source blood --count', 'Step 2: narrow to USA bloodstream isolates')}
            {code_block('saurus --lineage USA300 --country USA --source blood -o usa300_blood.txt', 'Step 3: export the accession list')}
            {code_block('datasets download genome accession --inputfile usa300_blood.txt --filename usa300_blood.zip', 'Step 4: download the genomes from NCBI')}

            <div class="callout success">
                <strong>That's it.</strong> Four commands, four steps — from "I want USA300 bloodstream
                isolates from the USA" to "I have the genome files on my laptop." No scripting, no
                intermediate files, no pipeline.
            </div>
        </section>

        <!-- ============ INSTALL ============ -->
        <section class="manual-section" id="install">
            <h2>📦 Installation</h2>
            <p>
                SAURUS CLI is a lightweight Python package. It requires <strong>Python 3.8+</strong>
                and <code>pandas</code>. No other dependencies. No root access.
            </p>

            <h3>Install from GitHub</h3>
            {code_block('git clone https://github.com/bbeckley-hub/saurus-cli.git')}
            {code_block('cd saurus-cli')}
            {code_block('pip install -e .')}

            <p>
                Once installed, the <code>saurus</code> command is available globally from any terminal.
            </p>

            <h3>Verify the install</h3>
            {code_block('saurus --version')}

            <div class="callout info">
                <strong>Data files:</strong> SAURUS CLI loads pre-computed TSVs from a local
                <code>data/</code> directory. If your data directory is elsewhere, use
                <code>--data-dir /path/to/data</code>.
            </div>
        </section>

        <!-- ============ FIRST QUERY ============ -->
        <section class="manual-section" id="first-query">
            <h2>🎯 Your First Query</h2>
            <p>
                Once installed, run the banner — it shows your version, affiliation, and a quick-start
                reference:
            </p>
            {code_block('saurus --examples', 'Show the full example gallery')}
            {code_block('saurus --about', 'Show author, affiliation, citations, and links')}

            <p>Now try your first real query — count USA300 genomes:</p>
            {code_block('saurus --lineage USA300 --count')}

            <p>You should see a number like <code>8,657</code>. That's the number of USA300
            genomes in the SAURUS database right now.</p>
        </section>

        <!-- ============ CORE FLAGS ============ -->
        <section class="manual-section" id="flags">
            <h2>🧾 Core Flags</h2>
            <p class="lead">
                Every flag can be combined with every other flag. The CLI applies them
                sequentially — each filter narrows the result set further.
            </p>
            {flags_html}
        </section>

        <!-- ============ LINEAGE SIGNATURES ============ -->
        <section class="manual-section" id="lineages">
            <h2>🏷️ Lineage Signatures</h2>
            <p class="lead">
                Typing an entire clone's genotype by hand is tedious. Use <code>--lineage</code> to
                apply a curated signature in one flag. Any flag you pass <em>alongside</em>
                <code>--lineage</code> will override the corresponding component.
            </p>
            {lineage_html}

            <h3>Override a component</h3>
            <p>
                For example, USA300 is globally distributed. Restrict it to Japan:
            </p>
            {code_block('saurus --lineage USA300 --country Japan --count')}

            <p>
                The USA300 signature supplies ST8, t008, SCCmec IV, agr I, capsule 5. Your
                <code>--country Japan</code> flag overrides nothing — it just adds a filter on top.
                But if you also passed <code>--spa t437</code>, that would override the signature's t008.
            </p>
        </section>

        <!-- ============ EXAMPLES GALLERY ============ -->
        <section class="manual-section" id="examples">
            <h2>📚 Example Queries</h2>
            <p class="lead">
                Copy-paste any of these commands. Each is a real query that returns real data.
                The full list is also available in the terminal with <code>saurus --examples</code>.
            </p>
            {examples_html}
        </section>

        <!-- ============ MULTI-FORMAT ============ -->
        <section class="manual-section" id="multi-format">
            <h2>📤 Multi-Format Output</h2>
            <p class="lead">
                Need both the metadata table <em>and</em> the accession list? Request both in one run.
            </p>

            <h3>Two files, one command</h3>
            {code_block('saurus --lineage USA300 --format tsv,accession -o usa300_results', 'produces usa300_results.tsv + usa300_results.txt')}

            <h3>Three formats at once</h3>
            {code_block('saurus --lineage EMRSA-15 --format tsv,json,accession -o emrsa15_results', 'produces usa300_results.tsv, .json, and .txt')}

            <h3>Which format should I use?</h3>
            <table class="flag-table">
                <thead>
                    <tr><th>Format</th><th>Best for</th><th>Extension</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>accession</code></td>
                        <td>Downstream NCBI datasets downloads, pipeline integration</td>
                        <td><code>.txt</code></td>
                    </tr>
                    <tr>
                        <td><code>tsv</code></td>
                        <td>Excel, R, pandas, Spotfire — tab-separated for easy parsing</td>
                        <td><code>.tsv</code></td>
                    </tr>
                    <tr>
                        <td><code>csv</code></td>
                        <td>Sharing with collaborators who prefer CSV, or MS Access</td>
                        <td><code>.csv</code></td>
                    </tr>
                    <tr>
                        <td><code>json</code></td>
                        <td>Web apps, jq, JavaScript, reproducible archival</td>
                        <td><code>.json</code></td>
                    </tr>
                </tbody>
            </table>

            <div class="callout info">
                <strong>Tip:</strong> If you pass <code>--output</code> without a recognized extension,
                SAURUS appends the correct one for each format. So
                <code>-o usa300_results</code> works — you don't have to add <code>.tsv</code>.
            </div>
        </section>

        <!-- ============ CONFIG FILES ============ -->
        <section class="manual-section" id="config">
            <h2>🔁 Reproducible Configs</h2>
            <p class="lead">
                For recurring surveillance tasks, save your query as a JSON config file and
                share it with collaborators. Anyone with the same dataset will reproduce your
                exact result set.
            </p>

            <h3>Create <code>usa100_surveillance.json</code></h3>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this)">📋 Copy</button>
                <pre><code>{{
  "lineage": "USA100",
  "country": "United States",
  "source": "blood",
  "mrsa": true,
  "year": "2020-2025",
  "format": "tsv,accession",
  "output": "usa100_surveillance_2020_2025"
}}</code></pre>
            </div>

            <h3>Run it</h3>
            {code_block('saurus --config usa100_surveillance.json')}

            <div class="callout success">
                <strong>Reproducibility guarantee:</strong> When you email that JSON file to a
                collaborator, they run the same command and get identical results — byte-for-byte,
                assuming the same SAURUS data release. This is exactly the reproducibility model
                that journals and funders are asking for.
            </div>

            <h3>Override a config value from the command line</h3>
            <p>
                Config values are defaults. Any command-line flag overrides the corresponding
                config field:
            </p>
            {code_block('saurus --config usa100_surveillance.json --country Japan', 'runs the same query but for Japan instead of the United States')}
        </section>

        <!-- ============ PIPELINE ============ -->
        <section class="manual-section" id="pipeline">
            <h2>⚙️ Pipeline Integration</h2>
            <p class="lead">
                SAURUS CLI is designed to fit into existing pipelines. It reads from
                <code>./data/</code>, writes to stdout, and exits silently when piped.
            </p>

            <h3>Pipe accessions directly into NCBI datasets</h3>
            {code_block('saurus --lineage USA300 | datasets download genome accession --inputfile /dev/stdin --filename usa300.zip', 'No intermediate file needed')}

            <h3>Chain with other tools</h3>
            {code_block('saurus --lineage USA300 -q | wc -l', 'Count how many genomes match (quiet mode, no banner)')}

            {code_block('saurus --lineage USA300 -q > accessions.txt && datasets download genome accession --inputfile accessions.txt --filename usa300.zip', 'Shell pipeline — download immediately')}

            <h3>Use in a Snakemake or Nextflow rule</h3>
            <p>Because <code>saurus</code> exits silently when piped and accepts <code>--quiet</code>,
            it can be called directly from any pipeline tool:</p>
            <div class="code-block">
                <button class="copy-btn" onclick="copyCode(this)">📋 Copy</button>
                <pre><code><span class="comment"># Snakemake rule</span>
rule download_usa300:
    output: "data/usa300_accessions.txt"
    shell:
        "saurus --lineage USA300 --country USA -q -o "</code></pre>
            </div>

            <div class="callout warn">
                <strong>Quiet mode matters:</strong> always pass <code>-q</code> when calling
                <code>saurus</code> from a pipeline or script. It suppresses the banner, quote,
                and marketing footer — so the only thing that reaches your stdout is the data.
            </div>
        </section>

        <!-- ============ TROUBLESHOOTING ============ -->
        <section class="manual-section" id="diagnostics">
            <h2>🐞 Troubleshooting</h2>

            <h3>Zero matches — but the query should work?</h3>
            <p>
                The most common reason a query returns 0 is that the genotype you're asking
                for <em>doesn't exist in nature</em>. For example, ST5 + agr I + capsule 8 is
                impossible — USA100 is agr II + capsule 5. Run with <code>--debug</code> to see
                exactly where the count drops:
            </p>
            {code_block('saurus --st 5 --agr I --capsule 8 --debug --count', 'shows which filter is the culprit')}

            <p>You'll see something like:</p>
            <div class="code-block">
                <pre><code><span class="comment">  [debug] Initial load: 139,257 rows</span>
<span class="comment">  [debug] --st 5: 14,930 rows</span>
<span class="comment">  [debug] --agr I: 0 rows       ← the culprit</span></code></pre>
            </div>

            <h3>Master file not found</h3>
            <p>
                The CLI needs a master TSV at <code>data/mrsa/mrsa_all.tsv</code>. If it's missing,
                regenerate it:
            </p>
            {code_block('python scripts/build_master_tsv.py')}

            <h3>BrokenPipeError when piping to head / less</h3>
            <p>
                This is <em>not a bug</em> — it's Python's default behavior. SAURUS CLI suppresses
                it automatically since v0.2. If you're on an older version, upgrade:
            </p>
            {code_block('pip install --upgrade -e .')}

            <h3>Command not found: saurus</h3>
            <p>The package wasn't installed correctly. Try reinstalling with the dash:</p>
            {code_block('pip install -e .', 'note: it is "-e .", not "e ." — the dash matters!')}

            <h3>Still stuck?</h3>
            <p>
                Open an issue at
                <a href="https://github.com/bbeckley-hub/saurus/issues" target="_blank">github.com/bbeckley-hub/saurus/issues</a>
                — include your terminal command and the <code>--debug</code> output.
            </p>
        </section>

        <!-- ============ CLI COMMANDS ============ -->
        <section class="manual-section" id="cli-commands">
            <h2>💻 Built-in CLI Commands</h2>
            <p class="lead">
                The CLI documents itself. You don't have to remember the manual.
            </p>

            <table class="flag-table">
                <thead>
                    <tr><th>Command</th><th>What it does</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>saurus</code></td>
                        <td>Bare invocation — shows banner, help, and a quick-start hint</td>
                    </tr>
                    <tr>
                        <td><code>saurus --examples</code></td>
                        <td>Full gallery of example queries (same as this manual's gallery)</td>
                    </tr>
                    <tr>
                        <td><code>saurus --about</code></td>
                        <td>Author, affiliation, citations, and links</td>
                    </tr>
                    <tr>
                        <td><code>saurus --help</code></td>
                        <td>Formal argparse help — full flag reference</td>
                    </tr>
                    <tr>
                        <td><code>saurus --version</code></td>
                        <td>Version number</td>
                    </tr>
                </tbody>
            </table>

            <div class="callout info">
                <strong>Pro tip:</strong> Try <code>saurus --examples</code> right now — it prints
                the same gallery you see on this page, with rotating science quotes at the bottom.
            </div>
        </section>

        <!-- ============ SUPPORT ============ -->
        <section class="manual-section" style="background: linear-gradient(135deg, #0a1628 0%, #1e293b 100%); color: white; border-left: 6px solid var(--gold);">
            <h2 style="color: var(--gold); border-bottom-color: rgba(212,175,55,0.3);">⭐ Support the Project</h2>
            <p style="color: #cbd5e1; font-size: 1.05em; line-height: 1.75;">
                SAURUS CLI is developed and maintained by
                <strong style="color:#f8fafc;">{CLI_AUTHOR}</strong>
                ({CLI_AFFILIATION}) as an independent, unfunded project.
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 20px;">
                <div style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 18px 20px;">
                    <div style="font-size: 1.8em; margin-bottom: 8px;">⭐</div>
                    <div style="font-weight: 800; font-size: 1em; margin-bottom: 6px; color: var(--gold);">Star the repo</div>
                    <div style="font-size: 0.88em; color: #cbd5e1; line-height: 1.5; margin-bottom: 12px;">
                        A GitHub star helps other researchers discover SAURUS.
                    </div>
                    <a href="https://github.com/bbeckley-hub/saurus" target="_blank"
                       style="display:inline-block;padding:8px 16px;background:var(--gold);color:var(--navy);border-radius:8px;text-decoration:none;font-weight:800;font-size:0.85em;">
                        ⭐ Star on GitHub
                    </a>
                </div>
                <div style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 18px 20px;">
                    <div style="font-size: 1.8em; margin-bottom: 8px;">🐛</div>
                    <div style="font-weight: 800; font-size: 1em; margin-bottom: 6px; color: var(--gold);">Report bugs</div>
                    <div style="font-size: 0.88em; color: #cbd5e1; line-height: 1.5; margin-bottom: 12px;">
                        Found an error? Open an issue — every report improves the resource.
                    </div>
                    <a href="https://github.com/bbeckley-hub/saurus/issues" target="_blank"
                       style="display:inline-block;padding:8px 16px;background:rgba(255,255,255,0.08);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:8px;text-decoration:none;font-weight:700;font-size:0.85em;">
                        🐛 Open an issue
                    </a>
                </div>
                <div style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 18px 20px;">
                    <div style="font-size: 1.8em; margin-bottom: 8px;">📚</div>
                    <div style="font-weight: 800; font-size: 1em; margin-bottom: 6px; color: var(--gold);">Cite us</div>
                    <div style="font-size: 0.88em; color: #cbd5e1; line-height: 1.5; margin-bottom: 12px;">
                        Citations are the strongest signal that open tools deserve funding.
                    </div>
                    <a href="about.html#citation"
                       style="display:inline-block;padding:8px 16px;background:rgba(255,255,255,0.08);color:white;border:1px solid rgba(255,255,255,0.2);border-radius:8px;text-decoration:none;font-weight:700;font-size:0.85em;">
                        📚 See citation
                    </a>
                </div>
            </div>
        </section>

    </div>
</div>

<footer class="saurus-footer">
    <div class="footer-line full-name">
        <strong style="color:#d4af37;">SAURUS</strong> — Staphylococcus aureus Unified Resource for Universal Surveillance
    </div>
    <div class="footer-line">
        CLI v{CLI_VERSION} · {CLI_AFFILIATION} · MIT License
    </div>
    <div class="footer-line">
        <a href="https://github.com/bbeckley-hub/saurus-cli">CLI Repo</a> ·
        <a href="https://github.com/bbeckley-hub/saurus">Web Repo</a> ·
        <a href="mailto:brownbeckley94@gmail.com">Contact</a> ·
        Updated {generated}
    </div>
</footer>

<script>
function copyCode(btn) {{
    const pre = btn.nextElementSibling;
    const text = pre.innerText.replace(/^\\$ /gm, '').replace(/^# .*$/gm, '').trim();
    navigator.clipboard.writeText(text).then(() => {{
        const original = btn.textContent;
        btn.textContent = '✓ Copied';
        btn.classList.add('copied');
        setTimeout(() => {{
            btn.textContent = original;
            btn.classList.remove('copied');
        }}, 1500);
    }});
}}

// Smooth-scroll TOC highlighting
const sections = document.querySelectorAll('.manual-section');
const tocLinks = document.querySelectorAll('.toc a');
const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
        if (entry.isIntersecting) {{
            const id = entry.target.id;
            tocLinks.forEach(a => {{
                a.style.background = a.getAttribute('href') === '#' + id ? 'rgba(212,175,55,0.15)' : '';
                a.style.color = a.getAttribute('href') === '#' + id ? 'var(--navy)' : '';
                a.style.fontWeight = a.getAttribute('href') === '#' + id ? '700' : '';
            }});
        }}
    }});
}}, {{ rootMargin: '-100px 0px -80% 0px' }});
sections.forEach(s => observer.observe(s));
</script>

</body>
</html>'''

    out_path.write_text(html, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Generate the SAURUS CLI Manual page")
    ap.add_argument("-o", "--output", default="../docs/manual.html",
                    help="Output HTML path (default: ../docs/manual.html)")
    args = ap.parse_args()

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SAURUS CLI MANUAL GENERATOR")
    print("=" * 60)

    build_html(out_path)
    print(f"✅ Written: {out_path} ({out_path.stat().st_size / 1024:.0f} KB)")
    print(f"   Example categories: {len(EXAMPLE_CATEGORIES)}")
    print(f"   Total examples: {sum(len(c['examples']) for c in EXAMPLE_CATEGORIES)}")
    print(f"   Lineage signatures: {len(LINEAGES)}")
    print(f"   Flag groups: {len(FLAGS)}")


if __name__ == "__main__":
    main()
