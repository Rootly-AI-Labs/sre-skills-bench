# SRE-skills-bench: General Knowledge

The **comprehend** track of SRE-skills-bench.

GMCQ (GitHub Multiple Choice Questions) evaluates a model's ability to identify
the pull request that closes a bug-fix issue from a real-world GitHub repository —
a core comprehension skill for engineers triaging incidents and reviewing changes
under time pressure.

## Methodology

- Source issues labeled "bug" from leading open-source GitHub repositories.
- For each issue, collect its description and the pull request that resolved it.
- Present the model with the issue and **four candidate PRs** — the one that
  actually closed the issue, plus three real PRs from the same repository that
  closed *different* issues. No codebase context is provided.

Because every choice is a genuine, self-consistent PR, the task rewards real
understanding of the change rather than surface pattern-matching.

## Task format

```
Task Description:
Issue Title: <title>
Issue Description: <description>

---
Choice A: <changed filenames + code patch>
---
Choice B: <changed filenames + code patch>
---
Choice C: <changed filenames + code patch>
---
Choice D: <changed filenames + code patch>
```

The model responds with a single letter (A–D).

## Dataset

- `data/v0.1/target_sre_mcq.jsonl` — 82 questions in `{"input": [...], "ideal": "<letter>"}` format.
- `configs/rootly_sre_mcq_mini.yaml` — OpenAI-evals registry entry.

The canonical dataset is published on Hugging Face at
[`TheFloatingString/gmcq`](https://huggingface.co/datasets/TheFloatingString/gmcq);
the file here is a local snapshot.

## Running

GMCQ ships as a first-class benchmark in [openbench](https://github.com/groq/openbench)
(`rootly_gmcq`), which pulls the dataset from Hugging Face — so it runs out of the box:

```bash
uv pip install openbench
export GROQ_API_KEY=...        # or OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

# Whole dataset
bench eval rootly_gmcq --model "groq/llama-3.1-8b-instant"

# A single repository subtask (e.g. mastodon, bluesky, chroma, cloudflare, duckdb, tailscale)
bench eval rootly_gmcq --model "groq/llama-3.1-8b-instant" -T subtask=mastodon
```

The local snapshot in `data/` uses the same record schema openbench expects, so it
stays interchangeable with the Hugging Face source.

## Results (v0.1)

Measured with the [OpenAI evals](https://github.com/openai/evals) framework.

| Model | Accuracy |
| --- | --- |
| o4-mini | 0.927 ± 0.029 |
| o3 | 0.915 ± 0.032 |
| grok-3-beta | 0.915 ± 0.032 |
| Qwen-2.5-Coder-32B (Groq) | 0.902 ± 0.034 |
| grok-3-mini-beta | 0.902 ± 0.032 |
| o3-mini | 0.893 ± 0.034 |
| Gemini-2.5-Flash | 0.878 ± 0.036 |
| GPT-4o | 0.866 ± 0.039 |
| GPT-4.1 | 0.841 ± 0.039 |
| Gemini-2.0-Flash | 0.841 ± 0.042 |
| GPT-4o mini | 0.829 ± 0.042 |
| Qwen-2.5-32B (Groq) | 0.793 ± 0.044 |
| Claude 3.5 Sonnet | 0.780 ± 0.048 |
| DeepSeek V3.1 (Together AI) | 0.756 ± 0.049 |
| Llama-3.3 70B (Groq) | 0.720 ± 0.050 |
| Llama-4-Maverick (Groq) | 0.695 ± 0.051 |
| Llama-4 Scout (Groq) | 0.598 ± 0.053 |
| Llama-3.1 8B-instant (Groq) | 0.341 ± 0.052 |

## Roadmap

- Grow the dataset beyond v0.1 and broaden repository coverage.
- Refresh the leaderboard against current frontier models via `openbench eval rootly_gmcq`.

## Credits

GMCQ was developed by Rootly AI Labs fellow Laurence Liang. Built by the
[Rootly AI Labs](https://labs.rootly.ai/).
