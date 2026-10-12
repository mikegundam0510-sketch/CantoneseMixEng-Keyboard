# Clause-start and complement cues (2026-10-12)

The previous Tatoeba trial improved many examples but moved `你交咗錢未` and
`你交咗表未` behind `係交咗...`. This change supplies bounded clause-head
evidence during lattice search. It does not store text or add full sentences to
the vocabulary. The preceding Tatoeba report remains a record of the rejected
trial; this is a separate intervention with its own frozen evaluation.

## Behaviour

`ClauseStartRelations` gives one positive authored cue when an explicit personal
subject is followed by a recognized action and `咗`, `緊` or `過` near the start
of a clause. It handles plural subjects, up to three short temporal/adverb
elements, focused `係我...` subjects, and `係咪...` questions. Recognized
complement introductions such as `你話`, `我想問` and `我唔記得` also license a
subject-omitting `係交咗...`. These are limited linguistic priors, not learned
use-frequency statistics or a full grammatical parser. Unknown words/forms are
neutral; no candidate is deleted for having `係`.

The cue spans editor context and lattice tokens. It is applied once at the aspect
endpoint, resets on punctuation/Latin, and uses at most twelve preceding Han
characters. An exactly twelve-character prefix may have been truncated, so its
first surviving character is never treated as an observed clause head. Long
contexts, names, omitted subjects without a recognized cue and other valid
constructions continue to rely on the existing models and personal learning.
Identity phrases such as `你係老師` receive zero additional score.

Lookahead retains its existing four-character scores for the other models, but
corrects the new cue using the full bounded clause context. This prevents a
four-character suffix from accidentally becoming a fresh clause head. Once the
head is outside the twelve-character bound, a private cache marker preserves
the old suffix cache sharing. The marker is never shown or stored. Beam width,
candidate limit, exact-code checks and learning controls are unchanged.

After the first speed checks, clause scoring was changed to allocate history only
at an aspect endpoint. A conservative prefix gate restores suffix cache sharing
when a Han continuation cannot complete any recognized cue. The gate was checked
against 27,727 actual output texts and 280,597 continuations, and 500 complete
candidate lists remain byte-identical after this optimization.

The subsequent speed change skips the two identical independent-score calls
whose difference is exactly zero for words of at most twelve characters. It also
shares independent word scores across positions within one decode. Personal
bonuses stay outside this cache, and editor-dependent scores retain their
existing per-position cache. The cache is local to a decode, disappears on return,
and writes no learning record. Both model arms again reproduce all 500 candidate
lists byte-for-byte. These changes reduce redundant work without reducing beam
width, word options or candidate checks.

The final cache also reuses immutable character-transition log probabilities
(at most 8,192 entries) and `phraseBonus` results under its original five-Han
context (at most 256 contexts × 256 words). Each is local to one decode; Unicode
and punctuation resets retain exact scores. Personal and longer-context scorers
are not cached under a shorter history. Another 500-list equality check passed.

The combined model is adopted in source after the completion guard is restored.
Only `language_model.b64` and `MODEL_REPORT.json` are copied from the pinned trial;
the accompanying generated vocabulary is not installed. The report's vocabulary
counts describe its frozen training inputs, not newly added runtime entries.
Bundled Tatoeba attribution and checksums are available in app settings.

The final paired timing run fixes CPU 0, alternates old/new engines in one JVM,
warms up 12 times and takes 15 samples. Combined-model wall medians (milliseconds):

| Input | Previous source | Final combined source |
| --- | --- | --- |
| 11 letters | 52.265 | 58.461 |
| 12 letters | 63.735 | 68.786 |
| 22 letters | 102.632 | 106.689 |
| 18 letters | 78.852 | 89.789 |
| 16 letters | 98.593 | 103.853 |
| 48-letter pressure input | 374.877 | 357.555 |

The pressure case improves 4.6%; ordinary cases remain 4.0–13.9% slower, so no
general speedup is claimed. Initial versions of the cue/model were slower, and
all attempted measurements are preserved in the work report. Timing on this
cloud JVM does not measure Android ART, allocation cost or a physical Fold7.

Production constructors delegate to the selected constant in `QuickDecoder`.
The extra ten-argument constructor accepts a finite strength 0..2 for offline
ablation; strength zero reproduces the previous engine. `RankingEvaluation`
accepts a fifth argument for this strength. Its `baseline` model-ablation flag
still does not mean the previous release: use `full 0` with archived baseline
assets to isolate this change.

## Frozen comparison

The [protocol](../tools/data/clause_start/protocol.json) was fixed before
candidate decoding. Strengths 0.5/1/1.5 are compared against zero in both the
unchanged bundled model and the previous Tatoeba weight-2 trial. Selection uses
70 authored validation cases and the existing 200 natural validation cases in
each arm. Both top-1 and top-5 must remain no lower in every arm/set; mean MRR
breaks eligible settings, with lower strength as the tie-breaker. All three
settings qualify; 1.5 wins and is frozen before guard evaluation.

