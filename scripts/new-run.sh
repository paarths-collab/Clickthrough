#!/usr/bin/env bash
# Compatibility entry point. --help lists supported modes and options.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$here/ct-new-run.py" "$@"
