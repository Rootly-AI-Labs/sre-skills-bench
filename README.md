# SRE-skills-bench

<h2 align="center">
 <br>
 <img src="static/SRE-skills-bench-logo.png" alt="SRE-skills-bench">
</h2>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

> *Can Language Models Resolve SRE Tasks?*

SRE-skills-bench evaluates LLMs on tasks commonly performed by Site Reliability Engineers, helping reliability practitioners choose the right model for the job, whether it's powering IDE assistants, automating operational workflows, or improving incident response. Think of SRE-skills-bench as the SWE-bench of Site Reliability Engineering.

At the Rootly AI Labs, we run SRE-skills-bench on frontier models the day they are released, and we share our findings on our social media platforms ([LinkedIn](https://linkedin.com/company/rootlyhq/), [X](https://x.com/rootlyhq)). We also present our benchmarks at leading ML research conferences, including as workshop papers at NeurIPS, ICML, and ACL.

## Benchmarks

SRE-skills-bench is organized as three sub-benchmarks along a **comprehend → write → act** capability ladder. Each is self-contained under `benchmarks/<name>/` with its own README, dependencies, and runner, and reports its own score (there is no single blended number).

| Track | Capability | What it tests | Status |
|-------|------------|---------------|--------|
| [**General Knowledge**](benchmarks/general-knowledge/) | Comprehend | Given a bug-fix issue and four candidate PRs from the same repo, identify the PR that closed it (GMCQ) | Available — runs via `openbench eval rootly_gmcq` |
| [**Terraform**](benchmarks/terraform/) | Write | Generate **executable** Terraform from a natural-language prompt; graded by running the full `fmt → init → validate → plan → apply → destroy` lifecycle against LocalStack | Available |
| [**Incident Response**](benchmarks/incident-response/) | Act | Run live incident scenarios; grade an agent across detect → localize → diagnose → mitigate → verify | Planned |

```
benchmarks/
├── general-knowledge/   # comprehend  (GMCQ — runs via openbench)
├── terraform/           # write       (executable Terraform generation)
└── incident-response/   # act         (live incident scenarios — planned)
```

## 📰 News
* **[Dec. 2, 2025]**: [presenting our work](https://x.com/LaurenceLiang1/status/1993446585062375710?s=20) at ER – NeurIPS in San Diego, USA.
* **[Nov. 24, 2025]**: [released](https://rootly.com/blog/gemini-3-lead-in-sre-tasks) ~3,000 new tasks testing LLMs on compute, network, and storage actions across AWS, GCP, and Azure.
* **[Jul. 27, 2025]**: [presented](https://x.com/LaurenceLiang1/status/1950315795248222646?s=20) our work at KnowFM – ACL 2025 in Vienna, Austria.
* **[Jul. 19, 2025]**: [presented](https://www.linkedin.com/posts/rootlyhq_icml-last-week-was-packed-with-the-people-activity-7353091496885084160-Kg6h?utm_source=share&utm_medium=member_desktop&rcm=ACoAAADGnFABrpDYk0E2FAxG_0rQwv3fcQbkd7E) our work at New In ML – ICML 2025 in Vancouver, Canada.

## Getting Started

This project uses [mise](https://mise.jdx.dev/) for tool version management and [uv](https://docs.astral.sh/uv/) for Python packaging.

```bash
# Install mise (if not already installed)
curl https://mise.run | sh
mise trust && mise install
```

Each benchmark is run from its own directory — see the per-track README for setup and commands:

- **Terraform** → [`benchmarks/terraform/README.md`](benchmarks/terraform/README.md)
- **General Knowledge** → [`benchmarks/general-knowledge/README.md`](benchmarks/general-knowledge/README.md)
- **Incident Response** → [`benchmarks/incident-response/README.md`](benchmarks/incident-response/README.md)

## 🔗 About the Rootly AI Labs
SRE-skills-bench is built with ❤️ by the [Rootly AI Labs](https://rootly.com/ai-labs) for engineering teams everywhere. The Rootly AI Labs is a fellow-led community designed to redefine reliability engineering. We develop innovative prototypes, create open-source tools, and produce research that's shared to advance the standards of operational excellence. We want to thank Anthropic, Google Cloud, and Google DeepMind for their support.
