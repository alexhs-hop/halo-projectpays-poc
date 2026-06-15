# Halo project-pays review — proof of concept

This is a throwaway PoC of the **project-pays** review model (separate from the
own-key model). It demonstrates: a contributor opens a PR → a GitHub Action runs
Claude Code **read-only** against the rubric using the **repo owner's** API key
(via `pull_request_target`, so the contributor never holds the key and can't
modify the review) → the verdict is posted as a PR comment and gates the check.

It is seeded with one real sample task at the repo root so the first PR produces
a substantive verdict. In production the base repo would be README-only and the
contributor would add the task.

## One-time setup (owner)

Add your Anthropic key as the repo secret — this is the "project pays" key:

```bash
gh secret set ANTHROPIC_API_KEY --repo <owner>/<this-repo>   # paste your key
```

(Optional, to test real fork PRs: enable forking in Settings → General, and set
Settings → Actions → "Fork pull request workflows from outside collaborators" to
run without approval. Not needed to test with your own branch.)

## How to test it

```bash
git clone <this-repo> && cd <repo>
git checkout -b test-change
# make any small edit to the task (e.g. tweak instruction.md or task.toml)
git add -A && git commit -m "test"
git push -u origin test-change
gh pr create --fill
```

Within a few minutes the **Halo Review** check runs and a verdict comment appears
on the PR. The review reads the PR's files under `submission/`, grades all 25
criteria, and posts PASS/FAIL with per-criterion notes.

## How it works (files)

- `.github/workflows/review.yml` — `pull_request_target`; checks out the PR head
  read-only into `submission/`, runs the review with the owner's key, comments + gates.
- `.halo/halo-eval-prompt.md` — read-only reviewer instructions (grades `submission/`).
- `.halo/halo-rubric.toml` — the 25-criterion rubric.
- `.halo/report.sh` — parses the verdict, posts the sticky comment + `accepted`/`needs-revision` label, fails the check on FAIL.

## Safety notes (the important part)

- The contributor has no write to this base repo (they fork), so they can't alter
  the review workflow or reach the key.
- The workflow checks out the PR **read-only and never executes it** — no building,
  no `pip`/`npm install` from the submission, no running solve/tests. That is the
  one rule that keeps the project key safe under `pull_request_target`.
- The key lives only in this repo's secret and is only ever used by this fixed
  base-branch workflow.
