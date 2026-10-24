#!/usr/bin/env bash
# Run Terraform Generation Benchmark
# Compatible with SRE-skills-bench structure

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# Create/refresh the virtual environment from uv.lock
echo "Syncing dependencies..."
uv sync --locked

# Set default models.json if not exists
if [ ! -f "models.json" ]; then
    echo "Warning: models.json not found. Using default models."
    cat > models.json << EOF_MODELS
[
  {"provider": "anthropic", "model": "claude-opus-5-5", "effort": "high"},
  {"provider": "anthropic", "model": "claude-sonnet-5-5", "effort": "high"}
]
EOF_MODELS
fi

# Run benchmark
echo "Running Terraform Generation Benchmark..."
uv run python -m terraform_generation_bench.benchmark_cli suite \
  --models models.json \
  --tasks all \
  --runs-per-model 1

echo "✓ Benchmark complete! Check reports/ directory for results."
