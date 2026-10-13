# Daily written evaluation and prefix-specific training (2026-10-13, unreleased)

This experiment separates daily usage evaluation from training and fits errors
observed during search, before a complete sentence exists. It compares with the
fixed `241803b` source, including the completed-pool and SRK3 changes described
in [SENTENCE_SEARCH.md](SENTENCE_SEARCH.md). Installed APK 0.6.39 and this source
comparison must not be treated as identical baselines.

## Data and exposure

The pinned words.hk sample CSV contains 58,364 entries. Only 15,597 reviewed `OK`
and `已公開` entries are eligible. The preparation tool extracts punctuation-
terminated Cantonese examples, retains NFC glyphs, removes pronunciation/markup
and omits internal commas for continuous Han composition. Targets contain 6–24
characters with exact reachable codes, a Cantonese marker and a bounded rare-
character ratio. It does not map historical variants or remove dictionary entries.

Headwords, exact examples and one-edit variants form connected groups before
splitting and sampling. One example per family is selected by deterministic hash
order. The 10,559 eligible examples form 6,897 groups. 200 examples are validation;
800 are reserved for decoding only after the selection decision. They are human
dictionary usage examples, not private chats or measured current typing frequency.
The dictionary data has the Non-Commercial Open Data License1.0, distinct from
the mirror's MIT parser code. These examples never train a model or enter the APK.
See [NOTICE](../tools/data/daily_prefix/NOTICE.txt) and its full data license.

Training uses 2,529 filtered existing licensed training cases plus 552 independently
authored daily variants, covering work, questions, travel, food, payment, home,
shopping and messages. Entire authored sentences are not dictionary entries or
model features. Repeated template variants are not measured frequency. Training
and evaluation targets are substring-disjoint at 6+ characters; known previous
test targets are excluded without consulting prediction outcomes. Preparation
inputs and train/evaluation files are frozen by checksums and the baseline file list.

A pre-test exposure audit additionally checks raw HKCanCor training utterances,
licensed Tatoeba training and the baseline word vocabularies. One reserved target,
「點解你唔返學」, occurs in Tatoeba training. It remains in the original 800; results
also report the 799 without observed overlap. No outcome-based replacements occur.
Shared shorter words remain possible, as in normal language model evaluation.

## Training objective and bounded search

The archive-only observer labels an actual prefix as positive only if it starts
the gold sentence and both consumed and remaining codes have a valid split. Gold
completion text labels training; it is never a runtime feature or vocabulary hint.
Non-leading prefixes within the original raw beam floor minus4 are observed;
discarded checkpoints take priority. At most two checkpoints and three competing
prefixes per checkpoint contribute to one target. The actual original pruning-
score margin is part of the loss. Export publishes a complete UTF-8 artifact only
after success, so interrupted jobs cannot leave partially written training files.

There are 7,632 pairs from 1,577 targets, grouped into 721 independent conversation,
translation or authored template families. Minimum feature support is three such
families. Short 2–4-character collocations, endpoint 1–3-character surfaces, marker/
role relations and cross-boundary 1–2-character hint units share evidence. Runtime
history is bounded to 12 trailing Han; punctuation and Latin reset it. At most six
actual vocabulary hints matching remaining typed codes are used, with separate
leading/alternative buckets. Each feature contributes at most twice; complete
sentences are not features.80 full-batch AdaGrad epochs use rate 0.3 and L2=0.01.
Individual weights are bounded to±1.5; prefix evidence to±2 before strength.

The PRK1 experiment has 2,403 features and 23,429 encoded bytes. The original 48
paths and eight lexical reserves remain intact. Cheap positive endpoint 2–3-gram,
endpoint-character and leading-hint lookups retrieve up to 32 close discarded
histories for full scoring. At most four receive survival protection when their
correction exceeds the same-code core boundary correction by more than 0.25.
Unknown endpoints receive no proposal. Endpoint evidence remains available
without lookahead.
This changes survival only: raw path scores, confidence filtering, completed
pool 96, display 20 and explicit personal ordering remain unchanged. Absence or
failure of the optional asset retains the old behavior. The immutable ranker
does not store editor text or change the local learning schema.

The initial rank 24+ training-only observer yielded too few cases; supervision
was broadened to non-leading rank 2+ prefixes before any trial validation decoding.
A source grouping defect found before accepting trial outcomes was repaired:
distinct Tatoeba families are independent, while HKCanCor utterances share their
conversation and authored slot variants share their template. The earlier
incorrectly grouped trial is excluded from results.

The first absolute-score reserve increases written validation top20 from 106 to 108
with no first/top-five gain. Its original-case guards also show no first/top-five
gain. The signed pairwise training objective instead supports a difference
against a same-code rival, including less-negative evidence; an absolute-positive
gate discards that distinction. Only inspecting the first 32 raw-ranked paths can
also overlook correct prefixes: median raw rank of 64 missing prefix frontiers is 104.
The revised retrieval and relative boundary comparison are defined in a separate
[policy protocol](../tools/data/daily_prefix/relative-protocol.json), after seeing
initial validation outcomes and before opening the 800 reserve. The 200 now serves
as calibration for this policy; only the final reserved outcomes are independent.
Weights and feature extraction remain frozen. The initial reserve source fragment
and `--initial-policy` option permit reproducing that earlier policy.

