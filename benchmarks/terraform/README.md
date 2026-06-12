# SRE-skills-bench: Terraform

The **write** track of SRE-skills-bench. Evaluates LLMs on their ability to
generate **executable Terraform code** from natural-language prompts, testing
end-to-end code generation and execution against LocalStack.

## Install & run

```bash
cd benchmarks/terraform
uv venv && source .venv/bin/activate
uv pip install -e .
docker compose up -d            # LocalStack
./run.sh                        # or use the CLI directly (see below)
```

## Architecture

```
src/terraform_generation_bench/
├── __init__.py
├── llm_client.py              # Multi-provider LLM client (OpenAI, Anthropic, OpenRouter)
├── terraform_generator.py     # Code extraction from LLM responses
├── benchmark.py               # Benchmark runner
├── benchmark_cli.py           # CLI interface
├── report_generator.py        # Report generation (JSON, HTML, Markdown)
└── runner/
    ├── __init__.py
    ├── run_task.py           # Terraform pipeline execution
    ├── checks.py             # Post-apply validation
    └── utils.py              # Utility functions

tasks/terraform_generation/
├── task_vpc_3subnets_3ec2/
│   ├── spec.yaml             # Task specification
│   └── prompt.txt            # LLM prompt template
├── task_ec2_instance_profile/
├── task_iam_role_policy/
├── task_s3_bucket_policy/
├── task_s3_cors_configuration/
├── task_s3_lifecycle_versioning/
├── task_s3_public_access_block/
├── task_security_group_complex/
├── task_vpc_internet_gateway/
├── task_vpc_multiple_route_tables/
└── task_vpc_nat_gateway/
```

## Task Pipeline

Each task runs through the following pipeline:

1. **Code Generation**: LLM generates Terraform code from prompt
2. **Format Check**: `terraform fmt -check`
3. **Initialize**: `terraform init`
4. **Validate**: `terraform validate`
5. **Plan**: `terraform plan`
6. **Apply**: `terraform apply` (creates resources in LocalStack)
7. **Post-Apply Checks**: Verify resources exist and are correctly configured
8. **Idempotency Check**: Second `terraform plan` (should show no changes)
9. **Destroy**: `terraform destroy` (cleanup)

## Failure Categories

- **SYNTAX**: Terraform syntax errors
- **INIT**: Provider initialization failures
- **VALIDATE**: Configuration validation errors
- **PLAN**: Planning phase errors
- **APPLY**: Resource creation failures
- **CHECKS**: Post-apply validation failures
- **IDEMPOTENCY**: Second apply shows changes
- **DESTROY**: Cleanup failures
- **Generation**: LLM API errors

## Results

Results are stored in `results/<model>/<task>/<run>/`:
- `benchmark_result.json`: Complete benchmark results
- `check.json`: Post-apply validation results
- `logs/`: Terraform command logs

Reports are generated in `reports/`:
- `comprehensive.md`: Overall model performance across all tasks
- Individual task reports

## Example Usage

```bash
# Run single benchmark
python -m terraform_generation_bench.benchmark_cli benchmark \
  --provider openai \
  --model gpt-4 \
  --task-id task_vpc_3subnets_3ec2

# Run benchmark suite
python -m terraform_generation_bench.benchmark_cli suite \
  --models models.json \
  --tasks all \
  --runs-per-model 1

# Generate comprehensive report
python -m terraform_generation_bench.benchmark_cli report \
  --format comprehensive \
  --output reports/comprehensive.md
```

## Configuration

### models.json

```json
[
  {"provider": "openai", "model": "gpt-4"},
  {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
  {"provider": "openrouter", "model": "google/gemini-2.5-flash"}
]
```

### Environment Variables

```bash
export OPENAI_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key
export OPENROUTER_API_KEY=your_key  # Optional, used as fallback
```

## LocalStack Setup

LocalStack is required for safe testing. Start it with:

```bash
docker compose up -d
```

Verify it's running:
```bash
curl http://localhost:4566/_localstack/health
```

## Findings Summary

Based on testing 16 models across 11 tasks:

- **99% of failures** occur during Terraform execution (not code generation)
- **Most common failures**: INIT (33%), SYNTAX (21%), VALIDATE (13%)
- **Top performers**: DeepSeek Chat (27%), Mistral Large (18%), Llama 3 70B (18%)
- **Only 25% of models** pass at least one task

This indicates that while LLMs can generate code, they struggle with:
- Correct provider configuration
- Valid Terraform syntax
- Proper resource relationships and dependencies

