# Preserve the first choice and rerank positions 2–20

This is the user's explicitly authorized next experiment after the rejected
[learned head gate](HEAD_CHANGE_GATE.md). Parent `61e62e5` retains the production
app from `e209474`. The fixed candidate passed every predeclared gate and is
adopted in source, without an APK. The scope is better access to existing
alternatives while preserving every original first choice. The adapted
sentence-language checkpoint is reused byte for byte.

## One fixed policy

Run the parent's search, confidence, personal and head gates and its original
twenty-candidate cutoff. Use the preceding experiment's unchanged nonincreasing
isotonic projection of raw display scores and bounded neural evidence to order
the original candidates. Move the original first choice back to index0, keeping
the neural relative order of every other candidate. This means that the score
projection includes the original head; projecting an isolated19-item tail is
not this experiment. No candidate is added or removed.

Explicit learned whole words, confirmed contextual chains and matching contextual
corrections retain the entire parent order. Isolated familiar characters retain
their old path bonuses. Mixed and translated-prefix combinations use the parent
decode path. Missing or corrupt optional language data leaves the parent usable.
No learning file format, dictionary, signing or Fold7 layout changes.

The guarantee concerns the continuous-Chinese decoder's original first/list.
Optional service-level typo suggestions may depend on the first three results
and are not covered by exact-set preservation. No physical-device rendering or
latency claim follows from a native JVM list comparison.

The original first is retained by construction, even when it is wrong. First
accuracy and top20 coverage therefore cannot improve in this scope. The benefit
being tested is moving the intended answer into the first five alternatives.

## Freeze and gates

`tools/data/pinned_head/protocol.json` and `seal.json` precede all ordinary
results. `inference-freeze.json` additionally pins native source/class/asset
bytes. One fixed adapted checkpoint and strength are used; no threshold, arm,
training or post-outcome policy grid is permitted.

The observed1,450 calibration cases require exact per-case first and candidate
sets, nondecreasing top5 in new150 and old1300, a top5 gain on new150 and old
per-set top5 loss at most1pp. The known3,893 guard requires exact first/sets,
aggregate top5 preservation and per-set top5 loss at most1pp. These sets overlap
prior evaluations and are not new independent accuracy evidence.

They run together in one four-shard ordinary batch of5,343 rows, then return to
their original calibration/guard order. No labels or reference answers influence
search: reference lists are used only for assertions after ordinary decoding.
Every native row asserts first and set preservation. Actual enabled Single32,
exact service-wired Android unit/Lint and quiet paired timing are also required.
Timing uses30 warmups,11 samples and six fixed codes, each wall/thread-CPU median
ratio at most1.2 relative to the parent in the same JVM.

Only after all earlier gates pass and exact sources/models/evidence are frozen
may the unused context-search500 run once in each parent/candidate arm. Adoption
there requires strict original-first/set equality and a positive top5 net gain.
No post-test changes are permitted. A25/500 net top5 gain would be a substantial
top5 result; the separate1.0 first-choice and physical-device gates remain.
Version0.6.39/code46 stays in place and no APK is requested.

## Implementation checks

Four hundred randomized displays test first/set preservation, exact relative
tail order, neutral/constant evidence, invalid-evidence fallback and unchanged
input containers. A controlled real decode starts with `丙乙,丁乙,甲乙` and moves
`甲乙` to second while keeping `丙乙` first. It also checks positive/negative
personal context, familiar characters and unchanged mixed/translated lists.
These are mechanism checks, not typing-accuracy gains.

## Reproduction

Use Java17 from the existing activation and fresh ignored native archives.
Historical guard inputs are reconstructed from the first four columns of
`tools/reports/clean-language-models-2026-10-16/guard3893.tsv`, with trailing
newlines, at `.native/joint-ranking-20261015/guard-cases3893.tsv`. All source,
model and case hashes must match the protocol. The original first and set
checks remain mandatory in learning and ordinary evaluation.

```sh
source /workspace/android-environment/activate.sh
python3 tools/run_pinned_head.py prepare /tmp/pinned-native
python3 tools/check_pinned_head.py /tmp/pinned-native/candidate /tmp/pinned-checks
# Pin actual native bytes in inference-freeze.json before ordinary runs.
python3 tools/run_pinned_head.py run /tmp/pinned-native \
  tools/data/context_search/calibration1450.tsv \
  tools/reports/context-search-2026-10-16/baseline1450.tsv /tmp/pinned-results.tsv
python3 tools/pinned_head_guards.py harnesses /tmp/pinned-native/candidate
```

