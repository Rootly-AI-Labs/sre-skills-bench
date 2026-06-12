# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

SRE-skills-bench is a benchmark suite for evaluating LLMs on Site Reliability Engineering tasks. It helps reliability practitioners choose the right model for IDE assistants, operational workflows, and incident response.

It is organized as three self-contained sub-benchmarks along a **comprehend → write → act** capability ladder. There is no blended cross-track score; each track reports its own result.

## Tech Stack

- **Language**: Python 3.12
- **Package Manager**: uv
- **Tool Version Manager**: mise

## Project Structure

```
.
├── benchmarks/
│   ├── general-knowledge/   # COMPREHEND: GMCQ — match a bug-fix issue to the PR that closed it (runs via `openbench eval rootly_gmcq`)
│   ├── terraform/           # WRITE: generate executable Terraform, graded against LocalStack (self-contained: own pyproject + run.sh)
│   └── incident-response/   # ACT: live incident scenarios graded across the incident lifecycle (planned; placeholder)
├── static/                  # Assets used by the README
└── mise.toml                # Tool version configuration
```

Each benchmark under `benchmarks/` is independently installable and run from its
own directory. When working on a track, treat its directory as the project root.
The repository root holds only documentation and tool configuration — there is no
root-level Python package.

## Development Setup

```bash
# Install tools via mise
mise trust
mise install
```

Then follow the per-benchmark README for setup. For example, the Terraform track:

```bash
cd benchmarks/terraform
uv venv && source .venv/bin/activate
uv pip install -e .
docker compose up -d        # LocalStack
./run.sh
```