The authored validation and heldout probes use different verb/object families,
each with eight contexts/variants, plus six protective copula identity phrases.
These 70-case sets share constructions and their variants are correlated. They
are generalization/regression checks, not independent estimates of HK typing
accuracy. The new public sample selects 100 previously undecoded Tatoeba
heldout families, excluding the entire families represented by the 200 cases
observed in the prior experiment. The source was never added to training, but
authors are unavailable and external dictionaries may contain its words.

Validation results (top-1 / top-5 / top-20):

| Arm / set | Without clause cue | Selected cue 1.5 |
| --- | --- | --- |
| Bundled model / authored 70 | 14 / 22 / 43 | 14 / 28 / 49 |
| Bundled model / natural 200 | 77 / 116 / 135 | 77 / 116 / 135 |
| Tatoeba trial / authored 70 | 16 / 26 / 44 | 18 / 33 / 51 |
| Tatoeba trial / natural 200 | 79 / 116 / 137 | 79 / 116 / 137 |

Post-selection results (top-1 / top-5 / top-20):

| Set | Previous bundled source | Clause cue alone | Cue + previous corpus trial |
| --- | --- | --- | --- |
| New authored constructions, 70 | 5 / 24 / 37 | 13 / 33 / 42 | 14 / 36 / 45 |
| Previously undecoded public families, 100 | 28 / 50 / 64 | 28 / 50 / 64 | 46 / 71 / 81 |
| Old examples, 600 | 282 / 423 / 477 | 282 / 423 / 477 | 286 / 427 / 484 |
| Existing natural utterances, 200 | 72 / 112 / 133 | 72 / 112 / 133 | 72 / 114 / 137 |
| Previous authored chat, 120 | 56 / 81 / 96 | 56 / 81 / 98 | 74 / 85 / 98 |
| Daily examples, 32 | 20 / 29 / 32 | 21 / 30 / 32 | 22 / 31 / 32 |
| Completion questions, 16 | 16 / 16 / 16 | 16 / 16 / 16 | 16 / 16 / 16 |
| Previously observed Tatoeba cases, 200 | 64 / 105 / 124 | 64 / 105 / 124 | 81 / 131 / 157 |

The previous trial alone scored 14/16 first choices on completion questions; the
cue restores all sixteen, including the two reported regressions. The six copula
identity probes in each authored set retain their ranks when adding the cue in
each model arm. Some identities were already second/fourth/fifth, so preserving
them does not establish that every identity now ranks first.

The new public first-choice gain is predominantly the previous corpus model's
gain: clause cues alone leave 28/100 unchanged; adding the cue to the corpus
trial leaves its 46 first choices unchanged and increases top-five from 70 to
71. Authored improvements are correlated construction tests. These desktop
source comparisons do not measure a published APK or real Fold7 typing habits.
The existing natural-heldout first-choice gain remains zero and the earlier
authored top-five gain is 3.33 percentage points, below the five-point 1.0 gate.
Version 0.6.39/code46 is retained without creating an APK.

Aggregate protection does not retain every earlier first choice: old600 gains
eight first choices and loses four; public100 gains twenty and loses two. The
natural200 first choices have no individual gains or losses. Full per-case
first-choice changes and every timing attempt are preserved in the
[work report](../tools/reports/clause-start-work-2026-10-12.json).

Final verification: 195 Java unit tests pass, with no failures or skips; Lint has
zero errors and 25 existing warnings; three preparation tests pass. A simulation
of three explicit Single confirmations per daily example retains all 32 first
choices with context learning (30/32 using the same legacy history alone).
The prior APK, signing configuration, app ID and existing stroke files are unchanged.

## Reproduce

Python uses only the standard library; Java requires JDK 17. Activate
`/workspace/android-environment/activate.sh` in this cloud environment.

```sh
python3 tools/prepare_clause_start_cases.py
python3 -m unittest discover -s tools -p 'test_clause_start_preparation.py'

mkdir -p /tmp/clause-baseline
git archive e4387bfef96be601b264feb5617e15e0ad0fea81 \
  app/src/main/assets | tar -x -C /tmp/clause-baseline

# Rebuild the pinned weight-2 trial with the original frozen inputs using
# docs/TATOEBA_EXPERIMENT.md, preserving the baseline vocabulary/scorers.
python3 tools/evaluate_clause_start.py \
  /tmp/clause-baseline/app/src/main/assets /path/to/trial-assets \
  /tmp/clause-comparison

./gradlew testDebugUnitTest lintDebug --offline --no-daemon
```

The evaluator pins both model files using the previous work report, verifies
case hashes, writes selection before guard decoding, and never installs assets
or creates an APK. The controls for old regression sets can reuse the previous
raw results because baseline assets are identical and the zero-strength engine
reproduces all 200 natural-validation candidate lists byte-for-byte. New public
and authored baseline cases are decoded afresh.
