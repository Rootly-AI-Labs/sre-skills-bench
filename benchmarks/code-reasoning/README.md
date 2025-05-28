# Environment-Free Coding Benchmark

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

## Prototype-Ready Results

### GMCQ-Easy (v0.2)

Higher score is better. (0 to 1)

| Model Name | Score |
| --- | --- |
| o3-mini |  0.920 |
| sonnet-4| 0.878 | 
| llama-3.3-70b-versatile (Together) | 0.817 |
| opus-4 | 0.812 |

### GMCQ-Hard (v0.2)

Higer score is better. (0 to 1)

| Model Name | Score |
| --- | --- |
| opus-4 | 0.873 |
| sonnet-4| 0.784 | 
| o3-mini | 0.732 |
| llama-3.3-70b-versatile (Together) | 0.404 |

### Reverse QA (v0.2)

Higher score is better. (0 to 10)

| Model Name | Score |
| --- | --- |
| opus-4 | 1.88 +/- 1.93 |
| llama-3.3-70b-versatile (Together) | 1.70 +/- 1.33 |
| sonnet-4| 1.58 +/- 1.40 | 
| o3-mini | 1.56 +/- 1.12  |

### Reverse QA-Hallu (v0.2)

Lower score is better (0% to 100%)

| Model Name | Hallucination Rate |
| --- | --- |
| sonnet-4| 73.7% | 
| opus-4 | 74.2% |
| llama-3.3-70b-versatile (Together) | 79.8% |
| o3-mini | 82.6% |

### MPR-Gen (v0.2)

Higher is better (0 to 10)

| Model Name | Score |
| --- | --- |
| sonnet-4| 7.16 +/- 2.70  |  
| o3-mini | 6.98 +/- 2.28  |
| opus-4 | 6.90 +/- 2.49 |
| llama-3.3-70b-versatile (Together) | 6.625 +/- 2.76 |
