#!/usr/bin/env bash
# Install the user-flow QA pack into a project.
#
#   ./install.sh claude <project-path>    skills go to .claude/skills/, rules to CLAUDE.md
#   ./install.sh codex  <project-path>    skills go to .agents/skills/, rules to AGENTS.md
#   ./install.sh both   <project-path>
#   ./install.sh plugin <project-path>    no skills copied; .claude/settings.json makes
#                                         Claude Code load the user-flow-qa plugin
#
# Safe to run again: it updates the skills, guide and scripts, and leaves
# your registry (flows.yaml), tool-gaps.md and run folders alone. It never
# deletes anything.
set -euo pipefail

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

[ $# -eq 2 ] || usage
target="$1"
case "$target" in claude|codex|both|plugin) ;; *) usage ;; esac
if [ ! -d "$2" ]; then
  echo "Project folder not found: $2" >&2
  exit 1
fi

pack="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project="$(cd "$2" && pwd)"
touched=""   # paths to commit, printed at the end
touch_path() { case " $touched " in *" $1 "*) ;; *) touched="$touched $1" ;; esac; }

# Many repos ignore all of .claude/ or .agents/. Then the files we add
# never reach git, and cloud sessions never see them. Re-include only what
# we add: turn an exact `.claude/` line into `.claude/*`, then add
# `!.claude/<keep>`. Anything else in the folder stays ignored.
keep_tracked() { # $1 = folder (.claude or .agents), $2 = path inside it to keep
  local dir="$1" keep="$2" probe ignore esc tmp
  git -C "$project" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  probe="$dir/$keep"
  case "$keep" in */) probe="$dir/${keep}uf-run/SKILL.md" ;; esac
  git -C "$project" check-ignore -q "$probe" 2>/dev/null || return 0
  ignore="$project/.gitignore"
  esc="\\$dir"
  if [ -f "$ignore" ] && grep -qE "^/?${esc}/?$" "$ignore"; then
    tmp="$ignore.uf-tmp"
    awk -v d="$dir" '{ l = $0; sub(/^\//, "", l); sub(/\/$/, "", l); if (l == d) print d "/*"; else print }' "$ignore" > "$tmp"
    mv "$tmp" "$ignore"
  fi
  if git -C "$project" check-ignore -q "$probe" 2>/dev/null; then
    if [ -s "$ignore" ] && [ -n "$(tail -c1 "$ignore")" ]; then printf '\n' >> "$ignore"; fi
    printf '!%s/%s\n' "$dir" "$keep" >> "$ignore"
  fi
  if git -C "$project" check-ignore -q "$probe" 2>/dev/null; then
    echo "ignore   -> WARNING: $dir/$keep is still git-ignored by another rule; add it with git add -f" >&2
  else
    echo "ignore   -> .gitignore hid $dir/; now it keeps $dir/$keep and still ignores the rest"
    touch_path .gitignore
  fi
}

