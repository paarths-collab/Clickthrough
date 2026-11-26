#!/usr/bin/env bash
# Copy the harness's own session log into a run folder, so the run can be
# studied later. It only ever copies; it never deletes anything. Safe to run
# more than once: a later copy overwrites an earlier one. Run it again after
# the session has ended to get the complete log.
#
# Usage:
#   collect-run.sh [--project DIR] [--run RUN_ID] [--harness claude|codex|cursor]
#                  [--session ID_OR_FILE] [--out DIR]
#
# Where the logs come from:
#   Claude Code: ~/.claude/projects/<project path with non-alphanumerics as "-">/<session>.jsonl
#   Codex:       ${CODEX_HOME:-~/.codex}/sessions/YYYY/MM/DD/rollout-*.jsonl (may be .zst)
#
# These logs can contain secrets the agent read. Keep them out of git.
set -euo pipefail

project=""; run=""; harness=""; session=""; out=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) project="$2"; shift 2 ;;
    --run) run="$2"; shift 2 ;;
    --harness) harness="$2"; shift 2 ;;
    --session) session="$2"; shift 2 ;;
    --out) out="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$project" ]; then
  project="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
project="$(cd "$project" && pwd)"

run_dir=""
if [ -z "$out" ]; then
  if [ -z "$run" ] && [ -f "$project/.clickthrough/runs/CURRENT" ]; then
    run="$(cat "$project/.clickthrough/runs/CURRENT")"
  fi
  if [ -z "$run" ]; then
    echo "No run found. Start one with new-run.sh, or pass --run or --out." >&2
    exit 1
  fi
  run_dir="$project/.clickthrough/runs/$run"
  if [ ! -d "$run_dir" ]; then
    echo "Run folder not found: $run_dir" >&2
    exit 1
  fi
  out="$run_dir/raw"
fi
mkdir -p "$out"

if [ -z "$harness" ] && [ -n "$run_dir" ] && [ -f "$run_dir/run.json" ]; then
  harness="$(sed -n 's/.*"harness": *"\([^"]*\)".*/\1/p' "$run_dir/run.json" | head -1)"
  if [ "$harness" = "unknown" ]; then harness=""; fi
fi

newest() { # prints the newest of the file paths given on stdin
  local best="" f
  while IFS= read -r f; do
    if [ -z "$best" ] || [ "$f" -nt "$best" ]; then best="$f"; fi
  done
  echo "$best"
}

collect_claude() {
  local encoded dir="" file side base candidate
  base="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects"
  # Claude Code names the folder after the path it was started in. Try the
  # path as given and with symlinks resolved (on macOS /tmp is /private/tmp).
  for candidate in "$project" "$(cd "$project" && pwd -P)"; do
    encoded="$(printf '%s' "$candidate" | sed 's/[^A-Za-z0-9]/-/g')"
    if [ -d "$base/$encoded" ]; then dir="$base/$encoded"; break; fi
  done
  if [ -z "$dir" ] && [ -z "$session" ] && [ -d "$base" ]; then
    # Fallback (cloud sessions, sessions started in a parent folder): the
    # newest session log whose start names this project folder.
    local f best=""
    while IFS= read -r f; do
      if head -c 20000 "$f" 2>/dev/null | grep -qF "\"cwd\":\"$project"; then
        if [ -z "$best" ] || [ "$f" -nt "$best" ]; then best="$f"; fi
      fi
    done < <(find "$base" -maxdepth 2 -name '*.jsonl' -mmin -1440 2>/dev/null)
    if [ -n "$best" ]; then
      session="$best"
      echo "claude: no folder named after this project; using the newest log that mentions it" >&2
    fi
  fi
  if [ -z "$dir" ] && { [ -z "$session" ] || [ ! -f "$session" ]; }; then
    echo "No Claude Code logs for this project at $base/$encoded" >&2
    echo "If the session was started in another folder, or you are a subagent, pass --session <log file>." >&2
    return 1
  fi
  if [ -n "$session" ] && [ -f "$session" ]; then
    file="$session"
  elif [ -n "$session" ]; then
    file="$dir/$session.jsonl"
  else
    file="$(find "$dir" -maxdepth 1 -name '*.jsonl' | newest)"
  fi
  if [ -z "$file" ] || [ ! -f "$file" ]; then
    echo "No session log found in $dir" >&2
    return 1
  fi
  cp "$file" "$out/"
  # Subagent transcripts and large tool results sit in a folder named after the session.
  side="${file%.jsonl}"
  if [ -d "$side" ]; then cp -R "$side" "$out/"; fi
  echo "claude: copied $(basename "$file") ($(wc -l < "$file" | tr -d ' ') lines)"
}

names_project() { # does the start of this rollout file mention the project folder?
  case "$1" in
    *.zst)
      command -v zstd >/dev/null 2>&1 || return 1
      zstd -dc "$1" 2>/dev/null | head -c 20000 | grep -qF "$project" ;;
    *)
      head -c 20000 "$1" | grep -qF "$project" ;;
  esac
}

collect_codex() {
  local dir file="" f
  dir="${CODEX_HOME:-$HOME/.codex}/sessions"
  if [ ! -d "$dir" ]; then
    echo "No Codex logs at $dir" >&2
    return 1
  fi
  if [ -n "$session" ] && [ -f "$session" ]; then
    file="$session"
  else
    # Prefer the newest rollout whose header names this project folder.
    while IFS= read -r f; do
      if [ -n "$session" ] && [ "${f#*"$session"}" = "$f" ]; then continue; fi
      if names_project "$f"; then
        if [ -z "$file" ] || [ "$f" -nt "$file" ]; then file="$f"; fi
      fi
    done < <(find "$dir" -type f -name 'rollout-*.jsonl*')
    if [ -z "$file" ]; then
      file="$(find "$dir" -type f -name 'rollout-*.jsonl*' | newest)"
      if [ -n "$file" ]; then
        echo "codex: no rollout names this project; taking the newest one. Check it is the right session." >&2
      fi
    fi
  fi
  if [ -z "$file" ] || [ ! -f "$file" ]; then
    echo "No Codex rollout found in $dir" >&2
    return 1
  fi
  cp "$file" "$out/"
  echo "codex: copied $(basename "$file")"
}

status=0
case "$harness" in
  cursor|other)
    echo "No automatic log collection for $harness yet. Export the chat or agent transcript" >&2
    echo "and save it in $out, then note it in decisions.md." >&2
    status=1 ;;
  claude) collect_claude || status=1 ;;
  codex) collect_codex || status=1 ;;
  *)
    # Harness not stated: take whatever exists.
    found=0
    if collect_claude 2>/dev/null; then found=1; fi
    if collect_codex 2>/dev/null; then found=1; fi
    if [ "$found" = 0 ]; then
      echo "No Claude Code or Codex session log found. Pass --harness and --session." >&2
      status=1
    fi
    ;;
esac

if [ -n "$run_dir" ] && [ -f "$run_dir/run.json" ]; then
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sed "s/\"ended_at\": *[^,]*,/\"ended_at\": \"$now\",/" "$run_dir/run.json" > "$run_dir/run.json.new"
  mv "$run_dir/run.json.new" "$run_dir/run.json"
fi
if [ "$status" = 0 ]; then
  echo "Raw logs are in $out"
else
  echo "No session log was copied; $out is unchanged. Note this in decisions.md and carry on." >&2
fi
exit $status
