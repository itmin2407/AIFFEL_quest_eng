import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def load_labels():
    path = BASE_DIR / "data" / "labels.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_config():
    path = BASE_DIR / "data" / "config.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)