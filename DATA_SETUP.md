# Data setup: download and load into S3

For the teammate who owns the AWS account. This takes about 20 minutes, mostly waiting on downloads. Do it first: the traffic engine, the AI residents and the map all need this data.

**Where the data goes:** an S3 bucket in your AWS account. It does **not** go in GitHub, because the census files are over GitHub's 100 MB file limit and the Lambdas read from S3.

```
s3://citysim-data-<your-account-id>/
  raw/          untouched downloads (this guide)
  processed/    cleaned + district-tagged files (BUILD.md Step 3)
  personas/     AI residents, one file per district (BUILD.md Step 4)
```

---

## 1. One-time setup (5 min)

You need Python 3.11+, git and the AWS CLI.

```bash
# check
python3 --version
aws --version
aws sts get-caller-identity      # must print your account id; if not, run: aws configure
```

Get a free Census API key (arrives by email in a minute or two): https://api.census.gov/data/key_signup.html

Clone and install:

```bash
git clone https://github.com/Salem-CSS/citysim-detroit.git
cd citysim-detroit
python3 -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r data/requirements.txt
cp .env.example .env                   # Windows: copy .env.example .env
```

Open `.env` and fill in:

```
CENSUS_API_KEY=<the key from the email>
AWS_REGION=us-east-1
DATA_BUCKET=citysim-data-<your-account-id>
```

## 2. Create the bucket (1 min)

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws s3 mb s3://citysim-data-$ACCOUNT --region us-east-1
```

Windows PowerShell:

```powershell
$ACCOUNT = aws sts get-caller-identity --query Account --output text
aws s3 mb "s3://citysim-data-$ACCOUNT" --region us-east-1
```

The bucket is private by default. Leave it that way.

## 3. Download everything (10–15 min)

From the repo root, with the venv active:

```bash
python -m data.download.all
```

This runs three scripts. You can also run them one at a time if one fails:

```bash
python -m data.download.detroit    # council districts, parcels, zoning, traffic counts, 311, tracts
python -m data.download.census     # map boundaries, ACS tables, block population, PUMS
python -m data.download.lodes      # where residents work
```

Re-running is safe: files already downloaded are skipped. If the PUMS step is slow, run `python -m data.download.census --skip-pums` first and come back for it.

## 4. Check what you got

```bash
find data/raw -type f | sort       # Windows: Get-ChildItem -Recurse data\raw -File
```

You should see roughly this (years may differ; the scripts pick the newest published):

```
data/raw/detroit/council_districts_2026.geojson
data/raw/detroit/parcels.*
data/raw/detroit/zoning.*
data/raw/detroit/traffic_volumes.*
data/raw/detroit/improve_detroit_311.*
data/raw/detroit/census_tracts_2020.*
data/raw/census/tiger/tl_20xx_26_tract.zip
data/raw/census/tiger/tl_20xx_26_bg.zip
data/raw/census/tiger/tl_20xx_26_tabblock20.zip
data/raw/census/tiger/tl_20xx_26_place.zip
data/raw/census/acs/acs5_20xx_B01001_tract_wayne.csv      (+ 8 more tables and variables.json)
data/raw/census/decennial/dec2020_pl_P1_blocks_wayne.csv
data/raw/census/rel/2020_Census_Tract_to_2020_PUMA.txt
data/raw/census/pums/pums5_20xx_csv_pmi.zip
data/raw/census/pums/pums5_20xx_csv_hmi.zip
data/raw/lodes/mi_od_main_JT00_20xx.csv.gz               (+ od_aux, rac, wac, xwalk)
```

If anything printed `FAILED`, see Troubleshooting below.

## 5. Upload to S3 (2–5 min)

```bash
aws s3 sync data/raw s3://citysim-data-$ACCOUNT/raw/
aws s3 ls s3://citysim-data-$ACCOUNT/raw/ --recursive --human-readable --summarize
```

The last line should show the total size and object count. Post both in the team chat.

## 6. Give your teammate access (optional, 3 min)

If the other teammate needs to read the bucket from their machine, create an IAM user for them in the console with this policy and send them the keys **privately** (not in GitHub, not in a group chat):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
    "Resource": ["arn:aws:s3:::citysim-data-ACCOUNT_ID", "arn:aws:s3:::citysim-data-ACCOUNT_ID/*"]
  }]
}
```

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `none of these exist` for a TIGER or PUMS file | That year isn't published yet and the fallback years failed too. Check the URL in a browser, then edit the year lists at the top of `data/config.py`. |
| ACS step returns HTTP 400/403 | `CENSUS_API_KEY` missing or not activated yet. Click the activation link in the key email. |
| Detroit dataset `FAILED` | The dataset id changed on detroitdata.org. Search the site for it, copy the id from the URL, update `DATASETS` in `data/download/detroit.py`. |
| Block population request times out | Census API is slow for all of Wayne County at once. Re-run; it skips what's already done. |
| `aws s3 mb` says bucket exists | Bucket names are global. Use `citysim-data-$ACCOUNT-<your initials>` and update `DATA_BUCKET` in `.env`. |
| `ModuleNotFoundError: data` | Run commands from the repo root, not inside `data/`. |

## What's next

Next: build the 3D building layer with [BUILDINGS.md](BUILDINGS.md). Once `raw/` is in S3, the Data lane also continues with BUILD.md Step 3 (clean and district-tag) and Step 4 (personas). Those write to `processed/` and `personas/` in the same bucket.
