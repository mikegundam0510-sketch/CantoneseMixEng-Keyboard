# Offline model and compact candidates: 0.6.0 source preview

## Current character-model revision (unreleased, 2026-10-16)

The [clean primary-model experiment](CLEAN_LANGUAGE_MODELS.md) adopts a retrained
character5gram after fixed ablations, old-case/learning checks, Android tests,
warmed timing and one independent500 comparison. Independent first choices stay
107/500; top5 improves179→180 and top20 improves235→236. This is a small gain,
not the1.0 target or a real-phone accuracy result. The word model and decoder
remain unchanged, version is0.6.39/code46, and no APK is released.

`app/src/main/assets/PRIMARY_MODEL_REPORT.json` now describes the current
`language_model.b64`. The original `MODEL_REPORT.json` is retained byte-identical
as the historical baseline training reference; its counts/perplexities refer to
the previous model. Dated comparisons below are historical results.

## Completed-pool coverage and longer relations (unreleased, 2026-10-13)

The [new comparison](SENTENCE_SEARCH.md) keeps up to96 confidence-eligible
completed candidates for scoring before displaying20. Ordinary beam48 plus8
lexical reserves remains unchanged. The previous short correction is frozen;
a separately fitted, independently capped long-relation channel promotes only
positively supported combinations above0.1 score. Unknown/negative new evidence
does not demote an established candidate. This is statistical evidence rather
than a semantic parser or proof of grammaticality.

The final source improves natural200 first choices76→77 and top20 coverage137→138.
Existing600 first/top-five remains291/432; top20 drops484→483. Public100 top20
improves81→85. The final unused reserve100 has unchanged36 first,54 top-five and74
top20 hits. This is a modest source change, without a demonstrated independent
first-choice/top-five improvement. Version remains0.6.39/code46, with no new APK.

## Whole-candidate correction (2026-10-12, historical source comparison)

The [sentence-ranking comparison](SENTENCE_RANKING.md) trains a small residual
scorer on separate HKCanCor/Tatoeba training examples and actual same-code
competitors. It reranks the existing twenty candidates while protecting an
original first choice with positive structural evidence. It cannot recover a
missing search path. New followup100 improves36→40 first choices and56→61 top-five;
existing natural200 improves72→76 and114→119. Completion/handover first choices
are preserved, and all vocabulary and other trained assets stay unchanged.

The added asset is 36,336 bytes. The final desktop benchmark's largest ordinary
wall-median increase is 2.3%; no physical Fold7 latency was measured. All 202 Java
unit tests and eight Python tests pass; Lint has zero errors. Version 0.6.39/code46
is retained without a new APK; the existing 1.0 gate remains unmet. Rejected
policies, individual regressions and detailed limits are recorded in the report.

## Clause-start cues and community model (unreleased, 2026-10-12)

The [clause-start comparison](CLAUSE_START_RANKING.md) adds bounded subject/action
evidence across editor and lattice boundaries. The selected strength 1.5 restores
all sixteen completion-question first choices with the previously rejected
Tatoeba weight-2 model, which is now bundled in source with attribution. Only the
character model and its report change; the existing runtime vocabulary and other
trained scorers stay unchanged. New authored probes improve 5 → 14 first choices
out of 70, and 100 previously undecoded public families improve 28 → 46, mostly
from the added corpus. Existing natural-heldout first choices remain 72/200.

Per-decode caches reuse character transitions and five-character phrase evidence;
personal weights are evaluated separately. Five hundred full candidate lists
remain byte-identical after these speed changes. A paired desktop run on one CPU,
after 12 warmup passes with 15 alternating samples, measures the 48-letter pressure
case at 374.9 → 357.6 ms; ordinary cases are 4.0–13.9% slower than the previous
source engine. This does not establish a general speedup or Fold7 latency. The
earlier slower measurements are retained in the work report. Version 0.6.39/code46
is retained without an APK because the predefined 1.0 improvement gate is not met.

## Community-sentence corpus trial (2026-10-11, historical)

The [Tatoeba experiment](TATOEBA_EXPERIMENT.md) adds a licensed, frozen development
corpus and an offline training/evaluation pipeline. The selected trial improves
new heldout examples but drops two existing completion questions from first to
second. It failed the predeclared acceptance guard at that time; its raw results
remain available. The separate October 12 change above resolves that guard before
adoption. Neither experiment creates a new APK or version bump.

