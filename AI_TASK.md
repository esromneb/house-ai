# AI Smart Home Agent — Task Summary

## Goal

Build a local AI agent that controls a smart thermostat and water heater via an LLM (Ollama) that can make real HTTP requests against a mock smart-home server.

## Architecture

```
┌─────────────┐       curl (POST)       ┌──────────────────┐
│  home.py    │ ──────────────────────▶  │  mock_server.py  │
│  (LLM agent)│ ◀────────────────────── │  (HTTP on :8099) │
│             │       JSON responses     │                  │
│  Python does│                          │  In-RAM state:   │
│  GETs first,│                          │  - thermostat    │
│  feeds state│                          │  - water heater  │
│  into prompt│                          │  - fake/real time│
└─────────────┘                          └──────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `prototype/mock_server.py` | Standalone HTTP server (stdlib only). Stores thermostat (2 rooms) and water heater state in RAM. Serves a `/time` endpoint with real or fake (60× speed) clock. |
| `prototype/home.py` | LangChain agent loop. Reads state via Python `urllib`, feeds current time + set-points into the LLM prompt, then lets the LLM call `curl` to POST any needed changes. Loops every 5 seconds. |

## Tech Stack

- **Python 3.10** (venv: `venv/`)
- **Ollama** — local LLM server
- **LangChain 1.2.13** — `create_agent` (LangGraph-based)
- **langchain-ollama** — `ChatOllama` with `bind_tools()` support
- **langchain-community** — installed but deprecated `ChatOllama` (do not use)

### Key pip packages (in `venv`)
```
langchain==1.2.13
langchain-ollama
langchain-community
langchain-core
langgraph
ollama
python-dotenv
```

## Mock Server Endpoints

### Time
- `GET /time` — returns `{"datetime", "hour", "minute", "date", "time"}`

### Thermostat (two rooms: `living_room`, `bedroom`)
- `GET /thermostat` — full state
- `GET /thermostat/<room>/current_temp`
- `GET /thermostat/<room>/set_temp`
- `POST /thermostat/<room>/set_temp` — body: `{"set_temp": <float>}`

### Water Heater
- `GET /water_heater` — full state
- `GET /water_heater/current_temp`
- `GET /water_heater/set_temp`
- `POST /water_heater/set_temp` — body: `{"set_temp": <float>}`

### Fake time mode
```bash
python3 prototype/mock_server.py --fake-time
# 1 real minute = 1 simulated hour, starts at midnight
```

## Winter Schedule (hardcoded in home.py)

| Time Period | Living Room | Bedroom | Water Heater |
|---|---|---|---|
| Night (10 PM – 6 AM) | 62°F | 60°F | 110°F |
| Morning (6 AM – 9 AM) | 72°F | 70°F | 125°F |
| Day (9 AM – 5 PM) | 68°F | 66°F | 120°F |
| Evening (5 PM – 10 PM) | 72°F | 70°F | 125°F |

## Key Design Decisions & Lessons Learned

1. **LangChain API churn**: `initialize_agent` was removed in LangChain 1.x. We use `create_agent` from `langchain.agents` which returns a LangGraph `CompiledStateGraph`.

2. **`ChatOllama` must come from `langchain-ollama`**, not `langchain-community`. The community version doesn't support `bind_tools()` which `create_agent` requires.

3. **LLM won't POST after GETting**: When the LLM was responsible for both GETs and POSTs, it would do the GETs, see the results, then output text saying "I will now POST..." but end its turn before actually calling tools again. Small local models (llama3, llama3-groq-tool-use) treat one round of tool calls as "done."

4. **Solution — Python does GETs, LLM only POSTs**: We read state in Python with `urllib`, inject it into the user message, so the LLM's first (and only) tool call round is the POSTs. This is far more reliable.

5. **curl prefix fix**: The LLM sometimes passes just the URL (`http://...`) instead of a full `curl ...` command. The tool auto-prepends `curl -s` if the input doesn't start with `curl`.

6. **Models tested**: `llama3:latest` (best classification accuracy), `llama3-groq-tool-use` (current default for tool use), `qwen3-coder-30b`. The groq-tool-use model is specifically fine-tuned for tool calling.

## Current Status

- Mock server works, with both real and fake time.
- Agent loop runs, reads state, feeds it to the LLM, and the LLM is instructed to POST changes.
- **Still validating** whether `llama3-groq-tool-use` reliably issues the POST tool calls (vs just describing them). This is the core open issue.

## How to Run

```bash
# Terminal 1 — start mock server (use --fake-time for accelerated testing)
source venv/bin/activate
python3 prototype/mock_server.py --fake-time

# Terminal 2 — start agent
source venv/bin/activate
python3 -u prototype/home.py
```

## Future Work / Resume Points

### Immediate (fixing the POST problem)
- **Try different models**: Some models are better at tool calling. Try `qwen3-coder-30b`, `mistral`, or a larger llama variant. The model must support structured tool-calling (not just text generation).
- **Bypass LLM for simple logic**: If the model still won't reliably POST, consider having Python compute the diffs itself and only use the LLM for reasoning about *unusual* situations (e.g., "should I override the schedule because outdoor temp is extreme?").
- **Add a fallback**: If the agent's response contains no tool calls but mentions needing to change something, Python could parse the answer and make the POSTs itself.

### Enhancements
- **Simulate current_temp drift**: The mock server could simulate room temps drifting toward/away from set_temp based on a simple thermal model (e.g., rooms cool toward 40°F outdoor temp, heating system pushes toward set_temp).
- **Add outdoor temperature endpoint**: `GET /weather` returning simulated outdoor temp that varies by time of day. The agent could factor this into decisions.
- **Add occupancy sensor**: `GET /occupancy/<room>` — agent could lower temps in unoccupied rooms.
- **Persistent conversation**: Currently each loop iteration is a fresh conversation. Could maintain message history so the agent remembers what it did last time and avoids redundant changes.
- **Move to real smart-home APIs**: Replace mock server with actual Home Assistant or similar integration.
- **Add energy usage tracking**: `GET /energy` endpoint showing simulated kWh usage, let the agent optimize for cost.
- **Web dashboard**: Simple HTML page served by mock_server showing current state, time, and a log of agent actions.
- **Multiple seasons**: Let user specify season, or auto-detect from date, with different schedules.
- **User override support**: `POST /override` so a human can temporarily override the agent's settings, and the agent respects the override for N hours.
