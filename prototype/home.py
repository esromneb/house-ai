"""LLM Prompt for controlling a home smart heating and temperature sustem.

"""

import time

from prompts import (
    prompt,
)

if __name__ == "__main__":
    model = "qooba/qwen3-coder-30b-a3b-instruct:q3_k_m"  # Model must support tool use

    # Record start time
    start_time = time.time()

    prompt_sentence = """You are an AI agent responsible for controlling the heating and hot-water systems of my house.
You interact with the smart-home devices through a local HTTP server at http://127.0.0.1:8099.

============================
SKILL: Thermostat Control
============================
The house has two rooms with independent thermostats: "living_room" and "bedroom".

Reading current temperatures (GET):
  • GET /thermostat/living_room/current_temp  → returns {"room": "living_room", "current_temp": <float>}
  • GET /thermostat/bedroom/current_temp      → returns {"room": "bedroom",     "current_temp": <float>}

Reading the set-point (target temperature) (GET):
  • GET /thermostat/living_room/set_temp      → returns {"room": "living_room", "set_temp": <float>}
  • GET /thermostat/bedroom/set_temp          → returns {"room": "bedroom",     "set_temp": <float>}

Reading all thermostat state at once (GET):
  • GET /thermostat                           → returns full thermostat state for both rooms

Changing the set-point (POST):
  • POST /thermostat/living_room/set_temp
    Body (JSON): {"set_temp": <desired_temp_float>}
    → returns {"ok": true, "room": "living_room", "set_temp": <new_value>}

  • POST /thermostat/bedroom/set_temp
    Body (JSON): {"set_temp": <desired_temp_float>}
    → returns {"ok": true, "room": "bedroom", "set_temp": <new_value>}

All temperatures are in degrees Fahrenheit.

============================
SKILL: Water Heater Control
============================
The house has one water heater.

Reading the current water temperature (GET):
  • GET /water_heater/current_temp            → returns {"current_temp": <float>}

Reading the water heater set-point (GET):
  • GET /water_heater/set_temp                → returns {"set_temp": <float>}

Reading all water heater state at once (GET):
  • GET /water_heater                         → returns full water heater state

Changing the water heater set-point (POST):
  • POST /water_heater/set_temp
    Body (JSON): {"set_temp": <desired_temp_float>}
    → returns {"ok": true, "set_temp": <new_value>}

Water temperature is in degrees Fahrenheit.

============================
GOAL
============================
Optimize my house for winter usage. Consider raising room temperatures to comfortable winter levels,
and ensure the water heater is set to an efficient but safe temperature for cold-weather use.
Explain your reasoning and list every HTTP request you would make, in order, with the exact URL, method, and JSON body.
"""
    response_text = prompt(prompt_sentence, model, False)

    print(response_text)

    # Record end time and print elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Run time: {elapsed_time:.2f} seconds")
