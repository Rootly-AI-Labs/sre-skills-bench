# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

SRE-skills-bench is a benchmark suite for evaluating LLMs on Site Reliability Engineering tasks. It helps reliability practitioners choose the right model for IDE assistants, operational workflows, and incident response.

It is organized as self-contained sub-benchmarks along a **comprehend → write → act** capability ladder. There is no blended cross-track score; each track reports its own result.

## Tech Stack

- **Language**: Python 3.12
- **Package Manager**: uv
- **Tool Version Manager**: mise

## Project Structure

```
.
├── benchmarks/
│   ├── code-comprehension/  # COMPREHEND: reason about real PR diffs across 5 tasks, environment-free (data + judge prompts; GMCQ subset runs via `openbench eval rootly_gmcq`)
│   ├── terraform/           # WRITE: generate executable Terraform, graded against LocalStack (self-contained: own pyproject + run.sh)
│   └── incident-response/   # ACT: replay postmortems as live scenarios (planned; placeholder)
├── plot_benchmark.py        # Leaderboard visualization (reads static/data.csv)
├── static/                  # Logos and assets used by the README
├── mise.toml                # Tool version configuration
└── pyproject.toml           # Root: deps for plot_benchmark.py only
```

Each benchmark under `benchmarks/` is independently installable and run from its
own directory. When working on a track, treat its directory as the project root.

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

## Root-level tooling

`plot_benchmark.py` renders the leaderboard graph from `static/data.csv`:

```bash
uv venv && source .venv/bin/activate
uv pip install -e .         # installs matplotlib + adjusttext
python plot_benchmark.py
```
