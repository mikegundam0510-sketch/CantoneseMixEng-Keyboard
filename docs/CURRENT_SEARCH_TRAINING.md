# Current-parent first-loss and final-rival training

Parent `3aa8870` has the same production implementation and assets as `e209474`.
This experiment follows [context-search diagnosis](CONTEXT_SEARCH.md) and the
rejected [final-only recurrent model](CONTEXT_NEURAL.md). It addresses the user's
first requested direction: learn which unfinished paths to preserve together
with complete-sentence ordering. It does not undertake broader language-model
pretraining. Version remains 0.6.39/code46 until a separate release decision.

## Current inference supplies training errors

All 7,891 existing clean, attributed TRAIN cases are decoded again using the
current parent. Historical decoder margins are not reused. The archive-only
observer runs ordinary pruning first, then inspects a copy of actual inputs and
survivors. A positive must be generated, contain at least two Han characters,
match the consumed code, and have an exactly code-aligned remainder of its TRAIN
target. None of these labels affects ordinary search.

For each example, retain the earliest observed cut with no continuable target
prefix surviving, followed by the largest raw-score violation at another
checkpoint. If no loss is observed, retain early/hard survived-prefix protection.
At most two checkpoints and three real rivals are emitted. Rivals come from the
raw leader and actual returned beam leader/boundary. Raw margins omit bounded
lookahead, so training loss alone cannot demonstrate survival gains. An observed
loss need not be the unique cause across every possible segmentation.

The ordinary final pool supplies up to three actual hard rivals using the more
difficult raw-entry or final-score margin. Correct-first examples supply
protection. Missing complete TRAIN targets receive the existing separately
audited legal-path reconstruction under unchanged generation bounds. Those
positives remain outside normal inference. Shadow output lists must exactly
match the current ordinary lists. Duplicate comparisons keep the harder current
margin; they do not multiply independent source support.

## One score throughout search and final ranking

The new residual learns contiguous two-to-five-character features, each charged
once when its last character is added. Four/five-character terms extend the
previous short two/three-character experiment. The same accumulated score affects
prefix pruning, complete-pool survival and final ordering. There is no second
addition after the full sentence is built and no direct target lookup.

Runtime uses the existing immutable bounded Han trie (`CandidateRanker`, WRK1
loader) with maximum depth five. Although that generic format is also used for
word relations, these features are character sequences. Maximum context is four
characters, compatible with existing lookahead-cache histories. Token splitting
preserves the exact residual. Each weight is bounded to 0.25; at most four terms
end at one character, so their sum never reaches the runtime clip of 1.5.
Unknown features are neutral. Existing exact-code and personal-learning behavior
continues to run around the changed score.

The design fixes 150 deterministic full-batch AdaGrad updates, rate0.2, L2=.003,
minimum three original supporting families, and at most24,000 features. Family,
case and rival mass is normalized; prefix/final stages receive 50/50 mass and
HK/UD, Tatoeba, authored domains receive70/20/10. An independently supported
feature count is not a contemporary chat frequency. Attribution is in the
[NOTICE](../tools/data/current_search/NOTICE.md).

Two strengths,0.5 and1, are eligible candidates. A same-data, same-optimizer
two/three-character control at0.5 diagnoses whether the longer features add
anything; it is not an extra candidate. No capacity/strength grid is expanded
after calibration outcomes. Source/data hashes are sealed before fitting.

## Evaluation and limits

The already observed context-search150 plus old1300 are calibration. Each
subset must preserve first/top5/top20, the150 must gain at first or top5, and old
per-set first/top5 loss must stay within one percentage point. Selection uses
equal-set mean first/top5/top20/MRR, then the smaller strength. Current ordinary
baseline lists are byte-equivalent to the previous production-parent lists.

Only a qualified candidate proceeds to the observed3,893 guard, actual enabled
Single32, Android JUnit/Lint, and quiet paired timing (30 warmups,11 samples,
six codes; wall/CPU ratios at most1.2). A final-only control with the selected
weights separates final ordering from search effects. Then freeze exact source,
model and guard evidence before one parent/candidate evaluation on the still
unused context-search500 reserve. Require no first/top5/top20 losses and a
first/top5 net gain there. No post-test model, threshold or label changes.

The proposed substantial-gain target is at least25 extra top5 hits on that500
(five percentage points), with first choices and existing guards preserved.
Smaller qualifying gains remain small. Neither laboratory accuracy nor desktop
timing substitutes for the original1.0 and physical Fold7 release gates.

