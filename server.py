"""Minimal MCP server showing the 3 primitives: tools, resources, prompts.

Run standalone check:  .venv/Scripts/python.exe server.py --check
Claude Code runs it over stdio via .mcp.json.
"""
import sys
from mcp.server import MCPServer

mcp = MCPServer("notes-poc")
notes: dict[str, str] = {}  # ponytail: in-memory, lost on restart; swap for a file/sqlite if you want persistence


@mcp.tool()
def add_note(title: str, body: str) -> str:
    """Save a note under a title."""  # docstring = description the model sees
    notes[title] = body
    return f"Saved '{title}' ({len(notes)} notes total)"


@mcp.tool()
def search_notes(query: str) -> list[str]:
    """Return titles of notes whose title or body contains the query."""
    q = query.lower()
    return [t for t, b in notes.items() if q in t.lower() or q in b.lower()]


@mcp.resource("notes://{title}")
def read_note(title: str) -> str:
    """Read-only data the client can pull in (like a GET)."""
    return notes.get(title, f"No note named '{title}'")


@mcp.prompt()
def summarize_notes() -> str:
    """A reusable prompt template; shows up as a slash command in Claude Code."""
    return "Summarize these notes in 3 bullets:\n" + "\n".join(f"- {t}: {b}" for t, b in notes.items())


if __name__ == "__main__":
    if "--check" in sys.argv:
        import asyncio

        async def check():
            await mcp.call_tool("add_note", {"title": "mcp", "body": "Model Context Protocol"})
            print(await mcp.call_tool("search_notes", {"query": "protocol"}))
            print([t.name for t in await mcp.list_tools()])
        asyncio.run(check())
    else:
        mcp.run()  # stdio: client launches us as a subprocess and talks JSON-RPC over stdin/stdout
