import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

from data.config import RAW

UA = {"User-Agent": "citysim-detroit/0.1 (hackathon; contact via GitHub)"}
MANIFEST = RAW / "manifest.json"


def record(dest: Path, source_url: str, **extra) -> None:
    """Note one downloaded file in data/raw/manifest.json: source, size, time, plus any extras (rows, vintage)."""
    entries = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    entries[dest.relative_to(RAW).as_posix()] = {
        "source_url": source_url,
        "bytes": dest.stat().st_size,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **extra,
    }
    MANIFEST.write_text(json.dumps(entries, indent=1, sort_keys=True))


def looks_like_html(path: Path) -> bool:
    with open(path, "rb") as f:
        head = f.read(512).lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def exists(url: str) -> bool:
    try:
        r = requests.head(url, headers=UA, timeout=30, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False


def fetch(url: str, dest: Path, retries: int = 3, **manifest_extra) -> Path:
    """Download url to dest (skips if already there). Streams large files.

    Refuses to keep a web page: a data URL that answers with HTML is an error, not a dataset.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  have  {dest.name}")
        return dest
    for attempt in range(retries):
        try:
            tmp = dest.with_suffix(dest.suffix + ".part")
            with requests.get(url, headers=UA, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            if looks_like_html(tmp):
                tmp.unlink()
                raise RuntimeError(f"{url} returned a web page, not data")
            tmp.replace(dest)
            record(dest, url, **manifest_extra)
            print(f"  got   {dest.name}  ({dest.stat().st_size/1e6:.1f} MB)")
            return dest
        except requests.RequestException as e:
            print(f"  retry {attempt+1}/{retries} {url}: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def first_available(urls: list[str]) -> str:
    for u in urls:
        if exists(u):
            return u
    raise RuntimeError("none of these exist:\n  " + "\n  ".join(urls))
