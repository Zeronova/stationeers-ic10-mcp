"""MCP Server for Stationeers IC10 programming reference.

Provides tools to look up IC10 instructions, device properties,
and code examples for the Stationeers game.
"""

from __future__ import annotations

import json
import os
import re
from difflib import get_close_matches
from typing import Any

import mcp.server.stdio
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    TextResourceContents,
)

# --- Data loading ---

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all_device_properties() -> dict[str, dict]:
    """Load all device property files."""
    devices = {}
    index = load_json("device_index.json")
    for key in index:
        filepath = os.path.join(DATA_DIR, f"device_{key}.json")
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                devices[key] = json.load(f)
    return devices


def get_instructions() -> dict[str, dict]:
    return load_json("instructions.json")


# Cache
_INSTRUCTIONS: dict[str, dict] | None = None
_DEVICES: dict[str, dict] | None = None
_DEVICE_INDEX: dict | None = None


def instructions() -> dict[str, dict]:
    global _INSTRUCTIONS
    if _INSTRUCTIONS is None:
        _INSTRUCTIONS = get_instructions()
    return _INSTRUCTIONS


def devices() -> dict[str, dict]:
    global _DEVICES
    if _DEVICES is None:
        _DEVICES = load_all_device_properties()
    return _DEVICES


def device_index() -> dict:
    global _DEVICE_INDEX
    if _DEVICE_INDEX is None:
        _DEVICE_INDEX = load_json("device_index.json")
    return _DEVICE_INDEX


def clean_device_name(name: str) -> str:
    """Remove wiki suffix from device names."""
    return re.sub(r"\s*[–-]+\s*Unofficial Stationeers Wiki\s*$", "", name).strip()


# --- Server setup ---

server = Server("stationeers-ic10")


