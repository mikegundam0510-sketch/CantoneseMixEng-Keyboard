# TRAIN-supported character expansion (not adopted)

The generator was expanded from2,248 to2,493 characters and fitted with its old
parameters frozen. The final known regression comparison loses three top20
targets overall, so the app retains `d7dec75` and its previously validated tail
supplement. Version0.6.39/code46, signing, local learning and Fold7 layout stay
unchanged. No APK is produced. The new independent500 remains unused.

## Selection and fitting

Existing licensed TRAIN text contains useful characters excluded by the former
requirement of three occurrences across two families. Additions require at
least two TRAIN occurrences and either two original families or three HK
occurrences; existing licensed lexical frequency at least500 or three HK
occurrences; actual native dictionary codes; and at least one completely
supported2..24-character TRAIN span. No validation/test character drives selection.
All old2248 characters and their aliases remain. The full primary dictionary is
unchanged; this experiment only concerns the optional neural generator.

The count-ranked limit is512 additions;245 qualify after input supervision
checks. Before fitting, an audit made new-character prefixes supervised targets
and removed one addition whose only TRAIN spans required another unsupported
character. The ignored preflight archives are preserved. This was a TRAIN-input
audit before protocol sealing, with no decoder result used.

Existing teacher rows are copied exactly into the new Unicode-sorted indices.
The old GRU, code encoder, length weights and all original character rows remain
bit-identical throughout every epoch. New embeddings copy UNK with seeded0.01
noise; new word-history rows copy UNK; code-affinity rows start at zero; biases
divide the old UNK prior using TRAIN counts. Only19,845 new-row parameters train.

The unchanged legal-edge generator trains for12 fixed Adam epochs, rate0.001,
batch64, clipping5, seed20261018. Half the mass protects the original8,192
examples; half uses494 new-character views, with original family/source
normalization. Validation uses1,190 old protection views and25 new-character
views from original held-out TRAIN families. Common Voice has no author IDs
and remains TRAIN only. No new pair/reranking objective is introduced.
Internal conditional loss changes1.239238→0.988647, selecting epoch12. This
loss decrease is not a keyboard hit-rate improvement. Primitive arrays occupy
836,808 bytes. Corpus views containing CV text stay ignored, not committed.

## Evaluation and compatibility

The same existing native whole-text scorers and final-two-slot policy assess
the frozen new provider. The native pool is the exact unsupplemented decoder
pool; the reference is deployed `d7dec75`, including its old generator. The
new and old providers are not stacked. Targets/ranks are stripped before
generation and scoring, and joined only to calculate outcomes.

The original frozen replacement trial gains one/no losses on known1450, but
violates the deployed first18 contract in one case: the native pool has16
choices, so the old two generated items occupy protected slots17/18.
The original reporter stops on this guard. `assess.py` completes read-only
reporting of the already completed predictions; the rejected protocol/model/
outputs are preserved, rather than edited to appear successful.

A separately declared compatibility experiment keeps the same checkpoint and
vocabulary. Whenever the native pool has fewer than18 choices, use the exact
legacy provider; otherwise use the expanded provider. This threshold follows
the protection contract, with no target lookup or threshold search. Original
parameter equality makes a legacy subset view possible without another weight
copy: filter new lexical edges and treat new context letters as old UNK.
The screening reuses byte-pinned legacy outputs only on identical known inputs.
The Java subset implementation/port is not reached because the next gate fails.

| Known comparison | First | Top5 | Top20 |
| --- | ---: | ---: | ---: |
| Parent1450 | 301 | 568 | 738 |
| Compatible expanded1450 | 301 | 568 | 739 |
| Parent3893 | 1,358 | 2,263 | 2,729 |
| Compatible expanded3893 | 1,358 | 2,263 | 2,726 |

On1450, one enters and none leaves. On3893, one enters and four leave, net−3;
the old600 subset loses three. Every deployed first18 prefix is retained after
compatibility repair (six and269 legacy fallback cases respectively). The
aggregate and per-set nonregression gates fail, so this experiment is rejected.
These are known sets, not independent evidence of general accuracy.

Static character/code coverage on1450 improves: unsupported targets317→251,
so66 more targets can be represented by the learned alphabet. This does not
mean66 more correct candidates. Extra legal edges change normalized sequence
probabilities and search competition even while all old parameters stay fixed.
Frozen parameter bits do not guarantee unchanged generated candidate lists.
Post-rejection inspection finds all four lost targets already used old supported
characters, and all four are absent from the expanded provider's20 proposals.
The existing native scorer cannot restore a proposal it never receives.

## Verification, isolation and delivery

Six meaningful checks cover index remapping and old-weight identity, actual
gradient updates restricted to new rows, newly legal outputs, old-character
retention, protection/new-row weighting and detection of frozen-row corruption.
The exact unchanged Java dictionary confirms2,493 character facts,2,745 legal
code choices,96 training alignments and all29,000 initial ordinary generated
candidates. Each known output has exact codes and at most20 unique choices.

Before vocabulary selection or fitting, a complete5,550-family evaluation pool
yielded591 unused families after excluding all tracked prior targets/groups and
full original pretrain/adaptation text. Hash order fixes a new500, including
their code/normalization provenance. They are evaluation-only NCDOL examples,
never fitted or packaged. Both earlier500 sets are observed; the new500 has
not been decoded. The old context_search500 is not decoded again.

Because the known3893 gate fails, the dynamic Java model export/legacy subset
port, full Java decoder qualification, Single32 candidate checks, Android unit/
Lint, paired latency and independent500 candidate comparison are unrun. Prior
app test results are not claimed as tests of this rejected model. No app files
are changed and no APK is built. This is a completed research result, with no
claim of improved deployed accuracy or a1.0 milestone.

Sources and frozen inputs are in `tools/vocabulary_expansion/` and
`tools/data/vocabulary_expansion/`; reports are under
`tools/reports/vocabulary-expansion-2026-10-18/`. Both the original rejected
trial and separately sealed compatibility trial are retained. Predecessor
artifacts/checkpoints remain immutable; source licences are in the new NOTICE.

Historical commands (existing outputs are protected):

```sh
source /workspace/android-environment/activate.sh
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python tools/vocabulary_expansion/prepare.py
python tools/vocabulary_expansion/test_model.py
python tools/vocabulary_expansion/evaluate.py native
# Seal the fixed protocol before fitting, then:
python tools/vocabulary_expansion/fit_expansion.py
python tools/vocabulary_expansion/evaluate.py freeze
# Generate each part0..3, then score once:
python tools/vocabulary_expansion/evaluate.py generate --part 0
python tools/vocabulary_expansion/evaluate.py report
# The strict original prefix guard intentionally fails; report existing output:
python tools/vocabulary_expansion/assess.py
# Separately declare the structural compatibility experiment, without refitting:
python tools/vocabulary_expansion/compat.py seal
python tools/vocabulary_expansion/compat.py calibration
# Generate each known-guard part0..3, then:
python tools/vocabulary_expansion/compat.py generate --part 0
python tools/vocabulary_expansion/compat.py guard
```

Reproduction needs separate paths and the pinned predecessor caches. Do not
overwrite frozen artifacts, treat either consumed500 as unseen, or decode the
new500 to tune a failed model.
