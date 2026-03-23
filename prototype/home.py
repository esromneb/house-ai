"""AI agent that controls a smart thermostat and water heater via curl.

Uses LangChain's create_agent (LangGraph-based) with a shell/curl tool so the
LLM can actually hit the mock smart-home server (prototype/mock_server.py).
"""

import subprocess
import time
import os
import warnings

warnings.filterwarnings("ignore")

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage


# ── curl tool ────────────────────────────────────────────────────────────────

@tool
def curl(command: str) -> str:
    """Run a curl shell command to make HTTP GET or POST requests against the smart-home server.
    Examples:
      GET:  curl http://127.0.0.1:8099/thermostat
      POST: curl -X POST http://127.0.0.1:8099/thermostat/living_room/set_temp -H 'Content-Type: application/json' -d '{"set_temp": 72}'
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


# ── main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # model = "llama3:latest"
    model = "llama3-groq-tool-use"  # Model must support tool use
    # model = "qooba/qwen3-coder-30b-a3b-instruct:q3_k_m" # Works for prompting but not for tools

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    llm = ChatOllama(model=model, base_url=OLLAMA_BASE_URL, temperature=0)

    system_prompt = """You are an AI agent responsible for controlling the heating and hot-water systems of my house.
You have a tool called "curl" that lets you run curl commands against a local HTTP server at http://127.0.0.1:8099.

============================
SKILL: Thermostat Control
============================
The house has two rooms with independent thermostats: "living_room" and "bedroom".

Reading current temperatures (GET):
  curl http://127.0.0.1:8099/thermostat/living_room/current_temp
  curl http://127.0.0.1:8099/thermostat/bedroom/current_temp

Reading the set-point / target temperature (GET):
  curl http://127.0.0.1:8099/thermostat/living_room/set_temp
  curl http://127.0.0.1:8099/thermostat/bedroom/set_temp

Reading all thermostat state at once (GET):
  curl http://127.0.0.1:8099/thermostat

Changing a room's set-point (POST):
  curl -X POST http://127.0.0.1:8099/thermostat/living_room/set_temp -H 'Content-Type: application/json' -d '{"set_temp": 72}'
  curl -X POST http://127.0.0.1:8099/thermostat/bedroom/set_temp -H 'Content-Type: application/json' -d '{"set_temp": 68}'

All temperatures are in degrees Fahrenheit.

============================
SKILL: Water Heater Control
============================
The house has one water heater.

Reading the current water temperature (GET):
  curl http://127.0.0.1:8099/water_heater/current_temp

Reading the water heater set-point (GET):
  curl http://127.0.0.1:8099/water_heater/set_temp

Reading all water heater state at once (GET):
  curl http://127.0.0.1:8099/water_heater

Changing the water heater set-point (POST):
  curl -X POST http://127.0.0.1:8099/water_heater/set_temp -H 'Content-Type: application/json' -d '{"set_temp": 125}'

Water temperature is in degrees Fahrenheit.
"""

    user_goal = """Optimize my house for winter usage.
First, read the current state of the thermostat and water heater.
Then, raise room temperatures to comfortable winter levels and ensure the water heater
is set to an efficient but safe temperature for cold-weather use.
Use the curl tool to make real HTTP requests. Do not just describe what you would do — actually do it."""

    agent = create_agent(
        llm,
        tools=[curl],
        system_prompt=system_prompt,
    )

    start_time = time.time()

    # Stream events so we can see the agent's tool calls as they happen
    final_message = None
    for event in agent.stream(
        {"messages": [HumanMessage(content=user_goal)]},
        stream_mode="updates",
    ):
        for node_name, node_output in event.items():
            if "messages" in node_output:
                for msg in node_output["messages"]:
                    print(f"[{node_name}] {msg.type}: {msg.content[:200] if msg.content else '(tool call)'}")
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            print(f"  -> tool_call: {tc['name']}({tc['args']})")
                    final_message = msg

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("AGENT FINAL ANSWER:")
    print("=" * 60)
    if final_message and final_message.content:
        print(final_message.content)
    print(f"\nTotal run time: {elapsed:.2f} seconds")
