# Traceable, code-admitted Hong Kong training spans

This experiment follows the structured-path diagnosis. It changes training
preparation and research artifacts. Production stays0.6.39 / versionCode46 until
a candidate qualifies; no APK is produced.

## Data preparation

The preceding9,981-row dataset contained600 added Tatoeba targets with
dictionary-coded punctuation that the Han-only decoder could not emit. Many
historical HKCanCor spellings also fell outside the existing token scans.
Training more comparisons for an impossible full target cannot repair that
generation barrier. The new dataset is prepared before any candidate outcomes:

| Part | Rows |
| --- | ---: |
| Admitted retained TRAIN protection/examples | 4,077 |
| Original46 HKCanCor TRAIN files, Han spans | 2,614 |
| Existing Tatoeba TRAIN translation families, Han spans | 1,200 |
| Total | **7,891** |

`provenance.jsonl` records each original text, its source/ID/group, code-point
start/end offsets, explicit transformations, retained-row origin, old/new code,
and maximum native character rank. Hash selection occurs before decoding;
HKCanCor had2,614 eligible additions against a4,000 cap, while Tatoeba had2,365
eligible spans against a1,200 cap. These are additional ranking examples from
already exposed public source text, not new speakers, recordings or private
keyboard-use measurements.

Every non-Han boundary ends a span. Punctuation, English, digits, quotation marks
and missing-speech markers are never removed to join the surrounding Chinese.
The raw HKCanCor parser accepts English tokens with internal spaces, such as
`Mr Bean`, and keeps malformed non-Han missing-speech annotations as boundaries.
Unparsed Han token syntax fails instead of being silently skipped. Three thousand
eight hundred fourteen selected examples use an explicit original subspan.
Overlong spans are discarded, not cut into arbitrary sentence fragments.
Previously trained retained examples are marked separately from new raw spans.

Normalization uses Unicode NFC and six reviewed, one-to-one OpenCC glyph pairs:
爲→為, 僞→偽, 檯→枱, 脣→唇, 鍼→針, 衆→眾. In this actual sample, only four
occurrences of檯→枱 across three rows change. The historical forms𡃉/𠻺/𠸏/𡁵
have no approved replacement and remain unchanged before feasibility filtering.
Same pronunciation is not sufficient evidence to replace a character. Neither
editor text nor evaluation gold is normalized by the runtime.

## Code feasibility, not oracle accuracy

`export_training_codes.py` calls the actual frozen Java dictionary and records
129,624 character/code/rank facts, rather than approximating its Hong Kong
frequency priorities in Python. Each admitted code has a valid alignment using
the original **cold first24 character options**. Another valid code may be chosen
when the historical spelling code is outside that boundary; provenance retains
the old code. This changes no keyboard dictionary, vocabulary, beam or glyph
generator. It guarantees basic option admission only, not beam survival,
display membership, device font support or successful recognition.

Only the original46 TRAIN conversations and frozen Tatoeba TRAIN families are
read for additions. New/transformed targets exclude known evaluation overlap of
six or more characters, including the normalized variants and the untouched
joint-ranking reserve500. No words.hk example trains a model. Licences and
original attribution are in the dataset's [NOTICE](../tools/data/clean_ranking/NOTICE.md).

The filtered training baseline is6,630 first /954 later-top5 /110 later-top20 /
75 outside20 /122 missing from the complete eligible pool. **Do not compare these
counts or their rates with older datasets as an accuracy gain**: eligibility,
sampling, code alignment and target populations have changed.

## Real rivals and supervised reconstruction

The ordinary baseline observer records real raw/final competitors and close
prefix comparisons. Only identical context/code/gold under unchanged baseline
code/assets can reuse historical TRAIN observations. Source labels are re-keyed
to the current provenance, never used as prediction features. Fifteen stratified
cache examples match newly decoded pools, displayed lists and prefix comparisons.
The pre-fit English-boundary correction required six additional input decodes;
the cache graph and hashes remain in the work report.

All122 missing clean targets have a legal shadow path within the original
generation bounds. Reconstructing them gives405 prefix and366 complete
comparisons, added to19,461 ordinary complete and15,144 prefix comparisons:
**35,376** total. The ordinary122 output lists match baseline exactly; gold
reconstruction never alters inference. Offsets and maximum-violation mining
follow [the preceding structured experiment](STRUCTURED_TRAINING.md).

## Frozen model comparison

The optional shared Han bigram/trigram residual and all original runtime rules
remain unchanged. Family support,70/20/10 HK/Tatoeba/authored source weighting,
50/50 prefix/complete weighting, endpoint bounds and optimizer are fixed.
Two predeclared configurations use L2=.003/.015, both at strength.5. This isolates
data-quality effects without expanding the preceding failed parameter grid.

