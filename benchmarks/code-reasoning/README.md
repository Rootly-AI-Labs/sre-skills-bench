# Environment-Free Coding Benchmark ⚗️

This coding benchmark aims to offer robust and challenging tasks to evaluate
language models on, without requiring the need to use a coding environment to
simplify the benchmark setup.

| Prototype Ready? | Production-Ready? | Name | Categories | Eval | Description |
| --- | --- | --- | --- | --- | --- |
| Yes ✅| Not yet | GMCQ-easy | understanding | mcq | choose the correct code diff that closes a PR |
| Yes ✅| Not yet | GMCQ-hard | understanding | mcq | choose the correct code diff that closes a PR, with additions and removals |
| Yes ✅| Not yet| Reverse-QA | text generation | LLM-as-a-judge | generate an issue title and body given code diff |
| Yes ✅ | Not yet | MPR-Gen | code generation | LLM-as-a-judge | given a maksed section of a code diff, generate the code |
| Yes ✅ | Not yet | Reverse-QA-Hallu | hallucination detection | LLM-as-a-judge | uses an LLM-as-a-judge to determine whether the model hallucinated |

## Overall Results (v0.3) 🏆

| Model Name                   | GMCQ-Easy | GMCQ-Hard | MPR-Gen | Reverse-QA | Reverse-QA-Hallu | EFCB Score |
|------------------------------|----------|--------|-------------|--------|-----------|--------|
| together/llama-3.3-70b-turbo |    0.803 |  0.476 |   3.74 |  7.23   | 0.965 |   0.482 |
| openai/o4-mini               |    0.892 |  0.868 |    3.67 |   7.41 |    0.946 |    0.584 |


## Detailed Results (v0.3) 📊

### GMCQ-Easy (v0.3)

| Model Name                   | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | unweighted average |
|------------------------------|----------|--------|-------------|--------|-----------|--------|--------------------|
| together/llama-3.3-70b-turbo |    0.912 |  0.699 |       0.845 |    0.8 |     0.759 |  0.801 |              0.803 |
| openai/o4-mini               |    0.975 |  0.869 |       0.872 |  0.893 |     0.824 |  0.918 |              0.892 |
| anthropic/claude-4-sonnet    |     0.95 |  0.801 |       0.851 |  0.856 |     0.786 |  0.862 |              0.851 |

### GMCQ-Hard (v0.3)

| Model Name                   | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | unweighted average |
|------------------------------|----------|--------|-------------|--------|-----------|--------|--------------------|
| together/llama-3.3-70b-turbo |    0.452 |  0.392 |       0.574 |   0.47 |     0.465 |    0.5 |              0.476 |
| openai/o4-mini               |    0.883 |  0.824 |       0.919 |  0.879 |     0.834 |  0.867 |              0.868 |

### MPR-Gen (v0.3)

| Model Name                   | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | unweighted average |
|------------------------------|----------|--------|-------------|--------|-----------|--------|--------------------|
| together/llama-3.3-70b-turbo |     7.48 |    6.9 |        6.88 |   7.18 |       7.5 |   7.45 |               7.23 |
| openai/o4-mini               |      7.5 |   7.35 |        7.49 |   7.29 |      7.73 |   7.11 |               7.41 |

### Reverse-QA (v0.3)

| Model Name                   | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | unweighted average |
|------------------------------|----------|--------|-------------|--------|-----------|--------|--------------------|
| together/llama-3.3-70b-turbo |     3.94 |    3.4 |        4.01 |   3.97 |      3.84 |   3.28 |              3.740 |
| openai/o4-mini               |     4.26 |   3.36 |        4.07 |    3.4 |      3.74 |   3.18 |              3.668 |

### Reverse-QA-Hallu (v0.3)

| Model Name                   | mastodon | indigo | cloudflared | duckdb | tailscale | chroma | unweighted average |
|------------------------------|----------|--------|-------------|--------|-----------|--------|--------------------|
| together/llama-3.3-70b-turbo |    0.941 |  0.983 |       0.959 |  0.967 |     0.984 |  0.954 |              0.965 |
| openai/o4-mini               |    0.946 |  0.949 |       0.966 |  0.944 |     0.957 |  0.913 |              0.946 |