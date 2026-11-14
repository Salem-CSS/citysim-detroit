import time
from pathlib import Path
import requests

UA = {"User-Agent": "citysim-detroit/0.1 (hackathon; contact via GitHub)"}

def exists(url: str) -> bool:
    try:
        r = requests.head(url, headers=UA, timeout=30, allow_redirects=True)
        return r.status_code == 200
    except requests.RequestException:
        return False

def fetch(url: str, dest: Path, retries: int = 3) -> Path:
    """Download url to dest (skips if already there). Streams large files."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  have  {dest.name}")
        return dest
    for attempt in range(retries):
        try:
            with requests.get(url, headers=UA, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                tmp.rename(dest)
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
