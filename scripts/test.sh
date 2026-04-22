#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# UCP Connector - Standardized Test Entrypoint
# =============================================================================

COMMAND=${1:-"--unit"}
VENV_DIR=".venv-test"
PYTHONPATH_BASE="src${PYTHONPATH:+:$PYTHONPATH}"

pick_python() {
    local candidates=()
    if [[ -n "${TALOS_PYTHON:-}" ]]; then
        candidates+=("${TALOS_PYTHON}")
    fi
    candidates+=(python3 python3.14 python3.13 python3.12 python3.11 python3.10)

    local candidate
    for candidate in "${candidates[@]}"; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
        then
            echo "$candidate"
            return 0
        fi
    done

    echo "Talos UCP connector tests require Python >= 3.10. Set TALOS_PYTHON to a compatible interpreter." >&2
    exit 1
}

HOST_PYTHON="$(pick_python)"

ensure_virtualenv() {
    if [[ ! -x "$VENV_DIR/bin/python" ]]; then
        echo "Creating local UCP connector test virtualenv with $("$HOST_PYTHON" --version 2>&1)..."
        "$HOST_PYTHON" -m venv "$VENV_DIR"
    fi
}

ensure_virtualenv
PYTHON_BIN="$VENV_DIR/bin/python"

ensure_test_dependencies() {
    if PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import importlib.util

required = ["pytest", "httpx", "jsonschema", "mcp", "talos_contracts"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
raise SystemExit(0 if not missing else 1)
PY
    then
        return 0
    fi

    echo "Installing UCP connector test dependencies with $("$PYTHON_BIN" --version 2>&1)..."
    local install_args=()
    if [[ -f "../../contracts/python/pyproject.toml" ]]; then
        install_args+=(-e ../../contracts/python)
    fi
    install_args+=(-e ".[dev]")
    PIP_DISABLE_PIP_VERSION_CHECK=1 "$PYTHON_BIN" -m pip install "${install_args[@]}"
}

ensure_test_dependencies

run_unit() {
    echo "--- Running Unit Tests ---"
    if [ -d "tests" ] && find tests -name "test_*.py" | grep -q .; then
        if ! PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" -m pytest tests/ --maxfail=2 -q; then
            return 1
        fi
    else
        echo "  ⚠ No test files found. Checking imports..."
        if PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" -c "import importlib; importlib.import_module('talos_ucp_connector')" >/dev/null 2>&1; then
            echo "  ✓ UCP connector module imports OK"
        else
            echo "  ⚠ Import check skipped (dependencies not installed)"
            return 1
        fi
    fi
}

run_smoke() {
    echo "--- Running Smoke Tests ---"
    run_unit
}

case "$COMMAND" in
    --smoke) run_smoke ;;
    --unit) run_unit ;;
    --integration) echo "--- Skipping Integration (Not configured) ---" ;;
    --coverage) run_unit ;;
    --ci) run_smoke && run_unit ;;
    --full) run_smoke && run_unit ;;
    *) echo "Usage: $0 {--smoke|--unit|--integration|--coverage|--ci|--full}"; exit 1 ;;
esac

echo "ucp-connector tests completed."