## Signed word and POS collocations (unreleased, 2026-10-11)

`word_ranker.b64` adds a separate incremental scorer to the existing character model, positive word evidence and signed short-character ranker. It learns exact two/three-word surface relations, coarse majority-POS sequences, and lexical first/last-word anchors. Shared POS/anchor evidence is compiled into 49,672 training-derived surfaces; the phone uses a bounded reverse trie, without running a tagger or greedily committing to a segmentation. This is lexical evidence, not full syntactic parsing or a proof that a candidate cannot form a sentence.

The lexicon has 3,201 words occurring at least twice in training, with authored family variants collapsed for word support. Corpus word boundaries and coarse POS come only from the 46 original training conversations; validation and held-out conversation files are excluded. Relations have two or three words, at least one multi-character word, and at most twelve Han characters. Ambiguous surfaces use the most frequent original training segmentation (deterministic ties); candidate-only surfaces use a deterministic known-word segmentation. The same frozen 4,422 exact-code competing pairs supply signed training supervision. Features require two independent positive utterances/families, and multiple competitors do not multiply support. There are 2,707 learned lexical/POS parameters; the larger compiled surface count is not 49,672 independent observations.

A lexical-only ablation learned 283 relations but did not improve validation MRR, so it was rejected before inspecting regression results. The POS extension used the same 0.25/0.5/1/1.5 strength grid, L2 0.002, 80 epochs, and zero approximate margins. Selection required both validation sets to retain aggregate top-1/top-5 counts, then maximized their mean MRR. Strength 1.5 won. The selection protocol, rejected ablation, selected metrics and subsequent guard results are in `tools/data/word_ranking/`. Existing short/positive models and word vocabulary were not retrained.

Each compiled surface and each endpoint sum are capped at ±1.5 before strength multiplication. Training is a linear approximation to these caps. Unknown surfaces contribute zero, punctuation/Latin reset history, and splitting across decoder tokens preserves scores. Matching occurs through `QuickDecoder.languageScore`, including beam expansion and lookahead; it is not limited to reranking the final displayed candidates. Single-character scoring follows only matching suffix edges, avoiding a context array allocation per lattice edge. The old constructors delegate with a null word ranker, and an unavailable/malformed optional asset leaves sentence decoding usable. Local learning controls, storage and protected-editor rules are unchanged.

The initial separate-process timing runs drifted substantially, including the unchanged basic dictionary loader. A follow-up `PairedRankingPerformance` run alternates historical and current engines in one JVM, recording both wall and thread CPU medians after warmup. The largest wall-median increase was 12.7%; the 48-letter pressure case measured 626.1 → 615.4 ms. This does not establish a device speedup, and the original slower measurements remain in the report. The paired harness takes four arguments: baseline compiled classes, baseline assets, current compiled classes, current assets.

The bundled file is 839,572 bytes and uses 1,882,976 bytes of primitive arrays. These are model sizes, not total application memory. Output is deterministic and byte-for-byte reproduction was checked. Source and output hashes are in `WORD_RANKER_REPORT.json`; attribution is in `THIRD_PARTY_NOTICES.md`.

Reused regression results (top-1 / top-5 / top-20):

| Set | Previous `0f5aa98` | Word/POS scorer |
| --- | --- | --- |
| Authored chat, 120 | 51 / 76 / 96 | 56 / 81 / 96 |
| Natural utterances, 200 | 71 / 114 / 134 | 72 / 112 / 133 |
| Existing examples, 600 | 281 / 422 / 479 | 282 / 423 / 477 |
| Daily examples, 32 | 20 / 29 / 32 | 20 / 29 / 32 |
| Completion questions, 16 | 16 / 16 / 16 | 16 / 16 / 16 |

The guard protects aggregate top-1/top-5 on old/daily examples, not every sentence or top-20 recall. Four old first choices move to second while five move to first; two old targets disappear from the displayed top 20. Four of the five authored first-choice gains are variants of one money-transfer template. No gains should be interpreted as independent modern-chat accuracy. These results do not meet the existing 1.0 gate; version 0.6.39/code 46 remains source-only, without a new APK. No Fold7 device measurements were made. See the work report for final desktop timings and their limits.

