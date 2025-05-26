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
