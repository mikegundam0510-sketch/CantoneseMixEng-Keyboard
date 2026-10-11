# Offline model and compact candidates: 0.6.0 source preview

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
