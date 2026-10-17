# Rerank the original visible candidates

This is the user's separately authorized follow-up to the closed
[sentence-pretraining experiment](SENTENCE_PRETRAINING.md). Parent `523d133`
retains the production app from `e209474`. The previous placement of language
evidence sometimes removed a target that the parent could display. This policy
first runs the parent search and all confidence, personal and head gates, keeps
its original list of at most20 continuous-Chinese candidates, and only then
changes their order. Every ordinary evaluation asserts identical per-case sets
and counts; keeping aggregate top20 alone would be insufficient.

## Fixed implementation

The language-only and same-code-adapted checkpoints are reused byte for byte
from `tools/data/sentence_pretrain/models`. There is no new training, corpus,
strength sweep or per-sentence override. Their original runtime reads at most12
prior Han characters and48 composing characters. Its bounded evidence remains
`0.5 * 2 * tanh(mean(log conditional - log TRAIN unigram))`.

The parent's raw final scores do not always follow its visible order, because
later gates can promote a trusted head. A least-squares nonincreasing isotonic
projection, using pool-adjacent-violators, reconciles those scores with the
established order without a new rank-decay parameter. Model evidence is added
once to these projected scores. Stable ties, including neutral or constant
evidence, retain the original order. Missing or nonfinite scores fall back to
the entire original order. The original input list and score map are not edited.

An explicitly learned whole-word preference, a fully confirmed context chain,
or a matching contextual correction takes priority: the entire original order
is retained in those cases. Familiarity with isolated characters alone does
not imply that the user confirmed a whole sentence; those existing character
bonuses remain in the base scores without disabling the model everywhere.
The learning format, persistence and recency rules do not change.

Mixed English/Chinese spans and translated prefixes use an explicit baseline
decode path so their existing bounded combinations and order are retained.
The exact-set guarantee concerns continuous-Chinese decoder candidates.
Optional service-level typo suggestions can depend on its first three results,
so those suggestions are not covered by that guarantee. The policy cannot
retrieve an answer already absent from the parent's list.

## Frozen evaluation

`tools/data/visible_rerank/protocol.json` pins21 source/model files, six evaluation
references and the immutable parent app tree. `seal.json` records protocol SHA256
`bff0a76e8ffc08618d3df49ccb89da9beaadcc5504ce730f4ac0292a178fc4f2`.
`inference-freeze.json` additionally pins the generated Java sources, classes
and assets before any new-policy calibration result.

The previously observed1,450 cases are calibration, not independent evidence.
Both new150 and old1300 must preserve first/top5, new150 must gain first or top5,
and old per-set first/top5 loss must stay within1pp. Exact candidate-set equality
also requires every target's top20 availability to stay the same. Select the
eligible arm by equal-set mean first/top5/top20/MRR, breaking ties toward the
language-only model. No policy or strength changes follow these results.

Only an eligible selected arm proceeds to3,893 guard cases, actual model-enabled
Single32 after three simulated confirmations, Android unit/Lint in the exact
wired archive, and quiet paired timing. The guard preserves aggregate first/
top5/top20, every original visible set and per-set first/top5 within1pp. Single
must retain32/32 first choices and the original learned candidate sets. Timing
uses30 warmups and11 samples on six fixed codes, with every median wall and
thread-CPU ratio at most1.2 relative to the parent in the same JVM.

After all guards pass, freeze the exact selected source/model/evidence before
one ordinary parent/candidate pass on the still-unused context-search500.
Adoption requires identical visible sets, no first/top5 loss and a first/top5
gain. No post-test fitting or policy changes are permitted. At least25 extra
top5 hits out of500 are required to call this a substantial gain; the separate
physical-device and update-persistence requirements for1.0 still apply.

## Implementation checks and reproduction

The projection checker verifies a hand-computed projection and200 randomized
displays, including stable neutral/constant ordering, unchanged inputs, exact
sets and nonfinite fallback. An integration fixture uses a deliberately
supporting model to change `丙乙` to `甲乙` while retaining both choices. Positive
and negative contextual preferences preserve parent order; globally familiar
characters still allow model evidence. Mixed and translated-suffix fixtures
retain their entire parent lists and order. These are implementation checks,
not typing-accuracy gains.

Use Java17 from the existing environment activation. All stages use fresh
ignored archives; no app packaging task is needed.

