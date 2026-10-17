# Direct code-conditioned generation and actual-error adaptation

The user authorized two research steps: learn `Quick code + context → text`,
then learn from actual wrong candidates. Parent `22d26b5` has the same app tree
as adopted `28dfb69`. Both fixed research arms fail the predeclared ordinary
calibration gates. The production app, version 0.6.39/code 46, signing,
personalization storage and Fold7 layouts remain unchanged. No APK is produced.

## Model and legal decoding

A pretrained 32-dimensional character embedding/GRU supplies left context. A
new reverse 16-dimensional tanh RNN encodes the remaining input keys. Their
outputs jointly predict a normalized distribution over legal
`(character, consumed length 1 or 2)` edges from the actual dictionary.
Both code context and character history contribute to lexical and length
logits. The full input must be consumed; incomplete prefixes cannot be output.

The flat lexical head is initialized with a first-order approximation of the
old hierarchical-softmax log probability at zero hidden state. This is a new
head, with no claim of score equivalence to the old ranker. All components are
then trained with masked conditional cross entropy. There are 2,248 learned
characters and 2,479 actual code choices; generation has no cold-frequency
cutoff within that character set. Existing dictionary characters outside the
model remain available through the native decoder.

Inference keeps 24 histories per consumed-code position, merges duplicate
texts using their best alignment, and returns at most 20 complete strings.
Hidden-state transitions are evaluated only for surviving histories. Sequence
ranking uses summed legal-edge log probability; comparisons between sentences
with the same input normalize by input-key count. Training and inference share
this probability definition, including variable-length code consumption.

## Data and two fixed stages

Generation fitting uses 8,192 already licensed TRAIN examples: 5,325 HKCanCor,
1,638 CC0 Common Voice prompts, 819 Tatoeba, 205 retained UD and 205 authored
examples. The internal validation has 1,190 examples from the original held-out
TRAIN families, including 998 HKCanCor, 154 Tatoeba and 38 authored examples.
No CV author-disjoint validation is claimed. Vocabulary, source families and
the original pretrained model's internal split stay fixed.

For a deterministic third of longer examples, the first three characters form
context and the remaining text forms the coded target. A hash-controlled subset
uses another attested code alias. These views stay in the original family and
do not count as independent source observations. Every alignment is legal.
External evaluation text is read only for six-character overlap exclusion,
including the still-unused `prefix_language/reserve.tsv`.

The second stage uses 2,254 fit and 507 internal validation comparisons from
the 2,534 current-parent observations already collected. Cache reuse requires
the exact output hashes and identical parent app tree. There are 625 actual
wrong/missing fit comparisons (517 wrong-first, 108 missing entirely) and 1,629
protected-first comparisons. Fit weighting assigns 75% actual-error and 25%
protection mass within each source, with family/case/rival normalization.
Pairs are public TRAIN derivatives; Common Voice text is absent from the
published pair archive. No private phone correction or learning record is used.

Teacher fitting runs 12 fixed Adam epochs at rate 0.001; contrast fitting runs
8 at 0.0003. Old character embedding/GRU parameters use a quarter rate. Gradient
clipping is 5, batch size 64, seed 20261017. Teacher checkpoint selection uses
only internal conditional CE, which changes 1.054307→0.626319 (epoch 12).
Contrast selection uses softplus of the signed code-normalized pair gap plus
0.1 positive CE: 0.788239→0.753157 (epoch 8). These are internal training
objectives, not keyboard hit rates. Primitive parameter arrays occupy 757,428
bytes. NumPy checkpoints disable pickle loading.

## Fixed fusion and calibration

Two arms only: `teacher` and `contrast`. Each generates at most 20 strings and
combines them with the native parent's original display. The original first
stays at slot zero. Native sentences outside the learned vocabulary/codebook
retain their original slots. Remaining legal sentences are ranked by the new
conditioned likelihood, with stable native-before-generated ties, and the
display remains bounded to 20. Explicit personal/mixed handling would require
the later native implementation gates before any adoption.

The sealed protocol requires nondecreasing first/top5/top20 separately on the
known 150 and 1,300 groups, a net top20 gain, and at most one percentage point
per-set first/top5 loss. Both source and model bytes are frozen before ordinary
calibration. Targets are consulted only after generation and fusion finish.
The baseline is the adopted app's byte-pinned cached output.

| Ordinary research display, 1,450 cases | First | Top5 | Top20 |
| --- | ---: | ---: | ---: |
| Adopted native parent | 301 | 568 | 736 |
| Teacher hybrid | 301 | 369 | 443 |
| Contrast hybrid | 301 | 371 | 443 |

First choices remain fixed by construction. Both hybrid arms regress and are
rejected; contrast learning adds two top5 hits over the teacher hybrid but
remains far below production. The generator alone is diagnostic: teacher
66/122/191, contrast 60/123/185. Those counts do not describe a deployed app.

The teacher generator recovers 20 targets missing from the original display;
contrast recovers 17. Combining all original and generated strings gives
oracle membership counts 756 and 753, against the parent's 736. That union may
contain 40 choices and uses the known answer to measure membership. It is not
a 20-candidate result or a hit-rate improvement. The fixed fusion loses more
existing correct choices than it gains. Another limitation is that 317 targets
are outside the learned character/codebook coverage. These observations identify
limitations; they do not establish a single cause for every failed sentence.

## Verification and scope

Six tests check finite differences through both recurrent networks, legal-edge
softmax and pair adaptation; legal complete decoding; future-code dependence;
conditional sequence scores; and protected native slots. The exact Java
DictionaryEngine verifies every learned character's code facts, 96 admitted
training inputs and all 58,000 ordinary generated candidates across both arms.
Each checkpoint also passes 80 unambiguous generated-path score comparisons
against the teacher-forced scorer, with maximum absolute error below 3.2e-7.
Read-only parameter arrays work throughout inference.

After rejection, a model-only research timing probe uses three warmups and
seven samples on six fixed codes, with one NumPy thread. Medians range roughly
4–21ms. It excludes the native parent, fusion, loading, Java and Android; it
cannot establish app latency or pass the native latency gate.

The Java neural port, 3,893-case regression guard, Single32 candidate gate,
wired Android tests/Lint and native paired latency gate are not run because
calibration already fails. The Java check validates dictionary legality, not a
Java neural implementation. The new reserve500 is not decoded. The previous
context-search500 is not decoded again. No model, code or threshold is tuned
after the ordinary result, and all tracked app files remain unchanged.

## Artifacts and reproduction

`tools/data/code_generator/` contains source/input hashes, manifest, legal code
facts, protocol/seal, both checkpoints, the public TRAIN pair archive, frozen
inference hashes and the final decision. Full results and checks are under
[`tools/reports/code-generator-2026-10-17/`](../tools/reports/code-generator-2026-10-17/).
Raw/derived Common Voice text remains only in ignored local caches; its pinned
source URL and terms are in the predecessor sentence-pretrain source audit.

Historical run commands:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/code_generator/test_model.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/code_generator/prepare.py
# Seal the fixed protocol before fitting; preserve original family splits.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/code_generator/train.py
# Freeze exact models/inference before running each arm and parts0..3.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/code_generator/evaluate.py run teacher 0
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/code_generator/evaluate.py report
```

Preparation/fitting refuse existing completed outputs. Reproduction needs
separate paths and the pinned predecessor caches; it must preserve this
experiment's files and not use the unused reserve for tuning. All source
attributions and licences remain linked from the data notice.
