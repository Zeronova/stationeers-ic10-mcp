"""
Stationeers IC10 MCP Server

Provides IC10 programming language reference and device data
for the game Stationeers via the Model Context Protocol.

Transport modes:
  --sse          SSE/HTTP mode (Docker default)
  --stdio        Stdio mode (default)
"""

from __future__ import annotations

import json
import os
import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DATA_DIR = Path(__file__).parent / "data"

mcp = FastMCP("stationeers-ic10")


# --- Data loading -----------------------------------------------------------

def instructions() -> list[dict]:
    """Load instructions reference."""
    path = DATA_DIR / "instructions.json"
    if path.exists():
        data = json.loads(path.read_text())
        # instructions.json is a dict: {opcode: {name?, syntax, desc, ...}}
        if isinstance(data, dict):
            result = []
            for opcode, info in data.items():
                entry = {"opcode": opcode}
                if isinstance(info, dict):
                    entry.update(info)
                    # some entries use "desc", others use "description"
                    if "desc" in info and "description" not in info:
                        entry["description"] = info["desc"]
                    elif "description" in info and "desc" not in info:
                        entry["desc"] = info["description"]
                else:
                    entry["description"] = str(info)
                result.append(entry)
            return result
        return data
    return []


def devices() -> list[dict]:
    """Load device database: merge index with detailed device files."""
    idx_path = DATA_DIR / "device_index.json"
    if not idx_path.exists():
        return []
    idx = json.loads(idx_path.read_text())
    result = []
    for slug, info in idx.items():
        dev = dict(info)  # copy {name, properties (list of str), count}
        # Try to merge detailed properties
        detail_path = DATA_DIR / f"device_{slug}.json"
        if detail_path.exists():
            detail = json.loads(detail_path.read_text())
            dev["description"] = detail.get("description", "")
            # properties with full details
            dev["properties"] = detail.get("properties", [])
        else:
            dev["description"] = ""
        result.append(dev)
    return result


def examples() -> list[dict]:
    """Load code examples."""
    path = DATA_DIR / "examples.json"
    if path.exists():
        import json
        return json.loads(path.read_text())
    return []


# --- Tools ------------------------------------------------------------------


@mcp.tool(
    name="search_instruction",
    description="Search IC10 instructions by name or keyword. Returns opcode, syntax, stack behavior, and a description.",
)
def search_instruction(query: str) -> str:
    """Search instructions by name or keyword."""
    query_lower = query.lower().strip()
    results = []
    for inst in instructions():
        name = inst.get("name") or inst.get("opcode", "")
        opcode = inst.get("opcode", "")
        desc = inst.get("description") or inst.get("desc", "")
        if (
            query_lower in name.lower()
            or query_lower in opcode
            or query_lower in desc.lower()
        ):
            refs = inst.get("references", "")
            # Handle if references is a list
            if isinstance(refs, list):
                refs = "; ".join(str(r) for r in refs)
            syntax = inst.get("syntax", "")
            stack = inst.get("stack", "")
            results.append(
                f"**{name}** (`{opcode}`)"
                + (f"\n  Syntax: {syntax}" if syntax else "")
                + (f"\n  Stack: {stack}" if stack else "")
                + (f"\n  {desc}" if desc else "")
                + (f"\n  {refs}" if refs else "")
            )
    if not results:
        return f"No instruction found for '{query}'."
    return "\n\n".join(results[:20])


@mcp.tool(
    name="get_all_instructions",
    description="Get ALL IC10 instructions grouped by category.",
)
def get_all_instructions() -> str:
    """Return all instructions grouped by category."""
    from collections import defaultdict

    by_category = defaultdict(list)
    for inst in instructions():
        name = inst.get("name") or inst.get("opcode", "?")
        opcode = inst.get("opcode", "?")
        cat = inst.get("category", inst.get("cat", "Uncategorized"))
        by_category[cat].append(f"  {name} (`{opcode}`)")

    parts = []
    for cat in sorted(by_category):
        items = "\n".join(sorted(by_category[cat]))
        parts.append(f"**{cat}**\n{items}")
    return "\n\n".join(parts)


@mcp.tool(
    name="search_device",
    description="Search for a device and show its data network properties. Returns device description and all available properties with types and descriptions.",
)
def search_device(query: str) -> str:
    """Find device by name and return its properties."""
    query_lower = query.lower().strip()
    results = []
    for dev in devices():
        name = dev.get("name", "")
        if query_lower in name.lower():
            props = dev.get("properties", [])
            prop_lines = []
            for p in props:
                # Handle both dict and string formats
                if isinstance(p, dict):
                    pname = p.get("property", p.get("name", "?"))
                    ptype = p.get("type", "?")
                    pdesc = p.get("description", "") or p.get("col5", "")
                    paccess = p.get("access", "")
                    extras = f" ({paccess})" if paccess else ""
                    prop_lines.append(
                        f"  • **{pname}**: {ptype}{extras}"
                        + (f" – {pdesc[:120]}" if pdesc else "")
                    )
                else:
                    # Just a string name
                    prop_lines.append(f"  • **{p}**")
            results.append(
                f"## {name}\n{dev.get('description', '')}\n\nProperties:\n"
                + ("\n".join(prop_lines) if prop_lines else "  (none)")
            )
    if not results:
        return f"No device found for '{query}'."
    return "\n\n".join(results[:10])