Reproduce with the checksum-pinned public corpus already used by the project:

```sh
python3 tools/train_word_ranker.py /path/to/hkcancor-utf8.zip \
  --pairs tools/data/candidate_ranking/pairs.tsv \
  --manifest tools/data/candidate_ranking/manifest.json \
  --output /tmp/word-ranker --role-backoff --l2 .002 --strength 1.5
python3 -m unittest discover -s tools -p 'test_word_training.py'
python3 -m unittest discover -s tools -p 'test_candidate*.py'
HK_PHRASE_CORPUS=/path/to/hkcancor-utf8.zip python3 tools/test_phrase_training.py
source /workspace/android-environment/activate.sh
./gradlew testDebugUnitTest lintDebug --offline --no-daemon
javac -encoding UTF-8 -sourcepath app/src/main/java -d /tmp/word-ranking-classes tools/RankingEvaluation.java
java -Xmx1g -cp /tmp/word-ranking-classes hk.cantonesemixeng.keyboard.RankingEvaluation \
  app/src/main/assets tools/data/word_ranking/old600.tsv /tmp/word-ranking-old600.tsv
```

For the prior baseline, archive `0f5aa98` and compile its own Java helpers/assets. The `baseline` argument of `RankingEvaluation` is a much older ablation that omits multiple models, and must not be used as the previous-version comparison.


## Unreleased competing-candidate model (2026-10-11)

`CandidateRanker` adds immutable signed Han bigram/trigram weights to the incremental sentence score. Positive and negative training texts must both match the complete typed Quick code. Unknown relations are neutral. Scoring resets on punctuation/Latin, remains additive across decoder token boundaries, and caps the sum of relations at each character. The public model does not write user preferences or retain editor text. Personal/contextual learning supplies its existing separate weights.

The 4,422 pairs come from 1,500 full utterances in the existing training conversations plus 240 authored training variants. Negatives are actual baseline candidates above gold (up to ten when gold was absent), with one easier competitor for calibration. Baseline revision, source hashes and excluded sources are pinned in `tools/data/candidate_ranking/manifest.json`. Unreachable exact-code gold answers remain teacher positives; ranking alone cannot make them searchable. Authored variants are not measured use frequencies.

Feature admission requires at least two independent positive targets; authored variants collapse to one family. The initial implementation counted competing pairs, so two negatives from one utterance incorrectly supported a penalty for `你交`. Production checks detected two first-choice regressions. Repairing support counts removed the unsupported relation without adding sentence exceptions; all 16 completion examples retained their first choices. A bundled-model JUnit check covers those examples. Initial results and the repair are retained in the work report. Subsequent evaluations of the new 200 utterances are reused regression observations, not another blind test.

Search remains bounded. Reserve paths now use histories absent from the original 48 paths. Common HK particles beyond the ordinary character scan can compete for the same four contextual reserve slots, still requiring context support. Other characters remain available through direct single lookup. Diagnostics observe gold paths only in temporary archived source; complete candidate lists are checked against the plain engine.

Reproduce the bundled model:

```sh
python3 tools/train_candidate_ranker.py \
  --pairs tools/data/candidate_ranking/pairs.tsv \
  --manifest tools/data/candidate_ranking/manifest.json \
  --output /tmp/candidate-ranker-reproduction \
  --ignore-offset --l2 .002 --strength 1.5
```

Approximate baseline language margins omit segmentation/vocabulary priors; validation selected the zero-margin fit. The linear training objective also approximates the runtime cap. Fitting loss is not test accuracy. To rebuild pairs, freeze data with `prepare_candidate_training.py`, evaluate using the pinned archived baseline, extract pairs with `--evaluation`, then optionally add margins with `ExportCandidateMargins`. Keep the corpus split and hashes. Results, speed and release decision are in [the work report](../tools/reports/contrastive-ranking-work-2026-10-11.json).

## Unreleased segmented-word model (2026-10-11)

