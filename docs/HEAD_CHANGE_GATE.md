# Learn when to replace the first choice

This separately authorized experiment follows the rejected
[visible-candidate reranker](VISIBLE_CANDIDATE_RERANKING.md). Parent `f7cd44c`
has the same production app as `e209474`. The fixed adapted language checkpoint
and original visible candidates are unchanged. We fit one small decision model
to accept or reject the language model's proposed first choice. Rejecting a
replacement restores the parent head while retaining the neural order of all
other choices. It does not restore an unavailable answer or expand search.

## Data and separation

The cached7,891 ordinary TRAIN observations were generated from `3aa8870`, whose
app tree equals the current parent. Their original pool/display hashes and
ordered TRAIN identities are checked. Admission and the internal split inherit
the sentence-pretraining experiment's original conversations, translation
families, authored scenarios and full-target exclusions. This also keeps the
gate's internal validation out of both neural training stages. No evaluation
sentence is made a training exception.

Other immutable parent models may already have used these original TRAIN
sources. This separation concerns the new gate and the added neural stages;
it is not an end-to-end unseen-source test of the whole keyboard.

There are7,553 admitted displays with a visible target and at least one rival:

| Source | TRAIN displays | Internal validation displays |
|---|---:|---:|
| HKCanCor/UD |4258|636|
| Tatoeba |1799|222|
| Authored scenarios |565|73|
| Total |6622|931|

The two sides contain1,736 and214 original families, with no intersection.
142 rows fail the inherited admission check and196 lack a visible target or
rival. All original sources remain TRAIN-only relative to external evaluation.
They are not newly collected phone messages or measured modern chat frequency.

When the original head is correct, each rival teaches protection. When it is
wrong, the visible correct candidate teaches repair. Pairs where neither is the
target remain unlabeled. This yields84,384 TRAIN pairs (935 repair,83,449
protection) and11,609 internal-validation pairs. Rival counts are normalized per
case, then original family and source; source mass is HK/UD65%, Tatoeba20%,
authored15%. The label imbalance is reported rather than mistaken for independent
sentence count. No character, word or complete-sentence identity enters the gate.

## Fixed model and selection

Twenty numeric dimensions describe the original raw/projected score margin,
fixed neural evidence, existing structural support, candidate rank, length,
shared-character position fractions, combined margin, competing score gaps and
three product terms. The sealed protocol prose says four interactions; the
frozen extractor actually has three products and an additive combined-margin
term. The protocol and implementation are not changed after outcomes.

One logistic fit uses TRAIN-weighted means/scales, L2.01 excluding the bias,
and deterministic L-BFGS-B with at most400 iterations. The only threshold grid
is.5/.6/.7/.8/.9/.95/.99. Selection evaluates the actual neural head proposal,
not an oracle-selected challenger: every represented source domain must retain
its first count and aggregate first count must improve. Equal-domain first-rate
gain selects the threshold, then fewer losses and the higher threshold break
ties. No threshold is selected using external calibration or guard sentences.

The selected threshold is.99. This is a score threshold on a weighted model,
**not a claim of99% real-world confidence**. Internal validation first counts
change807→818: HK594→594 (one gain/one loss), Tatoeba181→187, authored32→37.
There are14 proposed swaps; an already wrong head changing to another wrong
head is not counted as a gain. These results select the gate and are not
independent keyboard-accuracy evidence.

The numerical fit first completed but failed while serializing a relative cache
path into its provenance report. The exact frozen fit was repeated with an
absolute cache path, without changing any parameter or source. The preserved
first binary and completed binary are byte-identical, SHA256
`bdb53df0d2f5958094287b66c0c6228b3d512442db7dca04bcf68c0bf775de2d`.

## Runtime and checks

The existing search, confidence filters and original twenty-candidate selection
run first. The established nonincreasing score projection and fixed adapted
neural evidence propose an ordering. Only a new head invokes the gate. Rejection
moves the original head back to first, preserving the new relative tail order
and the exact original candidate set. All prior explicit personal preferences,
contextual corrections and mixed/translated baseline paths remain in force.
Missing or invalid optional gate data restores the entire parent order.

The exact-set guarantee concerns continuous-Chinese decoding. Optional service
typo suggestions can depend on the first three results, as in the preceding
experiment, and are not covered by that guarantee.

The fitted gate passes80 Python/Java probability comparisons at tolerance1e-11.
Controlled real decoding proves both an enabled repair and an enabled rejection;
the rejected head still permits a reordered tail. Missing-gate constructors,
positive/negative personal context, familiar characters and mixed/translated
paths preserve their intended behavior. Eight malformed parameter/threshold
files are rejected, as are nonfinite inference features.

