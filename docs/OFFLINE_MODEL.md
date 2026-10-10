# Offline model and compact candidates: 0.6.0 source preview

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
