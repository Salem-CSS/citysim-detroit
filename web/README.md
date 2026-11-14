# web/

Next.js + deck.gl frontend. Owner: Lane E (BUILD.md Steps 6, 12, 14).

- **Design reference:** `prototype/index.html`. Match its layout, CSS tokens and component split.
- Not initialized yet. Start with: `npx create-next-app@latest . --ts --app --eslint --no-src-dir` (run inside `web/`, keep `prototype/`).
- Build against `fixtures/run_result.drone.json` first; add `?offline=1` mode that loads cached results from `public/cached/`.
