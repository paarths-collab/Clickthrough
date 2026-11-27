#!/usr/bin/env bash
# Install the Clickthrough pack into a project.
#
#   ./install.sh claude <project-path>    skills go to .claude/skills/, rules to CLAUDE.md
#   ./install.sh codex  <project-path>    skills go to .agents/skills/, rules to AGENTS.md
#   ./install.sh cursor <project-path>    same files as codex: Cursor reads .agents/skills/ and AGENTS.md
#   ./install.sh both   <project-path>    claude + codex, which also covers Cursor
#   ./install.sh plugin <project-path>    no skills copied; .claude/settings.json makes
#                                         Claude Code load the clickthrough plugin
#
# Safe to run again: it updates the skills, guide and scripts, and leaves
# your registry (flows.yaml), tool-gaps.md and run folders alone. It never
# deletes anything.
set -euo pipefail

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

if [ $# -eq 2 ]; then
  exec python3 "$(dirname "${BASH_SOURCE[0]}")/scripts/ct-install.py" "$@"
fi
[ $# -eq 3 ] && [ "$3" = "--transaction" ] || usage
set -- "$1" "$2"
target="$1"
case "$target" in claude|codex|cursor|both|plugin) ;; *) usage ;; esac
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
  case "$keep" in */) probe="$dir/${keep}ct-run/SKILL.md" ;; esac
  git -C "$project" check-ignore -q "$probe" 2>/dev/null || return 0
  ignore="$project/.gitignore"
  esc="\\$dir"
  if [ -f "$ignore" ] && grep -qE "^/?${esc}/?$" "$ignore"; then
    tmp="$ignore.ct-tmp"
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
  # Skills from before the rename (uf-*) would load next to the ct-* ones.
  old=$(cd "$dest" && ls -d uf-*/ 2>/dev/null | tr '\n' ' ' || true)
  if [ -n "$old" ]; then
    echo "skills   -> WARNING: old skills from before the rename are still in $1/: $old- delete them so they do not load twice" >&2
  fi
  touch_path "$1"
  keep_tracked "${1%%/*}" "skills/"
}

add_rules() { # $1 = instructions file inside the project
  local file="$project/$1"
  if [ -f "$file" ] && grep -qE '(clickthrough|user-flow-qa):start' "$file"; then
    # user-flow-qa is the block marker from before the rename to Clickthrough.
    # Replace the block between the markers with the current rules; leave
    # everything outside the markers exactly as it is.
    local tmp="$file.ct-tmp"
    awk -v snippet="$pack/templates/rules-snippet.md" '
      /<!-- (clickthrough|user-flow-qa):start -->/ { while ((getline line < snippet) > 0) print line; skip = 1; next }
      /<!-- (clickthrough|user-flow-qa):end -->/ { skip = 0; next }
      !skip { print }
    ' "$file" > "$tmp"
    if cmp -s "$tmp" "$file"; then
      rm -f "$tmp"
      echo "rules    -> $1 already up to date"
    else
      mv "$tmp" "$file"
      echo "rules    -> updated the Clickthrough block in $1"
      touch_path "$1"
    fi
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
if [ "$target" = "codex" ] || [ "$target" = "cursor" ] || [ "$target" = "both" ]; then
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
    "clickthrough": {
      "source": { "source": "github", "repo": "paarths-collab/Clickthrough" }
    }
  },
  "enabledPlugins": {
    "clickthrough@clickthrough": true
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
data.setdefault("extraKnownMarketplaces", {})["clickthrough"] = {
    "source": {"source": "github", "repo": "paarths-collab/Clickthrough"}}
data.setdefault("enabledPlugins", {})["clickthrough@clickthrough"] = True
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
    echo "plugin   -> added the marketplace and plugin to .claude/settings.json"
  else
    echo "plugin   -> .claude/settings.json exists and python3 is missing; add by hand:" >&2
    echo '            "extraKnownMarketplaces": {"clickthrough": {"source": {"source": "github", "repo": "paarths-collab/Clickthrough"}}}' >&2
    echo '            "enabledPlugins": {"clickthrough@clickthrough": true}' >&2
  fi
}