## Reproduction

Activate the existing Java17 environment. NumPy2.3.5 and SciPy1.17.0 are used
offline; neither is an Android dependency. Use fresh output directories.

```sh
source /workspace/android-environment/activate.sh
python3 tools/observe_current_search.py prepare /tmp/current-observer
python3 tools/observe_current_search.py split /tmp/current-training
# Run train-0/1/2.tsv separately, producing train-0/1/2 directories.
python3 tools/observe_current_search.py run /tmp/current-observer \
  --cases /tmp/current-training/train-0.tsv --output /tmp/current-training/train-0
python3 tools/observe_current_search.py merge /tmp/current-training --output /tmp/current-pools
python3 tools/observe_current_search.py prepare-shadow /tmp/current-shadow-observer
# Run each generated repair-N.tsv with run-shadow, then merge-shadow.
python3 tools/observe_current_search.py merge-shadow /tmp/current-training \
  --pools /tmp/current-pools --output /tmp/current-shadow
python3 tools/train_current_search.py collect /tmp/current-pools /tmp/current-shadow \
  --output /tmp/current-data-replay
# Replay pairs/categories/manifest must match the committed hashes before fitting.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/train_current_search.py fit /tmp/current-fit
python3 tools/run_current_search.py prepare /tmp/current-half /tmp/current-fit/search-0.5.b64
python3 tools/run_current_search.py run /tmp/current-half \
  tools/data/context_search/calibration1450.tsv /tmp/current-results/half.tsv
```

The committed collected pairs allow a fit without the larger native observation
cache. Reports distinguish implementation tests, exposed calibration and unused
independent examples. Result and delivery decision are appended after evaluation.

## Collected data and implementation evidence

All 7,891 current-parent observations are complete. There are 197 examples with
an observed loss of a continuable prefix and 120 missing eligible full targets;
these populations differ because later alternatives or whole-word paths can
still recover a full sentence after an earlier cut. The raw observer supplies
20,645 prefix comparisons. Reconstruction supplies 759 more prefix/final pairs
for the120 missing targets, with exact ordinary-list parity for all120.

After deduplicating by stage/family/context/code/positive/rival and retaining the
harder current margin, there are42,500 comparisons:19,760 prefix and22,740 final.
Current TRAIN ranks are6,636 first,948 later-top5,111 later-top20,76 outside20,
and120 missing. These are exposed TRAIN observations, not recognition accuracy
on unseen input or a comparison with a differently filtered training population.

The long model contains5,548 features:3,885 bigrams,1,357 trigrams,268 four-character
and38 five-character sequences. Primitive arrays use387,036 bytes. The306 longer
features expose a limitation of the existing independently supported training
material; this experiment does not claim broad grammatical understanding.

Six focused Python tests pass. Each of the two strengths passes84 Java/Python
score comparisons and648 token splits, including direct decoder score integration;
the short control passes84/552. The optional-null constructor preserves20 complete
baseline lists. Observer labels preserve20 ordinary visible lists and20 complete
pools/scores after substitution. The shadow checks verify six exhaustive tiny
path maxima, three label-invariance cases, exact alignment, selected-option
isolation and supplementary Unicode.

Data pairs/categories/manifest and all long-model/report artifacts reproduce
byte-identically. Neither150 calibration nor500 reserve full target appears in
the new positive/negative comparisons or their reviewed-normalized spans.
These checks establish implementation and provenance; actual ranking results
determine adoption.

## Calibration results and diagnostic scope

The fixed full-strength arm passes calibration and proceeds to the declared
remaining gates. Counts below are first/top5/top20 hits on the already observed
1,450 examples; they are not independent accuracy estimates.

| Model | Observed150 | Old1300 | Combined1450 | Calibration gate |
|---|---|---|---|---|
| Parent | 22/53/77 | 279/505/659 | 301/558/736 | Reference |
| Half | 24/53/77 | 280/504/660 | 304/557/737 | Fail old top5 |
| Full | 25/54/77 | 280/506/663 | 305/560/740 | Pass |
| Short control | 24/53/77 | 280/504/660 | 304/557/737 | Ineligible diagnostic |

Full strength gains6 and loses2 first choices, gains3 and loses1 top5 hit,
and gains4 with no lost top20 hits. The net changes are small: +4 first,
+2 top5 and+4 top20. The paired changes are archived in
`tools/reports/current-search-2026-10-16/calibration-changes.json`.

