"""Build the Detroit buildings table in Athena and download it.

Runs sql/01..04 in order against Athena in us-west-2 (where the Overture bucket
lives), then copies the clipped Parquet to data/processed/buildings/.

    python -m data.buildings.athena_build --bucket citysim-athena-<acct>-usw2
    python -m data.buildings.athena_build --bucket ... --download-only

Needs AWS credentials with Athena + Glue + S3 on your bucket. Cost: ~150 MB
scanned per full run (well under a cent; Free plan accounts are not charged).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = Path(__file__).parent / "sql"
OUT_DIR = ROOT / "data" / "processed" / "buildings"
REGION = "us-west-2"


def statements(text: str, **fmt) -> list[str]:
    """Split a .sql file into statements, dropping comments, filling {placeholders}."""
    text = re.sub(r"--[^\n]*", "", text)
    for k, v in fmt.items():
        text = text.replace("{" + k + "}", v)
    return [s.strip() for s in text.split(";") if s.strip()]


def run(athena, sql: str, output: str) -> dict:
    qid = athena.start_query_execution(
        QueryString=sql, ResultConfiguration={"OutputLocation": output}
    )["QueryExecutionId"]
    while True:
        q = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        state = q["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)
    if state != "SUCCEEDED":
        raise RuntimeError(f"{state}: {q['Status'].get('StateChangeReason')}\n{sql[:300]}")
    mb = q["Statistics"].get("DataScannedInBytes", 0) / 1e6
    print(f"  ok  {mb:8.1f} MB  {sql.splitlines()[0][:70]}")
    return q


def print_rows(athena, qid: str) -> None:
    rows = athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
    head = [c.get("VarCharValue") for c in rows[0]["Data"]]
    for r in rows[1:]:
        vals = [c.get("VarCharValue") for c in r["Data"]]
        print("  " + "  ".join(f"{h}={v}" for h, v in zip(head, vals)))


def download(s3, bucket: str, prefix: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("part-*"):
        old.unlink()
    n = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Size"] == 0:
                continue
            dest = OUT_DIR / f"part-{n:03d}.parquet"
            s3.download_file(bucket, obj["Key"], str(dest))
            n += 1
    print(f"downloaded {n} file(s) to {OUT_DIR.relative_to(ROOT)}")
    return n


def latest_prefix(s3, bucket: str) -> str:
    """Newest detroit_buildings_* folder in the bucket."""
    res = s3.list_objects_v2(Bucket=bucket, Prefix="detroit_buildings", Delimiter="/")
    prefixes = sorted(p["Prefix"] for p in res.get("CommonPrefixes", []))
    if not prefixes:
        raise SystemExit("no detroit_buildings_* folder in bucket; run without --download-only")
    return prefixes[-1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True, help="your Athena bucket in us-west-2")
    ap.add_argument("--release", default="2026-10-21.0", help="Overture release")
    ap.add_argument("--download-only", action="store_true")
    a = ap.parse_args()

    import boto3

    s3 = boto3.client("s3", region_name=REGION)
    if not a.download_only:
        athena = boto3.client("athena", region_name=REGION)
        run_id = dt.datetime.now().strftime("%Y%m%d%H%M")
        output = f"s3://{a.bucket}/results/"
        last = None
        for f in sorted(SQL_DIR.glob("*.sql")):
            print(f.name)
            for sql in statements(f.read_text(), bucket=a.bucket, release=a.release, run=run_id):
                last = run(athena, sql, output)
        print_rows(athena, last["QueryExecutionId"])
        prefix = f"detroit_buildings_{run_id}/"
    else:
        prefix = latest_prefix(s3, a.bucket)
    download(s3, a.bucket, prefix)


if __name__ == "__main__":
    main()
