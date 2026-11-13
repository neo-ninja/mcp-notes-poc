"""Tiny MCP client + Claude: type a sentence, watch every hop.

    you -> [LLM] -> tool_use -> [MCP server] -> tool_result -> [LLM] -> answer

Run: .venv/Scripts/python.exe client.py
Auth: `ant auth login` once (SDK picks up the profile), or set ANTHROPIC_API_KEY.
"""
import asyncio
import json
import sys

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command=sys.executable, args=["server.py"])
MODEL = "claude-opus-5-5"


async def main():
    # 1. Launch server.py as a subprocess and do the MCP handshake (once, kept open)
    async with stdio_client(SERVER) as (read, write), ClientSession(read, write) as mcp:
        await mcp.initialize()

        # 2. Ask the server what it offers, translate to Claude's tool format
        tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
            for t in (await mcp.list_tools()).tools
        ]
        print(f"[mcp] server offers: {[t['name'] for t in tools]}\n")

        llm = anthropic.Anthropic()
        messages = []  # the API is stateless: we resend the whole history every call
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not text:
                continue
            messages.append({"role": "user", "content": text})

            while True:
                # 3. >>> THE ONLY PLACE THE LLM IS CALLED <<<
                print(f"  [llm] calling {MODEL} ...")
                resp = llm.messages.create(model=MODEL, max_tokens=16000, tools=tools, messages=messages)
                messages.append({"role": "assistant", "content": resp.content})

                for b in resp.content:
                    if b.type == "text":
                        print(f"claude> {b.text}")
                if resp.stop_reason != "tool_use":
                    break  # model is done talking

                # 4. Model asked for tools: we (not the model) execute them via MCP
                results = []
                for b in resp.content:
                    if b.type != "tool_use":
                        continue
                    print(f"  [llm wants] {b.name}({json.dumps(b.input)})")
                    r = await mcp.call_tool(b.name, b.input)
                    out = "\n".join(c.text for c in r.content if c.type == "text")
                    print(f"  [mcp returned] {out}")
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out, "is_error": r.is_error})
                # 5. Hand results back; loop so the model can use them
                messages.append({"role": "user", "content": results})
            print()


asyncio.run(main())