A separate diagnostic was fixed to **half strength before complete calibration
results**; it must not be described as a diagnosis of the selected full model.
All264 instrumented ordinary lists exactly match the clean half-arm lists.
Among this originally missing old500 subset, the166 prefix-search losses remain
lost; one target becomes visible from beyond display20. Two other cases exchange
completed-pool-cut and outside-display20 stages. These stage counts do not include
regressions among originally visible targets and cannot override calibration.

For the model-enabled Single harness, compile its existing helper dependencies
with the archived sourcepath before invoking the frozen harness preparer:
`SingleSelectionHistory.java`, `PhraseLearning.java`, and `RecentLearning.java`.
The preparer deliberately compiles against archived classes, so these must already
be present. The recorded run first reported missing helper symbols, then compiled
the same generated harness with `-sourcepath <archive>/app/src/main/java`; no frozen
source or predictive behavior changed. Actual enabled Single learning reaches
32/32 first choices after three confirmations (legacy learning alone31/32).
This preserves the existing contextual learning behavior, not a new real-device
learning or update-persistence result.

The isolated Android candidate applies the archived
`android-integration.patch` to parent3aa8870 and includes the exact selected
`search-1.b64` as `joint_ranker.b64`. This patch wires the actual service loader,
including the established optional-model fallback. It does not alter preferences,
signing, version or layout. Android results and final adoption decision follow.

The isolated Android build passes222 unit tests (36 suites, no failures/errors/
skips) and Lint (zero errors,25 existing warnings). The222 tests are the existing
regression suite; they are not all model-enabled accuracy tests. The dedicated
Java/Python score checks and Single32 harness explicitly load the fitted model.
The build used offline dependencies and no packaging task. Gradle initially
could not obtain a local wildcard interface inside the sandbox; the isolated
candidate check succeeded with the permitted local-interface access.

Descriptive TRAIN feature coverage finds only22 of460 actual lost-prefix
comparisons have a nonzero difference involving a trained four/five-character
feature. Across all19,760 prefix comparisons the count is390. This limits the
new longer-history signal; it is neither a held-out result nor permission to
change this experiment's fixed model after evaluation. Full counts are retained
in `feature-coverage.json`.

## Guard result and delivery decision

The selected full arm fails the fixed per-set regression gate. On the complete
observed3,893 guard, first/top5/top20 change from1,358/2,215/2,625 to
1,362/2,219/2,637. These aggregate net gains do not override the per-set rule.
The authored70 subset loses one first choice (15 to14), a1.43-percentage-point
loss against the predeclared at-most1-point limit; its top5 remains41 and top20
remains48. The affected sentence is「係我搬咗屋」, which moves from rank1 to3.
We do not change the threshold after seeing the outcome or substitute the
ineligible short/final-only controls.

**Neither trained strength is adopted.** Half failed old1300 top5 at calibration;
full passed calibration but failed the larger guard. Production Java/assets,
version0.6.39/code46, signing, personal storage and Fold7 behavior remain unchanged.
No APK is built. The unused context-search500 reserve is not decoded. Paired
speed checks are not run after rejection, so there is no new speed claim. Native
memory/score correctness and Android checks do not establish typing latency.

`selection.json` is the earlier calibration-stage decision; `decision.json` is
the final delivery decision. Guard output hashes identify the actual e209474
cached reference, whose app tree equals parent3aa8870. The generic comparison
helper's unrelated historical default revision is retained as
`comparison_utility_default_revision` in the corrected guard metadata; metrics,
reference files and qualification thresholds are unchanged.

This completes the requested current-error prefix/final training experiment.
The next evidence-based direction is broader independent training support for
longer patterns and failed prefixes, evaluated under a newly frozen protocol.
The small observed gains do not justify a1.0 claim or reserve-based retuning.

## Same-weight final-only control

The completed diagnostic uses the exact full weights only after complete-pool
filtering. On the same1,450 observed cases it yields305/559/739 first/top5/top20,
versus305/560/740 when shared through search. Thus the shared placement adds only
one net top5 and one net top20 hit over this control, with no first-choice gain.
Most of this experiment's small aggregate improvement is also obtainable at
final ordering; it has not demonstrated a large search-survival improvement.
This control is not an eligible fallback candidate and is not tested on the
reserved500. No model or threshold is changed in response to these outcomes.

Full evidence index: `tools/reports/current-search-work-2026-10-16.json`.
