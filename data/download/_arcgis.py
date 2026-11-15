"""Page a whole ArcGIS feature-service layer to one GeoJSON file.

The city's layers cap each response (1,000 or 2,000 rows), so a layer is read in pages ordered by
its object id. The download fails unless the number of features written equals the layer's own count.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import requests

from data.download._http import UA, record


def _get(url: str, params: dict, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=180)
            r.raise_for_status()
            body = r.json()
            if "error" in body:
                raise RuntimeError(f"{url}: {body['error']}")
            return body
        except (requests.RequestException, ValueError, RuntimeError) as e:
            if attempt == retries - 1:
                raise RuntimeError(f"failed after {retries} tries: {url} {params}: {e}")
            time.sleep(3 * (attempt + 1))


def layer_meta(layer_url: str) -> dict:
    return _get(layer_url, {"f": "json"})


def fetch_layer(layer_url: str, dest: Path, drop_fields: tuple[str, ...] = (), workers: int = 4, **manifest_extra) -> Path:
    """Download every feature of one layer to dest as GeoJSON (WGS84). Skips if dest exists."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  have  {dest.name}")
        return dest
    meta = layer_meta(layer_url)
    names = [f["name"] for f in meta["fields"]]
    missing = [f for f in drop_fields if f not in names]
    if missing:
        raise RuntimeError(f"{layer_url}: columns to drop are not in the layer: {missing}")
    out_fields = ",".join(n for n in names if n not in drop_fields) if drop_fields else "*"
    total = _get(layer_url + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    page = meta["maxRecordCount"]
    oid = meta["objectIdField"]

    def one(offset: int, count: int | None = None, retries: int = 5) -> list[dict]:
        count = count or page
        try:
            body = _get(layer_url + "/query", {
                "where": "1=1", "outFields": out_fields, "outSR": 4326, "f": "geojson",
                "orderByFields": oid, "resultOffset": offset, "resultRecordCount": count,
            }, retries=retries)
            return body["features"]
        except RuntimeError:
            # Some pages are refused whole (the server answers 400) though their rows are fine in
            # smaller requests. Split the page; a single row that still fails stops the download.
            if count == 1:
                raise
            half = count // 2
            return one(offset, half, 2) + one(offset + half, count - half, 2)

    tmp = dest.with_suffix(dest.suffix + ".part")
    written = 0
    with open(tmp, "w", encoding="utf-8") as f, ThreadPoolExecutor(workers) as pool:
        f.write('{"type":"FeatureCollection","features":[\n')
        for feats in pool.map(one, range(0, total, page)):
            for feat in feats:
                f.write(("," if written else "") + json.dumps(feat, separators=(",", ":")) + "\n")
                written += 1
        f.write("]}\n")
    if written != total:
        tmp.unlink()
        raise RuntimeError(f"{layer_url}: layer reports {total} features but {written} were downloaded")
    tmp.replace(dest)
    edited = (meta.get("editingInfo") or {}).get("lastEditDate")
    record(dest, layer_url, rows=written, layer_name=meta.get("name"),
           layer_last_edit_utc=datetime.fromtimestamp(edited / 1000, timezone.utc).isoformat(timespec="seconds") if edited else None,
           dropped_columns=list(drop_fields), **manifest_extra)
    print(f"  got   {dest.name}  ({written:,} rows, {dest.stat().st_size/1e6:.1f} MB)")
    return dest
