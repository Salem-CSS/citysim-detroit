# AWS access and deploys (both teammates)

One AWS account (Salem's, `574246332084`), one backend defined as code in `infra/`, and a test copy of the backend for each person.

| Stack | Who deploys | Used by |
| --- | --- | --- |
| `citysim-salem` | Salem | Salem's testing |
| `citysim-partner` | Partner | Partner's testing |
| `citysim-main` | Whoever pushes working code to `main` | the Vercel site + the demo |

Shared by all stacks (one per account): Bedrock model access, the data bucket, the Athena tables (us-west-2, see BUILDINGS.md).

## 1. Get access (once)

**Salem** (account owner, in the console): IAM → Users → Create user → name it after your partner → "Provide user access to the AWS Management Console" → set a temporary password (they change it at first sign-in) → Attach policies directly → `AdministratorAccess` (hackathon only; tighten or delete the user after). Send them the sign-in URL and username. Never share your own keys or root sign-in.

**Partner**: sign in, change the password, then IAM → Users → (you) → Security credentials → Create access key → "Command Line Interface". On your laptop:

```bash
aws configure --profile citysim     # paste your own key + secret, region us-east-1, output json
export AWS_PROFILE=citysim
aws sts get-caller-identity          # should show account 574246332084
```

Never commit keys or `.env` files.

## 2. Tools

- AWS CLI v2 and AWS SAM CLI (`brew install aws-sam-cli` / `pip install aws-sam-cli`)
- Python 3.12

No AWS tools on hand? AWS CloudShell (the `>_` icon in the console) has the AWS CLI and SAM preinstalled: `git clone https://github.com/Salem-CSS/citysim-detroit && cd citysim-detroit`.

## 3. Bedrock (once per account, Salem)

Bedrock console (us-east-1) → Model access → enable **Amazon Nova Pro** (turns questions into blocks) and **Nova Lite / Nova 2 Lite** (residents). If the account is on the AWS Free plan and Bedrock is blocked, decide whether to upgrade before deploying. Add a $5 budget alert first if you upgrade.

Check: `aws bedrock-runtime converse --model-id us.amazon.nova-pro-v1:0 --messages '[{"role":"user","content":[{"text":"hi"}]}]' --region us-east-1`

## 4. Deploy your stack

```bash
./infra/deploy.sh salem        # or: partner / main
```

It prints the API URL. Model ids and the data bucket are parameters:
`./infra/deploy.sh salem AgentModelId=us.amazon.nova-pro-v1:0 DataBucket=citysim-data-574246332084`

Try it:

```bash
curl -s -X POST "$API/scenario" -H 'content-type: application/json' \
  -d '{"question":"What if we expand the Newlab drone route to 200 flights a day?","districts":[5,6]}' | jq .spec.actions
```

Point the site at a stack: set `window.CITYSIM_API` in `web/prototype/config.js` (empty = offline mock). Only commit the `main` URL there.

## 5. What's in the stack (`infra/template.yaml`)

| Piece | Code | Route |
| --- | --- | --- |
| Question → blocks (Bedrock, validated against `contracts/actions.json`) | `agent/handler.py` | `POST /scenario` |
| Start a run | `infra/runs.py:start_run` | `POST /runs` |
| Run status / result | `infra/runs.py:get_run` | `GET /runs/{id}` |
| Run pipeline (Step Functions): engine → 25-resident batches (10 at a time) → aggregate | `engine/`, `residents/` via `infra/runs.py` | — |
| Runs table (DynamoDB, `citysim-<stage>-runs`) | | |

Engine actions and `residents/batch.py` / `aggregate.py` are still stubs. The pipeline records `not_implemented` for those steps instead of failing, so the whole path can be deployed and tested end to end.

## Rules

- Change things through `infra/template.yaml` + a deploy, not by clicking in the console.
- Each person deploys only their own stack. Deploy `main` only from code pushed to `main`.
- Log deploys that change the API or the stack in LOG.md.