Production now combines the existing character five-gram with bounded word-transition evidence. HKCanCor's original word boundaries are retained while counting word bigrams/trigrams from its 46 training conversation files. Validation and held-out conversation files never contribute counts. The project also supplies 40 authored training scenario families expanded into 240 examples, with 10 different validation families (60 examples) and 20 held-out families (120 examples). These are synthetic Hong Kong chat situations, not collected messages or measured frequencies. Each training family contributes a transition at most once with an authored prior of three, so subject/time expansion cannot inflate a phrase's apparent frequency sixfold. No full authored sentence is added as a vocabulary token.

Transition evidence uses a smoothed conditional-to-marginal log likelihood ratio, capped at three and attenuated by observation support. Runtime gives unknown transitions zero additional score and uses the strongest matching relation at each character endpoint, avoiding overlapping reward sums. This is a small word-transition scorer alongside the character model, not a calibrated whole-sentence probability model or a neural model. Its reversed trie has 13,863 nodes with about 271 KiB of trie arrays and a 256 KiB root index (527 KiB total); relations are at most twelve Han characters. The direct root index skips unknown candidate endings without allocating history. Scoring is independent of decoder token boundaries, supports supplementary Han and clears on punctuation/Latin. Existing exact-code checks, twenty-result limit, confidence filtering and local learning gates remain in effect. No editor history is stored by the model.

The strength was frozen at 1.0 after comparing 0.25/0.5/0.75/1.0 on the separate authored 60-case and natural 240-case validation sets. New evaluation uses 120 held-out authored examples and 180 complete utterance chunks from excluded HKCanCor conversations. The natural sample rejects earlier regression target substrings and is frozen before model selection; conversations themselves have been reused in past evaluations, and HKCanCor is older speech, so this is not an independent study of modern messaging. Authored families share vocabulary across splits, and six variants in a family are correlated. Improvements on either set must not be described as general real-user accuracy.

The authored held-out set improves from 47/71/88 to 51/76/96 exact top-1/top-5/top-20 matches. The new natural set changes from 60/99/122 to 60/100/120. Existing 600 regressions change from 281/428/479 to 280/426/480, while 32 daily examples improve from 18/28/32 to 22/29/32. Model-only ablation reproduces the authored gains; adding training vocabulary alone does not. This does not meet the predeclared 1.0 release gate. Source version remains 0.6.39; no update APK is produced.

Reproduce data and its boundary/repeatability checks with the checksum-pinned corpus from the notices:

```sh
python3 tools/train_phrase_model.py path/to/hkcancor-utf8.zip --strength 1
HK_PHRASE_CORPUS=path/to/hkcancor-utf8.zip python3 tools/test_phrase_training.py
source /workspace/android-environment/activate.sh
./gradlew testDebugUnitTest lintDebug
javac -encoding UTF-8 -sourcepath app/src/main/java -d /tmp/word-model-classes tools/RankingEvaluation.java
java -Xmx1g -cp /tmp/word-model-classes hk.cantonesemixeng.keyboard.RankingEvaluation app/src/main/assets tools/data/hk_chat_cases/heldout.tsv /tmp/word-after.tsv
java -Xmx1g -cp /tmp/word-model-classes hk.cantonesemixeng.keyboard.RankingEvaluation app/src/main/assets tools/data/hk_chat_cases/heldout.tsv /tmp/word-before.tsv baseline
```

`RankingEvaluation` additionally accepts `words-only` and `model-only` ablations. Bundled assets are declared as JVM-test inputs so data-only changes rerun the tests. The pinned previous engine revision and complete metrics, limits and release gate are in `tools/reports/hk-word-model-work-2026-10-11.json`.

The IME loads a bundled character five-gram model and an expanded Quick vocabulary. Context is the last four contiguous Han characters before composition; punctuation and Latin text reset it. Context is transient and is never stored. Existing learning controls continue to govern character/English learning; no automatic full-sentence logging was added.

The runtime stores 498,947 sorted hash keys with probability and backoff arrays (~7.6 MiB arrays, excluding vocabulary and loader allocations). Training checks hash collisions and pinned source hashes. Scoring interpolates orders 1–5, with pruning-aware escape mass and validation-selected prior strength 128. Known full phrases combine likelihood with frequency priority. Across lattice tokens the first four characters receive prefix context; later characters can reuse the token-internal score. Exact-code validation is retained.

