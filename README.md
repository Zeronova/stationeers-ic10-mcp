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

## Installation

### Docker (empfohlen)

Auf dem Medienserver bauen und starten:

```bash
git clone https://github.com/Zeronova/stationeers-ic10-mcp
cd stationeers-ic10-mcp
docker build -t stationeers-ic10-mcp .
# Oder via docker-compose:
docker compose build
```

MCP-Client-Konfiguration (z.B. nanobot config.json):
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

> **Warum Docker?** Der Server läuft als MCP stdio-Prozess – der Docker-Container wird vom AI-Agenten bei Bedarf gestartet, kommuniziert via stdin/stdout, und wird danach automatisch gelöscht (`--rm`).

### Oder direkt mit Python

```bash
git clone https://github.com/Zeronova/stationeers-ic10-mcp
cd stationeers-ic10-mcp
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

## Beispiel

```
→ Nachricht: Hilf mir, eine IC10 Drucksteuerung für einen Volume Pump zu schreiben

← Agent ruft search_device("Volume Pump") → sieht PressureSetting, On, etc.
← Agent ruft search_instruction("s") → sieht set syntax
← Agent liefert fertigen IC10 Code mit Kommentaren
```
