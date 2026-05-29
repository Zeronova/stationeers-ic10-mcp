FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY stationeers_ic10_mcp/ stationeers_ic10_mcp/

RUN pip install --no-cache-dir build && \
    python -m build --wheel

FROM python:3.11-slim

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl && \
    rm -rf /root/.cache

# Verify
RUN python3 -c "from stationeers_ic10_mcp.server import instructions, devices; print(f'Loaded {len(instructions())} instructions, {len(devices())} devices')"

# Default: SSE/HTTP mode for Docker deployment
# Override with: docker run ... stationeers-ic10-mcp (stdio)
ENV MCP_TRANSPORT=sse
EXPOSE 8765
ENTRYPOINT ["python3", "-m", "stationeers_ic10_mcp.server"]
CMD ["--sse", "--host", "0.0.0.0", "--port", "8765"]
