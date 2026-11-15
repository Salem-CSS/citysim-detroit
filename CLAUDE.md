# Instructions for AI assistants working in this repo

Two people are building CitySim Detroit at the same time, each with their own AI assistant. **LOG.md is how the assistants stay in sync.**

## Every session

1. `git pull --rebase` before doing anything.
2. Read `LOG.md`: the Status board, Open questions / handoffs, and the newest 10 entries. Tell your person anything relevant (blockers, contract changes, handoffs addressed to them).
3. Read `SCOPE.md` (what we're building) and `BUILD.md` (order and lanes) if you haven't this session.

## After making changes

1. Add a LOG.md entry at the top of **Entries** using the template in that file. Mark yourself as `<Name> (AI)`.
2. Update the Status board row for your lane if it changed. Add handoffs to the other person under Open questions / handoffs.
3. Commit LOG.md together with the work, then `git pull --rebase && git push` immediately so the other side sees it.
4. If you changed anything in `contracts/`, say exactly what in the entry and update `fixtures/` to match.

## Ground rules

- Stay in your lane's folders (see BUILD.md "Lanes"). If you must touch another lane's files, say so in the log.
- Engines produce numbers; the AI never invents traffic counts, trip rates or poll results.
- Residents answer only support / neutral / oppose + one reason (quote for a ~10% sample), and never see the raw prompt.
- Never commit secrets (`.env`, keys) or data files (`data/raw/`, `data/processed/`, `*.parquet`).
- If you hit a merge conflict in LOG.md, keep both sides' entries.
- Don't rewrite history (`git push --force`) on `main`.

## Key files

| File | What it is |
| --- | --- |
| SCOPE.md | Full project scope |
| BUILD.md | Step-by-step build plan, lanes, checkpoints |
| DATA_SETUP.md | Download data and load into S3 |
| BUILDINGS.md | 3D building layer pipeline |
| LOG.md | Team change log (read first, write last) |
| contracts/ | JSON schemas shared by all lanes (start with contracts/README.md) |
| contracts/actions.json | The 6 action types and their editable constraints |
| web/prototype/index.html | Frontend design reference |
