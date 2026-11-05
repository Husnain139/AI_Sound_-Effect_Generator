"""
Where generated sounds live.

Each sound is an audio file plus a `<id>.json` record. On Vercel the disk is
read-only, so sounds go to Vercel Blob; locally they go to ./sounds.
"""

import json
import mimetypes
import os
import shutil
from pathlib import Path

PREFIX = "sounds/"


class LocalStore:
    def __init__(self, directory: Path):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, meta: dict, audio: Path) -> dict:
        shutil.copy(audio, self.dir / meta["file"])
        meta["url"] = f"/sounds/{meta['file']}"
        (self.dir / f"{meta['id']}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    def list(self) -> list:
        items = []
        for p in self.dir.glob("*.json"):
            try:
                meta = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (self.dir / meta["file"]).exists():
                items.append(meta)
        return items

    def delete(self, sound_id: str) -> bool:
        meta_path = self.dir / f"{sound_id}.json"
        if not meta_path.exists():
            return False
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        (self.dir / meta["file"]).unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        return True


class BlobStore:
    """Public Vercel Blob store, so the browser can play blob URLs directly."""

    def __init__(self):
        from vercel.blob import sync as blob

        self.blob = blob

    def save(self, meta: dict, audio: Path) -> dict:
        content_type = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
        uploaded = self.blob.put_blob(
            PREFIX + meta["file"], audio.read_bytes(), access="public", content_type=content_type
        )
        meta["url"] = uploaded.url
        self.blob.put_blob(
            f"{PREFIX}{meta['id']}.json",
            json.dumps(meta, indent=2).encode(),
            access="public",
            content_type="application/json",
        )
        return meta

    def list(self) -> list:
        items = []
        for b in self.blob.query_blobs(prefix=PREFIX):
            if b.pathname.endswith(".json"):
                try:
                    items.append(json.loads(self.blob.get_blob(b.url, access="public").body))
                except Exception:
                    continue
        return items

    def delete(self, sound_id: str) -> bool:
        meta_path = f"{PREFIX}{sound_id}.json"
        try:
            meta = json.loads(self.blob.get_blob(meta_path, access="public").body)
        except self.blob.BlobNotFoundError:
            return False
        self.blob.delete_blob([meta["url"], meta_path])
        return True


def make_store(local_dir: Path):
    if os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv("BLOB_STORE_ID"):
        return BlobStore()
    if os.getenv("VERCEL"):
        raise RuntimeError(
            "No Vercel Blob store connected. Create a public Blob store in the Vercel dashboard "
            "(Storage tab) and connect it to this project."
        )
    if os.getenv("SOUNDS_DIR"):
        return LocalStore(Path(os.environ["SOUNDS_DIR"]))
    if os.getenv("RENDER"):
        print("[sfx-studio] WARNING: no BLOB_READ_WRITE_TOKEN or SOUNDS_DIR set; sounds are lost on every restart.")
    return LocalStore(local_dir)
