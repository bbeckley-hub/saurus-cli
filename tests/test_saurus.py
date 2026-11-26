"""Regression tests addressing Reviewer 1 and Reviewer 2 findings, plus
release-gate tests against the published v1.1.0 data bundle (must be run with
the data directory exported as SAURUS_DATA_DIR)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import make_data_dir, write_config, run_cli, count  # noqa: E402
import saurus_cli  # noqa: E402


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    return make_data_dir(tmp_path_factory.mktemp("fixture"))


# ---------------------------------------------------------------------------
# Reviewer 1, point 1 (a): lineage in a JSON config must expand like --lineage
# ---------------------------------------------------------------------------

def test_config_lineage_key_is_expanded(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"lineage": "USA100", "count": True})
    code, out, err = run_cli(data_dir, "--config", cfg)
    assert code == 0, err
    from conftest import count as _count
    assert count(data_dir, "--lineage", "USA100") == count(data_dir, "--config", cfg)


def test_config_lineage_yaml_alias_and_casing(data_dir, tmp_path):
    for spelling in ("lineage", "LINEAGE", "Lineage"):
        cfg = write_config(tmp_path, {spelling: "USA100", "count": True})
        code, out, err = run_cli(data_dir, "--config", cfg)
        assert code == 0, err
        assert out.strip().splitlines()[-1].replace(",", "") != "0"


# ---------------------------------------------------------------------------
# Reviewer 2: config keys silently dropped ("SCCmec" written for --sccmec)
# ---------------------------------------------------------------------------

def test_config_sccmec_casing_is_accepted(data_dir, tmp_path):
    cfg_key = write_config(tmp_path, {"SCCmec": "II", "count": True})
    cfg_flag = write_config(tmp_path, {"sccmec": "II", "count": True})
    assert count(data_dir, "--config", cfg_key) == count(data_dir, "--config", cfg_flag)
    assert count(data_dir, "--config", cfg_key) == count(data_dir, "--sccmec", "II")


def test_config_unknown_key_is_fatal(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"scc": "5", "count": True})
    code, out, err = run_cli(data_dir, "--config", cfg)
    assert code == 1
    assert "Unknown config key 'scc'" in err


def test_config_lineage_plus_filters_match_cli(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"country": "USA", "count": True})
    a = count(data_dir, "--config", cfg, "--lineage", "USA100")
    b = count(data_dir, "--lineage", "USA100", "--country", "USA")
    assert a == b


# ---------------------------------------------------------------------------
# Reviewer 1, point 1 (b): unknown gene + --any returned the whole master table
# ---------------------------------------------------------------------------

def test_unknown_gene_any_mode_is_fatal(data_dir, tmp_path):
    code, out, err = run_cli(data_dir, "--amr", "NOT_A_REAL_GENE_9Z", "--any", "--count")
    assert code == 1
    assert "not found" in err


def test_unknown_gene_all_mode_is_fatal_not_silent_zero(data_dir):
    code, out, err = run_cli(data_dir, "--amr", "NOT_A_REAL_GENE_9Z", "--count")
    assert code == 1
    assert "not found" in err


def test_any_across_modules_is_union_not_intersection(data_dir):
    any_count = count(data_dir, "--amr", "mecA", "--vfdb", "lukS-PV", "--any")
    amr_only = count(data_dir, "--amr", "mecA")
    vfdb_only = count(data_dir, "--vfdb", "lukS-PV")
    assert any_count == amr_only + vfdb_only - count(
        data_dir, "--amr", "mecA", "--vfdb", "lukS-PV"
    )
    assert any_count >= max(amr_only, vfdb_only)


# ---------------------------------------------------------------------------
# Gene matching must be anchored (no substring inflation)
# ---------------------------------------------------------------------------

def test_base_name_matches_alleles(data_dir):
    assert count(data_dir, "--amr", "mecA") == 20
    assert count(data_dir, "--amr", "tetM") == 10
    assert count(data_dir, "--plasmid", "rep21") == 10


def test_no_substring_false_positives(data_dir):
    code, out, err = run_cli(data_dir, "--amr", "ecA", "--count")
    assert code == 1


def test_gene_query_never_returns_more_than_matching_annotation(data_dir):
    total = count(data_dir, "--mrsa")
    assert count(data_dir, "--amr", "mecA") <= total


# ---------------------------------------------------------------------------
# Reviewer 2: --cc silently dropped genomes without a CC assignment
# ---------------------------------------------------------------------------

def test_cc_warns_about_unmapped_genomes(data_dir):
    code, out, err = run_cli(data_dir, "--cc", "5", "--country", "USA", "--count")
    assert code == 0
    assert "no clonal-complex assignment" in err


def test_cc_filter_excludes_unmapped_rows_deterministically(data_dir):
    assert count(data_dir, "--st", "5", "--country", "USA") == 10
    assert count(data_dir, "--cc", "5", "--country", "USA") == 10
    assert count(data_dir, "--st", "8", "--country", "USA") == 8
    assert count(data_dir, "--cc", "8", "--country", "USA") == 8
    assert count(data_dir, "--st", "99", "--country", "USA") == 2
    assert count(data_dir, "--cc", "99", "--country", "USA") == 0


# ---------------------------------------------------------------------------
# Missing annotation must be distinguished from genuine absence
# ---------------------------------------------------------------------------

def test_sparse_gene_table_triggers_truncation_warning(data_dir):
    code, out, err = run_cli(data_dir, "--vfdb", "lukS-PV", "--count")
    assert code == 0
    assert "truncated data release" in err
    assert "missing annotation, not confirmed absence" in err


def test_dense_gene_table_does_not_trigger_warning(data_dir):
    code, out, err = run_cli(data_dir, "--amr", "mecA", "--count")
    assert code == 0
    assert "truncated data release" not in err


# ---------------------------------------------------------------------------
# General regression: signature == expanded flags; multi-format consistency
# ---------------------------------------------------------------------------

def test_lineage_signature_equals_expanded_flags(data_dir):
    sig = saurus_cli.LINEAGE_SIGNATURES["USA100"]
    flags = []
    for k, v in sig.items():
        flags += [f"--{k}", v]
    assert count(data_dir, "--lineage", "USA100") == count(data_dir, *flags)


def test_multi_format_output_is_consistent(data_dir, tmp_path):
    out = tmp_path / "query_out"
    code, _, err = run_cli(
        data_dir, "--lineage", "USA100", "--format", "tsv,accession,json",
        "--output", str(out)
    )
    assert code == 0, err
    tsv = (tmp_path / "query_out.tsv").read_text().strip().splitlines()[1:]
    acc = (tmp_path / "query_out.txt").read_text().splitlines()
    js = json.loads((tmp_path / "query_out.json").read_text())
    assert len(tsv) == len(acc) == len(js)


# ---------------------------------------------------------------------------
# Release gate: golden counts against the published v1.1.0 data bundle
# (argus-data, saurus-data-v1.1.0). All values verified with
# smoke_test_v040.sh on the released bundle. Gene counts are MASTER-SPACE
# (134,273-genome denominator); the catalogue/freq-table values are
# annotation-space (98,948 VFDB-annotated genomes) and are pinned separately
# below.
# ---------------------------------------------------------------------------

pytestmark_env = "SAURUS_DATA_DIR"

GOLDEN_V110 = [
    # typing / metadata (master space)
    (["--lineage", "USA300"], 10448),
    (["--lineage", "USA100"], 3342),
    (["--lineage", "USA100", "--country", "USA", "--source", "blood"], 341),
    (["--st", "5", "--sccmec", "II", "--agr", "II", "--capsule", "5",
      "--spa", "t002", "--source", "blood", "--country", "USA"], 341),
    (["--st", "5", "--sccmec", "II", "--agr", "II", "--mrsa"], 7133),
    (["--lineage", "USA300", "--country", "USA", "--source", "blood"], 1195),
    (["--mrsa"], 80220),
    (["--cc", "8"], 29135),
    (["--cc", "8", "--mrsa"], 24161),
    (["--has-sra"], 22322),
    (["--mrsa", "--country", "Ghana"], 102),
    (["--cc", "398", "--mrsa", "--country", "Denmark"], 328),
    (["--lineage", "USA300", "--source", "blood", "--year", "2005-2015"], 483),
    (["--st", "152"], 749),
    # lineage shortcuts
    (["--lineage", "USA400"], 41),
    (["--lineage", "USA500"], 831),
    (["--lineage", "USA700"], 70),
    (["--lineage", "USA800"], 125),
    (["--lineage", "EMRSA-15", "--country", "United Kingdom"], 654),
    (["--lineage", "EMRSA-16", "--country", "United Kingdom"], 190),
    (["--lineage", "Bengal_Bay"], 380),
    (["--lineage", "ST152"], 16),
    # gene queries (master space)
    (["--amr", "mecA"], 45432),
    (["--amr", "mecA", "--lineage", "USA300"], 5086),
    (["--amr", "mecA,tetM", "--any"], 45915),
    (["--amr", "mecA,ermB"], 1383),
    (["--vfdb", "lukS-PV"], 14856),
    (["--vfdb", "lukF-PV"], 53293),
    (["--st", "8", "--vfdb", "lukS-PV"], 6919),
    (["--plasmid", "rep21"], 14039),
]


@pytest.mark.parametrize("argv,expected", GOLDEN_V110)
def test_golden_counts_v110_data(argv, expected):
    import os
    real_data = os.environ.get(pytestmark_env, "")
    fixture_marker = os.environ.get("SAURUS_TEST_FIXTURE_ONLY", "")
    if not real_data or fixture_marker:
        pytest.skip("requires the real v1.1.0 data bundle in SAURUS_DATA_DIR")
    data = Path(real_data)
    from conftest import count as _count
    assert _count(data, *argv) == expected


# ---------------------------------------------------------------------------
# Two-denominators gate: the freq catalogues count in ANNOTATION space
# (Shelenkov et al. 2025 snapshot; 98,948 VFDB-annotated GCA accessions,
# larger than the 134,273-genome master), so catalogue prevalence values
# cited in the manuscript must never be compared with CLI master-space
# counts. These pins freeze the annotation-space values.
# ---------------------------------------------------------------------------

def _real_data_dir():
    import os
    real = os.environ.get(pytestmark_env, "")
    if not real or os.environ.get("SAURUS_TEST_FIXTURE_ONLY"):
        pytest.skip("requires the real v1.1.0 data bundle in SAURUS_DATA_DIR")
    return Path(real)


def test_freq_catalogue_annotation_space_pins():
    import pandas as pd
    f = _real_data_dir() / "gene_annotation" / "vfdb_gene_freq.tsv.gz"
    df = pd.read_csv(f, sep="\t", dtype=str, header=None, skiprows=1)
    lukS = df[df.iloc[:, 0] == "lukS-PV"]
    lukF = df[df.iloc[:, 0] == "lukF-PV"]
    assert len(lukS) == 1 and len(lukF) == 1
    assert int(lukS.iloc[0, 2]) == 19002
    assert int(lukF.iloc[0, 2]) == 70301


def test_amr_freq_catalogue_meca_annotation_space_pins():
    import gzip
    d = _real_data_dir() / "gene_annotation"

    allele_sum = 0
    with gzip.open(d / "amr_gene_freq.tsv.gz", "rt") as fh:
        next(fh)
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if parts[0].startswith("mecA"):
                allele_sum += int(parts[2])
    assert allele_sum == 60726, "allele-level freq sum (double-counts multi-allele genomes)"

    accs = set()
    with gzip.open(d / "amr_all.tsv.gz", "rt") as fh:
        next(fh)
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if parts[1].startswith("mecA"):
                accs.add(parts[0].removesuffix(".fna"))
    assert len(accs) == 60609, "unique annotated genomes carrying any mecA allele"


def test_vfdb_annotated_universe_size():
    import gzip
    f = _real_data_dir() / "gene_annotation" / "vfdb_all.tsv.gz"
    accs = set()
    with gzip.open(f, "rt") as fh:
        next(fh)
        for line in fh:
            accs.add(line.split("\t", 1)[0].removesuffix(".fna"))
    assert len(accs) == 98948


def test_has_sra_above_reviewer_threshold():
    from conftest import count as _count
    assert _count(_real_data_dir(), "--has-sra") > 20000


def test_year_single_year_within_range():
    from conftest import count as _count
    data = _real_data_dir()
    single = _count(data, "--lineage", "USA300", "--source", "blood", "--year", "2010")
    window = _count(data, "--lineage", "USA300", "--source", "blood", "--year", "2005-2015")
    assert 0 < single <= window == 483


def test_numeric_year_config_matches_flag_on_release_data(tmp_path):
    from conftest import count as _count, write_config as _cfg
    data = _real_data_dir()
    cfg = _cfg(tmp_path, {"year": 2010, "count": True})
    assert _count(data, "--config", cfg) == _count(data, "--year", "2010")


# ---------------------------------------------------------------------------
# Reviewer 2, section 2.5: numeric "year" in a config crashed; CLI flags were
# silently overridden by config values
# ---------------------------------------------------------------------------

def test_config_numeric_year_is_coerced(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"year": 2019, "count": True})
    code, out, err = run_cli(data_dir, "--config", cfg)
    assert code == 0, err
    assert count(data_dir, "--year", "2019") == int(out.strip().splitlines()[-1])


def test_config_year_range_string_still_works(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"year": "2019-2020", "count": True})
    assert count(data_dir, "--config", cfg) == 40


def test_cli_flags_override_colliding_config_values(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"st": "5", "count": True})
    code, out, err = run_cli(data_dir, "--config", cfg, "--st", "8")
    assert code == 0, err
    assert "overrides config for 'st'" in err
    assert int(out.strip().splitlines()[-1]) == count(data_dir, "--st", "8")


def test_cli_flags_apply_when_not_in_config(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"country": "Denmark", "count": True})
    code, out, err = run_cli(data_dir, "--config", cfg, "--year", "2019")
    assert code == 0, err
    assert int(out.strip().splitlines()[-1]) == 0
    assert "overrides config" not in err


def test_cli_lineage_flag_overrides_config_country(data_dir, tmp_path):
    cfg = write_config(tmp_path, {"lineage": "USA300", "country": "Japan", "count": True})
    n = count(data_dir, "--config", cfg, "--country", "USA")
    assert n == count(data_dir, "--lineage", "USA300", "--country", "USA")


def test_numeric_st_and_cc_in_config_are_coerced(data_dir, tmp_path):
    cfg_num = write_config(tmp_path, {"st": 5, "count": True})
    cfg_str = write_config(tmp_path, {"st": "5", "count": True})
    assert count(data_dir, "--config", cfg_num) == count(data_dir, "--config", cfg_str)
    cfg_cc = write_config(tmp_path, {"cc": 5, "count": True})
    assert count(data_dir, "--config", cfg_cc) == count(data_dir, "--cc", "5")


# ---------------------------------------------------------------------------
# Reviewer 2, section 2.6: country matching was substring-based
# (--country Oman returned Romania; --country India matched Indiana)
# ---------------------------------------------------------------------------

def test_country_match_is_not_substring(data_dir):
    assert count(data_dir, "--country", "Denmark") == 20
    assert count(data_dir, "--country", "Den") == 0
    assert count(data_dir, "--country", "omani") == 0


def test_country_case_insensitive_and_raw_prefix(data_dir):
    assert count(data_dir, "--country", "usa") == 20
    assert count(data_dir, "--country", "USA:City") == 20
    assert count(data_dir, "--country", "USA") == 20


# ---------------------------------------------------------------------------
# Reviewer 2, section 3: saurus init refused to switch version with -v
# ---------------------------------------------------------------------------

def test_init_reinstalls_when_version_requested(data_dir, tmp_path, monkeypatch):
    import saurus_cli as sc

    calls = []

    def fake_download(url, dest):
        calls.append(url)

    monkeypatch.setattr(sc, "_download_with_progress", fake_download)
    monkeypatch.setattr(sc, "_resolve_init_target", lambda output: data_dir)
    monkeypatch.setattr(sc, "_resolve_data_url", lambda v: ("http://x/saurus_data.zip", "http://x/saurus_data.zip.sha256"))
    code = sc.cmd_init(["-v", "v9.9.9", "-q"])
    assert code != 0 or calls
    assert calls, "-v must trigger a re-download even when data is installed"


def test_init_noop_without_version_flag(data_dir, monkeypatch, capsys):
    import saurus_cli as sc

    calls = []
    monkeypatch.setattr(sc, "_download_with_progress", lambda url, dest: calls.append(url))
    monkeypatch.setattr(sc, "_resolve_init_target", lambda output: data_dir)
    code = sc.cmd_init(["-q"])
    assert code == 0
    assert calls == []
