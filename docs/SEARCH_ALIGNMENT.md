# Search retention and displayed-candidate alignment (unreleased)

This follows [PHRASE_RELATIONS.md](PHRASE_RELATIONS.md). Baseline is `4c57f95`,
with the previous relation model still absent from production assets. Work is
sequential: diagnose and validate search retention, then train against the
actual displayed top-five boundary. Version remains0.6.39/code46; no APK build.

## Diagnose the354 missing displayed targets

The previous796 examples have observed results and are now diagnostic material.
The archive-only observer now loads the active prefix model and distinguishes
the actual confidence-eligible final rank from its earlier raw rank. All354
complete candidate lists exactly match the original baseline and all codes are
exact. Terminal observations classify231 prefix losses,33 completed-path losses,
83 targets outside display20,5 character-option omissions and2 confidence losses.
They are observed furthest frontiers, not proof that every alternative word
segmentation fails at the same earlier boundary. Target text is never given to
production search. The omitted characters remain available in Single lookup.

Most prefix losses occur during intermediate1024-path compaction. Coalescing
duplicate text before truncation changes one displayed list but no target hits.
That trial is not adopted. Adding bounded character futures when no lexical
suffix word is known restores one target, but unrestricted extra scoring fails
the predeclared desktop1.2 ratio budget. Several slower trials are retained as
calibration evidence rather than installed-phone improvements.

The selected implementation runs only on compositions of at least14 letters.
It keeps the original48 primary paths and original lexical/prefix reserves.
When no attested multi-character suffix hint exists, it takes up to four exact
common dictionary characters. An existing HK particle gets priority within a
budget of128 cached character-language-model future scores; otherwise the budget
is divided among the available hints. At most four close, distinct histories
are added, only with positive conditional evidence above0.25. Actual extensions
retain every original phrase, grammar and personal score. Pool96, display20,
confidence10 and dictionary contents are unchanged.

Temporary hints use an empty `CharacterHint` subtype, retaining the original
String/double fields of persistent vocabulary tokens. A flag added to every
token and unnecessary whole-word scoring were removed. No object-size probe is
claimed. The search-only paired comparison has maximum wall/CPU ratio1.051
(30 warm-up passes,15 samples, alternating order in one JVM on CPU0).
Apparent speedups and host variability do not establish Fold7 responsiveness.

On the known796, first/top5 stay180/338 and top20 increases442→443. All903
calibration cases and1,594 original guards preserve per-set first/top5/top20
counts. The search decision precedes training policy changes and fresh testing.
This is a small coverage gain, not an independent accuracy result.

## Align training with bounded displayed-tail scores

Training reuses the licensed, source-separated5,381 examples and train-only
5,610-word POS lexicon. Native observation uses the selected search and original
models. It reports4,104 first targets,793 later targets within20,68 outside20
and416 missing targets. No missing target is inserted into a candidate pool.

PRR2 applies `strength * clip(raw(candidate)-raw(legacyFirst), -2, 2)` to the
displayed tail. The actual existing first and existing20-candidate membership
remain protected, including original local word-count ordering. The model
scores at most19 additional texts. Unknown words are not banned, and all
remaining dictionary choices are still available through Single mode.
PRR1 retains its original inference behaviour and optional-file fallback.

The first full96-tail pilot improves several known top5 counts but loses one
fresh-written top20 hit at otherwise safe strengths. It is rejected. The
revised display-only policy trains only reachable ranks2..20. Gold targets
below5 compare with the actual rank5/4/3 blockers; ranks2..5 compare with rank6/7
cutoff threats. Pinned-first and missing/outside20 targets are explicitly
reported rather than assigned fake optimizable losses.

The weighted pairwise loss uses actual baseline adjusted-score offsets and the
same clipped candidate/reference and rival/reference corrections as inference.
Its gradient includes reference features and is zero on saturated sides.
Minimum feature support is two source families, with conversation/production,
translation-family and authored-template grouping. Source weights remain
HK/UD65%, Tatoeba20%, authored15%. The final model has1,524 pairs from304
families,2,165 features and a59,230-byte unscaled encoding. The clipped training
objective decreases0.29113→0.20636; this is not measured typing accuracy.

Known3,293-case calibration combines903, the earlier796 and1,594 guards; some
examples overlap across sets. Strength1 is selected on equal-set top5 thenMRR,
with lower strengths on ties and no per-set first/top5/top20 loss. Native
top20 parity, simulated Single learning and warmed timing are required before
opening the fresh reserve. No complete sentence is a model feature, and no
evaluation text or POS tag trains the model.

## Fresh reserve and sources