## Selection and reproducibility

The [protocol](../tools/data/daily_prefix/protocol.json) precedes trial evaluation.
Strengths 0.25,0.5,1 and1.5 are compared on the new 200 plus the existing authored 60,
natural 200 and public 200 validation sets. Eligibility requires no first-choice or
top-five loss in each set; selection maximizes equally weighted set MRR, with the
lower strength breaking ties. An ineffective scorer is disabled. Existing known
regressions constrain delivery before the untouched reserve is opened. The new
major gate requires at least five percentage points of first/top-five gain on
both the original 800 and audited799, safe regressions and warmed median latency
at most 1.2 times baseline. Physical Fold7 evidence is required for device claims.

```sh
source /workspace/android-environment/activate.sh
python3 tools/prepare_daily_prefix_data.py /path/to/wordshk.csv
python3 tools/audit_daily_prefix.py /path/to/hkcancor-utf8.zip
python3 tools/export_prefix_pairs.py tools/data/daily_prefix/train.tsv /tmp/pairs.tsv
python3 tools/train_prefix_ranker.py /tmp/pairs.tsv /tmp/prefix-model
python3 tools/verify_prefix_parity.py /tmp/pairs.tsv /tmp/prefix-model/weights.json
python3 tools/evaluate_daily_prefix.py /tmp/prefix-model/weights.json /tmp/validation-cases.tsv /tmp/prefix-validation
# Only after the decision and existing regression checks:
python3 tools/evaluate_daily_prefix.py /tmp/prefix-model/weights.json tools/data/daily_prefix/heldout.tsv /tmp/prefix-heldout --selection /tmp/prefix-validation/selection.json
PYTHONPATH=tools python3 -m unittest tools/test_daily_prefix.py tools/test_sentence_search.py tools/test_sentence_ranking.py
./gradlew testDebugUnitTest lintDebug --offline --max-workers=2
```

The combined validation file prepends `validation:written200` to the new 200,
then names the three previous validation sets in the first TSV field. The fourth
field remains the target. Baseline/trial native evaluators check full input codes
for every returned candidate. Each trial uses an isolated asset directory. No
network or online inference is needed with pinned sources and cached dependencies.

## Final results and delivery

The revised policy selects strength0.25. On the final800, exact top1/top5/top20
are178/316/399 before and178/317/401 after. Excluding the previously observed
Tatoeba phrase, the799 are177/315/398 before and177/316/400 after. First-choice
gain is zero; top-five gain is0.125 percentage points on800. Three new targets
enter display20, including「你噉樣笑佢好傷佢自尊」at rank5. One previously rank20
target,「結婚之後佢希望太太辭職留喺屋企做家庭主婦」, falls outside display20.
No test outcome changes training, selected strength or search policy.

The revised written200 calibration stays46/78/106; existing public200 coverage
increases153→154. Authored60 and natural200 aggregate hits remain unchanged.
All1,594 original regression targets retain their per-set top1/top5/top20 counts
(aggregate758/1119/1263); this does not assert every candidate list is identical.
Three explicit Single confirmations retain32/32 contextual first choices,
against30/32 legacy-only, with489 sequence records. All209 Java tests and19 Python
tests pass; Lint has zero errors and25 existing warnings. Every observed training
feature vector and serialized correction agrees with Python/Java:9,972 cases.
Frozen training assets reproduce byte for byte. The actual bundled0.25 asset
loads and recovers the exact rank5 candidate in an end-to-end test while explicit
personal choices remain first.

Paired desktop timing uses one JVM with isolated before/after classes, CPU0,
twelve warmup passes and fifteen alternating samples. No build, training or other
decoding benchmark runs concurrently.

| Input letters | Baseline wall median,ms | Active prefix wall median,ms |
| --- | --- | --- |
|11 |78.921 |78.102 |
|12 |162.634 |159.120 |
|22 |140.443 |149.110 |
|18 |227.335 |227.532 |
|16 |142.333 |143.120 |
|48 pressure |551.104 |632.620 |

Maximum ordinary increase is6.2%; pressure increase is14.8%. The1.2 ratio guard
passes, but this establishes no speedup or physical Fold7/Android ART latency.
The [delivery rule](../tools/data/daily_prefix/delivery-rule.json) was recorded
before independent decoding: an asset requires an independent first/top-five
gain, neither metric worse, passing old guards and acceptable desktop timing.
The small top-five gain meets that limited rule. The optional0.25 asset and its
training-source attribution are included in unreleased source; settings exposes
the notice. Dictionaries, other model assets, local-learning schema, signing,
application ID and Fold layout settings remain intact.

Neither first/top-five gain meets the five-percentage-point major threshold.
Version remains0.6.39/code46; no APK or release is produced. These dictionary
examples support a narrow reproducible gain, not reliable population accuracy
or measured contemporary Hong Kong chat frequency. See the [full report](../tools/reports/daily-prefix-work-2026-10-13.json).

