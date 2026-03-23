"""AI agent that controls a smart thermostat and water heater via curl.

Uses LangChain's create_agent (LangGraph-based) with a shell/curl tool so the
LLM can actually hit the mock smart-home server (prototype/mock_server.py).

The GETs are done in Python so the LLM's only job is to issue POSTs.
"""

import subprocess
import json
import time
import os
import warnings
import urllib.request

warnings.filterwarnings("ignore")

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

BASE_URL = "http://127.0.0.1:8099"


# ── helpers ──────────────────────────────────────────────────────────────────

def http_get(path: str) -> dict:
    """Quick GET against the mock server, returns parsed JSON."""
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return json.loads(resp.read())


# ── curl tool (for the LLM to POST) ─────────────────────────────────────────

@tool
def curl(command: str) -> str:
    """Run a curl shell command to make HTTP POST requests against the smart-home server.
    Example:
      curl -X POST http://127.0.0.1:8099/thermostat/living_room/set_temp -H 'Content-Type: application/json' -d '{"set_temp": 72}'
    """
    # LLMs sometimes pass just the URL — prepend curl if needed
    cmd = command.strip()
    if not cmd.startswith("curl"):
        cmd = f"curl -s {cmd}"
    try:
        result = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
        return result
    except subprocess.CalledProcessError as e:
        return f"ERROR (exit {e.returncode}): {e.output}"


# ── target schedule ──────────────────────────────────────────────────────────

SCHEDULE = """TARGET VALUES BY TIME OF DAY (winter schedule):
  Time Period          | Living Room | Bedroom | Water Heater
  Night  (10 PM – 6 AM) |   62°F      |  60°F   |   110°F
  Morning (6 AM – 9 AM) |   72°F      |  70°F   |   125°F
  Day    (9 AM – 5 PM)  |   68°F      |  66°F   |   120°F
  Evening (5 PM – 10 PM)|   72°F      |  70°F   |   125°F"""


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # model = "llama3:latest"
    model = "llama3-groq-tool-use"  # Model must support tool use
    # model = "qooba/qwen3-coder-30b-a3b-instruct:q3_k_m" # Works for prompting but not for tools

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    llm = ChatOllama(model=model, base_url=OLLAMA_BASE_URL, temperature=0)

    system_prompt = f"""You are an AI agent that controls a home's thermostat and water heater.
You have a tool called "curl" to make HTTP POST requests to http://127.0.0.1:8099.

{SCHEDULE}

RULES:
- I will tell you the current time and current set-points.
- Compare each set-point to the target for the current time period.
- For EACH set-point that does not match: you MUST call the curl tool with a POST to change it.
- If all set-points already match: respond with "No changes needed."
- Do NOT just describe what you would do. Actually call the curl tool.

POST commands:
  Living room:  curl -X POST http://127.0.0.1:8099/thermostat/living_room/set_temp -H 'Content-Type: application/json' -d '{{"set_temp": <value>}}'
  Bedroom:      curl -X POST http://127.0.0.1:8099/thermostat/bedroom/set_temp -H 'Content-Type: application/json' -d '{{"set_temp": <value>}}'
  Water heater: curl -X POST http://127.0.0.1:8099/water_heater/set_temp -H 'Content-Type: application/json' -d '{{"set_temp": <value>}}'
"""

    agent = create_agent(
        llm,
        tools=[curl],
        system_prompt=system_prompt,
    )

    LOOP_DELAY = 5  # seconds between agent iterations
    iteration = 0

    print("Starting agent loop (Ctrl+C to stop)...")
    print(f"Polling every {LOOP_DELAY}s\n")

    try:
        while True:
            iteration += 1
            print(f"\n{'=' * 60}")
            print(f"ITERATION {iteration}")
            print(f"{'=' * 60}")

            # ── 1. Read state ourselves (GETs) ──────────────────────────
            try:
                time_data = http_get("/time")
                thermo_data = http_get("/thermostat")
                water_data = http_get("/water_heater")
            except Exception as e:
                print(f"  ERROR reading state: {e}")
                time.sleep(LOOP_DELAY)
                continue

            current_time = time_data["time"]
            hour = time_data["hour"]
            print(f"  Time: {current_time}  (hour={hour})")
            print(f"  Thermostat: living_room set={thermo_data['living_room']['set_temp']}, bedroom set={thermo_data['bedroom']['set_temp']}")
            print(f"  Water heater: set={water_data['set_temp']}")

            # ── 2. Build user message with current state ────────────────
            user_msg = f"""Current time: {time_data['time']} (hour {hour})
Current set-points:
  - Living room: {thermo_data['living_room']['set_temp']}°F
  - Bedroom: {thermo_data['bedroom']['set_temp']}°F
  - Water heater: {water_data['set_temp']}°F

Look up the target values for hour {hour} in the winter schedule.
If any set-point differs from the target, call curl to POST the correct value NOW.
Do not explain first — just make the curl calls, then summarize what you did."""

            # ── 3. Run agent with continuation loop ───────────────────
            # Some models only make one tool call per turn, so we loop until
            # either: (a) no tool calls made, or (b) max rounds reached.
            start_time = time.time()
            messages = [HumanMessage(content=user_msg)]
            max_rounds = 5
            total_tool_calls = 0

            for round_num in range(1, max_rounds + 1):
                print(f"\n  --- Round {round_num} ---")
                
                # Run the agent graph
                result = agent.invoke({"messages": messages})
                
                # Extract messages from result
                result_messages = result.get("messages", [])
                round_tool_calls = 0
                final_content = ""
                
                # Process and display each message
                for msg in result_messages:
                    # Skip the initial human message we sent
                    if msg.type == "human" and msg.content == user_msg:
                        continue
                    
                    content_preview = msg.content[:300] if msg.content else "(no content)"
                    print(f"  [{msg.type}] {content_preview}")
                    
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"    -> tool_call: {tc['name']}({tc['args']})")
                            round_tool_calls += 1
                    
                    # Track the final AI message content
                    if msg.type == "ai" and msg.content:
                        final_content = msg.content
                
                total_tool_calls += round_tool_calls
                
                # If no tool calls this round, the agent is done
                if round_tool_calls == 0:
                    print(f"  (no tool calls — done)")
                    break
                
                # Otherwise, continue the conversation
                # Update messages to be the full history, then add a follow-up
                messages = result_messages + [
                    HumanMessage(content="Continue. If there are more set-points that need changing, call curl for each one now. If all set-points are now correct, say 'All done.'")
                ]

            elapsed = time.time() - start_time
            print(f"\n  SUMMARY: {total_tool_calls} tool call(s) across {round_num} round(s) ({elapsed:.2f}s)")

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print(f"\n\nStopped after {iteration} iterations.")