`protocol.json` and `seal.json` precede fitting and internal selection.
`inference-freeze.json` pins additional evaluation runners, fitted parameters,
model report and all native source/class/asset bytes before external outcomes.
The same previously observed1,450 calibration and3,893 guard gates remain in
force, including exact per-case visible-set equality. Actual enabled Single32,
service-wired Android unit/Lint and quiet paired timing are required before any
new independent500 pass. No policy change or fallback trial follows a failed
gate. Version0.6.39/code46, signing, storage and Fold7 settings remain in place;
no APK is requested.

## Reproduce

Activate the existing Java17 environment and use one BLAS thread. Keep the
attributed corpus caches in ignored `.native`, reconstruct original observations
using `observe_current_search.py` if needed, and use fresh output folders.
The fit command requires an absolute cache path for provenance serialization.

```sh
source /workspace/android-environment/activate.sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/head_change_training.py \
  prepare /absolute/path/to/head-data
# Compile HeadGateTrainingEvaluation with SentenceLanguageRanker,
# VisibleCandidateReranker and HeadChangeGate; score each of four displays shards.
# Verify exactly one feature row per existing nonleading rival before fitting.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/head_change_training.py \
  fit /absolute/path/to/head-data /tmp/head-model
python3 tools/run_head_change.py prepare /tmp/head-native
python3 tools/check_head_change.py /tmp/head-native/candidate \
  /absolute/path/to/head-data /tmp/head-checks
# Freeze the actual runners, selected model and native bytes before external runs.
```

The native runner uses the canonical committed `tools/data/head_change/model`
and validates its report/hash. Rebuilding into a temporary model folder allows
byte comparison with that checkpoint before a native run. The independent500
is not consumed by the calibration commands.

## External calibration

The same previously observed1,450 cases pass the unchanged calibration gate.
The gate makes a conservative tradeoff against the earlier rejected unrestricted
adapted reranker:

| Metric | Parent | Unrestricted neural | Learned first-choice gate |
|---|---:|---:|---:|
| First |301|322|313|
| Top5 |558|568|568|
| Top20 |736|736|736|
| First gained/lost |—|31/10|12/0|

Every original candidate set/count is unchanged. New150 first/top5/top20 changes
22/53/77→23/57/77; old1300 changes279/505/659→290/511/659. Top5 still gains17 and
loses7 cases, so zero first-choice losses is not a guarantee about every rank.
All original per-set calibration allowances pass. This establishes the intended
conservative behavior on known calibration; it does not prove independent
accuracy or that every previously correct head will be preserved elsewhere.

The enabled gate/neural Single simulation retains32/32 first choices after
three confirmations, with489 context records and identical learned candidate
sets. Legacy-only learning gives31/32, as before. The exact wired Android
archive passes222 unit tests with no failures, errors or skips; Lint has25
warnings and no errors. These checks do not measure physical Fold7 latency or
update persistence, and no APK task is run.

## Completed guard and decision

|3,893 known guard cases|Parent|Unrestricted neural|Learned gate|
|---|---:|---:|---:|
|First|1358|1443|1377|
|Top5|2215|2263|2263|
|Top20|2625|2625|2625|
|First gained/lost|—|124/39|26/7|

All original candidate sets/counts are identical. The learned gate retains
fewer repairs but reduces displaced correct heads from39 to7. Net first gain
is19; net top5 gain is48 (69 gains/21 losses). This does not establish a new
independent accuracy rate: these are previously observed, overlapping guards.

The three groups rejected in the preceding experiment now preserve first
counts: fresh-UD20→20, authored120 79→79, handover29→29. However, authored70
changes first15→14, top541→41, top2048→48. One lost first out of70 is a1.43pp
decline, exceeding the frozen1pp allowance. 「係我搬咗屋」 moves from first to
third. These words are a post-outcome diagnostic example, not a new training
row or exception. The unrestricted model had five gains/one loss in this group;
the gate rejects all five repairs while still accepting that incorrect swap.
Aggregate safety therefore does not imply safety in each scenario family.

**Production adoption is rejected.** We do not change the threshold, add an
exception, switch to a fallback arm or fit on these guard cases. Quiet timing
and the still-unused context-search500 are not run after rejection. No speed,
real-device or1.0 claim is made. The reserve runner remains fail-closed without
a successful qualification file.

The new model, implementation, numerical checks, full ordinary outputs and
failed-gate report are retained for review. Production app source/assets remain
unchanged at0.6.39/code46, with no APK. The final decision is
`tools/data/head_change/decision.json`; the complete work report is
`tools/reports/head-change-work-2026-10-17.json`.

A separately frozen future experiment would need to improve reliability across
scenario families, using additional TRAIN protection/repair comparisons and
family-level validation. Changing only a probability threshold against these
observed failures would not demonstrate generalization. No such extra trial is
included in this completed experiment.
