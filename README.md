# mcp-notes-poc

The smallest MCP setup that shows the whole loop: a server with the three primitives (tool, resource, prompt) and a hand-rolled client that lets you watch every hop between you, the model and the server.

```
you -> [Claude] -> tool_use -> [MCP server] -> tool_result -> [Claude] -> answer
```

Companion guide, interactive: **[MCP, wired up](https://neo-ninja.github.io/mcp-notes-poc/)**. A message player for four scenarios, a describe-a-tool lab that renders both wire formats live, a session simulator (stdio vs HTTP, memory vs database), two quizzes. The code here is the appendix to that guide.

## What it shows

**The model never talks to MCP.** It sees a tool list and answers with a `tool_use` JSON block. The client (here `client.py`, in Claude Code it's Claude Code) turns that into a JSON-RPC `tools/call`, runs it, and feeds the result back. Claude Code's permission prompt sits exactly at that seam.

**One line calls the LLM**, inside a loop. Once to pick the tool, once more to phrase the answer. A task that needs two tools goes round three times. That loop is the entire "agent loop".

**The docstring is the prompt.** No system prompt is written anywhere. The API wraps the tool definitions into a hidden system prompt, so the function docstring is what the model reads when deciding whether to call it. The schema comes from the type hints.

**Session = transport.** With stdio, each client launches its own private server process. State in memory dies with it. With HTTP, one shared server, and a session is just an ID. Either way, the connection is not storage.

## Files

| File | Role |
|---|---|
| `server.py` | `MCPServer("notes-poc")` with `add_note`, `search_notes` (tools), `notes://{title}` (resource), `summarize_notes` (prompt). In-memory dict on purpose. |
| `client.py` | Launches the server over stdio, converts `tools/list` into the Claude API's `tools=` shape, runs the tool-use loop, prints every hop. |
| `.mcp.json` | Registers the server with Claude Code (project scope). Run `claude` in this folder, then `/mcp`. |

## Run

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# server self-check, no model involved
.venv\Scripts\python.exe server.py --check

# the real thing: needs `ant auth login` once, or ANTHROPIC_API_KEY
.venv\Scripts\python.exe client.py
```

A real run:

```
[mcp] server offers: ['add_note', 'search_notes']

you> save a note called groceries: eggs and milk
  [llm] calling claude-opus-5-5 ...
  [llm wants] add_note({"title": "groceries", "body": "eggs and milk"})
  [mcp returned] Saved 'groceries' (1 notes total)
  [llm] calling claude-opus-5-5 ...
claude> I saved a note called "groceries" with "eggs and milk".

you> what notes mention eggs?
  [llm] calling claude-opus-5-5 ...
  [llm wants] search_notes({"query": "eggs"})
  [mcp returned] groceries
  [llm] calling claude-opus-5-5 ...
claude> One note mentions eggs: "groceries".
```

Inspect the server without any model: `npx @modelcontextprotocol/inspector .venv/Scripts/python.exe server.py`.

## Things that bit me

- **mcp 2.x renamed `FastMCP` to `MCPServer`.** `from mcp.server import MCPServer`. Most tutorials still show the 1.x import and fail with a migration-guide message.
- **`tools/list` says `inputSchema`, the Claude API wants `input_schema`.** That one renamed key is the entire "translation" a host does.
- **No API key needed locally.** `ant auth login` stores an OAuth profile the SDK picks up. An exported `ANTHROPIC_API_KEY` always wins over it.
- **Claude Code reads `.mcp.json` at startup only.** Edit it, restart `claude`.

## Deliberately not here

SQLite persistence and an HTTP transport. Both are a few lines and neither changes the mental model. The simulator in the guide covers what they'd change.