```sh
source /workspace/android-environment/activate.sh
python3 tools/run_visible_rerank.py prepare /tmp/visible-native
python3 tools/run_visible_rerank.py run /tmp/visible-native language \
  tools/data/context_search/calibration1450.tsv \
  tools/reports/context-search-2026-10-16/baseline1450.tsv /tmp/visible-results/language.tsv
python3 tools/run_visible_rerank.py run /tmp/visible-native adapted \
  tools/data/context_search/calibration1450.tsv \
  tools/reports/context-search-2026-10-16/baseline1450.tsv /tmp/visible-results/adapted.tsv
python3 tools/run_visible_rerank.py report /tmp/visible-results
```

The historical guard-case file can be reconstructed from the first four columns
of `tools/reports/clean-language-models-2026-10-16/guard3893.tsv`, with a trailing
newline, at `.native/joint-ranking-20261015/guard-cases3893.tsv`. Its hash must
match the protocol before any run. The scripts do not automatically consume
the independent500. Version0.6.39/code46, signing, local learning storage and
Fold7 settings remain in place; no APK is requested.

## Calibration result

| Arm | New150 first/top5/top20 | Old1300 first/top5/top20 | Combined1450 first/top5/top20 |
|---|---|---|---|
| Parent |22/53/77|279/505/659|301/558/736|
| Language only |28/56/77|288/514/659|316/570/736|
| Same-code adapted |26/57/77|296/511/659|322/568/736|

Both arms satisfy the fixed calibration gates and preserve every original
candidate set and count, rather than merely the number of visible targets.
The adapted arm is selected by the predeclared equal-set ordering. Language
only has two more top5 hits overall; selection is not an assertion that the
adapted model wins on every metric. Adapted gains31 and loses10 first choices
(net+21), and gains17 and loses7 top5 hits (net+10). Its1,432 changed lists
still contain exactly the parent's original candidates.

The three targets lost by the previous early-placement experiment all remain
available, as does every other parent target. No new top20 coverage can result
from a permutation. The six-case-set calibration and descriptive paired values
do not establish independent accuracy or a substantial1.0 improvement.

The selected enabled model passes the Single32 harness after three simulated
confirmations: legacy-only learning yields31/32 first choices and contextual
learning32/32, with identical parent candidate sets in both paths. There are489
context-sequence records. This verifies preservation of the existing learning
behavior, not a new learning-accuracy gain or update-persistence measurement.

The exact service-wired Android archive passes222 unit tests with no failures,
errors or skips. Lint has25 warnings and no errors, matching the existing warning
count. The default sandbox could not initialize Gradle's local lock socket;
the same offline command passes with the permitted sandbox escalation. Neither
test command packages an APK. The optional model loader falls back to the
original decoder when the model asset is unavailable or invalid.

## Final guard and delivery decision

| Selected adapted model | Parent | Candidate |
|---|---:|---:|
| Guard first |1358/3893|1443/3893|
| Guard top5 |2215/3893|2263/3893|
| Guard top20 |2625/3893|2625/3893|

Every one of the3,893 original candidate sets and counts is identical. First
choices gain124 and lose39 (net+85); top5 hits gain69 and lose21 (net+48).
These correspond to aggregate gains of2.18 and1.23 percentage points on this
previously observed guard. They are not independent typing-accuracy estimates.

The fixed per-set rule nevertheless fails:

| Guard set | Cases | First before/after | Top5 before/after |
|---|---:|---:|---:|
| Fresh UD validation |43|20/19|29/30|
| Authored daily scenarios |120|79/75|86/92|
| Handover scenarios |30|29/28|30/30|

Each first-choice decline exceeds that set's1pp allowance. In the authored set,
five variants of 「買完餸先返屋企」 move from first to second, while one other
sentence improves to first. These are correlated variants of a scenario, not
five independent newly discovered language phenomena. 「淨係坐郵輪嗰度都」
moves from first to third, and 「你交返功課畀老師未」 from first to second.
All remain available. Preserving availability does not guarantee that a
previously correct first choice stays first.

The selected model is **not adopted**. We do not switch to the other arm, change
the scoring policy or relax a gate after seeing these outcomes. Quiet timing
and the independent context-search500 are not run after rejection; no speed
claim is made. The reserve runner remains fail-closed without a successful
qualification file. Its separate seal predates the guard result. The unused500
is retained for a future qualified candidate.

The implementation, complete ordinary lists, frozen sources and failed-gate
details are retained for review. Production Java and assets remain unchanged
at0.6.39/code46, with no APK. The final machine decision is
`tools/data/visible_rerank/decision.json`; the work report is
`tools/reports/visible-rerank-work-2026-10-17.json`.

A future separately frozen experiment could learn a better-calibrated ordering
of strong existing heads from TRAIN rivals, with independent scenario-family
validation. It should address these semantic tradeoffs without hard-coding the
observed guard sentences or using the untouched500 for tuning. That is not an
additional trial in this completed experiment.