# --- Tool implementations ---

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_instruction",
            description="Search for an IC10 instruction/opcode by name or keyword. Returns matching instructions with syntax and description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Instruction name or keyword (e.g. 'add', 'batch', 'branch', 'move')",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_all_instructions",
            description="List ALL IC10 instructions grouped by category. Get a complete overview.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter: Arithmetic, Math, Trig, Bitwise, Compare, Branch, Batch IO, Data Transfer, Stack, Control, Preprocessor, Device Check",
                    }
                },
            },
        ),
        Tool(
            name="search_device",
            description="Search for a Stationeers device by name and get its data network properties.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Device name or keyword (e.g. 'Furnace', 'Sensor', 'Door', 'Pump')",
                    },
                    "property_filter": {
                        "type": "string",
                        "description": "Optional: filter properties by keyword (e.g. 'Pressure', 'Temperature', 'On', 'Open')",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_devices",
            description="List all available Stationeers devices that have data network properties.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional filter: e.g. 'structure', 'kit', 'pipe', 'machine'",
                    }
                },
            },
        ),
        Tool(
            name="search_property",
            description="Search for a specific property/logicType across all devices. Find which devices have a property.",
            inputSchema={
                "type": "object",
                "properties": {
                    "property": {
                        "type": "string",
                        "description": "Property name to search (e.g. 'Pressure', 'Temperature', 'On', 'Open', 'Lock')",
                    }
                },
                "required": ["property"],
            },
        ),
        Tool(
            name="search_example",
            description="Search through bundled IC10 code examples for common patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What pattern to find (e.g. 'pressure control', 'door', 'temperature', 'airlock')",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_ic10_basics",
            description="Get a quick overview of IC10 basics: registers, pins, labels, and execution model.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "search_instruction":
        return search_instruction(arguments.get("query", ""))
    elif name == "get_all_instructions":
        return get_all_instructions(arguments.get("category"))
    elif name == "search_device":
        return search_device(arguments.get("query", ""), arguments.get("property_filter"))
    elif name == "list_devices":
        return list_devices(arguments.get("category"))
    elif name == "search_property":
        return search_property(arguments.get("property", ""))
    elif name == "search_example":
        return search_example(arguments.get("query", ""))
    elif name == "get_ic10_basics":
        return get_ic10_basics()
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def search_instruction(query: str) -> list[TextContent]:
    """Search instructions by name or keyword."""
    ic = instructions()
    query_lower = query.lower().strip()

    results = {}

    # For very short queries (1-2 chars): exact + prefix only
    if len(query_lower) <= 2:
        if query_lower in ic:
            results[query_lower] = ic[query_lower]
        for name, data in ic.items():
            if name.startswith(query_lower) and name not in results:
                results[name] = data
            elif len(query_lower) == 1:
                continue  # Single char: only exact + prefix
    else:
        # Exact match first
        if query_lower in ic:
            results[query_lower] = ic[query_lower]

        # Prefix match
        for name, data in ic.items():
            if name.startswith(query_lower) and name not in results:
                results[name] = data

        # Fuzzy match
        all_names = list(ic.keys())
        fuzzy = get_close_matches(query_lower, all_names, n=10, cutoff=0.4)
        for name in fuzzy:
            if name not in results:
                results[name] = ic[name]

        # Content match (search in description + category)
        for name, data in ic.items():
            if name in results:
                continue
            search_text = f"{data.get('desc', '')} {data.get('cat', '')} {data.get('syntax', '')}"
            if query_lower in search_text.lower():
                results[name] = data

    if not results:
        return [TextContent(type="text", text=f"No instructions found matching '{query}'.")]

    lines = [f"## IC10 Instructions matching '{query}'\n"]
    for name in sorted(results.keys()):
        data = results[name]
        lines.append(f"**{name}**")
        lines.append(f"  Syntax: `{data['syntax']}`")
        lines.append(f"  {data['desc']}")
        if data.get('example'):
            lines.append(f"  Example: `{data['example']}`")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


def get_all_instructions(category: str | None = None) -> list[TextContent]:
    """List all instructions, optionally filtered by category."""
    ic = instructions()
    
    grouped: dict[str, list[tuple[str, dict]]] = {}
    for name, data in ic.items():
        cat = data.get('cat', 'Other')
        grouped.setdefault(cat, []).append((name, data))
    
    # Filter by category if provided
    if category:
        cat_lower = category.lower().strip()
        matched = {c: v for c, v in grouped.items() if cat_lower in c.lower() or c.lower() in cat_lower}
        if not matched:
            available = sorted(grouped.keys())
            return [TextContent(type="text", text=f"Category '{category}' not found. Available: {', '.join(available)}")]
        grouped = matched
    
    lines = [f"## IC10 Instruction Set Reference\n"]
    
    for cat in sorted(grouped.keys()):
        lines.append(f"\n### {cat}\n")
        for name, data in sorted(grouped[cat], key=lambda x: x[0]):
            ex = f" — `{data['example']}`" if data.get('example') else ""
            lines.append(f"- **{name}** `{data['syntax']}` — {data['desc']}{ex}")
    
    total = sum(len(v) for v in grouped.values())
    lines.insert(1, f"*{total} instructions total*\n")
    
    return [TextContent(type="text", text="\n".join(lines))]


def search_device(query: str, property_filter: str | None = None) -> list[TextContent]:
    """Search for a device by name and show its properties."""
    devs = devices()
    idx = device_index()
    query_lower = query.lower().strip()
    
    matches = {}
    
    # Search by name
    for key, data in devs.items():
        name = clean_device_name(data.get('name', ''))
        if query_lower in name.lower() or query_lower in key.lower():
            matches[key] = data
    
    # Fuzzy on name
    if not matches:
        all_names = {k: clean_device_name(v.get('name', '')) for k, v in devs.items()}
        fuzzy_keys = get_close_matches(query_lower, list(all_names.keys()), n=5, cutoff=0.3)
        for key in fuzzy_keys:
            matches[key] = devs[key]
        
        if not matches:
            fuzzy_names = get_close_matches(query_lower, list(all_names.values()), n=5, cutoff=0.3)
            for key, name in all_names.items():
                if name in fuzzy_names:
                    matches[key] = devs[key]
    
    if not matches:
        return [TextContent(type="text", text=f"No devices found matching '{query}'.")]
    
    results = []
    for key, data in sorted(matches.items())[:5]:  # max 5 devices
        name = clean_device_name(data.get('name', ''))
        
        props = data.get('properties', [])
        
        # Filter by property if specified
        if property_filter:
            pf_lower = property_filter.lower().strip()
            props = [p for p in props if pf_lower in p.get('property', '').lower()]
        
        lines = [f"\n## {name}"]
        lines.append(f"  *Wiki key: {key}*\n")
        
        if not props:
            lines.append("  *No matching properties.*")
        else:
            for p in props[:30]:  # max 30 props per device
                prop_name = p.get('property', '?')
                # Skip enum-only entries (just numbers)
                if prop_name.isdigit() and len(prop_name) <= 2:
                    continue
                ptype = p.get('type', '')
                access = p.get('access', '')
                desc = p.get('description', '')
                extra = p.get('col5', '')
                
                access_str = f" [{access}]" if access else ""
                type_str = f" ({ptype})" if ptype else ""
                desc_str = f" — {desc}" if desc else ""
                extra_str = f" — {extra}" if extra and not desc else ""
                
                lines.append(f"  - **{prop_name}**{type_str}{access_str}{desc_str}{extra_str}")
            
            more = len(props) - 30
            if more > 0:
                lines.append(f"  *... and {more} more properties. Use property_filter to narrow down.*")
        
        results.extend(lines)
    
    return [TextContent(type="text", text="\n".join(results))]


def list_devices(category: str | None = None) -> list[TextContent]:
    """List all available devices."""
    idx = device_index()
    
    lines = [f"## Stationeers Devices with Data Network Properties\n"]
    lines.append(f"*Total: {len(idx)} devices*\n")
    
    for key, data in sorted(idx.items()):
        name = data.get('name', key)
        name = clean_device_name(name)
        count = data.get('count', 0)
        
        if category:
            cat_lower = category.lower()
            if cat_lower not in name.lower() and cat_lower not in key.lower():
                continue
        
        lines.append(f"- **{name}**: {count} properties")
    
    return [TextContent(type="text", text="\n".join(lines))]


def search_property(property_name: str) -> list[TextContent]:
    """Find which devices have a specific property."""
    devs = devices()
    idx = device_index()
    query_lower = property_name.lower().strip()
    
    found = {}
    for key, data in devs.items():
        matching_props = []
        for p in data.get('properties', []):
            prop = p.get('property', '')
            if query_lower in prop.lower():
                matching_props.append(p)
        
        if matching_props:
            name = clean_device_name(data.get('name', key))
            found[name] = matching_props
    
    if not found:
        return [TextContent(type="text", text=f"No devices found with property containing '{property_name}'.")]
    
    lines = [f"## Devices with property '{property_name}'\n"]
    lines.append(f"*Found in {len(found)} devices*\n")
    
    for device_name in sorted(found.keys()):
        props = found[device_name]
        # Show the matching property
        for p in props[:3]:
            prop = p.get('property', '?')
            ptype = p.get('type', '')
            access = p.get('access', '')
            desc = p.get('description', '') or p.get('col5', '')
            extra = f" ({ptype}) [{access}]" if ptype or access else ""
            lines.append(f"- **{device_name}** → `{prop}`{extra}: {desc[:120]}")
    
    return [TextContent(type="text", text="\n".join(lines))]


def search_example(query: str) -> list[TextContent]:
    """Return relevant code examples."""
    examples = {
        "pressure": {
            "title": "Pressure Control Loop",
            "code": """# Pressure regulator for a pipe/vent
# Requires: d0 = Pipe Volume Pump or similar
alias Pump d0
alias TargetPressure r0
alias CurrentPressure r1

move TargetPressure 100   # Target: 100 kPa
l CurrentPressure Pump PressureSetting

sgt r2 CurrentPressure TargetPressure
bnez r2 too_high

# Too low - pump in
s Pump On 1
j done

too_high:
# Too high - pump out (or close)
s Pump On 0

done:
yield
j start"""
        },
        "door": {
            "title": "Door Control with Sensor",
            "code": """# Automatic door with pressure check
alias Door d0
alias Sensor d1
alias PressureLimit r0

define MaxPressure 150

start:
l r0 Sensor PressureSetting
sgt r1 r0 MaxPressure
bnez r1 lock_door

# Normal - open if player nearby
s Door Open 1
j done

lock_door:
s Door Open 0

done:
yield
j start"""
        },
        "airlock": {
            "title": "Simple Airlock Control",
            "code": """# Simple 2-door airlock
alias InnerDoor d0
alias OuterDoor d1
alias InnerPressure d2  # Sensor in airlock
alias CycleButton d3    # Button or switch

define TargetPressure 100

# Wait for cycle command
l r0 CycleButton Mode
beqz r0 wait

# Close outer door if open
s OuterDoor Open 0

# Open inner door
s InnerDoor Open 1
yield
s InnerDoor Open 0

wait:
yield
j start"""
        },
        "furnace": {
            "title": "Furnace Temperature Control",
            "code": """# Simple furnace temperature monitor
alias Furnace d0
alias MaxTemp r0
alias WarningLight d1

define SafeTemp 2000

start:
l r1 Furnace Temperature
l r2 Furnace Combustion

# Check temperature
sgt r3 r1 SafeTemp
s WarningLight On r3

# Log temp if >1000
sgt r4 r1 1000
bnez r4 log_temp
j done

log_temp:
debug r1
yield
j start

done:
yield
j start"""
        },
        "generic": {
            "title": "IC10 Program Structure",
            "code": """# IC10 Program Template
# ── Setup ──
alias DeviceName d0
alias MyRegister r0
define MyConstant 42

# ── Main Loop ──
start:
    # Load from device
    l r0 DeviceName SomeProperty
    # Process
    sgt r1 r0 50
    bnez r1 above_threshold
    j below_threshold

above_threshold:
    s DeviceName SomeSetting 1
    j done

below_threshold:
    s DeviceName SomeSetting 0

done:
    yield   # Wait for next tick
    j start # Loop

# ── Subroutine ──
myFunction:
    # Do something
    return"""
        },
        "solar": {
            "title": "Solar Panel Tracking",
            "code": """# Basic solar panel control
alias Panel d0
alias PanelVertical d1

start:
# Read current output
l r0 Panel PowerOutput
l r1 PanelVertical PowerOutput

# Compare and adjust
sgt r2 r0 r1
bnez r2 use_panel1

# Use panel 2's angle
s PanelVertical Activate 1
s PanelVertical Deactivate 0
j done

use_panel1:
s Panel Activate 1
s Panel Deactivate 0

done:
yield
j start"""
        },
    }
    
    query_lower = query.lower().strip()
    
    # Score examples
    scored = []
    for key, ex in examples.items():
        score = 0
        search_text = f"{ex['title']} {ex['code']}".lower()
        if query_lower in key.lower():
            score += 5
        if query_lower in ex['title'].lower():
            score += 3
        if query_lower in search_text:
            score += 1
        if score > 0:
            scored.append((score, key, ex))
    
    if not scored:
        return [TextContent(type="text", text=f"No examples found matching '{query}'. Try: pressure, door, airlock, furnace, solar, or 'generic' for program structure.")]
    
    scored.sort(reverse=True)
    
    lines = []
    for score, key, ex in scored:
        lines.append(f"\n## {ex['title']}")
        lines.append(f"```")
        lines.append(ex['code'])
        lines.append(f"```")
    
    return [TextContent(type="text", text="\n".join(lines))]


def get_ic10_basics() -> list[TextContent]:
    """Return IC10 programming basics."""
    text = """# IC10 Programming Basics

## Registers
- **r0–r15** (16 total): Internal CPU registers. All math and logic happens here.
- **d0–d5** (6 total): Device pins. Each pin connects to exactly one device (set via screwdriver).
- **db**: Special — the device the IC chip is mounted ON (e.g., an IC Housing in a Furnace).

## Data Types
- **logicType**: A property name on a device (e.g., Pressure, Temperature, On, Open). Case-sensitive!
- **deviceHash**: HASH("StructureType") — used for batch operations
- **nameHash**: HASH("CustomName") — for filtering by device name

## Aliases
`alias TempSensor d0` — Makes d0 readable as "TempSensor" in your code.

## Labels
Line targets for jumps/branches. Followed by a colon:
```
start:     # Jump target
  ...
  j start  # Jump back
```

## Execution
- IC10 runs in a loop: top to bottom, then back to top (unless a jump branches elsewhere)
- **One tick = 0.5 seconds** game time
- `yield` = pause until next tick
- Without `yield`, the IC runs ALL instructions in one tick and then restarts.

## Common Commands
- `l r0 d0 Pressure` — Read Pressure from d0 into r0
- `s d0 On r0` — Write r0 (0/1) to d0's On property
- `move r0 100` — Set r0 = 100
- `yield` — Wait 1 tick
- `j loop` — Jump to label "loop"
- `beqz r0 done` — If r0 == 0, jump to "done"

## HASH() Function
Used for batch operations. Returns a number from a string.
- `HASH("StructureFurnace")` → hash for Furnace
- `HASH("StructureDoor")` → hash for Doors
- `HASH("PipePressureSensor")` → hash for pressure sensors
- `HASH("CustomName")` → hash for a device's custom name

## Boolean in IC10
- 0 = false/off/closed/unlocked
- 1 (or non-zero) = true/on/open/locked"""
    
    return [TextContent(type="text", text=text)]


# --- Prompt for guide ---

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="assist-ic10",
            description="Ask the AI to help you write stationeers IC10 code using the available tools",
            arguments=[
                PromptArgument(
                    name="task",
                    description="What do you want the IC10 code to do? Describe the automation.",
                    required=True,
                )
            ],
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    if name == "assist-ic10" and arguments:
        task = arguments.get("task", "")
        return GetPromptResult(
            description=f"Assist with IC10 code: {task}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"I need to write Stationeers IC10 code for: {task}\n\nPlease use the available tools (search_instruction, search_device, search_property, search_example) to research the needed instructions and device properties, then write the IC10 code for me. Include comments explaining what each section does."
                    ),
                )
            ],
        )
    raise ValueError(f"Unknown prompt: {name}")


# --- Main entry ---

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="stationeers-ic10",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
