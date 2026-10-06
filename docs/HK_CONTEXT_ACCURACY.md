# Hong Kong collocation accuracy, 2026-10-06

Baseline: `0bff053` on `codex/offline-semantic-ranking`.

Add everyday Hong Kong objects and reminder predicates as reusable vocabulary fragments, not complete benchmark sentences. The generator includes the same additions so regeneration preserves them. Increase bounded authored lexical evidence from 0.65 to 2 per phrase link; the existing per-character cap stays at 4. Exact-code validation, search width, input UI and model execution are unchanged. No user input is stored or collected. Neural experiments remain excluded from the default release build and are not needed by this change.

Reproduce from the repository root:

```sh
bash tools/context_accuracy.sh 0bff053 context-evidence
```

| Suite | Cases | Baseline first | Updated first | Baseline top 5 | Updated top 5 | Baseline top 8 | Updated top 8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | 40 | 31 | 33 | 38 | 39 | 38 | 39 |
| Separate held-out conversations | 120 | 60 | 61 | 98 | 97 | 105 | 105 |

The development suite informed tuning; it is not an independent accuracy estimate. The separate corpus sample has a small first-choice gain and a one-case top-five loss. Full candidate-pool coverage on that sample remains 108/120. Every returned candidate in both suites was checked against all input codes.

`你記得帶遮` moves from outside the first eight candidates to first. `買飛` after the movie context moves from second to first. This does not establish full-sentence understanding: `我買咗麵包同牛奶` remains wrong, as do long-distance negation/availability examples. Further improvement needs broader, attributed Hong Kong training data and fresh validation sentences, rather than further tuning to these forty cases.

Local warmed JVM measurements were 13.3→18.8 ms median / 53.7→52.2 ms P95 on development cases and 25.7→27.6 ms median / 37.0→40.9 ms P95 on held-out cases. These single-host measurements include variability and do not establish Android fluency or a speed improvement. Real-device and Android regression acceptance remain pending; no new APK is claimed.
