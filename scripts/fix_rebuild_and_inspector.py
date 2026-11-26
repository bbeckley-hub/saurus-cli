#!/usr/bin/env python3
"""
fix_rebuild_and_inspector.py -- one-shot patcher for the VFDB rebuild workflow.

1) ~/saurus/scripts/rebuild_gene_long_table.py -- adds norm_ident() so
   single-value identity cells are float-normalized exactly like the
   original melt (100.00 -> 100, 93.20 -> 93.2); multi-hit strings stay raw.
   This makes the rebuilt table byte-identical to the old truncated prefix.

2) scripts/inspect_annotations.py -- the 2^20 truncation flag now fires only
   at exactly the Excel 1,048,576-row cap, so the rebuilt 7.4M-row VFDB
   table is no longer flagged.

Idempotent: safe to run twice.
"""
from pathlib import Path

HELP = '''
def norm_ident(v):
    """Original melt convention: single-value cells float-normalized
    (100.00->100, 93.20->93.2); multi-hit strings kept raw."""
    if ";" in v or v == ".":
        return v
    f = float(v)
    return str(int(f)) if f.is_integer() else str(f)
'''

def patch(path, replacements):
    p = Path(path)
    if not p.exists():
        print(f"  !! {path} not found - skipped")
        return
    src = p.read_text()
    orig = src
    for old, new, what in replacements:
        if new in src:
            print(f"  ok: {what} (already applied)")
        elif old in src:
            src = src.replace(old, new, 1)
            print(f"  ok: {what}")
        else:
            print(f"  !! {what}: pattern not found")
    if src != orig:
        p.write_text(src)
        print(f"  saved {path}")

patch(str(Path.home() / "saurus/scripts/rebuild_gene_long_table.py"), [
    ("def split_value(s, k):", HELP.strip() + "\n\n\ndef split_value(s, k):",
     "add norm_ident() helper"),
    ("{v.count(';') + 1}\\t{v}", "{v.count(';') + 1}\\t{norm_ident(v)}",
     "normalize identities on emit"),
])

patch("scripts/inspect_annotations.py", [
    ("if len(all_df) >= (1 << 20) - 64:", "if len(all_df) == (1 << 20) - 1:",
     "truncation flag exactness"),
])

print("\nDone. Now re-run the rebuild -> prefix check -> redeploy.")
