# Final sentence ranking investigation (2026-10-14, unreleased)

This follows [DAILY_PREFIX.md](DAILY_PREFIX.md) using frozen `a65f43d` as the
baseline. The earlier independent800 already has observed outcomes; it is now
regression material. All660 cases here are previously inspected calibration
data. None of these pilots establishes new independent accuracy or changes
the production decoder, model assets, version or APK.

## Observe the actual candidate pool

`diagnose_sentence_priority.py` archives the committed Java/assets, loads all
models including the active prefix model, and observes raw, adjusted and
structural-support scores for the confidence-eligible final pool96. Removing
only the display20 cutoff preserves all660 native top20 candidate lists exactly.
The original trained corrections agree with Python within1.43e-14.

| Known calibration set | Cases | First | Top5 | Top20 |
| --- | ---: | ---: | ---: | ---: |
| Daily written |200 |46 |78 |106 |
| Authored |60 |27 |48 |60 |
| Natural |200 |80 |117 |140 |
| Public |200 |77 |131 |154 |

Across these660,230 targets rank first,275 exist later in pool96, and155 are
absent from that pool. Of the275,45 are outside display20. Ranking and search
coverage therefore remain separate problems. A gold usage example identifies
an intended target; it does not prove every competing sentence is invalid.

## Three bounded pilot policies

1. Prefix pair clipping: on7,632 training pairs, individually clipping both
   scores erases a nontrivial learned difference for1,004 pairs. Clipping their
   difference instead produces just one extra daily-written top20 target
   (106→107), with no first/top5 gain anywhere in660. No runtime change adopted.
2. First-choice protection:66 calibration cases pin the original raw winner.
   Unrestricted removal increases daily-written first46→47 and public first77→78;
   top5/top20 counts stay the same. Nine conservative support/score-margin
   combinations produce no aggregate change. This is not the main bottleneck.
3. Relative whole-sentence scores: six fixed-weight scale/pinning simulations
   have no top5 gain in any policy that preserves every set's existing counts.
   The full-strength policy adds one natural top20 target140→141; smaller
   strengths lose existing first/top20 hits. No gold-versus-raw-winner comparison
   has a nontrivial short-feature difference erased by individual clipping.

See the [prefix pilot](../tools/reports/prefix-clipping-pilot-2026-10-14.json),
[first-choice audit](../tools/reports/final-priority-report-2026-10-14.json) and
[relative-score audit](../tools/reports/final-priority-relative-score-report-2026-10-14.json).

## Mine current final-score errors

`pilot_final_hard_negatives.py` uses the frozen3,081 licensed/authored training
rows from daily-prefix work, and the actual current adjusted-score offsets.
Only targets already in the confidence-eligible pool provide sentence-ranking
pairs. Nonleading targets contribute up to three higher-scoring rivals; a
correct head contributes one close rival within3 score to protect existing
successes. Missing targets are reported, not invented or added to the pool.

HKCanCor utterances retain conversation grouping, Tatoeba translation families
remain independent, and authored slot variants share a template. Three source
families must support a feature. The existing schema3 features use local2–4 Han
units, marker/role relations and anchored1–2 units through12 trailing Han.
Counts are capped at2 and weights at1.5. Full sentences are not features.

The [protocol](../tools/data/final_hard_negative/protocol.json) freezes the training
list, baseline model and feature hashes before observation. Pairwise loss uses
actual current score differences. A simulated extra correction is positive
evidence above0.1, bounded to1.5 before strength, relative to the original raw
winner. The existing structural winner protection stays in place. Calibration
compares strengths0.25/0.5/1/1.5 and requires no first/top5/top20 loss in any set.

Training uses the already attributed HKCanCor CC BY4.0, Tatoeba CC BY2.0 France
and project-authored examples. Attribution is retained in
[the existing training notice](../app/src/main/assets/licenses/prefix/README.md).
words.hk usage examples with the Non-Commercial Open Data License1.0 stay
evaluation-only and do not train this pilot or enter the APK. These are not
private chats or measurements of current Hong Kong typing frequency.