if [ "$target" = "plugin" ]; then
  enable_plugin
  touch_path .claude/settings.json
  keep_tracked .claude settings.json
  add_rules "CLAUDE.md"
fi

# Projects set up before the rename to Clickthrough keep their registry,
# cases and tests: move the old folders to the new names.
for pair in .userflow:.clickthrough userflow-tests:clickthrough-tests; do
  old="${pair%%:*}" new="${pair#*:}"
  if [ -d "$project/$old" ] && [ ! -e "$project/$new" ]; then
    mv "$project/$old" "$project/$new"
    echo "moved    -> $old/ to $new/"
    touch_path "$old"
    touch_path "$new"
  fi
done

ct="$project/.clickthrough"
mkdir -p "$ct/bin" "$ct/templates" "$ct/runs" "$project/clickthrough-tests"
cp "$pack/templates/guide.md" "$ct/guide.md"
cp "$pack/docs/runner.md" "$pack/docs/service-doubles.md" "$pack/templates/case-card.yaml" "$pack/templates/assertions.json" "$pack/templates/report.md" "$pack/templates/decisions.md" "$pack/templates/ci-github.yml" "$pack/templates/tester-kit.md" "$ct/templates/"
cp "$pack/scripts/ct.py" "$pack/scripts/ct_core.py" "$pack/scripts/ct-new-run.py" "$pack/scripts/new-run.sh" "$pack/scripts/collect-run.sh" "$pack/scripts/ct-check.py" "$pack/scripts/ct-inventory.py" "$pack/scripts/ct-double.py" "$ct/bin/"
chmod +x "$ct/bin/new-run.sh" "$ct/bin/collect-run.sh" "$ct/bin/ct-check.py" "$ct/bin/ct-inventory.py" "$ct/bin/ct-double.py"
echo "folder   -> .clickthrough/ (guide, templates, bin)"
touch_path .clickthrough

for keep in flows.yaml tool-gaps.md bugs.yaml coverage.yaml; do
  if [ -f "$ct/$keep" ]; then
    echo "kept     -> .clickthrough/$keep (already there)"
  else
    cp "$pack/templates/$keep" "$ct/$keep"
    echo "created  -> .clickthrough/$keep"
  fi
done

ignore="$project/.gitignore"
# Run logs can contain secrets; .results/ is the test tool's scratch output.
for line in '.clickthrough/runs/' '.clickthrough/proof/' '.clickthrough-backups/' '.ct-install.lock' 'clickthrough-tests/.results/'; do
  if [ -f "$ignore" ] && grep -qxF "$line" "$ignore"; then
    echo "ignore   -> .gitignore already has $line"
  else
    if [ -s "$ignore" ] && [ -n "$(tail -c1 "$ignore")" ]; then printf '\n' >> "$ignore"; fi
    printf '# Clickthrough\n%s\n' "$line" >> "$ignore"
    echo "ignore   -> added $line to .gitignore"
    touch_path .gitignore
  fi
done

cat <<EOF

Installed. Next:
  1. Review the installed files. If you choose to publish them:
       git add$touched
     Sessions only see what is on the branch they start from: merge it
     into your default branch (or start sessions on this branch).
  2. Open a NEW session (skills load when a session starts), one that did
     not build the product, and ask:
       "Is this project ready for real users? Use ct-run."
     Add "auto" to run without stopping for your review.

From now on, building sessions run ct-ready-check before saying "done".
Cursor picks up the skills from .agents/skills/ and the rules from AGENTS.md
(installed by the codex, cursor and both modes).
Optional: if no README or spec says what the product is for, write it in
.clickthrough/flows.yaml (product.purpose).
EOF
