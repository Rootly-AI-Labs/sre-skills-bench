#!/bin/bash
# Run Terraform Generation Benchmark
# Compatible with SRE-skills-bench structure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -e .

# Set default models.json if not exists
if [ ! -f "models.json" ]; then
    echo "Warning: models.json not found. Using default models."
    cat > models.json << EOF
[
  {"provider": "openai", "model": "gpt-4"},
  {"provider": "openai", "model": "gpt-4o"},
  {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"}
]
EOF
fi

# Run benchmark
echo "Running Terraform Generation Benchmark..."
python -m terraform_generation_bench.benchmark_cli suite \
  --models models.json \
  --tasks all \
  --runs-per-model 1

echo "✓ Benchmark complete! Check reports/ directory for results."