The independent runner is fail-closed without the successful qualification
file. Its exclusive per-arm start markers prevent unrecorded repeat passes.
Do not use its reserve outcomes for subsequent tuning.

## Calibration and implementation evidence

The first 1,450 rows of the combined ordinary batch pass calibration: first
301→301, top5 558→568, top20 736→736. Every original first and candidate set is
identical. New150 changes 22/53/77→22/57/77; old1300 changes 279/505/659→279/511/659.
Top5 gains 17 and loses 7 cases, so an aggregate gain does not preserve every
previous top5 target. All predeclared per-set allowances pass. These completed
prefix rows were checked while the rest of the batch ran, and match the final
merged output byte for byte. All 5,343 combined input/reference rows were
checked against their strided partitions before restoring the original order.

The 3,893-case guard passes: first 1358→1358, top5 2215→2263 and top20
2625→2625. Every original first and candidate set is identical. One known
100-case written group changes top5 40→39, exactly the predeclared one
percentage point allowance. No other group loses top5 hits. These are observed
regression guards, not independent evidence of generalization.

The model-enabled Single harness preserves every learned first/set and reaches
32/32 contextual first choices after three confirmations, with 489 sequence
records. Legacy-only learning is 30/32: this pinned policy cannot gain a head
from isolated familiar-character history. This does not indicate loss of a
parent first; every learned first is checked against the explicit parent path.
The exact wired Android archive passes 222 unit tests with no failures/errors/
skips. Lint has 25 warnings and no errors. The existing generated stroke assets
are supplied unchanged to this archive by the repository build workflow. No APK
task is run.

Quiet paired timing passes all six wall/thread-CPU median ratios. With 30
warmups and 11 alternating-order samples, the maximum ratio is 1.01913, below
the fixed 1.2 ceiling. The 22-letter code changes wall median 144.273→147.032ms;
the 48-letter stress case changes 505.357→512.082ms. These are native host
measurements, not phone latency. Raw values are in `timing.tsv` and the checked
ratios are in `timing.json` in the report directory.

`qualification.json` seals the five successful guard records, exact native
Java/classes/assets, the wired Android sources/assets and the independent
runner before any context-search500 decode. The packaged checkpoint includes
its source attribution, CC BY-SA 4.0 terms, source audit and historical training
report; no evaluation text or Common Voice prompt cache is added to app assets.

## Independent result and adoption

After qualification, the parent and candidate each decoded the formerly unused
context-search500 once, with exclusive start markers. First/top5/top20 changes
**107/195/253→107/202/253**. Every original first and candidate set is identical.
Top5 gains 9 cases and loses 2, a net 7/500 or 1.4 percentage points
(39.0%→40.4%). MRR changes 0.293542→0.300058; the paired exact two-sided top5
p-value is 0.06543. This is limited evidence of a modest ranking improvement,
below the predeclared substantial-gain threshold of 25/500. It is not a measured
real-user success rate or a 1.0 qualification.

The exact validated QuickDecoder, three ranker classes, CandidateEngine,
EnglishChineseEngine, service loader and checkpoint are copied from the tested
Android archive. `adoption.json` pins all 12 copied source/asset hashes. Source
and checkpoint bytes match qualification and Android/native comparison records;
no predictive change follows the independent outcome. Attribution assets were
added before qualification and do not affect decoding. The primary language
model, version, signing, local-learning storage and layouts remain unchanged.

The parent deliberately remains first even when it is wrong. Targets outside
the original twenty still cannot be recovered; 2 previously top5 targets fall
below fifth. Optional service typo suggestions and real-device behavior remain
outside the strict decoder-list guarantee. Subsequent improvement needs a fresh
independent evaluation set: this context-search500 is now observed and must not
be reused for model selection or advertised as unused again.

All records are under
[`tools/reports/pinned-head-2026-10-17/`](../tools/reports/pinned-head-2026-10-17/).
`tools/data/pinned_head/decision.json` records adoption; the sealed protocol,
qualification and source/model hashes remain unchanged.
