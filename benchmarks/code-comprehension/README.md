# SRE-skills-bench: Code Comprehension

The **comprehend** track of SRE-skills-bench.

Code Comprehension evaluates how well a model understands real-world code changes —
reading a pull request diff and inferring its intent, identifying which change
closes an issue, reconstructing the issue it resolves, completing a masked change,
and avoiding hallucination. These are the day-to-day comprehension skills engineers
rely on when reviewing changes and triaging incidents, measured **without any
execution environment**: every task is static data, so the benchmark runs anywhere
with no repo checkout, build, or sandbox required.

It originated as the standalone *Environment-Free Coding Benchmark (EFCB)*.

## Methodology

- Source closed pull requests from leading open-source GitHub repositories.
- For each PR, scrape only the code patches from that pull request.
- Derive five tasks from the change, ranging from multiple-choice comprehension to
  open-ended generation graded by an LLM-as-a-judge. No codebase context beyond the
  diff is provided.

## Tasks

| Name | Category | Eval | Description |
| --- | --- | --- | --- |
| **GMCQ-Easy** | understanding | multiple choice | Choose the correct code diff that closes a PR |
| **GMCQ-Hard** | understanding | multiple choice | Same, but with both additions and removals in the candidates |
| **Reverse-QA** | text generation | LLM-as-a-judge | Generate an issue title and body given a code diff |
| **MPR-Gen** | code generation | LLM-as-a-judge | Given a masked section of a code diff, generate the missing code |
| **Reverse-QA-Hallu** | hallucination detection | LLM-as-a-judge | Detect whether the generated issue contains information absent from the diff |

GMCQ tasks are scored by exact match (a single letter A–D). Reverse-QA and MPR-Gen
are scored 0–10 for similarity to the ground truth; Reverse-QA-Hallu reuses the
Reverse-QA generations and scores each 0/1 for hallucinated content. The judge
prompts live in [`data/v0.3/judging_prompts/judging_prompts.yaml`](data/v0.3/judging_prompts/judging_prompts.yaml).

## Dataset

