# Completed-path recovery and evidence-gated first choices (unreleased)

Baseline is `db4b363`, including the adopted PRR2 displayed-tail model.
This continues [SEARCH_ALIGNMENT.md](SEARCH_ALIGNMENT.md). Version remains
0.6.39/code46; no APK is built. The two goals are evaluated separately:
recover a missing exact-code sentence, then improve the first choice without
displacing explicit personal learning.

## Search diagnosis and bounded trial

All500 previously independent dictionary examples are now observed calibration
material. Of their242 missing targets,165 lose an observed prefix,26 reach a
completed path that is pruned,49 fall outside display20, one loses a character
option and one fails confidence. These are furthest observed frontiers rather
than proofs about every alternative tokenization. All242 target codes are exact.

Two then four additional close histories ending in an attested vocabulary suffix
produce no extra hits on the known500 or new100 validation cases. Both trials
are rejected. A separate trial widens only the completed-path pool96→128;
ordinary beam48, existing future/prefix reserves, display20, confidence10 and
dictionary contents remain. The known500 gains one displayed target at rank16,
with89/193 first/top5 unchanged; validation100 stays23/45/56. The3,293 old
calibration/guard cases preserve every group's first/top5/top20 counts.
These observed results are not independent accuracy evidence.

## Evidence-gated first choice

The first pilot uses the fixed PRR2 weights and conservative gate. It makes no
head changes on the600 known/validation cases, so no improvement is claimed.
The next trial fits a separate head map from the original source-separated
5,381 licensed training examples, leaving the full existing tail payload intact.

The first fitted top-five pilot changes seven heads without a labeled first
gain on600 cases. The next trial considers all20 already displayed candidates.
Wrong-head targets in ranks2..20 compete with the actual current first.
Correct heads supply protection against their current ranks2..9. The native
observer loads the fixed PRR2 asset and selected search, preserves exact-code
checks, and records actual adjusted scores. No evaluation target is inserted
into search or admitted to fitting. No private messages or phone learning
records train these immutable weights.

With raw head difference `d`, existing candidate-minus-head score `b`, strength
1.5, correction limit2, margin0.5 and minimum raw lift0.5, the fitted surrogate
uses the signed margin `min(d-0.5, b + 1.5*clip(d,-2,2)-0.5)`. Labels distinguish
repair from protection. Derivatives follow the active branch and are zero on
saturated score branches. Features need two source families; conversation,
translation-family and authored-template weighting retains65/20/15 source mass.
Discrete structural gates are audited at inference, not represented as a smooth
training guarantee.

The expanded candidates compare L2=0.015/0.005. The selected0.005 fit has2,236
pairs from586 families and2,502 retained head features. Its training surrogate
decreases0.60751→0.37379; this is not typing accuracy. Selection compares eligible
model/threshold combinations by aggregate first gain, then summedMRR and more
conservative thresholds/regularization on ties. All known groups must preserve
their first/top5/top20 counts; some individual cases still regress.

PRR3 preserves the PRR2 tail lexicon/weights, adding bounded head thresholds and
an optional independent map. A proposed swap needs two supported relation kinds,
new positive evidence, and repair of adverse evidence or more supported
non-negation structure. Negation alone cannot settle two otherwise equally
supported meanings. The actual corrected score must pass the margin and raw
lift gates. Only an existing displayed challenger may move first; the old first
is retained as runner-up. Displayed membership stays intact for a fixed search
pool; top-five membership can change. An ordered Chinese numeral/ordinal
signature must match, protecting quantities and ordinal information. This
generic safeguard follows observed ordinal/numeral regressions in old fragments;
there are no complete-sentence exceptions. Candidates whose maximum bounded
correction cannot reach the score threshold are skipped exactly, without changing
any possible gate decision.
Positive whole-word, explicit sequence and contextual personal evidence on the
head prevents a swap. Missing/corrupt optional assets retain the service fallback.
PRR1 and PRR2 keep their previous first-choice behaviour.
PRR1/PRR2 and missing-model fallback also retain pool96. The PRR3 wrapper selects
pool128; zero head thresholds with an empty, zero-strength head map select the
search-only arm. This permits the predeclared delivery arms to be selected by
the bundled asset without changing decoder source after the reserve is opened.

## Selection, reserve and sources

A new100 validation and500 reserve are frozen before trials, extending the
unchanged dictionary family hash order. All baseline-tracked training/evaluation
targets, old dictionary source families, raw training exposure and cross-split
six-character full-target substrings are excluded. See the
[manifest](../tools/data/search_recovery/manifest.json) and
[protocol](../tools/data/search_recovery/protocol.json), including pre-reserve
amendments and separate search/head adoption criteria.

