#!/usr/bin/env bash
# Install the user-flow QA pack into a project.
#
#   ./install.sh claude <project-path>    skills go to .claude/skills/, rules to CLAUDE.md
#   ./install.sh codex  <project-path>    skills go to .agents/skills/, rules to AGENTS.md
#   ./install.sh both   <project-path>
#
# Safe to run again: it updates the skills, guide and scripts, and leaves
# your registry (flows.yaml), tool-gaps.md and run folders alone. It never
# deletes anything.
set -euo pipefail

usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

[ $# -eq 2 ] || usage
target="$1"
case "$target" in claude|codex|both) ;; *) usage ;; esac
if [ ! -d "$2" ]; then
  echo "Project folder not found: $2" >&2
  exit 1
fi

pack="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project="$(cd "$2" && pwd)"

install_skills() { # $1 = skills folder inside the project
  local dest="$project/$1" skill
  mkdir -p "$dest"
  for skill in "$pack"/skills/*/; do
    cp -R "$skill" "$dest/"
  done
  echo "skills   -> $1/ ($(ls "$pack/skills" | tr '\n' ' '))"
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
}

if [ "$target" = "claude" ] || [ "$target" = "both" ]; then
  install_skills ".claude/skills"
  add_rules "CLAUDE.md"
fi
if [ "$target" = "codex" ] || [ "$target" = "both" ]; then
  install_skills ".agents/skills"
  add_rules "AGENTS.md"
fi

uf="$project/.userflow"
mkdir -p "$uf/bin" "$uf/templates" "$uf/runs" "$project/userflow-tests"
cp "$pack/templates/guide.md" "$uf/guide.md"
cp "$pack/templates/report.md" "$pack/templates/decisions.md" "$uf/templates/"
cp "$pack/scripts/new-run.sh" "$pack/scripts/collect-run.sh" "$pack/scripts/uf-check.py" "$uf/bin/"
chmod +x "$uf/bin/new-run.sh" "$uf/bin/collect-run.sh" "$uf/bin/uf-check.py"
echo "userflow -> .userflow/ (guide, templates, bin)"

for keep in flows.yaml tool-gaps.md; do
  if [ -f "$uf/$keep" ]; then
    echo "kept     -> .userflow/$keep (already there)"
  else
    cp "$pack/templates/$keep" "$uf/$keep"
    echo "created  -> .userflow/$keep"
  fi
done

ignore="$project/.gitignore"
if [ -f "$ignore" ] && grep -qxF '.userflow/runs/' "$ignore"; then
  echo "ignore   -> .gitignore already has .userflow/runs/"
else
  if [ -s "$ignore" ] && [ -n "$(tail -c1 "$ignore")" ]; then printf '\n' >> "$ignore"; fi
  printf '# user-flow QA run logs can contain secrets\n.userflow/runs/\n' >> "$ignore"
  echo "ignore   -> added .userflow/runs/ to .gitignore"
fi

cat <<EOF

Installed. Next:
  1. Put what the product is for in .userflow/flows.yaml (product.purpose),
     or make sure there is a PRD or README the agent can read.
  2. Open a NEW agent session in $project (not the one that built it).
  3. Ask: "Is this project ready for real users? Use uf-run."
     Add "auto" to run without stopping for your review.
EOF
