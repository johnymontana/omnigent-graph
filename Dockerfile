# Sidecar image: the host-level shared MCP server (ADR-0001).
# In NAMS mode (MEMORY_API_KEY set) this is a light REST client.
# In local-Neo4j mode it also runs extraction + embeddings locally (heavier).
FROM python:3.12-slim

WORKDIR /app

# Install the package (which pulls neo4j-agent-memory[mcp]).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000

# serve reads OMNIGENT_MEMORY_* + MEMORY_API_KEY / NAM_NEO4J__* from the environment.
ENTRYPOINT ["omnigent-neo4j-memory", "serve"]
