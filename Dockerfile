# syntax=docker/dockerfile:1

# ============================================================
# Stage 1 — build the wheel (with bundled data)
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml MANIFEST.in LICENSE README.md saurus_cli.py ./
COPY data ./data

RUN test -f data/mrsa/mrsa_all.tsv.gz && \
    test -f data/DATA_VERSION || \
    (echo "ERROR: data files missing from build context. Check .dockerignore." && \
     ls -la data/ && exit 1)

RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    python -c "import glob, zipfile, sys; \
w = glob.glob('dist/*.whl')[0]; \
f = zipfile.ZipFile(w); \
n = sum(1 for x in f.namelist() if 'share/saurus/data' in x); \
print(f'Data files in wheel: {n}'); \
sys.exit(0 if n >= 16 else 1)"

# ============================================================
# Stage 2 — runtime
# ============================================================
FROM python:3.12-slim

LABEL org.opencontainers.image.title="saurus-cli" \
      org.opencontainers.image.description="Command-line interface for querying the SAURUS Staphylococcus aureus genomic surveillance database (data bundled)" \
      org.opencontainers.image.authors="Brown Beckley <brownbeckley94@gmail.com>" \
      org.opencontainers.image.source="https://github.com/bbeckley-hub/saurus-cli" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="0.4.0" \
      org.opencontainers.image.documentation="https://saurus-db.org/manual.html"

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip && \
    curl -fsSL "https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/datasets" \
        -o /usr/local/bin/datasets && \
    chmod +x /usr/local/bin/datasets && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN ls -lh /tmp/*.whl && \
    unzip -l /tmp/*.whl | grep -c "share/saurus/data" && \
    pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

RUN test -d /usr/local/share/saurus/data/mrsa && \
    test -d /usr/local/share/saurus/data/mlst && \
    test -d /usr/local/share/saurus/data/spa && \
    test -d /usr/local/share/saurus/data/sccmec && \
    test -d /usr/local/share/saurus/data/agr && \
    test -d /usr/local/share/saurus/data/capsule && \
    test -d /usr/local/share/saurus/data/gene_annotation && \
    test -d /usr/local/share/saurus/data/metadata || \
    (echo "Data bundle incomplete — check pyproject.toml data-files entries" && exit 1)

RUN saurus --lineage USA300 --count --quiet > /tmp/count.txt && \
    test -s /tmp/count.txt && \
    test "$(cat /tmp/count.txt)" = "10,448" || \
    (echo "CLI smoke test failed: got '$(cat /tmp/count.txt)', expected 10,448 (data v1.1.0)" && exit 1) && \
    rm -f /tmp/count.txt

COPY entrypoint.sh /usr/local/bin/saurus-entrypoint
RUN chmod +x /usr/local/bin/saurus-entrypoint

WORKDIR /work
ENTRYPOINT ["saurus-entrypoint"]
CMD ["--version"]
