# Stationeers IC10 MCP Server

MCP-Server für die IC10-Programmiersprache aus dem Spiel **Stationeers**.

## Was es macht

Der Server erlaubt einem AI-Agenten (wie mir), IC10-Befehle und Device-Properties nachzuschlagen. Statt raten zu müssen, kann ich:

- **IC10 Opcodes** suchen: Syntax, Beschreibung, Beispiele
- **Geräte-Properties** finden: Welche Daten hat eine Furnace? Was kann man von einem Sensor lesen?
- **Properties geräteübergreifend** suchen: Welche Geräte haben "Temperature"?
- **Code-Beispiele** abrufen: Grundlegende Pattern für Druckregelung, Türen, etc.

## Datenquellen

- **135+ IC10 Instruktionen** aus dem VSCode-Extension-Repo
- **120 Geräte** mit **960+ Data Network Properties** aus dem Stationeers Wiki
- IC10 Sprachreferenz und Code-Beispiele

## Tools

| Tool | Beschreibung |
|------|-------------|
| `search_instruction` | IC10 Befehl nach Name/Keyword suchen |
| `get_all_instructions` | Alle Befehle nach Kategorie gruppiert auflisten |
| `search_device` | Gerät suchen und dessen Data Network Properties anzeigen |
| `list_devices` | Alle verfügbaren Geräte auflisten |
| `search_property` | Property über alle Geräte hinweg suchen |
| `search_example` | Code-Beispiele für häufige Pattern finden |
| `get_ic10_basics` | IC10 Grundlagen: Register, Syntax, Aliase |

## Transportmodi

Der Server unterstützt zwei Modi – **SSE/HTTP** und **Stdio**.

### SSE/HTTP (empfohlen für Docker)

Läuft als langlaufender Webservice auf einem Port. Der AI-Agent verbindet sich via URL.

```bash
# Docker
docker run -d -p 8765:8765 stationeers-ic10-mcp

# Oder direkt
python3 -m stationeers_ic10_mcp.server --sse
```

### Stdio (für direkte Einbindung)

Der Agent startet den Server als Subprozess, Kommunikation über stdin/stdout.

```bash
python3 -m stationeers_ic10_mcp.server
```

## Docker

```bash
git clone https://github.com/Zeronova/stationeers-ic10-mcp
cd stationeers-ic10-mcp
docker build -t stationeers-ic10-mcp .
# Oder:
docker compose build
```

### docker-compose

```yaml
services:
  stationeers-ic10-mcp:
    build: .
    image: stationeers-ic10-mcp:latest
    container_name: stationeers-ic10-mcp
    ports:
      - "8765:8765"
    environment:
      - MCP_TRANSPORT=sse
    restart: unless-stopped
```

## MCP Client Konfiguration

### nanobot / Claude Desktop – via HTTP/SSE

```json
{
  "mcpServers": {
    "stationeers-ic10": {
      "url": "http://192.168.2.7:8765/sse"
    }
  }
}
```

Ersetze `192.168.2.7` durch die IP deines Medienservers. Der Container läuft dauerhaft, nanobot verbindet sich bei Bedarf.

### nanobot – via Stdio (Docker-subprozess)

```json
{
  "mcpServers": {
    "stationeers-ic10": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "stationeers-ic10-mcp:latest"]
    }
  }
}
```

Lässt nanobot den Container on demand starten, ohne dass ein Port freigegeben werden muss.

### Direkt mit Python

```bash
pip install -e .
```

```json
{
  "mcpServers": {
    "stationeers-ic10": {
      "command": "python3",
      "args": ["-m", "stationeers_ic10_mcp.server"]
    }
  }
}
```

## Umgebungsvariablen

| Variable | Effekt |
|----------|--------|
| `MCP_TRANSPORT=sse` | Startet automatisch im SSE-Modus (default im Docker-Image) |
| `MCP_TRANSPORT=stdio` | Explizit Stdio-Modus |

## Beispiel

```
→ Nachricht: Hilf mir, eine IC10 Drucksteuerung für einen Volume Pump zu schreiben

← Agent ruft search_device("Volume Pump") → sieht PressureSetting, On, etc.
← Agent ruft search_instruction("s") → sieht set syntax
← Agent liefert fertigen IC10 Code mit Kommentaren
```
