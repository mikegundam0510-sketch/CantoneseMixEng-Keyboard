# Training paths that ordinary search has lost

This research follows the joint-ranking experiment. Production remains
0.6.39 / versionCode 46 until a candidate passes the frozen qualification gates.
No APK is produced by these tools.

## What the missing targets actually mean

The previous 9,981-row TRAIN observation had 1,821 targets absent from the
confidence-eligible final pool. Of those, 1,044 supplied neither a final positive
nor a close-prefix comparison. It was tempting to treat those as pruned paths
needing stronger ranking supervision. The new observation does not support that
interpretation:

| Original 1,044 targets | Count |
| --- | ---: |
| Beyond the existing static token-option scan caps | 791 |
| No legal Han-only decoder path, including dictionary-coded punctuation | 253 |
| Score-learnable complete targets within the existing option bounds | 0 |

The full-target gap was therefore not repaired by inserting answer paths or
training impossible comparisons. Before any fit or candidate validation, the
observation scope was extended to the other 777 missing TRAIN targets:

| All 1,821 missing TRAIN targets | Count |
| --- | ---: |
| Beyond static option scan caps | 1,088 |
| No legal Han-only path | 600 |
| Selected-option lattice can spell gold; ordinary prefix search loses it | 110 |
| Gold generated but removed by a completed-pool cap | 15 |
| Gold in completed128 but excluded by confidence filtering | 8 |

These are counts of historical training targets, **not user accuracy or newly
recovered inference**. Static eligibility is an upper bound. In general an option
gap can itself follow earlier pruning, so these flags should not be presented as
an exhaustive causal trace for arbitrary input. For these 133 score-learnable
targets, selected-option DP confirms an exact complete spelling path already
exists without broadening the option rules.

The 600 non-Han targets expose a real preparation issue: a dictionary code can
exist for punctuation, while QuickDecoder only emits Han tokens. Old frozen data
and results remain intact for reproducibility; those labels provide no new
shadow-positive comparisons. The uncommon glyphs are not added to the keyboard's
candidate generation to make a research metric look better.

All600 are the preceding experiment's added Tatoeba rows. Preparation now rejects
non-Han additions by default and refuses to overwrite an existing output folder.
An explicit `--legacy-allow-coded-punctuation` flag into a fresh output directory
can reproduce the historical dataset. It is not used for new training. This
minimum admission check does not yet solve the separate static-option/orthography
barrier. No punctuation is silently removed or recoded in the frozen labels.

## Supervised reconstruction

`observe_structured_training.py` modifies an archived copy of the unchanged
production decoder. It observes generated token options, raw beam rivals,
surviving gold prefixes, complete-pool paths, and ordinary displayed candidates.
The Android source tree is untouched.

After ordinary decoding, a separate dynamic program enumerates exact gold
segmentations by code offset and gold code-point offset. Each transition uses the
decoder's actual language-score call, trailing12 Han history, internal score for
tokens longer than12, token prior and word bonus. Cold training has zero personal
bonuses. Vocabulary tokens retain their counts; Han character options retain
dictionary frequency. No evaluation gold, dictionary examples, or phone text
train this model.

Three shadow lattices distinguish all legal tokens, actually selected options,
and a conservative upper bound on options the existing scans can inspect.
The latter follows vocabulary24/64 and character64/HK-particle limits. It is not
a promise that a context selector will actually propose a token. For targets
outside those bounds, keep diagnosis and skip reconstructed training.

For the remaining 133 targets, mine at most two checkpoints: the earliest missing
reconstructed prefix, then the largest raw-score deficit. Compare each against
at most two actual rivals (raw leader and beam boundary). Add at most three
complete-pool comparisons. The result is **440 prefix + 399 complete = 839** new
comparisons, added to all **37,717** old error/protection comparisons, for
**38,556** total.

New prefix offsets compare actual accumulated raw transition scores; they do
not include lookahead. Complete offsets use the harder of raw and
raw-plus-SentenceRanker gaps. The missing teacher candidate is not passed through
the answer-dependent PRR3 head/visible gates. Only subsequent **ordinary,
answer-free native decoding** determines whether the model works.

## Frozen fitting and validation

The shared short-Han bigram/trigram residual is the same optional research
integration as the preceding experiment. It affects ordinary transitions and
search through one accumulated score. Family support, source weighting,
50/50 prefix/final balance, endpoint bounds and optimizer remain fixed.

