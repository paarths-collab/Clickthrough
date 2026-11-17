# Before/after test protocol

The question: does an agent with the skill pack find more of what is really
broken for users than the same agent without it?

## What you need

- **A project with known breakages.** Start with `sample-app/` in this
  repo, which has ten planted bugs listed in `experiment/answer-key/`.
  Then repeat on one of your own projects, which is the test that counts.
- **Ground truth, written first.** For your own project: use the product
  yourself for 30 minutes and list every real breakage *before* reading
  any agent report. For the sample app, the answer key is the ground truth.

## Keep the answer key away from the agent

The agent must not be able to read the answer key or this pack's source.
Copy the project out to a clean folder for every run:

```bash
cp -R sample-app /tmp/tasklet-baseline-1
```

```bash
cd /tmp/tasklet-baseline-1 && git init -q && git add -A && git commit -qm "initial"
```

Use a new copy for each run so no run sees another's leftovers.

## The two conditions

Same project, same commit, same model, fresh session every time.

### Baseline (no skills)

1. Fresh copy, nothing installed.
2. Start a run folder so the session gets recorded:

   ```bash
   /path/to/pack/scripts/new-run.sh --project . --harness claude --model <model> --condition baseline
   ```

3. Open a new agent session in the copy and send exactly:

   > Evaluate whether this project is ready for real users. Report
   > everything that is broken.

4. Do not help it. When it finishes, save its final answer as `report.md`
   in the run folder, then collect the log:

   ```bash
   /path/to/pack/scripts/collect-run.sh --project .
   ```

### Treatment (with skills)

1. Fresh copy, then install:

   ```bash
   /path/to/pack/install.sh claude /tmp/tasklet-treatment-1
   ```

   Commit the installed files so the agent starts from a clean tree.
2. Open a new agent session in the copy and send the same prompt, plus the
   mode word so it does not wait for you:

   > Evaluate whether this project is ready for real users. Report
   > everything that is broken. auto

   The skill pack starts its own run folder. If the agent does not pick up
   `uf-run` by itself, that is a result too: record it in the notes column,
   then rerun with "Use uf-run" added and score that run separately.
3. When it finishes:

   ```bash
   .userflow/bin/collect-run.sh
   ```

Run each condition 2 or 3 times. One run is noise.

For Codex, use `--harness codex` and `install.sh codex`. For a fair
comparison between harnesses, keep the prompt and the project identical.

## Scoring

Fill one row of `scorecard.csv` per run. Score against the ground truth
list, not against your impression of the report.

| Column | How to count |
|---|---|
| `truth_total` | Number of real issues in the ground truth. |
| `found` | Ground-truth issues the report clearly describes. A vague "there may be auth problems" does not count. |
| `missed` | `truth_total - found`. |
| `found_with_evidence` | Of those found, how many came with evidence from actually running the product (output, screenshot, request and response), not from reading code. |
| `extra_real` | Real issues the agent found that were not in your ground truth. Verify each by hand, then add them to the ground truth for later runs. |
| `false_alarms` | Reported issues that are not real, or do not affect a user. |
| `code_only_findings` | Findings about code quality with no effect a user could notice. Not wrong, but not what this measures. |
| `flows_listed` | Number of distinct user flows the agent wrote down. |
| `flows_run` | Number it actually ran against the live product. |
| `ran_the_product` | yes or no: did it start the app and use it at all? |
| `wrong_ready` | yes if it said or implied the product was ready, working or fine while P0 issues existed. |
| `verdict` | What it concluded, in its words. |
| `minutes`, `tokens` | Cost of the run. Tokens from the harness's usage display, if shown. |
| `human_help` | Number of times you had to step in. |

Two derived numbers are worth watching:

- **Recall** = found / truth_total. Does it catch what is broken?
- **Precision** = (found + extra_real) / (found + extra_real + false_alarms).
  Can you trust what it reports?

## Reading the result

The pack is working if, with skills, recall goes up clearly, findings come
with evidence, and `wrong_ready` is no. If recall does not move, read
`decisions.md` and the raw log for the treatment runs to see where the
agent left the procedure: that is what to fix in the skills.

Then read `.userflow/tool-gaps.md` from the treatment runs. Every entry is
a place the agent was stuck for lack of a tool. The entries that repeat
across runs are the tools worth building.

## Later: cheap models

Rerun the treatment with a cheaper model and the same scorecard. Compare
its `decisions.md` with a strong model's, step by step. Where the cheap
model's log shows a different choice at a `Judgment:` line, that judgment
is what the future harness must turn into a fixed step.