The completed observer contains3,081 targets:2,380 already rank first,616 appear
later, and85 are absent. Mining yields2,049 pairs from1,539 targets and792 source
families. Of the pairs,1,093 are actual score errors and956 protect close correct
heads. The initial2,230-feature residual has no eligible strength: at strength1,
public first77→83/top5 131→133 improves, but written first46→44 and natural
first80→78/top5 117→115 regress.

### Corpus weighting amendment

The independent training families comprise46 HK conversations,676 Tatoeba
translation families,16 earlier authored families and54 new authored templates.
Among supported training examples, the original per-family balancing gives HK
only6.191% of total objective weight, Tatoeba84.671%, and authored examples9.138%.
Independent support grouping remains appropriate; it does not establish that
the corpus mixture should equal its family counts.

The optional `source_mix` argument in the shared trainer normalizes existing
target/family weights inside each group, then assigns explicit corpus shares.
HK50%, Tatoeba25% and combined authored25% are tested. Prefix selectors may use
`|` alternatives to put earlier/new authored families in the same group. This
is a training priority, not measured Hong Kong usage frequency. Feature support,
all observed pairs, offsets, caps and inference policy remain fixed. The initial
[protocol](../tools/data/final_hard_negative/initial-protocol.json) remains available;
the amendment is written before balanced-model calibration. Default training
without a mixture preserves the initial weights byte for byte.

The balanced2,232-feature pilot still has no eligible strength. At strength1:

| Known set | Existing first/top5/top20 | Balanced pilot first/top5/top20 |
| --- | --- | --- |
| Daily written200 |46/78/106 |47/81/105 |
| Authored60 |27/48/60 |26/48/60 |
| Natural200 |80/117/140 |78/116/140 |
| Public200 |77/131/154 |84/132/154 |

At strength1.5, written top5 reaches83, but authored/natural first and written
top20 regress. Both residual pilots are rejected before a new independent test;
their weights remain temporary artifacts and are not production assets. All
changed gold ranks, including gains and losses, are recorded in the
[initial calibration](../tools/reports/final-hard-validation-report-2026-10-14.json)
and [balanced calibration](../tools/reports/final-hard-balanced-validation-report-2026-10-14.json).
Training reports preserve pair/model/input hashes for
[the initial model](../tools/reports/final-hard-model-training-report-2026-10-14.json)
and [the balanced model](../tools/reports/final-hard-balanced-model-training-report-2026-10-14.json).

The next useful direction is more independent licensed Hong Kong natural
utterances with classifier/noun, negation/action and subject/action confusions,
followed by phrase-level relation features that generalize to other words.
Changing weights on the same narrow corpus and features has not established a
safe first/top5 gain. Candidates absent from pool96 still need separate search
coverage work; sentence reranking alone cannot recover them. Evidence from
temporary scores must not be described as installed-phone improvement.

```sh
source /workspace/android-environment/activate.sh
python tools/diagnose_sentence_priority.py /tmp/validation-cases.tsv /tmp/current-results.tsv /tmp/priority
python tools/pilot_final_hard_negatives.py observe tools/data/daily_prefix/train.tsv /tmp/train-scored.tsv
python tools/pilot_final_hard_negatives.py train /tmp/train-scored.tsv /tmp/final-hard-model
python tools/pilot_final_hard_negatives.py validate /tmp/priority/scored.tsv /tmp/final-hard-validation.json --model /tmp/final-hard-model
PYTHONPATH=tools python -m unittest tools/test_source_balancing.py tools/test_daily_prefix.py tools/test_sentence_search.py tools/test_sentence_ranking.py
```

Observation publishes complete UTF-8 outputs only after native success. Frozen
input identity checks reject incomplete or non-training rows. A promising
calibration result still needs native scorer parity, existing regression/latency
checks and a newly frozen unopened source-family reserve before adoption.
22 Python tests pass, including mixture pressure, duplicate-family invariance,
ambiguous source rejection and the existing byte/feature-parity regressions.
Functional checks also reject a non-training source, truncated observer and
mutated fitted weights before producing any training/evaluation artifact.
Version remains0.6.39/code46; no update APK or1.0 release is produced.
