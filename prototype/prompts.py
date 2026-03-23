"""Prompt helper utilities shared between prototype and whatever else.

Put prompts in here and formatting strings in here
"""
from enum import Enum
from typing import Optional, Dict
import json
import re
import os
import ollama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

SEED = 4104859417


def extract_json(text: str) -> str:
    """Return the first JSON object substring found in `text`.

    This tries to be forgiving of models that wrap JSON in markdown fences.
    """
    # Remove markdown fences
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "").strip()

    # Find first JSON object in text
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")

    json_str = match.group(0)

    return json.loads(json_str)


# Json mode is 2x slower
# Potential better approach:
# Run without JSON mode
# Validate JSON in code
# If invalid → retry once with JSON mode
def prompt(p: str, model: str, json:bool):
    try:
        client = ollama.Client(host=OLLAMA_BASE_URL)
        
        opts = {'seed': SEED, 'temperature': 0}
        if json:
            response = client.generate(model=model, prompt=p, format="json", options=opts)
        else:
            response = client.generate(model=model, prompt=p, options=opts)
        # passing temp 0 gives a different result, because we are using the default temp
        #  but ALSO passing a seed. so there is a random applied but it's always the same
        # response = client.generate(model=model, prompt=p, options={'seed': SEED, 'temperature': 0})
        # response = client.generate(model=model, prompt=p, format="json", options={'seed': SEED})
        response_text = response['response'] if isinstance(response, dict) else getattr(response, 'response', str(response))
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    return response_text