Every record uses the OpenAI-evals / [openbench](https://github.com/groq/openbench)
schema — `{"input": [<chat messages>], "ideal": "<answer>"}` — so the GMCQ subset
runs as a first-class `openbench` benchmark out of the box (see [Running](#running)).

**v0.3** — six repositories, four task files each (GMCQ-Easy, GMCQ-Hard, MPR-Gen,
Reverse-QA; Reverse-QA-Hallu is computed from the Reverse-QA file). PR-only framing:
given a closed pull request, scrape only that PR's code patches.

| Repository | GMCQ-Easy / Hard / Reverse-QA | MPR-Gen |
| --- | --- | --- |
| mastodon/mastodon | 239 | 163 |
| bluesky-social/indigo | 176 | 141 |
| cloudflare/cloudflared | 148 | 82 |
| duckdb/duckdb | 215 | 174 |
| tailscale/tailscale | 187 | 148 |
| chroma-core/chroma | 196 | 160 |

- `data/v0.3/tasks/<repo>/` — per-repository task files.
- `data/v0.3/judging_prompts/` — judge prompts for the LLM-as-a-judge tasks.
- `data/v0.2/` — earlier mastodon-only snapshot, kept for provenance.
- `data/v0.1/target_sre_mcq.jsonl` — the original 82-question GMCQ on
  mastodon/mastodon, using the **issue → which of four PRs closed it** framing
  (v0.3 later switched to PR-only). Published on Hugging Face as
  [`TheFloatingString/gmcq`](https://huggingface.co/datasets/TheFloatingString/gmcq)
  and runnable via `openbench` (`rootly_gmcq`); the local file is a snapshot.
- `configs/rootly_sre_mcq_mini.yaml` — OpenAI-evals registry entry for the v0.1 set.

## Running

The GMCQ subset ships as a first-class benchmark in
[openbench](https://github.com/groq/openbench) (`rootly_gmcq`), which pulls the
dataset from Hugging Face — so it runs out of the box:

```bash
uv pip install openbench
export GROQ_API_KEY=...        # or OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

# Whole dataset
bench eval rootly_gmcq --model "groq/llama-3.1-8b-instant"

# A single repository subtask (e.g. mastodon, bluesky, chroma, cloudflare, duckdb, tailscale)
bench eval rootly_gmcq --model "groq/llama-3.1-8b-instant" -T subtask=mastodon
```

The local snapshots in `data/` use the same record schema openbench expects, so
they stay interchangeable with the Hugging Face source. A runner for the
LLM-as-a-judge tasks (Reverse-QA, MPR-Gen, Reverse-QA-Hallu) is on the roadmap.

## Results (v0.3)

| Model | GMCQ-Easy | GMCQ-Hard | MPR-Gen | Reverse-QA | Reverse-QA-Hallu |
|---|---|---|---|---|---|
| openai/o4-mini | 0.892 | 0.868 | 7.41 | 3.67 | 0.946 |
| together/llama-3.3-70b-turbo | 0.803 | 0.476 | 7.23 | 3.74 | 0.965 |
| anthropic/claude-4-sonnet | 0.851 | — | — | — | — |

GMCQ scores are accuracy (0–1, higher is better). MPR-Gen and Reverse-QA are mean
judge scores (0–10, higher is better). Reverse-QA-Hallu is the share of generations
flagged as hallucination-free in this run.

<details>
<summary>Per-repository breakdown (v0.3)</summary>

### GMCQ-Easy

| Model | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | average |
|---|---|---|---|---|---|---|---|
| together/llama-3.3-70b-turbo | 0.912 | 0.699 | 0.845 | 0.800 | 0.759 | 0.801 | 0.803 |
| openai/o4-mini | 0.975 | 0.869 | 0.872 | 0.893 | 0.824 | 0.918 | 0.892 |
| anthropic/claude-4-sonnet | 0.950 | 0.801 | 0.851 | 0.856 | 0.786 | 0.862 | 0.851 |

### GMCQ-Hard

| Model | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | average |
|---|---|---|---|---|---|---|---|
| together/llama-3.3-70b-turbo | 0.452 | 0.392 | 0.574 | 0.470 | 0.465 | 0.500 | 0.476 |
| openai/o4-mini | 0.883 | 0.824 | 0.919 | 0.879 | 0.834 | 0.867 | 0.868 |

### MPR-Gen

| Model | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | average |
|---|---|---|---|---|---|---|---|
| together/llama-3.3-70b-turbo | 7.48 | 6.90 | 6.88 | 7.18 | 7.50 | 7.45 | 7.23 |
| openai/o4-mini | 7.50 | 7.35 | 7.49 | 7.29 | 7.73 | 7.11 | 7.41 |

### Reverse-QA

| Model | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | average |
|---|---|---|---|---|---|---|---|
| together/llama-3.3-70b-turbo | 3.94 | 3.40 | 4.01 | 3.97 | 3.84 | 3.28 | 3.740 |
| openai/o4-mini | 4.26 | 3.36 | 4.07 | 3.40 | 3.74 | 3.18 | 3.668 |

### Reverse-QA-Hallu

| Model | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | average |
|---|---|---|---|---|---|---|---|
| together/llama-3.3-70b-turbo | 0.941 | 0.983 | 0.959 | 0.967 | 0.984 | 0.954 | 0.965 |
| openai/o4-mini | 0.946 | 0.949 | 0.966 | 0.944 | 0.957 | 0.913 | 0.946 |

</details>

<details>
<summary>Earlier results (v0.2, mastodon only)</summary>

GMCQ-Easy (accuracy, higher is better): o3-mini 0.920 · sonnet-4 0.878 ·
Llama-3.3-70B-Turbo 0.817 · opus-4 0.812

GMCQ-Hard (accuracy, higher is better): opus-4 0.873 · sonnet-4 0.784 ·
o3-mini 0.732 · Llama-3.3-70B-Turbo 0.404

MPR-Gen (0–10, higher is better): sonnet-4 7.16 ± 2.70 · o3-mini 6.98 ± 2.28 ·
opus-4 6.90 ± 2.49 · Llama-3.3-70B-Turbo 6.63 ± 2.76

Reverse-QA (0–10, higher is better): opus-4 1.88 ± 1.93 · Llama-3.3-70B-Turbo
1.70 ± 1.33 · sonnet-4 1.58 ± 1.40 · o3-mini 1.56 ± 1.12

Reverse-QA-Hallu (hallucination rate, lower is better): sonnet-4 73.7% ·
opus-4 74.2% · Llama-3.3-70B-Turbo 79.8% · o3-mini 82.6%

</details>

<details>
<summary>GMCQ v0.1 (issue → PR, mastodon only — measured via OpenAI evals)</summary>

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

</details>

## Roadmap

- Expand repository coverage and refresh the leaderboard against current frontier
  models.
- Publish a runner so the LLM-as-a-judge tasks reproduce out of the box, alongside
  the GMCQ subset that already runs via `openbench`.

## Credits

GMCQ was developed by Rootly AI Labs fellow Laurence Liang. Built by the
[Rootly AI Labs](https://labs.rootly.ai/).
