# Completed-pool coverage and longer relations (unreleased, 2026-10-13)

The previous `b82a517` source corrected only the twenty displayed candidates.
This change scores up to 96 confidence-eligible completed paths before selecting
the display20. The ordinary beam48 plus 8 lexical reserves, exact-code matching,
confidence margin 10 and explicit personal ordering remain in place. It can
recover a completed candidate lost to the final cutoff; earlier option/beam
losses remain possible. The optional model's absence retains the old decoder.

## Diagnosis and bounded evidence

The repaired archive-only observer loads all four prior models and the actual
sentence correction. On the existing natural200 set,63 targets are absent from
display20:26 reach a character-option cutoff,18 lose a prefix,9 lose an already
completed path, and 10 are ranked beyond 20. These are observed terminal frontiers,
not proof that an individual early prune caused every possible segmentation to
fail. Most cutoff characters are older transcript variants. No character or
dictionary asset was removed or changed to improve the benchmark.

`sentence_ranker.b64` retains all 3,855 previous short weights and their 1.5 strength.
It adds 9,216 separately trained longer lexical/role relations. Units have one or
two Han characters, at least one action/closed-class anchor, and shared distance
buckets for 2–3,4–7 and 8–12 positions. Context is bounded to 12 trailing Han;
punctuation/Latin resets relations. Each feature contributes at most twice.
Unknown new features are zero. No full sentence is a feature.

The SRK3 format retains SRK2 compatibility in the new loader and independent caps:
the old short correction remains bounded to±3 before its 1.5 strength; the added
long correction is bounded to±1.5 before its selected 0.25 strength. Only positive
evidence above 0.1 score contributes a final promotion, so the maximum added
bonus is 0.275. Negative/unknown new evidence does not demote an established
candidate. The existing positive-structure first-choice protection still applies.
These are statistical collocations, not a semantic parser or grammatical proof.

The runtime indexes only trained longer relations instead of constructing a map
of all possible longer features. The diagnostic extractor remains independently
comparable with Python. Editor text and constructed units are transient; this
immutable model does not store personal learning records.

## Training, selection and rejected trials

The frozen 3,140 cases reuse the prior 1,640 training cases and add 1,000 HKCanCor
training-conversation utterances plus 500 Tatoeba training families. Source
conversation/family splits and licenses remain unchanged; additional cases
exclude all known training/evaluation targets of 6+ characters by substring.
The character model already used the underlying training corpora. These cases
are new to this pair-training objective, not new underlying language exposure.

Of 3,140 targets,2,822 occur in the bounded training pool, producing 6,765 actual
same-code competing pairs. The long channel fits the original decoder path
margin plus the frozen short correction difference. Repeated competitors and
family variants are downweighted. Training uses 80 AdaGrad epochs, L2=0.01,
support from at least two independent targets/families and at most 12,000 long
features. Individual weights are bounded to±1.5. The fitting objective
approximates runtime clipping and the later conservative positive-evidence floor.

The [protocol](../tools/data/sentence_search/protocol.json) records each decision:

* A replacement short/long model fails validation at every strength and is rejected.
* A signed additive model passes validation but loses natural top-five and old600
  first/top-five hits. Its lost first choices include alternatives with only
  negative new evidence on both sides. It is rejected.
* Positive evidence must exceed 0.1 before promoting a candidate. Previously seen
  regression suites constrain calibration; they are development evidence.
* A bounded extra prefix reserve changes no hit/MRR metric in any of the twelve
  calibration suites at eligible 0.25 strength. It is removed from shipped code.

The unchanged 0.25/0.5/1/1.5 grid uses authored60, natural200 and Tatoeba 200
validation plus 100 frozen unused utterances. Eligibility requires no top1/top5/
top20 loss in each validation set. Intersecting that with previously inspected
regression constraints leaves only 0.25. The decision is saved before viewing the
second reserved 100 outcomes. An earlier reserve100 became diagnostic while
developing the search policy. Both reserves use unused utterances from previously
observed excluded conversations, not new speakers or contemporary chat logs.

The encoded asset is 125,754 bytes. Original source licenses and attribution are
retained in `THIRD_PARTY_NOTICES.md` and the bundled Tatoeba notice.

## Results against the previous source

Exact top1 / top5 / top20 hits, with personal learning disabled:

| Set | Previous `b82a517` | Final source |
| --- | --- | --- |
| Final unused reserve,100 |36 /54 /74 |36 /54 /74 |
| Existing natural utterances,200 |76 /119 /137 |77 /119 /138 |
| Existing examples,600 |291 /432 /484 |291 /432 /483 |
| Existing authored chat,120 |74 /85 /98 |74 /85 /98 |
| Earlier followup utterances,100 |40 /61 /69 |41 /61 /72 |
| Earlier fresh utterances,100 |36 /63 /71 |36 /63 /73 |
| Earlier public families,100 |46 /74 /81 |46 /74 /85 |
| Existing Tatoeba examples,200 |87 /143 /157 |87 /143 /162 |
| Existing clause probes,70 |15 /39 /45 |15 /39 /48 |

Natural 200 gains one first choice and loses none. Old 600 retains every previous
first choice; its top20 coverage gains two targets and loses three, a net loss of
one. Single mode remains available for exact characters. The additional natural
first choice is a post-selection example from older spoken material, not an
added full-sentence entry or evidence of current Hong Kong message frequency.
The final unused 100 has no aggregate hit gain; its MRR changes only
0.460734→0.460764. No substantial independent first-choice/top-five improvement
has been established.

## Verification and latency

All 204 Java unit tests and 13 Python tests pass; Lint has zero errors and 25 existing
warnings. All 40,568 longer-feature vectors match between Python and Java.
Serialized runtime ordering matches 2,054 validation/calibration candidate lists;
284 complete production decodes match the expected lists and check full codes
for every candidate. Training weights reproduce byte for byte. Three explicit
Single confirmations per daily example retain 32/32 contextual first choices,
versus 30/32 with legacy history alone, with 489 contextual sequence records.

The paired desktop benchmark isolates old/current classes in one JVM, fixes CPU 0,
warms twelve passes and alternates fifteen samples. No builds, training or other
decoding benchmarks run concurrently.

| Input letters | Previous wall median,ms | Final wall median,ms |
| --- | --- | --- |
|11 |77.771 |76.429 |
|12 |90.620 |91.052 |
|22 |130.640 |133.787 |
|18 |118.301 |120.559 |
|16 |136.255 |139.054 |
|48, pressure input |488.916 |477.726 |

Largest ordinary increase is 2.4%; pressure wall median is 2.3% lower. Host/JIT/GC
variation remains; this establishes neither a general speedup nor physical
Fold 7/Android ART latency. The ordinary 1.2 ratio guard passes.

Version remains 0.6.39/code 46, with no APK. Natural first 77/200 is below 82, and
authored top-five 85/120 is below 87. Android identity, signing configuration,
other model/vocabulary assets and existing stroke files are unchanged. The
[work report](../tools/reports/sentence-search-work-2026-10-13.json) retains
per-case changes, rejected trials, hashes and the release decision.

## Reproduce

Use JDK 17 and Python's standard library. Activate this cloud toolchain with
`source /workspace/android-environment/activate.sh`. The HKCanCor ZIP must match
the corpus manifest checksum.

```sh
python3 tools/prepare_sentence_search.py /path/to/hkcancor-utf8.zip --output /tmp/refrozen
python3 tools/prepare_sentence_search.py /path/to/hkcancor-utf8.zip --reserve --output /tmp/refrozen
git show b82a517:app/src/main/assets/sentence_ranker.b64 > /tmp/old-sentence.b64
python3 tools/export_sentence_candidates.py tools/data/sentence_search/train.tsv /tmp/train-scored.tsv \
  --revision b82a517 --working-tree --pool 96
python3 tools/train_sentence_search.py /tmp/train-scored.tsv /tmp/old-sentence.b64 \
  /path/to/hkcancor-utf8.zip /tmp/long-model
python3 -m unittest discover -s tools -p 'test_sentence_*.py'
./gradlew testDebugUnitTest lintDebug --offline --no-daemon
```

Selection inputs prepend
`validation:<set>` to the three-column cases: authored60 from
`tools/data/hk_chat_cases/validation.tsv`, natural200 from
`tools/data/candidate_ranking/validation.tsv`, public200 from
`tools/data/tatoeba_corpus/validation.tsv`, and new100 from
`tools/data/sentence_search/validation.tsv`. Historical pool 20 extraction uses
`--revision b82a517`; pool 96 extraction uses the current fixed source and
`--working-tree --pool 96`. Re-export a seven-column scored file to annotate the
structural support field, then use `select_sentence_search.py --additive` and
`evaluate_sentence_search.py`. The frozen calibration report and chosen model
are in `tools/data/sentence_search/`; these known cases are not independent tests.