Two L2 values (0.003, 0.015), each at strengths0.5 and1, make **four** predeclared
trials. All existing100/700/3,893 examples are calibration/guards. The separate
`joint_ranking/heldout.tsv`500 remains reserved until a selected candidate passes
the complete guard, personalization and performance checks. No additional grid
expansion is allowed after candidate outcomes.

The ordinary lists for **all 1,821** observed TRAIN targets exactly match the
previous baseline lists. A separate Java harness exhaustively checks six small
segmentation/transition maxima, three label-invariance cases, invalid alignment,
selected-option isolation and supplementary Unicode. The optimizer refactor
reproduces all seven artifacts of the preceding model003 bit for bit.

Final trial results and delivery decisions are recorded in
[`../tools/data/structured_ranking/selection.json`](../tools/data/structured_ranking/selection.json)
and the work report linked from README. These calibration results do not establish
an improvement on unseen conversation or meet the 1.0 release gate.

| L2 / strength | First / top5 / top20 on known800 | Qualified |
| --- | --- | --- |
| Production baseline | 171 / 324 / 421 | Reference |
| .003 / .5 | 171 / 323 / 422 | No |
| .003 / 1 | 170 / 324 / 422 | No |
| .015 / .5 | 172 / 324 / 422 | No |
| .015 / 1 | 172 / 323 / 422 | No |

Every arm loses one top5 hit on the old700 (280→279). The best research arm is
.015/.5: new100 improves19/44/59→19/45/60, old700 changes152/280/362→153/279/362.
The additional 839 comparisons produce **no net count gain over the previous
best research arm** on the same800. These are calibration outcomes, not fresh
evidence. All four arms are rejected; production source/assets remain identical
to the baseline. The new reserve500 is not decoded or used for selection.
The extended3,893 guard, final-only control, Single32 simulation, Android/Lint,
desktop timing and physical Fold7 checks are not run for these rejected arms.

Eleven focused Python tests pass, including rejection of evaluation/inexact shadow
positives and frozen model provenance/bounds. Each model also passes24 Python/Java
score comparisons and177 token-split checks. Those checks establish implementation
consistency, not an accuracy or speed improvement.

The next useful work is to improve **training admission and orthography quality**:
replace punctuation-bearing/non-emittable labels with separately attributed,
code-aligned Han spans or verified everyday HK forms, then mine genuinely
reachable errors. Do not blindly expand the keyboard to rare corpus glyphs or
change held-out labels to improve reported accuracy. Do not keep scaling this
same residual grid after its frozen trials failed.

## Reproduce without an APK

Activate the saved Java environment first:

```sh
source /workspace/android-environment/activate.sh
```

Recreate the previous complete TRAIN observations using
[`JOINT_RANKING.md`](JOINT_RANKING.md). Use a new empty archive directory; existing
archives and incomplete outputs are preserved. Select all missing targets with:

```sh
python3 tools/observe_structured_training.py select-all .native/structured-replay \
  --pools .native/joint-ranking-20261015/training/pools.tsv \
  --prefix .native/joint-ranking-20261015/training/prefix.tsv
python3 tools/observe_structured_training.py prepare .native/structured-replay/observer
```

Split `cases.tsv` into three interleaved shards, run each with `run --cases ...
--output .native/structured-replay/observed-N`, then run
`train_structured_ranking.py merge` with the same complete baseline observations.
Output into a fresh research-data directory to compare with the committed
checksums. The committed protocol is checked before fitting. For an exact fit:

```sh
python3 tools/train_structured_ranking.py train \
  --pools .native/joint-ranking-20261015/training/pools.tsv \
  --prefix .native/joint-ranking-20261015/training/prefix.tsv \
  --output .native/structured-replay/model015 --l2 .015
python3 tools/verify_structured_training.py .native/structured-replay/observer \
  .native/structured-replay/teacher-check.txt
python3 -m unittest discover -s tools -p 'test_structured_training.py'
```

Use `run_joint_ranking.py` to prepare/run the four ordinary native arms, and
`report_structured_ranking.py` to apply the original calibration gate. This report
tool never opens reserve500. All source licences and audit-column definitions are
in [`../tools/data/structured_ranking/NOTICE.md`](../tools/data/structured_ranking/NOTICE.md).
