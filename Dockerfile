FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY stationeers_ic10_mcp/ stationeers_ic10_mcp/

# Build and install
RUN pip install --no-cache-dir build && \
    python -m build --wheel

FROM python:3.11-slim

# Copy just the installed package
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl && \
    rm -rf /root/.cache

# Verify it's importable
RUN python3 -c "from stationeers_ic10_mcp.server import instructions, devices; print(f'Loaded {len(instructions())} instructions, {len(devices())} devices')"

# MCP stdio protocol - keep stdin open
ENTRYPOINT ["python3", "-m", "stationeers_ic10_mcp.server"]
