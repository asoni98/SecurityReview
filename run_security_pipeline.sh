#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_security_pipeline.sh --code-path <path> [options]

Options:
  --code-path <path>             Path to the application code under review (required).
  --infra-path <path>            Path to infrastructure-as-code directory (Terraform, CDK, etc). If omitted,
                                 deployment understanding is skipped unless --deployment-override is provided.
  --deployment-output <path>     Where to write the deployment understanding result (default:
                                 ./deployment_understanding/deployment_model.json).
  --deployment-override <path>   Use an existing deployment understanding artifact and skip running the agent.
  --tainted-output <path>        Output path for analyze.py findings (default: ./taintedSources.txt).
  --max-findings <number>        Maximum findings for analyze.py (default: 100).
  --format <fmt>                 Output format for analyze.py (default: jsonl).
  --no-debug-deployment          Disable --debug-deployment flag when invoking analyze.py.
  --uv-extra "<args>"            Extra arguments appended to the uv command (can be specified multiple times).
  --trace-dir <path>             Path to the Trace project (default: ./Trace).
  --generate-dir <path>          Path to the generate_sources project (default: ./generate_sources).
  --deployment-dir <path>        Path to the deployment_understanding project (default: ./deployment_understanding).
  -h, --help                     Show this help message and exit.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

abs_path() {
    python3 - "$1" <<'PY'
import os
import sys
print(os.path.abspath(sys.argv[1]))
PY
}

CODE_PATH=""
INFRA_PATH=""
DEPLOYMENT_OUTPUT="$(abs_path "$SCRIPT_DIR/deployment_understanding/deployment_model.json")"
DEPLOYMENT_OVERRIDE=""
TAINTED_OUTPUT="$(abs_path "$SCRIPT_DIR/taintedSources.txt")"
MAX_FINDINGS="100"
FORMAT="jsonl"
DEBUG_DEPLOYMENT=true
TRACE_DIR="$SCRIPT_DIR/Trace"
GENERATE_DIR="$SCRIPT_DIR/generate_sources"
DEPLOYMENT_DIR="$SCRIPT_DIR/deployment_understanding"
declare -a UV_EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --code-path)
            CODE_PATH="$(abs_path "$2")"
            shift 2
            ;;
        --infra-path)
            INFRA_PATH="$(abs_path "$2")"
            shift 2
            ;;
        --deployment-output)
            DEPLOYMENT_OUTPUT="$(abs_path "$2")"
            shift 2
            ;;
        --deployment-override)
            DEPLOYMENT_OVERRIDE="$(abs_path "$2")"
            shift 2
            ;;
        --tainted-output)
            TAINTED_OUTPUT="$(abs_path "$2")"
            shift 2
            ;;
        --max-findings)
            MAX_FINDINGS="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --no-debug-deployment)
            DEBUG_DEPLOYMENT=false
            shift
            ;;
        --uv-extra)
            UV_EXTRA_ARGS+=("$2")
            shift 2
            ;;
        --trace-dir)
            TRACE_DIR="$(abs_path "$2")"
            shift 2
            ;;
        --generate-dir)
            GENERATE_DIR="$(abs_path "$2")"
            shift 2
            ;;
        --deployment-dir)
            DEPLOYMENT_DIR="$(abs_path "$2")"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$CODE_PATH" ]]; then
    echo "Error: --code-path is required." >&2
    usage
    exit 1
fi

if [[ ! -d "$CODE_PATH" ]]; then
    echo "Error: code path is not a directory: $CODE_PATH" >&2
    exit 1
fi

if [[ -n "$INFRA_PATH" ]] && [[ ! -e "$INFRA_PATH" ]]; then
    echo "Error: --infra-path does not exist: $INFRA_PATH" >&2
    exit 1
fi

if [[ -n "$DEPLOYMENT_OVERRIDE" ]] && [[ ! -f "$DEPLOYMENT_OVERRIDE" ]]; then
    echo "Error: --deployment-override file not found: $DEPLOYMENT_OVERRIDE" >&2
    exit 1
fi

if [[ ! -d "$TRACE_DIR" ]]; then
    echo "Error: Trace directory not found: $TRACE_DIR" >&2
    exit 1
fi

if [[ ! -d "$GENERATE_DIR" ]]; then
    echo "Error: generate_sources directory not found: $GENERATE_DIR" >&2
    exit 1