Calibration may choose margin/lift0.5 or1, with useful first gain and no per-set
first/top5/top20 losses. More conservative thresholds break ties. Native parity,
old guards, Single32/32 and paired desktop wall/CPU ratios≤1.2 are required before
opening the reserve. The frozen independent arms are archived baseline,
search-only PRR2 and the selected combined model. Head adoption needs a first
gain over search-only; coverage-only gains are reported separately. Once opened,
the reserve is observed material and cannot tune this iteration.

words.hk dictionary examples remain NCDOL1.0 evaluation-only material, never
training or APK assets. The existing HKCanCor CC BY4.0, Tatoeba CC BY2.0 France,
UD-derived CC BY-SA4.0 and authored attribution remain applicable. These public
older spoken/dictionary examples do not measure contemporary private Hong Kong
typing frequency or Fold7 performance.

## Reproduction

```sh
source /workspace/android-environment/activate.sh
python tools/prepare_search_recovery.py /path/to/wordshk.csv /path/to/hkcancor-utf8.zip /path/to/yue_hk-ud-test.conllu
PYTHONPATH=tools python - <<'PY'
from pathlib import Path
from diagnose_sentence_priority import observe
observe(Path('tools/data/phrase_relations/train.tsv'), Path('/tmp/head-training.tsv'),
        revision='db4b363', working_tree=True, include_relation=True,
        relation_asset=Path('tools/data/search_recovery/search-only-relation_ranker.b64'))
PY
python tools/train_head_promotion.py /tmp/head-training.tsv /tmp/head-model
PYTHONPATH=tools python -m unittest tools/test_head_promotion.py tools/test_search_recovery.py
./gradlew testDebugUnitTest lintDebug --offline --max-workers=2
```

## Independent outcome and delivery

After source, model, thresholds, old guards, personal learning and timing were
fixed,500 new cases ran once in each native arm. The selection snapshot SHA-256
is `7c255399ff33be66216726fbb7ed37754c8737bef79b0008f8340dc0d758db73`.
There are no post-reserve runtime, weight, threshold or case changes. The reserve
is now observed evaluation material; unopened flags describe the frozen earlier
state. These cases differ from the previous October14 independent500.

| Metric | Archived baseline | Search only | Search + head |
| --- | ---: | ---: | ---: |
| First | 108/500 | 108/500 | 109/500 |
| Top five | 198/500 | 198/500 | 198/500 |
| Top twenty | 256/500 | 256/500 | 256/500 |
| MRR | 0.293102 | 0.293102 | 0.295035 |

Two targets enter first and one leaves it, giving one net hit (0.2 percentage
points). The paired exact two-sided first-hit p-value is1. This satisfies the
predeclared minimal-gain combined-arm condition but is very limited evidence,
not a statistically established population improvement. Search-only has no
independent target-hit gain; the dominant missing-prefix problem remains.
Known3,893-case calibration had13 first gains/3 losses; those sets overlap and
are not additional independent evidence.

The exact frozen combined asset is adopted for the unreleased build. The full
old tail payload remains unchanged; PRR3 asset flags select the qualified arm,
with old model fallback retaining the original search. The original user's
learning storage schemas and signing configuration are unchanged. Simulated
Single confirmation three times gives32/32 first targets and489 sequence records.

222 Java tests pass with no skipped cases; lint has0 errors/25 existing warnings.
42 unique Python checks pass: an initial41-case run skipped six missing original
source snapshots; those six passed after checksum-verified cache paths were
restored, and the final nine head/data checks include the new numeral case.
Native frozen-pool/score head-gate parity matches Python on3,893 cases;600 full
native decode lists match predictions, with byte-identical results after vector
sharing. The configured search-only wrapper matches the old128 trial on100
complete candidate lists. Four fitted output files reproduce byte for byte.

Two early30-warmup/15-sample timing trials exceed the1.2 budget. Exact feature
sharing, cheap bounded-score checks and deferred structural evidence avoid
repeated work. With50 warm-up passes/31 alternating samples onCPU0, the final
six-input paired maximum ratios are1.06296 wall and1.06262 CPU. Matched identical
baseline A/A ratios vary by less than1%. Apparent per-case speedups do not imply
faster recognition. This does not measure retained phone memory or Fold7 latency.

Version remains0.6.39/code46. No APK is produced and the1.0 goal is not reached.
The [work report](../tools/reports/search-recovery-work-2026-10-15.json) retains
source/model/input/output hashes, failed trials, verification details and the
three complete independent native outputs.