install_skills() { # $1 = skills folder inside the project
  local dest="$project/$1" skill
  mkdir -p "$dest"
  for skill in "$pack"/skills/*/; do
    # No trailing slash on the source: BSD cp (macOS) would copy the folder's
    # contents instead of the folder, and the skills would overwrite each other.
    cp -R "${skill%/}" "$dest/"
  done
  echo "skills   -> $1/ ($(ls "$pack/skills" | tr '\n' ' '))"
  touch_path "$1"
  keep_tracked "${1%%/*}" "skills/"
}

add_rules() { # $1 = instructions file inside the project
  local file="$project/$1"
  if [ -f "$file" ] && grep -q 'user-flow-qa:start' "$file"; then
    echo "rules    -> $1 already has them"
    return
  fi
  if [ -s "$file" ]; then printf '\n' >> "$file"; fi
  cat "$pack/templates/rules-snippet.md" >> "$file"
  echo "rules    -> appended to $1"
  touch_path "$1"
}

if [ "$target" = "claude" ] || [ "$target" = "both" ]; then
  install_skills ".claude/skills"
  add_rules "CLAUDE.md"
fi
if [ "$target" = "codex" ] || [ "$target" = "both" ]; then
  install_skills ".agents/skills"
  add_rules "AGENTS.md"
fi

enable_plugin() { # project settings that make Claude Code load the plugin
  local settings="$project/.claude/settings.json"
  mkdir -p "$project/.claude"
  if [ ! -f "$settings" ]; then
    cat > "$settings" <<'JSON'
{
  "extraKnownMarketplaces": {
    "user-flow-qa": {
      "source": { "source": "github", "repo": "paarths-collab/user" }
    }
  },
  "enabledPlugins": {
    "user-flow-qa@user-flow-qa": true
  }
}
JSON
    echo "plugin   -> created .claude/settings.json (marketplace + plugin enabled)"
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$settings" <<'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
data.setdefault("extraKnownMarketplaces", {})["user-flow-qa"] = {
    "source": {"source": "github", "repo": "paarths-collab/user"}}
data.setdefault("enabledPlugins", {})["user-flow-qa@user-flow-qa"] = True
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
    echo "plugin   -> added the marketplace and plugin to .claude/settings.json"
  else
    echo "plugin   -> .claude/settings.json exists and python3 is missing; add by hand:" >&2
    echo '            "extraKnownMarketplaces": {"user-flow-qa": {"source": {"source": "github", "repo": "paarths-collab/user"}}}' >&2
    echo '            "enabledPlugins": {"user-flow-qa@user-flow-qa": true}' >&2
  fi
}

if [ "$target" = "plugin" ]; then
  enable_plugin
  touch_path .claude/settings.json
  keep_tracked .claude settings.json
  add_rules "CLAUDE.md"
fi

uf="$project/.userflow"
mkdir -p "$uf/bin" "$uf/templates" "$uf/runs" "$project/userflow-tests"
cp "$pack/templates/guide.md" "$uf/guide.md"
cp "$pack/templates/report.md" "$pack/templates/decisions.md" "$pack/templates/ci-github.yml" "$uf/templates/"
cp "$pack/scripts/new-run.sh" "$pack/scripts/collect-run.sh" "$pack/scripts/uf-check.py" "$pack/scripts/uf-inventory.py" "$uf/bin/"
chmod +x "$uf/bin/new-run.sh" "$uf/bin/collect-run.sh" "$uf/bin/uf-check.py" "$uf/bin/uf-inventory.py"
echo "userflow -> .userflow/ (guide, templates, bin)"
touch_path .userflow

for keep in flows.yaml tool-gaps.md; do
  if [ -f "$uf/$keep" ]; then
    echo "kept     -> .userflow/$keep (already there)"
  else
    cp "$pack/templates/$keep" "$uf/$keep"
    echo "created  -> .userflow/$keep"
  fi
done

ignore="$project/.gitignore"
# Run logs can contain secrets; .results/ is the test tool's scratch output.
for line in '.userflow/runs/' 'userflow-tests/.results/'; do
  if [ -f "$ignore" ] && grep -qxF "$line" "$ignore"; then
    echo "ignore   -> .gitignore already has $line"
  else
    if [ -s "$ignore" ] && [ -n "$(tail -c1 "$ignore")" ]; then printf '\n' >> "$ignore"; fi
    printf '# user-flow QA\n%s\n' "$line" >> "$ignore"
    echo "ignore   -> added $line to .gitignore"
    touch_path .gitignore
  fi
done

cat <<EOF

Installed. Next:
  1. Commit and push:
       git add$touched
     Sessions only see what is on the branch they start from: merge it
     into your default branch (or start sessions on this branch).
  2. Open a NEW session (skills load when a session starts), one that did
     not build the product, and ask:
       "Is this project ready for real users? Use uf-run."
     Add "auto" to run without stopping for your review.

From now on, building sessions run uf-ready-check before saying "done".
Optional: if no README or spec says what the product is for, write it in
.userflow/flows.yaml (product.purpose).
EOF