Before native trials, a new100-case validation set and500-case reserve are
frozen from unused words.hk dictionary example families. Selection extends the
same source-family hash order, excludes all previously tracked train/evaluation
targets, old dictionary families, raw training exposure and cross-split
full-target substrings of six or more characters. The100 may tune policy; the
500 is opened only after a fixed model, native guards, personal learning and
timing decision. Once inspected it becomes observed evaluation material.

See [manifest](../tools/data/search_alignment/manifest.json),
[protocol](../tools/data/search_alignment/protocol.json) and
[source notice](../tools/data/search_alignment/NOTICE.md). words.hk NCDOL1.0
examples are evaluation-only and never APK assets. Derived UD lexicon/weights
retain CC BY-SA4.0; HKCanCor, Tatoeba and authored attribution remains in the
phrase-relations notice. These public spoken/dictionary sources do not measure
contemporary private Hong Kong typing. Phone learning records are never used.

## Independent outcome and delivery

After selection was frozen, the500 native cases were decoded once per engine.
The baseline is the exact archived `4c57f95`; the new engine uses the frozen
working-tree search and strength1 PRR2 asset. The corresponding source, model,
case and selection checksums are recorded in
[selection](../tools/data/search_alignment/selection.json) and checked by the
evaluation reporter. No model, strength, search rule or target changes follow
inspection of the reserve.

| Metric | Baseline | Selected search + PRR2 |
| --- | ---: | ---: |
| First | 89/500 | 89/500 |
| Top five | 185/500 (37.0%) | 193/500 (38.6%) |
| Top twenty | 258/500 | 258/500 |
| Mean reciprocal rank | 0.26453 | 0.26906 |

Eleven targets enter the top five and three leave it;93 target ranks change.
The paired exact two-sided sign/McNemar p-value is0.05737. The net eight-hit,
1.6-percentage-point gain satisfies the declared small-gain adoption condition,
but is limited evidence, not a statistically established population improvement
or a major-version result. The first-choice protection also deliberately limits
what this model can improve. The reserve is now observed evaluation material;
the protocol's unopened flags describe its frozen pre-evaluation state.

The final combined paired desktop run has maximum wall ratio1.05255 and CPU
ratio1.05108 across six fixed inputs, including a48-letter stress case. Identical
baseline A/A comparisons vary by less than1%. This passes the declared1.2 desktop
budget. It is a small processing cost, not faster recognition, and does not
measure Fold7 latency or retained memory.

The model is adopted as `app/src/main/assets/relation_ranker.b64`, with attribution,
original UD notice and full CC BY-SA4.0 license in `licenses/relations/`; settings
exposes the attribution/license. Existing personal storage schemas remain.
Simulated three-confirmation Single learning still achieves32/32 first targets.
Version stays0.6.39/code46, with no APK or1.0 release.

The environment restarted after the original219 Java/33 Python checks,2245-case
feature parity and3293-list native parity. Code, models and calibration evidence
persisted, but `/tmp` raw training/native logs did not. The exact frozen engine
was rebuilt; timing and the500 comparison ran on the restored environment.
Final checks and the restart limitations are recorded in the
[work report](../tools/reports/search-alignment-work-2026-10-14.json).
The full independent native candidate lists are retained under
`tools/reports/search-alignment-2026-10-14/`, alongside hashes and changed ranks.

## Reproduction

```sh
source /workspace/android-environment/activate.sh
python tools/prepare_search_alignment.py /path/to/wordshk.csv /path/to/hkcancor-utf8.zip /path/to/yue_hk-ud-test.conllu
# Capture training-only actual native pools with the selected working-tree search,
# without a relation asset in the observer. Do not observe gold on production paths.
PYTHONPATH=tools python - <<'PY'
from pathlib import Path
from diagnose_sentence_priority import observe
observe(Path('tools/data/phrase_relations/train.tsv'), Path('/tmp/aligned-training.tsv'), revision='4c57f95', working_tree=True)
PY
python tools/train_aligned_relations.py /tmp/aligned-training.tsv /tmp/aligned-model
python tools/verify_aligned_parity.py /tmp/aligned-model /tmp/parity.json
PYTHONPATH=tools python -m unittest tools/test_aligned_relations.py tools/test_search_alignment.py
./gradlew testDebugUnitTest lintDebug --offline --max-workers=2

# Re-summarize the retained independent outputs; this does not tune the model.
python tools/report_search_alignment.py \
  tools/reports/search-alignment-2026-10-14/heldout-baseline.tsv \
  tools/reports/search-alignment-2026-10-14/heldout-current.tsv \
  /tmp/independent.json
```

The bounded objective and reference derivatives match finite differences, and
encoding is deterministic. Data tests check hashes, exact codes and source
family/target separation. Training observer output in `/tmp` was lost at restart;
regenerate it with the training-only command above to reproduce the full fit.
Retained weights, pairs, encoding and their byte-reproduction report survive.
Frozen selection source hashes apply to this implementation, not later revisions.