The known800 examples are calibration; the old3,893 are additional guards.
A candidate must preserve first/top5/top20 on new100 and aggregate old700,
respect per-set head/top5 limits, and improve first or top5. A selected model
must then pass the larger guard, actual Single32 personalization, Android tests,
Lint and warmed paired desktop timing before its exact hashes are frozen and
the independent500 is decoded. The reserve is never used for fitting or selection.
No extra grid expansion after outcomes is allowed. These steps alone do not
meet the original1.0 major/device gates.

Actual result/decision artifacts are
[`selection.json`](../tools/data/clean_ranking/selection.json) and
[`clean-ranking-work-2026-10-15.json`](../tools/reports/clean-ranking-work-2026-10-15.json).
Both matched previous-research controls and production comparisons are reported;
all known-set results remain calibration evidence.

| Configuration | First / top5 / top20 on known800 | Qualified |
| --- | --- | --- |
| Production baseline | 171 / 324 / 421 | Reference |
| L2=.003, strength=.5 | 171 / 323 / 422 | No |
| L2=.015, strength=.5 | 172 / 324 / 422 | No |

Both configurations lose one top5 hit on old700 (280→279). The best research
configuration (.015/.5) changes new100 from19/44/59 to19/45/60, and old700 from
152/280/362 to153/279/362. Neither configuration adds any net first/top5/top20
hits over the preceding structured research at the same parameters; MRR is
slightly lower. **Cleaning these data did not improve the hit counts of this
same small residual model.** Both configurations are rejected; source/assets,
version, signing, local learning and Fold7 layout remain unchanged.

Twenty focused Python tests pass with no skips, covering original-source span
replay, exact cold-code admission, unverified replacement/evaluation rejection,
normalized reserve disjointness and model provenance/bounds. Each new model
passes24 Python/Java score checks and177 token-split checks. Independent Java
teacher checks cover six exhaustive segmentation maxima, three label-invariance
cases, invalid alignment, selected-option isolation and supplementary Unicode.
The three clean data artifacts also reproduce bit for bit.

After rejection, the larger3,893 candidate guard, final-only control, Single32,
Android JUnit/Lint, warmed timing, physical Fold7 and independent500 decoding
are **not run**. No accuracy, recognition-speed or1.0 improvement is claimed.

The useful next experiment is to retrain the main character/word language
models on the traced clean source material, with a separate frozen protocol.
Current character/phrase language models still reflect older corpus spellings;
this experiment deliberately changed only the additional short-feature residual.
Reliable evidence for the unconverted historical glyphs remains necessary before
normalizing them. Keep all future validation targets unchanged.

## Reproduction

Activate `/workspace/android-environment/activate.sh` for Java commands. Raw pinned
HKCanCor, original Tatoeba TRAIN rows and original attributed assets are reused.
Always use new output/archive directories. Copy `orthography/` to a fresh data
replay directory and run:

```sh
python3 tools/export_training_codes.py .native/clean-code-replay /tmp/clean-codes.tsv
python3 tools/prepare_clean_ranking.py /path/hkcancor-utf8.zip /tmp/clean-codes.tsv \
  --output /path/to/fresh-data-replay
```

`train.tsv`, provenance and manifest reproduce bit for bit. Do not overwrite the
committed frozen dataset. For native observations, prepare a fresh pool observer
with `clean_ranking_observations.py prepare-pool`. The `split` command can reuse
the complete pinned historical TRAIN observations; the `resplit` command can
reuse a complete clean-dataset pass after a source-only correction. Both check
dataset and output hashes and require identical code/context/gold.

For a completely uncached replay, initialize three shards from `cases()` and empty
`reused/{pools,visible,prefix}.tsv` files. Write `reuse.json` with the exact
`training_sha256`, `reused=0` and `new=len(rows)`. Run each shard with `run`, then
`merge`; all7,891 ordinary inputs are decoded. This is a slower equivalent of
the verified cache, not a different inference policy.

The merge emits missing-target `repair-N.tsv` inputs. Prepare a shadow observer
with `prepare-shadow`, run each repair shard with `run --kind shadow`, then
`merge-shadow` to a fresh repair folder. Train using:

```sh
python3 tools/train_clean_ranking.py /path/pools.tsv /path/prefix.tsv \
  /path/repair /tmp/clean-model --l2 .015
```

Use `run_joint_ranking.py` for each frozen ordinary native trial and
`report_clean_ranking.py` for the existing calibration gate. Score consistency
is checked by `verify_joint_score.py`; exhaustive shadow-path checks use
`verify_structured_training.py`. The focused Python suite is:

```sh
PYTHONPATH=tools python3 -m unittest test_joint_ranking test_structured_training test_clean_ranking
```

No source file, model weight, cutoff, selected target or evaluation label is
changed after independent500 outcomes.
