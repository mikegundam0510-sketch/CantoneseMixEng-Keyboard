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

Validation on 2026-10-04 (Hong Kong): all production Android Java sources compile against API 35; 45 JVM tests pass. No Gradle APK assembly or emulator/physical-device UI run was performed for this source preview. The updated URI mode switch and expanded panel still require device acceptance. No APK was produced at the user's request.

The candidate strip removes the code preview and separate repair strip. Repairs use ordinary text labels; accessibility descriptions and long-press options retain repair provenance. Only substantially stronger repairs are inserted after the first exact choices, with other repairs later in the same scrollable row. The per-character toggle resides in the expanded panel, preserving key sizes and one normal strip height.
