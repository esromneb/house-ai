"""Mock web server for smart home control (thermostat + water heater).

Stores all state in RAM. Prints every request to stdout for debugging.
Run with:  python prototype/mock_server.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# ── In-memory state ──────────────────────────────────────────────────────────

state = {
    "thermostat": {
        "living_room": {"current_temp": 68.0, "set_temp": 70.0},
        "bedroom":     {"current_temp": 65.0, "set_temp": 68.0},
    },
    "water_heater": {
        "current_temp": 120.0,
        "set_temp": 120.0,
    },
}

# ── Request handler ──────────────────────────────────────────────────────────

class SmartHomeHandler(BaseHTTPRequestHandler):

    # ── helpers ──────────────────────────────────────────────────────────────

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def _log(self, method):
        print(f"[{method}] {self.path}")

    # ── GET routes ───────────────────────────────────────────────────────────

    def do_GET(self):
        self._log("GET")
        path = self.path.rstrip("/")

        # --- thermostat -------------------------------------------------
        if path == "/thermostat/living_room/current_temp":
            self._send_json({"room": "living_room", "current_temp": state["thermostat"]["living_room"]["current_temp"]})

        elif path == "/thermostat/bedroom/current_temp":
            self._send_json({"room": "bedroom", "current_temp": state["thermostat"]["bedroom"]["current_temp"]})

        elif path == "/thermostat/living_room/set_temp":
            self._send_json({"room": "living_room", "set_temp": state["thermostat"]["living_room"]["set_temp"]})

        elif path == "/thermostat/bedroom/set_temp":
            self._send_json({"room": "bedroom", "set_temp": state["thermostat"]["bedroom"]["set_temp"]})

        elif path == "/thermostat":
            self._send_json(state["thermostat"])

        # --- water heater -----------------------------------------------
        elif path == "/water_heater/current_temp":
            self._send_json({"current_temp": state["water_heater"]["current_temp"]})

        elif path == "/water_heater/set_temp":
            self._send_json({"set_temp": state["water_heater"]["set_temp"]})

        elif path == "/water_heater":
            self._send_json(state["water_heater"])

        else:
            self._send_json({"error": "not found"}, 404)

    # ── POST routes ──────────────────────────────────────────────────────────

    def do_POST(self):
        self._log("POST")
        path = self.path.rstrip("/")
        body = self._read_body()
        print(f"  body: {body}")

        # --- thermostat set-point ---------------------------------------
        if path == "/thermostat/living_room/set_temp":
            if "set_temp" in body:
                state["thermostat"]["living_room"]["set_temp"] = float(body["set_temp"])
                self._send_json({"ok": True, "room": "living_room", "set_temp": state["thermostat"]["living_room"]["set_temp"]})
            else:
                self._send_json({"error": "missing 'set_temp' in body"}, 400)

        elif path == "/thermostat/bedroom/set_temp":
            if "set_temp" in body:
                state["thermostat"]["bedroom"]["set_temp"] = float(body["set_temp"])
                self._send_json({"ok": True, "room": "bedroom", "set_temp": state["thermostat"]["bedroom"]["set_temp"]})
            else:
                self._send_json({"error": "missing 'set_temp' in body"}, 400)

        # --- water heater set-point -------------------------------------
        elif path == "/water_heater/set_temp":
            if "set_temp" in body:
                state["water_heater"]["set_temp"] = float(body["set_temp"])
                self._send_json({"ok": True, "set_temp": state["water_heater"]["set_temp"]})
            else:
                self._send_json({"error": "missing 'set_temp' in body"}, 400)

        else:
            self._send_json({"error": "not found"}, 404)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 8099
    server = HTTPServer((HOST, PORT), SmartHomeHandler)
    print(f"Mock smart-home server running on http://{HOST}:{PORT}")
    print("Endpoints:")
    print("  GET  /thermostat                          – all thermostat state")
    print("  GET  /thermostat/living_room/current_temp  – living room current temp")
    print("  GET  /thermostat/bedroom/current_temp      – bedroom current temp")
    print("  GET  /thermostat/living_room/set_temp      – living room set point")
    print("  GET  /thermostat/bedroom/set_temp          – bedroom set point")
    print("  POST /thermostat/living_room/set_temp      – set living room target  {\"set_temp\": 72}")
    print("  POST /thermostat/bedroom/set_temp          – set bedroom target      {\"set_temp\": 68}")
    print("  GET  /water_heater                         – all water heater state")
    print("  GET  /water_heater/current_temp            – water heater current temp")
    print("  GET  /water_heater/set_temp                – water heater set point")
    print("  POST /water_heater/set_temp                – set water heater target  {\"set_temp\": 125}")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
