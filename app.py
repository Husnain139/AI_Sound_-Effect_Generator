"""
SFX Studio — local web app for generating sound effects.

The browser talks to this FastAPI server; the server calls the Stable Audio 3
Space on Hugging Face (via gradio_client) with your HF token, then saves every
generated sound + a small JSON record (prompt, model, date, license) via storage.py
(Vercel Blob when a store is connected, otherwise ./sounds).
"""

import os
import re
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from gradio_client import Client
from pydantic import BaseModel, Field

from storage import LocalStore, make_store

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN") or None
SPACE_ID = os.getenv("SPACE_ID", "stabilityai/stable-audio-3")
API_NAME = os.getenv("API_NAME") or None          # e.g. "/generate" — leave empty to auto-detect
MODEL_CHOICE = os.getenv("MODEL_CHOICE") or None  # e.g. "small-sfx" — leave empty to auto-pick an SFX model

BASE_DIR = Path(__file__).parent
SOUNDS_DIR = BASE_DIR / "sounds"
store = make_store(SOUNDS_DIR)
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
LICENSE_NOTE = "Generated with Stable Audio 3 (Stability AI Community License — see stability.ai/license)"

_client = None
_endpoint = None
_lock = threading.Lock()


# ---------------------------------------------------------------- HF Space ---

def _param_key(p: dict) -> str:
    return f"{p.get('parameter_name') or ''} {p.get('label') or ''}".lower()


def _pick_endpoint(api_info: dict):
    """Find the Space endpoint that takes a text prompt."""
    named = api_info.get("named_endpoints", {})
    if not named:
        raise RuntimeError("This Space exposes no API endpoints.")

    if API_NAME:
        if API_NAME not in named:
            raise RuntimeError(f"API_NAME {API_NAME} not found. Available: {list(named)}")
        return API_NAME, named[API_NAME]["parameters"]

    best, best_score = None, -1
    for name, info in named.items():
        params = info.get("parameters", [])
        keys = [_param_key(p) for p in params]
        score = 0
        if any(re.search(r"prompt|text|description", k) and "negative" not in k for k in keys):
            score += 10
        if any(re.search(r"duration|seconds|length", k) for k in keys):
            score += 5
        if "generate" in name.lower():
            score += 3
        if score > best_score:
            best, best_score = name, score

    if best_score < 10:
        raise RuntimeError(
            "Could not find a text-prompt endpoint automatically. "
            "Run `python inspect_space.py` and set API_NAME in .env."
        )
    return best, named[best]["parameters"]


def _choices(p: dict):
    t = p.get("type") or {}
    return t.get("enum") or []


def _build_kwargs(params: list, prompt: str, duration: float) -> dict:
    kwargs = {}
    prompt_set = False
    for p in params:
        name = p.get("parameter_name")
        if not name:
            continue
        key = _param_key(p)
        py_type = str((p.get("python_type") or {}).get("type", "")).lower()

        if "negative" in key:
            continue  # keep the Space's default
        if not prompt_set and re.search(r"prompt|text|description", key):
            kwargs[name] = prompt
            prompt_set = True
        elif re.search(r"duration|seconds|length", key):
            kwargs[name] = int(round(duration)) if py_type == "int" else float(duration)
        elif re.search(r"model", key) and _choices(p):
            choices = _choices(p)
            if MODEL_CHOICE and MODEL_CHOICE in choices:
                kwargs[name] = MODEL_CHOICE
            else:
                sfx = [c for c in choices if "sfx" in str(c).lower()]
                kwargs[name] = sfx[0] if sfx else choices[0]
        elif not p.get("parameter_has_default", True):
            kwargs[name] = None  # e.g. optional init-audio inputs

    if not prompt_set:
        raise RuntimeError("Endpoint has no prompt parameter. Check API_NAME in .env.")
    return kwargs


def _find_audio(result):
    """Dig the generated audio file path out of whatever the Space returned."""
    if isinstance(result, str):
        p = Path(result)
        return p if p.suffix.lower() in AUDIO_EXTS and p.exists() else None
    if isinstance(result, dict):
        for k in ("path", "value", "name"):
            found = _find_audio(result.get(k))
            if found:
                return found
    if isinstance(result, (list, tuple)):
        for item in result:
            found = _find_audio(item)
            if found:
                return found
    return None


def get_client():
    global _client, _endpoint
    with _lock:
        if _client is None:
            client = Client(SPACE_ID, token=HF_TOKEN, verbose=False)
            info = client.view_api(return_format="dict", print_info=False)
            _endpoint = _pick_endpoint(info)
            _client = client
            print(f"[sfx-studio] Using {SPACE_ID} endpoint {_endpoint[0]}")
    return _client, _endpoint


# ---------------------------------------------------------------- helpers ---

def _slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s[:limit].rstrip("-")) or "sound"


# -------------------------------------------------------------------- API ---

app = FastAPI(title="SFX Studio")


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=400)
    duration: float = Field(default=3, ge=0.5, le=30)


@app.post("/api/generate")
def generate(req: GenerateRequest):
    try:
        client, (api_name, params) = get_client()
        kwargs = _build_kwargs(params, req.prompt.strip(), req.duration)
        result = client.predict(api_name=api_name, **kwargs)
    except Exception as e:
        msg = str(e)
        low = msg.lower()
        if "quota" in low or "zerogpu" in low:
            raise HTTPException(429, "Hugging Face GPU quota used up for now. Try again later, or use a PRO token.")
        if "401" in msg or "unauthorized" in low or "gated" in low:
            raise HTTPException(401, "Hugging Face refused the token. Check HF_TOKEN in .env.")
        raise HTTPException(502, f"Generation failed: {msg[:300]}")

    src = _find_audio(result)
    if not src:
        raise HTTPException(502, "The Space answered, but no audio file came back. Run inspect_space.py to check the endpoint.")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sound_id = f"{stamp}_{_slug(req.prompt)}"

    meta = {
        "id": sound_id,
        "prompt": req.prompt.strip(),
        "duration": req.duration,
        "file": f"{sound_id}{src.suffix.lower()}",
        "space": SPACE_ID,
        "endpoint": api_name,
        "settings": {k: v for k, v in kwargs.items() if v is not None},
        "created": datetime.now().isoformat(timespec="seconds"),
        "license": LICENSE_NOTE,
    }
    try:
        return store.save(meta, src)
    except Exception as e:
        raise HTTPException(502, f"Sound was generated but could not be saved: {str(e)[:300]}")


@app.get("/api/sounds")
def list_sounds():
    return sorted(store.list(), key=lambda m: m["created"], reverse=True)


@app.delete("/api/sounds/{sound_id}")
def delete_sound(sound_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", sound_id):
        raise HTTPException(400, "Bad id")
    if not store.delete(sound_id):
        raise HTTPException(404, "Sound not found")
    return {"deleted": sound_id}


if isinstance(store, LocalStore):
    app.mount("/sounds", StaticFiles(directory=store.dir), name="sounds")
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
