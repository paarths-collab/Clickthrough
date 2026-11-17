#!/usr/bin/env bash
# Start a run folder: .userflow/runs/<run-id>/ with run.json and decisions.md.
# Prints the folder path. Usage:
#   new-run.sh [--harness claude|codex|other] [--model ID] [--mode review|auto|recheck]
#              [--condition skills|baseline] [--project DIR]
set -euo pipefail

harness="unknown"; model="unknown"; mode="review"; condition="skills"; project=""
while [ $# -gt 0 ]; do
  case "$1" in
    --harness) harness="$2"; shift 2 ;;
    --model) model="$2"; shift 2 ;;
    --mode) mode="$2"; shift 2 ;;
    --condition) condition="$2"; shift 2 ;;
    --project) project="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$project" ]; then
  project="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
project="$(cd "$project" && pwd)"

commit="none"; dirty="false"
if git -C "$project" rev-parse HEAD >/dev/null 2>&1; then
  commit="$(git -C "$project" rev-parse HEAD)"
  if [ -n "$(git -C "$project" status --porcelain 2>/dev/null)" ]; then dirty="true"; fi
fi

run_id="$(date -u +%Y%m%dT%H%M%SZ)-${commit:0:7}"
run_dir="$project/.userflow/runs/$run_id"
mkdir -p "$run_dir/evidence" "$run_dir/raw"

cat > "$run_dir/run.json" <<JSON
{
  "run_id": "$run_id",
  "harness": "$harness",
  "model": "$model",
  "condition": "$condition",
  "mode": "$mode",
  "commit": "$commit",
  "uncommitted_changes": $dirty,
  "evaluator_independent": null,
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "ended_at": null,
  "tokens": null,
  "notes": ""
}
JSON

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
template=""
for candidate in "$project/.userflow/templates/decisions.md" "$here/../templates/decisions.md"; do
  if [ -f "$candidate" ]; then template="$candidate"; break; fi
done
if [ -n "$template" ]; then
  cp "$template" "$run_dir/decisions.md"
else
  echo "# Decision log" > "$run_dir/decisions.md"
fi

echo "$run_id" > "$project/.userflow/runs/CURRENT"
echo "$run_dir"
