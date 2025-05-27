# Environment-Free Coding Benchmark

This coding benchmark aims to offer robust and challenging tasks to evaluate
language models on, without requiring the need to use a coding environment to
simplify the benchmark setup.

| Prototype Ready? | Production-Ready? | Name | Categories | Eval | Description |
| --- | --- | --- | --- | --- | --- |
| Yes ✅| Not yet | GMCQ-easy | understanding | mcq | choose the correct code diff that closes a PR |
| Yes ✅| Not yet | GMCQ-hard | understanding | mcq | choose the correct code diff that closes a PR, with additions and removals |
| Yes ✅| Not yet| Reverse-QA | text generation | LLM-as-a-judge | generate an issue title and body given code diff |
| Not yet | Not yet | MPR-Gen | code generation | LLM-as-a-judge | given a maksed section of a code diff, generate the code |
| Not yet | Not yet | Reverse-QA-Hallu | hallucination detection | Lynx-8B | uses Lynx-8B to determine whether the model hallucinated |

## Prototype-Ready Results

### GMCQ-Easy (v0.2)

| Model Name | Score |
| --- | --- |
| llama-3.3-70b-versatile (Groq) | 0.826 |
| o3-mini |  0.920 |
| opus-4 | 0.812 |
| sonnet-4| 0.878 | 

### GMCQ-Hard (v0.2)

| Model Name | Score |
| --- | --- |
| llama-3.3-70b-versatile (Groq) | 0.362 |
| o3-mini | 0.732 |
| opus-4 | 0.873 |
| sonnet-4| 0.784 | 

### Reverse QA (v0.2)

| Model Name | Score |
| --- | --- |
| llama-3.3-70b-versatile (Groq) | 1.69 +/- 1.37 |
| o3-mini | 1.56 +/- 1.12  |
| opus-4 | 1.88 +/- 1.93 |
| sonnet-4| 1.58 +/- 1.40 | 

### Reverse QA-Hallu (v0.2)

| Model Name | Hallucination Rate |
| --- | --- |
| llama-3.3-70b-versatile (Groq) | 78.4% |
| o3-mini |   |
| opus-4 |  |
| sonnet-4|  | 
