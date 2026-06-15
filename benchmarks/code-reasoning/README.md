# SRE-skills-bench: Code Reasoning

The **code-change reasoning** track of SRE-skills-bench.

Code Reasoning evaluates how well a model reasons about real-world code changes —
reading a pull request diff and inferring its intent, reconstructing the issue it
resolves, completing a masked change, and avoiding hallucination. These are the
day-to-day comprehension skills engineers rely on when reviewing changes and
triaging incidents, measured **without any execution environment**: every task is
static data, so the benchmark runs anywhere with no repo checkout, build, or
sandbox required.

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
schema — `{"input": [<chat messages>], "ideal": "<answer>"}` — so it is
interchangeable with the [General Knowledge](../general-knowledge/) track, which
ships the GMCQ subset as a first-class `openbench` benchmark.

**v0.3** — six repositories, four task files each (GMCQ-Easy, GMCQ-Hard, MPR-Gen,
Reverse-QA; Reverse-QA-Hallu is computed from the Reverse-QA file):

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

## Roadmap

- Expand repository coverage and refresh the leaderboard against current frontier
  models.
- Publish a runner so the LLM-as-a-judge tasks reproduce out of the box, alongside
  the GMCQ subset that already runs via `openbench`.

## Credits

Built by the [Rootly AI Labs](https://labs.rootly.ai/).
