#!/usr/bin/env python3
"""
build_master_tsv.py — Generate a unified master TSV for SAURUS CLI.
Merges MLST, spa, SCCmec (CGE & RPet), agr, capsule, and metadata.
"""

import pandas as pd
import sys
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUT_FILE = DATA_DIR / "mrsa_all.tsv"

def clean_acc(df, col='accession'):
    """Remove .fna and similar extensions from accession columns."""
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(r'\.(fna|fasta|fa)$', '', regex=True)
    return df

def main():
    print("Building master TSV...")
    
    # 1. Load and clean MLST
    df_mlst = pd.read_csv(DATA_DIR / "mlst" / "mlst_all.tsv", sep="\t", dtype=str)
    df_mlst = clean_acc(df_mlst)
    df_mlst = df_mlst.rename(columns={'ST': 'mlst_st'})
    
    # Load ST -> CC mapping
    cc_path = DATA_DIR / "mlst" / "cc.txt"
    if cc_path.exists():
        df_cc = pd.read_csv(cc_path, sep="\t", comment="#", names=["assembly", "CC", "ST"], dtype=str)
        df_cc['ST_clean'] = df_cc['ST'].str.replace('ST', '')
        st_to_cc = df_cc.groupby('ST_clean')['CC'].agg(lambda x: x.mode()[0] if not x.mode().empty else 'NA').to_dict()
        df_mlst['mlst_cc'] = df_mlst['mlst_st'].map(st_to_cc).fillna('NA')
    else:
        df_mlst['mlst_cc'] = 'NA'

    # 2. Load and clean spa
    df_spa = pd.read_csv(DATA_DIR / "spa" / "spa_all.tsv", sep="\t", dtype=str)
    df_spa = clean_acc(df_spa)
    df_spa = df_spa.rename(columns={'spa_Type': 'spa_type'})

    # 3. Load and clean SCCmec (CGE)
    df_cge = pd.read_csv(DATA_DIR / "sccmec" / "sccmec_cge_all.tsv", sep="\t", dtype=str)
    df_cge = clean_acc(df_cge)
    df_cge = df_cge.rename(columns={'SCCmec_Type': 'sccmec_cge', 'MRSA_Status': 'mrsa_cge'})

    # 4. Load and clean SCCmec (RPet)
    df_rpet = pd.read_csv(DATA_DIR / "sccmec" / "sccmec_rpet_all.tsv", sep="\t", dtype=str)
    df_rpet = clean_acc(df_rpet)
    df_rpet = df_rpet.rename(columns={'sccmec_type': 'sccmec_rpet', 'mrsa_status': 'mrsa_rpet'})

    # 5. Load and clean agr
    df_agr = pd.read_csv(DATA_DIR / "agr" / "agr_all.tsv", sep="\t", dtype=str)
    df_agr = clean_acc(df_agr)
    df_agr = df_agr.rename(columns={'agr_Type': 'agr_type'})

    # 6. Load and clean Capsule
    df_capsule = pd.read_csv(DATA_DIR / "capsule" / "capsule_all.tsv", sep="\t", dtype=str)
    df_capsule = clean_acc(df_capsule)
    df_capsule = df_capsule.rename(columns={'cap_type': 'capsule_type'})

    # 7. Load and clean Metadata
    df_meta = pd.read_csv(DATA_DIR / "metadata" / "metadata.tsv", sep="\t", dtype=str)
    df_meta = clean_acc(df_meta)
    # Select only the columns we want in the master file
    meta_cols = ['accession', 'country', 'country_raw', 'source', 'source_raw', 
                 'host', 'year', 'strain', 'biosample', 'bioproject']
    df_meta = df_meta[[c for c in meta_cols if c in df_meta.columns]]

    # --- Merge everything ---
    print("Merging datasets...")
    df = df_mlst[['accession', 'mlst_st', 'mlst_cc']]
    df = df.merge(df_spa[['accession', 'spa_type']], on='accession', how='outer')
    df = df.merge(df_cge[['accession', 'sccmec_cge', 'mrsa_cge']], on='accession', how='outer')
    df = df.merge(df_rpet[['accession', 'sccmec_rpet', 'mrsa_rpet']], on='accession', how='outer')
    df = df.merge(df_agr[['accession', 'agr_type']], on='accession', how='outer')
    df = df.merge(df_capsule[['accession', 'capsule_type']], on='accession', how='outer')
    df = df.merge(df_meta, on='accession', how='outer')

    # Resolve MRSA Status (CGE takes precedence, then RPet)
    df['mrsa_status'] = df['mrsa_cge'].fillna(df['mrsa_rpet']).fillna('Unknown')
    
    # Drop the intermediate MRSA columns
    df = df.drop(columns=['mrsa_cge', 'mrsa_rpet'])

    # Fill NaN with empty strings for cleaner output
    df = df.fillna('')

    print(f"Saving to {OUT_FILE}...")
    df.to_csv(OUT_FILE, sep="\t", index=False)
    print(f"✅ Master TSV created: {len(df):,} rows, {len(df.columns)} columns.")

if __name__ == "__main__":
    main()