fi

if [[ -n "$INFRA_PATH" ]] && [[ ! -d "$DEPLOYMENT_DIR" ]]; then
    echo "Error: deployment_understanding directory not found: $DEPLOYMENT_DIR" >&2
    exit 1
fi

if [[ ! -f "$GENERATE_DIR/analyze.py" ]]; then
    echo "Error: analyze.py not found at $GENERATE_DIR/analyze.py" >&2
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed or not in PATH." >&2
    exit 1
fi

if [[ ! -d "$TRACE_DIR/node_modules" ]]; then
    echo "Trace dependencies not installed; running npm install..."
    (cd "$TRACE_DIR" && npm install)
fi

if [[ -d "$DEPLOYMENT_DIR" ]] && [[ ! -d "$DEPLOYMENT_DIR/node_modules" ]]; then
    echo "Deployment understanding dependencies not installed; running npm install..."
    (cd "$DEPLOYMENT_DIR" && npm install)
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    read -r -s -p "Enter OpenAI API key: " OPENAI_KEY_INPUT
    echo
    if [[ -z "$OPENAI_KEY_INPUT" ]]; then
        echo "Error: OpenAI API key is required." >&2
        exit 1
    fi
    export OPENAI_API_KEY="$OPENAI_KEY_INPUT"
else
    echo "Using existing OPENAI_API_KEY from environment."
fi

mkdir -p "$(dirname "$TAINTED_OUTPUT")"
: > "$TAINTED_OUTPUT"

deployment_model_path=""

if [[ -n "$DEPLOYMENT_OVERRIDE" ]]; then
    echo "Using deployment model override: $DEPLOYMENT_OVERRIDE"
    deployment_model_path="$DEPLOYMENT_OVERRIDE"
elif [[ -n "$INFRA_PATH" ]]; then
    mkdir -p "$(dirname "$DEPLOYMENT_OUTPUT")"
    echo "Running deployment understanding agent..."
    (cd "$DEPLOYMENT_DIR" && npm start -- "$CODE_PATH" "$INFRA_PATH" "$DEPLOYMENT_OUTPUT")
    deployment_model_path="$DEPLOYMENT_OUTPUT"
else
    echo "No infrastructure path provided; skipping deployment understanding."
fi

if [[ -n "$deployment_model_path" ]] && [[ ! -f "$deployment_model_path" ]]; then
    echo "Warning: deployment model file not found at $deployment_model_path. The analyzer will run without it." >&2
    deployment_model_path=""
fi

echo "Starting source analyzer with uv..."
declare -a UV_CMD=("uv" "run" "--with" "pydantic" "--with" "pydantic-ai" "--with" "openai")
if (( ${#UV_EXTRA_ARGS[@]:-0} > 0 )); then
    for extra in "${UV_EXTRA_ARGS[@]}"; do
        [[ -n "$extra" ]] && UV_CMD+=("$extra")
    done
fi
UV_CMD+=("python3" "$GENERATE_DIR/analyze.py" "--target" "$CODE_PATH" "--max-findings" "$MAX_FINDINGS" "--format" "$FORMAT" "--output" "$TAINTED_OUTPUT")
if [[ "$DEBUG_DEPLOYMENT" == true ]]; then
    UV_CMD+=("--debug-deployment")
fi
if [[ -n "$deployment_model_path" ]]; then
    UV_CMD+=("--deployment-model" "$deployment_model_path")
fi

"${UV_CMD[@]}"
ANALYSIS_STATUS=$?

if [[ $ANALYSIS_STATUS -ne 0 ]]; then
    echo "Source analyzer exited with status $ANALYSIS_STATUS" >&2
    exit $ANALYSIS_STATUS
fi

if [[ ! -s "$TAINTED_OUTPUT" ]]; then
    echo "Warning: tainted sources output is empty; Trace will run but likely has no work." >&2
fi

echo "Starting Trace pipeline..."
(cd "$TRACE_DIR" && npm start -- "$TAINTED_OUTPUT")
TRACE_STATUS=$?

if [[ $TRACE_STATUS -ne 0 ]]; then
    echo "Trace pipeline exited with status $TRACE_STATUS" >&2
    exit $TRACE_STATUS
fi

echo "Pipeline finished successfully."
