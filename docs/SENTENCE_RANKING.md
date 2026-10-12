# Whole-candidate correction (unreleased, 2026-10-12)

The previous source can generate the intended sentence but place it behind
same-code alternatives. `sentence_ranker.b64` adds a trained residual score to
the **already displayed** candidates. It preserves the twenty-candidate pool,
exact-code matching, confidence eligibility, beam search and local learning.
It cannot recover a sentence that never reached that pool.

## Data and features

The frozen training set has 800 HKCanCor training-conversation utterances not in
the earlier pair-training sample, 600 Tatoeba training families, and 240 authored
variants of forty existing training scenarios. These utterances are new to this
pair-training objective; the underlying character model already used their
training corpora. Known validation/heldout targets of six or more characters
are excluded by substring, and the original validation/heldout conversations
remain excluded from training. The importer and trainer verify source checksums,
conversation/group membership and complete typed-code reachability.

The pinned `fac1e878eae03ff76fa3299e65f215299620b8f8` decoder supplies actual final
path scores, including its vocabulary priors. Only 1,477 of the 1,640 targets
are displayed; those produce 3,484 competing pairs. Several competitors of the
same target and variants of an authored/community family are downweighted.
The model learns 3,855 supported features with pairwise logistic fitting, L2
0.01 and eighty AdaGrad epochs. It stores no full training-sentence feature.

Features include two-to-four-character surfaces, one-to-three-character clause
boundaries, marker relations separated by two-to-five positions, and shared
first/last roles with a length bucket. Roles are coarse authored categories;
they are not a contextual tagger or a full grammar. Repetition contributes at
most twice per feature. Each weight is bounded to ±1.5 and the whole correction
to ±3 before the selected strength 1.5. Unknown features contribute zero.

Python and Android use the same explicit CJK blocks through Extension J, so an
older Unicode table does not reset a valid new CJK character's history. Latin
and punctuation reset local relations. The immutable model stores no editor
text or learning record; features are constructed transiently for each candidate.
The encoded asset is **36,336 bytes**, not total Android heap usage. An absent or
malformed optional asset leaves the previous sentence decoder usable.

## Selection and rejected attempts

The [protocol](../tools/data/sentence_ranking/protocol.json) was written before
candidate extraction. The fixed 0.25/0.5/1/1.5 strength grid uses the existing
authored60, natural200 and Tatoeba200 validation sets. Eligibility requires no
aggregate top-1/top-5 loss in any set; mean MRR selects the strength, with lower
strength as the tie-breaker. These reused validation sets are development data.

The first role schema conflated ordering words such as `先/再` and determiner
`啲` with ordinary characters. It dropped authored-validation top-five from
48 to 42 and was rejected. Splitting their roles was informed by validation,
before guard results. Runtime parity then identified a Python/Java difference
on newer CJK characters; both predicates were made explicit and the model
retrained without changing the numeric grid. Earlier selections are retained.

The resulting unrestricted correction improves natural200 but drops two
completion questions and eight handover first choices. It was rejected. A weak
structural guard retained the core aggregates but still lost two handover and
three clause-probe first choices. Those results remain diagnostic regressions.

The final guard retains the original first choice whenever the existing
completion, handover, clause or clause-start scorers provide positive support.
All remaining candidates keep their full residual-score order. Without that
support the correction may replace the first choice. Explicit personal word
counts still sort last, retaining their existing priority. This conservative
tradeoff can also retain an already supported but incorrect first choice; it is
not proof that the winner is grammatical or the best possible sentence.

Another hundred excluded-conversation utterances were frozen before final
selection, excluding the earlier fresh100 and prior/training target substrings.
Their results were inspected only afterwards. They are new utterances from
conversation sources already used in other evaluations, not new speakers or
contemporary Hong Kong message-frequency measurements.

## Results against the previous source

All figures are exact top-1 / top-5 / top-20 hits with personal learning disabled.

| Set | Previous `fac1e87` | Final correction |
| --- | --- | --- |
| New followup utterances, 100 | 36 / 56 / 69 | 40 / 61 / 69 |
| Earlier fresh100, now diagnostic | 35 / 61 / 71 | 36 / 63 / 71 |
| Existing natural utterances, 200 | 72 / 114 / 137 | 76 / 119 / 137 |
| Existing authored chat, 120 | 74 / 85 / 98 | 74 / 85 / 98 |
| Existing examples, 600 | 286 / 427 / 484 | 291 / 432 / 484 |
| Daily examples, 32 | 22 / 31 / 32 | 23 / 31 / 32 |
| Completion questions, 16 | 16 / 16 / 16 | 16 / 16 / 16 |
| Handover examples, 30 | 29 / 30 / 30 | 29 / 30 / 30 |
| Clause probes, 70 | 14 / 36 / 45 | 15 / 39 / 45 |
| Previous Tatoeba cases, 200 | 81 / 131 / 157 | 87 / 143 / 157 |
| Previous public families, 100 | 46 / 71 / 81 | 46 / 74 / 81 |