Reproduce training with Python 3 using the pinned inputs in THIRD_PARTY_NOTICES.md:

```sh
python tools/train_language_model.py path/to/hkcancor-utf8.zip path/to/jyut6ping3.words.dict.yaml
```

The split hashes conversation filenames before training: 46 training, 3 validation and 9 held-out conversation files. Held-out and validation conversations add neither n-grams nor corpus phrases. External word dictionaries can contain words in any split. MODEL_REPORT.json records revisions, SHA256 checksums, gram counts and held-out probability evaluation. Five-gram perplexity is 113.80 versus 119.93 for the same model truncated to bigrams; this measures next-character probability, not typing accuracy.

A deterministic sample of 120 reachable 2–4 character continuations from held-out conversations is included as tools/lm_heldout_cases.json and .tsv. OfflineModelBenchmark.java compares the previous decoder against the combined new model AND vocabulary: top-1 exact matches 14→56, top-5 35→99. This small selected corpus sample is not a real-user typing benchmark and cannot isolate the effect of the model from vocabulary expansion. On this host the new decoder median was about 10 ms, p95 about 26 ms; startup, repairs, mixed input and physical-device performance are not included.

Run the standalone benchmark from app/ after compiling the production Java core and tools/OfflineModelBenchmark.java onto a JVM classpath. The standard JUnit suite includes model loading, malformed-data rejection, finite probabilities, supplementary Han context, reset boundaries, split-score consistency and production decoder code reachability.

Initial source-only validation on 2026-10-04 (Hong Kong): all production Android Java sources compiled against API 35 and 45 JVM tests passed. Subsequent verification at `94bbaefa309af5ce5278202c8e12c40c563aa20e` passed Gradle checks, four Android touch instrumentation tests and the API 31 emulator UI acceptance, including the URI-type editor switch and expanded selector. Disposable internal test packages were used; no APK artifact was published. Physical Samsung/Fold and real browser acceptance remain unverified. See BUILD_VERIFICATION.md for the exact run, screenshots and limits.

The candidate strip removes the code preview and separate repair strip. Repairs use ordinary text labels; accessibility descriptions and long-press options retain repair provenance. Only substantially stronger repairs are inserted after the first exact choices, with other repairs later in the same scrollable row. The per-character toggle resides in the expanded panel, preserving key sizes and one normal strip height.

## Candidate confidence and completion questions (0.6.31)

The character model still uses four preceding characters. Productive completion-question evidence uses up to twelve contiguous Han characters, and lexical/request evidence uses five. Token-boundary scoring retains up to twelve characters so these rules are independent of how a sentence is segmented. Per-position score caches are scoped to a single decode and contain no persistent editor history.

Completed candidates more than ten score units below the best path are omitted when they exceed three characters and have neither an attested whole phrase nor positive learned counts for every aligned character. The margin was selected on 240 validation snippets to preserve reachable targets. This reduces weak guesses, not a guarantee of grammatical correctness; unusual text remains accessible in Single mode. The 48-path beam and 24 initial character choices remain unchanged: widening the latter increased latency and regressed first-choice results, so it was not shipped.

Reproduce the separate validation and additional held-out cases from the checksum-pinned source:

```sh
python3 tools/build_ranking_cases.py path/to/hkcancor-utf8.zip /tmp/ranking-cases
javac -d /tmp/ranking-classes app/src/main/java/hk/kaiboard/android/{DictionaryEngine,OfflineLanguageModel,QuickDecoder,RecentLearning}.java tools/RankingEvaluation.java
java -Xmx1g -cp /tmp/ranking-classes hk.kaiboard.android.RankingEvaluation app/src/main/assets /tmp/ranking-cases/validation.tsv /tmp/validation-results.tsv
java -Xmx1g -cp /tmp/ranking-classes hk.kaiboard.android.RankingEvaluation app/src/main/assets /tmp/ranking-cases/heldout.tsv /tmp/heldout-results.tsv
```

The additional held-out snippets exclude all 120 earlier evaluation context/target pairs. No snippets are added to the vocabulary or training model. Authored priorities and grammatical rules are documented separately from corpus measurements.
