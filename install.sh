#!/usr/bin/env bash
set -euo pipefail

# Bootstrap only: every package Python command runs inside a virtual environment.
PACKAGE_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Python 3 is required. Install it through your normal OS process, then retry.' >&2
  exit 2
fi
BOOTSTRAP_VENV="$(mktemp -d "${TMPDIR:-/tmp}/ui-design-bootstrap.XXXXXXXX")"
trap 'rm -rf -- "$BOOTSTRAP_VENV"' EXIT
if ! python3 -m venv --without-pip "$BOOTSTRAP_VENV"; then
  printf '%s\n' 'Unable to create a Python virtual environment. Ensure the Python venv module is available.' >&2
  exit 2
fi
INSTALLER="$PACKAGE_DIR/scripts/install.py"
for argument in "$@"; do
  if [[ "$argument" == "--mcp-global" ]]; then
    INSTALLER="$PACKAGE_DIR/scripts/install_mcp.py"
    break
  fi
done
"$BOOTSTRAP_VENV/bin/python" "$INSTALLER" "$@"
