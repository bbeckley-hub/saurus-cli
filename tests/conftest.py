import contextlib
import gzip
import io
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


MASTER_COLUMNS = [
    "accession", "mlst_st", "mlst_cc", "spa_type", "sccmec_cge", "sccmec_rpet",
    "agr_type", "capsule_type", "mrsa_status", "country", "country_raw",
    "source", "source_raw", "host", "year", "biosample", "bioproject",
    "sra_run", "sra_experiment",
]


def _tsv(path: Path, df: pd.DataFrame):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as fh:
        df.to_csv(fh, sep="\t", index=False)


def make_data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    rows = []
    for i in range(40):
        st = "5" if i < 20 else ("8" if i < 36 else "99")
        sccmec = "II" if i < 10 else "IV"
        spa = "t002" if i < 10 else "t008"
        country = "USA" if i % 2 == 0 else "Denmark"
        rows.append({
            "accession": f"GCA_{i:011d}.1" if i < 30 else f"GCF_{i:011d}.1",
            "mlst_st": st,
            "mlst_cc": None if (i < 5 or st == "99") else ("CC5" if st == "5" else "CC8"),
            "spa_type": spa,
            "sccmec_cge": f"SCCmec_Type_{sccmec}",
            "sccmec_rpet": f"SCCmec_Type_{sccmec}",
            "agr_type": "I" if i % 3 else "II",
            "capsule_type": "Capsule Type 5" if i < 30 else "Capsule Type 8",
            "mrsa_status": "MRSA" if i < 25 else "MSSA",
            "country": country,
            "country_raw": f"{country}:City",
            "source": "blood" if i % 4 == 0 else "nasal swab",
            "source_raw": "Blood" if i % 4 == 0 else "Nasal swab",
            "host": "Homo sapiens",
            "year": "2020" if i % 2 else "2019",
            "biosample": f"SAMN{i:07d}",
            "bioproject": f"PRJNA{i % 5:06d}",
            "sra_run": f"SRR{i:07d}" if i < 20 else "NA",
            "sra_experiment": f"SRX{i:07d}" if i < 20 else "NA",
        })
    master = pd.DataFrame(rows)
    _tsv(data / "mrsa" / "mrsa_all.tsv.gz", master)

    mlst = master[["accession", "mlst_st"]].copy()
    mlst["accession"] = mlst["accession"].str.replace(r"\.1$", ".1.fna", regex=True)
    mlst = mlst.rename(columns={"mlst_st": "ST"})
    _tsv(data / "mlst" / "mlst_all.tsv.gz", mlst)

    cc = pd.DataFrame({
        "assembly": master["accession"].head(20),
        "CC": ["CC5"] * 10 + ["CC8"] * 10,
        "ST": ["ST5"] * 10 + ["ST8"] * 10,
    })
    (data / "mlst").mkdir(parents=True, exist_ok=True)
    with gzip.open(data / "mlst" / "cc.txt.gz", "wt") as fh:
        fh.write("#Assembly code\tCC\tMLST ST\n")
        cc.to_csv(fh, sep="\t", index=False, header=False)

    amr = pd.DataFrame({
        "accession": [f"GCA_{i:011d}.1.fna" for i in range(0, 30)],
        "gene": ["mecA_6"] * 15 + ["mecA_7"] * 5 + ["tet(M)_13"] * 10,
        "num_hits": [1] * 30,
        "identities": [100] * 30,
        "database": ["AMR"] * 30,
    })
    _tsv(data / "gene_annotation" / "amr_all.tsv.gz", amr)
    _tsv(data / "gene_annotation" / "amr_gene_freq.tsv.gz", pd.DataFrame({
        "gene": ["mecA_6", "mecA_7", "tet(M)_13"],
        "database": ["AMR"] * 3,
        "num_genomes": [20, 5, 10],
        "prevalence_pct": [50.0, 12.5, 25.0],
        "num_occurrences": [20, 5, 10],
    }))
    vfdb = pd.DataFrame({
        "accession": [f"GCA_{i:011d}.1.fna" for i in range(4)],
        "gene": ["lukS-PV_1"] * 4,
        "num_hits": [1] * 4,
        "identities": [100] * 4,
        "database": ["VFDB"] * 4,
    })
    _tsv(data / "gene_annotation" / "vfdb_all.tsv.gz", vfdb)
    _tsv(data / "gene_annotation" / "vfdb_gene_freq.tsv.gz", pd.DataFrame({
        "gene": ["lukS-PV_1"], "database": ["VFDB"],
        "num_genomes": [4], "prevalence_pct": [10.0], "num_occurrences": [4],
    }))
    plasmid = pd.DataFrame({
        "accession": [f"GCA_{i:011d}.1.fna" for i in range(0, 20, 2)],
        "gene": ["rep21_3_rep(pS0385)"] * 10,
        "num_hits": [1] * 10,
        "identities": [100] * 10,
        "database": ["Plasmid"] * 10,
    })
    _tsv(data / "gene_annotation" / "plasmid_all.tsv.gz", plasmid)

    (data / "DATA_VERSION").write_text("v0.3.0-fixture\n")
    return data


def write_config(tmp_path: Path, payload: dict) -> str:
    cfg = tmp_path / "query.json"
    cfg.write_text(json.dumps(payload))
    return str(cfg)


def run_cli(data_dir: Path, *argv):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import saurus_cli
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            saurus_cli.main(list(argv) + ["--data-dir", str(data_dir), "--quiet"])
        except SystemExit as e:
            code = e.code
        else:
            code = 0
    return code, out.getvalue(), err.getvalue()


def count(data_dir: Path, *argv):
    code, out, err = run_cli(data_dir, *argv, "--count")
    assert code == 0, err
    return int(out.strip().splitlines()[-1].replace(",", ""))
