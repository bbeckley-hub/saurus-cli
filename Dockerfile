# syntax=docker/dockerfile:1

# ============================================================
# Stage 1 — build the wheel (with bundled data)
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml MANIFEST.in LICENSE README.md saurus_cli.py ./
COPY data ./data
RUN pip install --no-cache-dir build && \
    python -m build --wheel


# ============================================================
# Stage 2 — runtime
# ============================================================
FROM python:3.12-slim

LABEL org.opencontainers.image.title="saurus-cli" \
      org.opencontainers.image.description="Command-line interface for querying the SAURUS Staphylococcus aureus genomic surveillance database (data bundled)" \
      org.opencontainers.image.authors="Brown Beckley <brownbeckley94@gmail.com>" \
      org.opencontainers.image.source="https://github.com/bbeckley-hub/saurus-cli" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.documentation="https://saurus-db.org/manual.html"

## NCBI datasets CLI — so users can download genomes inside the container
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip && \
    curl -fsSL "https://ftp.ncbi.nlm.nih.gov/pub/datasets/command-line/v2/linux-amd64/datasets" \
        -o /usr/local/bin/datasets && \
    chmod +x /usr/local/bin/datasets && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install saurus-cli wheel (data ships inside → installs to /usr/local/share/saurus/data/)
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

# Sanity check: verify the full data bundle is present (not just the mrsa folder)
RUN test -d /usr/local/share/saurus/data/mrsa && \
    test -d /usr/local/share/saurus/data/mlst && \
    test -d /usr/local/share/saurus/data/spa && \
    test -d /usr/local/share/saurus/data/sccmec && \
    test -d /usr/local/share/saurus/data/agr && \
    test -d /usr/local/share/saurus/data/capsule && \
    test -d /usr/local/share/saurus/data/gene_annotation && \
    test -d /usr/local/share/saurus/data/metadata || \
    (echo "Data bundle incomplete — check pyproject.toml data-files entries" && exit 1)

# Smoke test: verify the CLI can actually load the bundled data and count genomes
RUN saurus --lineage USA300 --count --quiet > /tmp/count.txt && \
    test -s /tmp/count.txt && \
    grep -qE '^[0-9,]+$' /tmp/count.txt && \
    rm /tmp/count.txt || \
    (echo "CLI smoke test failed — bundled data is not loadable" && exit 1)

WORKDIR /work
ENTRYPOINT ["saurus"]
CMD ["--version"]