@mcp.tool(
    name="list_devices",
    description="List all available devices with their display names.",
)
def list_devices() -> str:
    """Return all device names."""
    names = sorted(
        dev.get("name", "?") for dev in devices()
    )
    return "Available devices:\n" + "\n".join(f"  • {n}" for n in names)


@mcp.tool(
    name="search_property",
    description="Search for a property name across ALL devices. Shows which devices have that property and the full property details.",
)
def search_property(query: str) -> str:
    """Find which devices have a property matching query."""
    query_lower = query.lower().strip()
    matches = []
    for dev in devices():
        for p in dev.get("properties", []):
            if isinstance(p, dict):
                pname = p.get("property", p.get("name", ""))
                pdesc = p.get("description", "") or p.get("col5", "")
                ptype = p.get("type", "?")
                if query_lower in pname.lower() or query_lower in pdesc.lower():
                    matches.append(
                        f"**{dev['name']}** → {pname} ({ptype})"
                        + (f" – {pdesc[:120]}" if pdesc else "")
                    )
            else:
                # String property name
                if query_lower in p.lower():
                    matches.append(f"**{dev['name']}** → {p}")
    if not matches:
        return f"No property found for '{query}'."
    return f"Devices with property matching '{query}':\n" + "\n".join(matches[:20])


@mcp.tool(
    name="search_example",
    description="Search IC10 code examples by keyword. Returns ready-to-use IC10 code snippets.",
)
def search_example(query: str) -> str:
    """Find code examples by keyword."""
    query_lower = query.lower().strip()
    results = []
    for ex in examples():
        title = ex.get("title", "")
        desc = ex.get("description", "")
        code = ex.get("code", "")
        if query_lower in title.lower() or query_lower in desc.lower():
            results.append(
                f"## {title}\n{desc}\n```\n{code}\n```"
            )
    if not results:
        return f"No examples found for '{query}'."
    return "\n\n".join(results[:5])


@mcp.tool(
    name="get_ic10_basics",
    description="Get IC10 basics: register aliases, type system, and general syntax rules.",
)
def get_ic10_basics() -> str:
    """Return general IC10 reference info."""
    return """## IC10 Basics

### Registers
- **r0–r15** – General-purpose registers
- **sp** – Stack pointer
- **fp** – Frame pointer
- **ra** – Return address
- **ap** – Argument pointer

Aliases:
- **r0** ≡ **sp** ≡ **zero** (also reads as 0)
- **r1** ≡ **fp**
- **r2** ≡ **ra**
- **r3** ≡ **ap**

### Types
- **Number** – Fixed-point (3 decimal places), range: -2147483.648 to 2147483.647
- **Device** – A specific device on the network (e.g., `d0` = first referenced device)
- **Slot** – e.g., `Slot0`–`Slot5` (dolly slots), `SlotX` (slot index)

### Device Reference
- `d0`–`d15` – Device references, assigned by the programmer or when the IC is first placed
- Devices are referenced by index (d0 is the first device)
- Use the `s` (set) instruction to assign a device to a register first (e.g., `s r0 d0 Off`)

### Units
- Various properties have different units (e.g., Temperature: K, Pressure: Pa, Energy: J)
- All values on the data network use SI base units (e.g., Kelvin, Pascals, Joules)
- For pressure: 1 kPa = 1000 Pa

### Key Notes
- Comments start with `#`
- Labels end with `:` (e.g., `loop:`)
- Branch instructions use labels (e.g., `beqz r0 loop`)
- `move rz, r0` works as a null-check pattern (rz is alias for r0)
- Hash is used for immediate values: `s r0 100` → `push 100; pop r0`
"""


# --- Main / transports ------------------------------------------------------


def run_stdio():
    """Run via stdio transport (default)."""
    mcp.run(transport="stdio")


def run_sse(host: str = "0.0.0.0", port: int = 8765):
    """Run via SSE/HTTP transport."""
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="sse")


def main():
    parser = argparse.ArgumentParser(description="Stationeers IC10 MCP Server")
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Run in SSE/HTTP mode instead of stdio",
    )
    parser.add_argument("--host", default="0.0.0.0", help="SSE bind host")
    parser.add_argument("--port", type=int, default=8765, help="SSE bind port")
    args = parser.parse_args()

    if args.sse or os.environ.get("MCP_TRANSPORT", "").lower() == "sse":
        run_sse(host=args.host, port=args.port)
    else:
        run_stdio()


if __name__ == "__main__":
    main()
