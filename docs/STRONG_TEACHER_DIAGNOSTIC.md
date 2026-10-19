# Stronger offline teacher: tools prepared, model evaluation blocked

The requested next step is to test a substantially larger language model on
existing same-code candidates, then code-constrained generation. No teacher
accuracy result exists yet: Hugging Face returned proxy CONNECT403. The saved
network draft adds huggingface.co and cas-bridge.xethub.hf.co, preserving all
previous custom domains and presets. Saving a draft does not apply or publish
it. Observed runtime uses spec3; the new domains are in draft revision4.

The supplied screenshot says publication is disabled until environment setup
completes. Runtime status reports running/connected, current observations and
no failure. Available tools can save configuration but cannot publish or toggle
that UI control. After this setup turn completes, retry Review/Save/Publish in
environment settings. If publication remains disabled, that platform gate is
still unresolved; do not treat the network as enabled or bypass its proxy.

## Prepared and verified

- Dedicated CPU tooling under /workspace/cantonese-teacher-environment, separate
  from the app: CMake3.31.6 and Ninja1.11.1.4 installed using official SHA256
  hashes; llama.cpp pinned to d7a695ef679138c13d86359b84c1731d36213d32.
- teacher-likelihood, llama-server and test-gbnf-validator compile. The complete
  setup script repeats successfully. Runtime version is0.6.0-dev/build11442.
  No model is downloaded during setup, no server is left running and no APK
  target is invoked. An upstream warning about absent embedded web UI is
  expected; the API/CLI workflow does not require those UI assets.
- The actual unchanged Android dictionary exports103,335 single-Han characters
  with129,624 Quick aliases. A finite GBNF grammar permits exactly the complete
  input's1/2-key paths. It has no target string, phrase or frequency cutoff.
- Six checks pass against llama.cpp's real grammar parser: complete native
  alignments, rejection of incomplete/punctuation/Latin output, supplementary
  Unicode, invalid code bounds, one/two-key ambiguity and input-field isolation.
  This tests constraints, not neural inference or accuracy.

The first validation run encountered an upstream diagnostic-display issue:
the grammar validator puts ANSI colours between UTF8 bytes when rejecting
non-ASCII input. The sealed original test and failing log are preserved.
validate_constraints.py reads its ASCII acceptance marker in raw bytes; all
six checks then pass without changing grammar or test cases. The repair is
recorded in validation-repair.json.

## A corrected diagnostic, not another unseen500

The previous500 and the old file named hk_daily_context_cases.tsv both have
empty initial context fields. They cannot establish contextual recognition
quality. The first preparation incorrectly treated that filename as supplied
context; its data/protocol/source are preserved in the ignored
.native/strong-teacher-preflight-no-context-20261019 archive. No teacher ran.

The corrected known diagnostic contains92 cases:

- 60 cold cases:20 each whose gold is already top5, ranked6–20, or missing,
  selected by fixed hash order from the already observed500.
- 32 supplied-context cases: for each existing authored6–8-character sentence,
  treat its first4 characters as already typed context. Remove those characters
  and their exact native code alignment from both target and remaining input.
  This is controlled completion, not newly collected conversation or independent
  data. Preserve the source/cut evidence in context-provenance.json.

The ordinary deployed native decoder supplies every parent pool. Teacher inputs
have context plus the entire actual candidate list, without source labels,
gold designation or ranks. Diagnostic sampling uses observed ranks explicitly;
report each stratum separately rather than a population hit rate.

Reranking uses continuation log probability per Han character, stable native
ties and the same candidate set. First-choice changes are allowed only in this
offline diagnostic and gains AND losses must be counted.28 generation grammars
are prepared for the20 missing cold cases and first8 controlled-context cases.
Four fixed samples are planned per code. A four-sample union oracle cannot be
reported as displayed20 accuracy. Generated text must be checked again by the
actual Java dictionary. No app adoption, distillation or1.0 decision belongs to
this phase.

## Remaining work after network publication

The proposed teacher is multilingual Qwen3-4B-Instruct-2507, with an external
Q4_K_M export. Its Cantonese ability, exact availability, licence and model
hash remain unverified. The resolver checks fixed public source identities,
Apache2.0 cards/text, exact revisions and authoritative LFS SHA/size before
allowing a download. It does not guess a different model on failure.

```sh
source /workspace/android-environment/activate.sh
bash tools/strong_teacher/setup_runtime.sh
cat tools/reports/strong-teacher-2026-10-19/constraint-checks.json
# After the new network policy is actually applied:
PYTHONDONTWRITEBYTECODE=1 python tools/strong_teacher/fetch_model.py resolve
PYTHONDONTWRITEBYTECODE=1 python tools/strong_teacher/fetch_model.py download
```

Completed preparation outputs are protected; do not overwrite or rerun the
one-time prepare/validation writers. Reproduction needs separate paths or the
retained predecessor caches. Once weights are available, smoke-test actual
inference, verify the chat template/token boundary scores, and freeze the exact
model/runtime/prompts before reranking. Then run the predeclared constrained
generation samples, report hits/losses/timeouts and teacher cost. A real-model
runner, inference freeze and both accuracy comparisons remain unrun/pending;
compilation and grammar tests do not substitute for those checks.

App source/assets, signing, local learning formats and Fold7 layout are
unchanged. Version remains0.6.39/code46; no APK is produced. Sources, public
evaluation terms and limitations are in tools/data/strong_teacher/NOTICE.md.