New followup100 gains four first choices and loses none. Existing natural200
gains six and loses two; old600 gains fifteen and loses ten. Aggregate protection
does not preserve every previously correct sentence. Examples promoted from
second to first include `你講埋啲噉嘅嘢`, `你揾佢做乜嘢啊`, `乜你乜都唔知`
and the new followup `你話乜嘢都唔識嗰個呀`. These are post-selection examples,
not added full-sentence dictionary entries.

## Verification and latency

All 8,796 validation feature vectors match between Python and Java. All 2,054
validation/guard candidate lists match with the serialized runtime model;
284 representative complete production decodes reproduce those lists byte for
byte and check every candidate's complete code. Simulated explicit Single
confirmation three times per daily example retains 32/32 contextual first choices,
versus 30/32 with the same legacy history alone. Eight Python tests and all 202
Java unit tests pass; Lint has zero errors and 25 existing warnings.

The paired desktop benchmark isolates old/current classes within one JVM,
fixes CPU 0, warms up twelve passes, alternates order and takes fifteen samples.
No builds, training or other decoding benchmarks run concurrently.

| Input letters | Before wall median, ms | After wall median, ms |
| --- | --- | --- |
| 11 | 77.834 | 77.502 |
| 12 | 92.833 | 94.939 |
| 22 | 134.418 | 135.075 |
| 18 | 118.888 | 118.915 |
| 16 | 132.941 | 132.206 |
| 48, pressure input | 485.440 | 456.063 |

The largest ordinary-case increase is 2.3%; the pressure wall median is 6.1%
lower. Host/JIT/GC variability remains, so this establishes neither a general
speedup nor Fold7/Android ART latency. The new scorer does not enlarge the beam.

Version stays **0.6.39/code46**, with no APK. Against the previously discussed
release comparison, natural first choices are 76/200, below the 82 target, and
authored top-five remains 85/120, below 87. The old APK, Android identity, signing
configuration, other model/vocabulary assets and existing stroke files are unchanged.
Detailed selections, rejected trials, per-case changes and hashes are in the
[work report](../tools/reports/sentence-ranking-work-2026-10-12.json).

## Reproduce

Use JDK 17 and Python's standard library. Activate the cloud toolchain with
`source /workspace/android-environment/activate.sh`. The HKCanCor ZIP must have
the checksum recorded in the corpus manifest. Corpus licenses and attribution
are retained in `THIRD_PARTY_NOTICES.md` and the bundled Tatoeba notice.

```sh
python3 tools/prepare_sentence_ranking.py /path/to/hkcancor-utf8.zip --output /tmp/reprepared
python3 tools/prepare_sentence_ranking.py /path/to/hkcancor-utf8.zip --followup --output /tmp/reprepared
python3 tools/export_sentence_candidates.py tools/data/sentence_ranking/train.tsv /tmp/train-scored.tsv
python3 tools/train_sentence_ranker.py /tmp/train-scored.tsv /tmp/sentence-model \
  --corpus /path/to/hkcancor-utf8.zip

# Four-column evaluation input: validation:<set>, context, code, target.
# Concatenate authored60/natural200/public200 validation cases with these labels.
python3 tools/export_sentence_candidates.py /tmp/validation-cases.tsv /tmp/validation-scored.tsv
python3 tools/export_sentence_candidates.py /tmp/validation-scored.tsv /tmp/validation-supported.tsv
python3 tools/evaluate_sentence_ranker.py /tmp/sentence-model/weights.json \
  /tmp/validation-supported.tsv /tmp/sentence-experiment
# Freeze selection before exporting/evaluating followup guard cases.

python3 -m unittest discover -s tools -p 'test_sentence_ranking.py'
./gradlew testDebugUnitTest lintDebug --offline --no-daemon
```

The current trainer reproduces the model byte for byte. `--gate none` and
`--gate weak` in the offline evaluator reproduce the later rejected guard
policies without changing production code. The first role schema's metrics and
source hashes are retained separately; its original Unicode implementation was
superseded during parity correction.
