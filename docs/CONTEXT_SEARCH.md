# Context diversity and complete-path admission

The parent production revision is `e209474`, version0.6.39/code46. Its character
model is retained. This experiment follows
[the primary-model comparison](CLEAN_LANGUAGE_MODELS.md) and targets actual
search loss before introducing another scoring model. No APK is produced.

## Diagnose the current failure population

The observed prior500 has107 first choices,180 top5 and236 top20. All264 missing
targets are traced with the unchanged native decoder in an archived tree:

| Observed missing target stage | Cases |
| --- | ---: |
| Selected token options can spell gold, but ordinary prefix search never completes it |166|
| Complete and eligible, below the displayed20 |67|
| Generated, removed by the complete-path pool cutoff |28|
| Beyond conservative static token-option bounds |1|
| Not covered by the options selected during ordinary visits |2|

All264 complete output lists match the previously recorded ordinary lists.
Replacing twelve labels with an unrelated Han string leaves their entire
display lists identical. Instrumentation records options and prune observations;
after-search DP only diagnoses legal/selected/static-bounded spelling paths.
No reconstructed path enters the actual lattice, no model is fitted from these
labels, and no pair file is emitted. The diagnostic helper reuses the pinned
archive-only observer; its unused training writer is never called.

Selected-option reachability is an upper bound aggregated over actual visits;
an absent option can follow earlier prefix loss. The first matching-prefix cut
is an observation, not a unique causal attribution across all tokenizations.
The old historical TRAIN gap counts are a different population and must not be
substituted for this current diagnosis. In these264, prefix survival dominates.

## Four fixed ablations

The [protocol](../tools/data/context_search/protocol.json) freezes exactly four
policies before new validation/candidate outcomes:

- `prefix40`: protect the first40 ranked prefixes; fill the same48 slots with
  distinct trailing4-code-point histories within the original48th raw score
  minus4, then fill shortages and restore the original ranking order.
- `prefix32`: the same rule with32 protected heads and16 possible diversity
  slots. This tests the protection/diversity tradeoff without widening the beam.
- `completed`: protect raw first`finalPool-32` complete paths and choose the
  remaining32 using existing raw plus SentenceRanker scores from at most
  `2*finalPool` raw-unique paths. Restore raw order before existing confidence
  and final ranking. Scores select admission and are not charged twice.
- `combined`: `prefix40` plus `completed`.

The original48 beam, existing reserve limits, constructor-specific96/128 complete
pool and20 display bounds remain. The model-free fallback is preserved. No
candidate-specific word, glyph, code, learned weight or new language model is
introduced. Controlled tests cover previously unreachable diverse histories,
protected heads, supplementary Unicode, model-free behavior, a complete sentence
supported by existing evidence below the raw cutoff, and an out-of-window
strong path that must remain unscanned.

## Data and qualification

Before candidate decoding,150 validation and500 heldout examples are selected
from the fixed5000-family source pool. An initial source-capacity request8000
exceeded the5550 eligible heldout families and was reduced before any prediction
outcomes. Exclusions leave1194 unused families. All previous4000 source-family
groups, parent tracked target containment6+ and the complete cleaned primary
TRAIN spans/normalized variants are excluded. Validation/heldout families and
full targets are separate; no successful-decoding filter selects the examples.
Attribution is in [NOTICE.md](../tools/data/context_search/NOTICE.md).

Each ablation uses ordinary answer-free native inference on new150 plus
observed800 and old500 (1,450 total). Require nondecreasing new first/top5/top20,
at least one new first/top5 gain, aggregate old1300 counts preserved, and per-set
old first/top5 losses within one percentage point. Select qualified policies by
equal-set mean first, top5, top20, MRR, then fixed arm priority. No extra grid is
added after outcomes.

Only the selected policy proceeds to the old3,893 guard, actual Single32
personalization, Android JUnit/Lint and warmed paired wall/CPU timing (six codes,
30 warmup passes,11 samples, max ratio1.2). Freeze the exact candidate and all
qualification evidence before one baseline/candidate fresh500 comparison.
Adoption requires nondecreasing first/top5/top20 and first/top5 net gain there.
The original1.0 major-gain and physical-device gates remain separate.

Six Python tests check family/code/provenance exclusions and evaluator integrity:
an old-only gain cannot qualify, new losses cannot be hidden, unchanged lists
cannot qualify, and partial/inexact outputs are rejected. Synthetic evaluator
fixtures are never reported as keyboard accuracy. Each of the five baseline/
candidate native archives passes controlled search-policy scenario checks.

## Reproduction

Activate `/workspace/android-environment/activate.sh` for Java commands. Raw
sources are pinned and already attributed. Use fresh archive/output directories.

```sh
python3 tools/diagnose_context_search.py cases /tmp/context-diagnosis
python3 tools/diagnose_context_search.py prepare /tmp/context-observer
# Run the three diagnosis shards with the observer, then report/compare lists.
python3 tools/prepare_context_search.py /path/wordshk.csv --output /tmp/context-data-replay
PYTHONPATH=tools python3 -m unittest test_context_search
python3 tools/run_context_search.py prepare /tmp/context-native
python3 tools/run_context_search.py run /tmp/context-native baseline \
  tools/data/context_search/validation.tsv /tmp/context-baseline150.tsv
# Append known-baseline1300.tsv to create the frozen baseline1450 result.
python3 tools/run_context_search.py run /tmp/context-native prefix40 \
  tools/data/context_search/calibration1450.tsv /tmp/context-results/prefix40.tsv
# Repeat only the other three predeclared arms, then report all four.
python3 tools/run_context_search.py report /tmp/context-results
```

`ContextSearchPolicyCheck.java` runs against each archived classpath with its
declared protected-head count and completed-policy boolean. The source generator
and all data/evaluator hashes are pinned by the protocol. Current new500 labels
can be read only for exclusion/provenance, not decoded until qualification.

## Search-policy result

| Policy | New150 first/top5/top20 | Old1300 first/top5/top20 | Qualified |
| --- | --- | --- | --- |
| Parent baseline |22/53/77|279/505/659| Reference |
| prefix40 |22/53/77|280/505/661| No new first/top5 gain |
| prefix32 |22/52/76|279/503/655| New and old losses |
| completed |22/53/77|279/505/659| No net gain |
| combined |22/53/77|280/505/661| No new first/top5 gain |

All four are rejected. The conservative prefix policy adds one old first choice
and two old top20 hits, but does not improve the new150 hit counts. Aggressive
diversity loses cases. Complete-path preselection adds no net counts. These
policies are not installed in the Android source, and their frozen grid is closed.
The extra3,893 guard, Single32, Android/Lint, paired timing and fresh500 comparison
are not run for these unqualified policies. App version/signing/learning/Fold7
remain unchanged; no APK or accuracy/speed improvement is claimed.

The next accepted direction is a separately frozen
[longer-context recurrent whole-candidate model](CONTEXT_NEURAL.md). Its training
uses only licensed TRAIN comparisons, not these dictionary examples. The150 and
all old sets are now observed calibration. The same still-unobserved500 reserve
may be used only after that model independently passes its qualification gates.
