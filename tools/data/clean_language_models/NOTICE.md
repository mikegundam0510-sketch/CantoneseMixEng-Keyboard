# Clean primary language-model experiment

`corpus.jsonl.gz` contains modified, attributed public TRAIN text and its original
span/word provenance. It is not current phone text or measured typing frequency.
No user learning records, private conversations or evaluation answers are fitted.
Reading reserve labels for exclusion is not decoding or model selection.

- HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), *The Hong Kong Cantonese
  Corpus: Design and Uses*, [source](https://github.com/fcbond/hkcancor), revision
  `39aeadf920e0b5ca93d0ad7792c59e740e7bdd65`, CC BY 4.0. Only the original46 TRAIN
  files are used. Original word boundaries and conversation/utterance IDs remain.
  Licence: [HKCANCOR-CC-BY-4.0.txt](../../../../app/src/main/assets/licenses/HKCANCOR-CC-BY-4.0.txt).
- Tatoeba contributors, via Aaron H. K. Tan's Jyut Dictionary
  `v4.25.0623-release`, snapshot2023-04-08, CC BY 2.0 France. IDs in provenance
  are redistributed database record IDs, not asserted original Tatoeba IDs.
  Full source credit, licences and limitations remain in
  [the Tatoeba notice](../tatoeba_corpus/NOTICE.md). Only its frozen TRAIN
  translation families are admitted. These sentences have no verified word
  segmentation and contribute to the character model only.
- Project-authored scenario TRAIN families: repository licence, synthetic
  priorities rather than observed use. Variants in one family count once per
  word relation. Full source templates remain in `../hk_chat_scenarios.json`.

The transformations split at every non-Han boundary, retain original code-point
offsets/words, apply Unicode NFC and only six reviewed one-to-one OpenCC glyph
pairs. No replacements for𡃉/𠻺/𠸏/𡁵 are guessed. Original OpenCC source,
BYVoid/contributor credit, Apache-2.0 licence and exact rules remain in
[`../clean_ranking/orthography/`](../clean_ranking/orthography/).

The separate pinned lexical priors are the same Rime Essay-derived Quick
vocabulary (LGPL-3.0), Rime Cantonese (CanCLID and contributors, CC BY 4.0),
and project-authored HK priorities as production. See the complete
[third-party notices](../../../../THIRD_PARTY_NOTICES.md) and linked bundled
licences. Those original sources are not duplicated in this corpus archive.
All source licences remain applicable to their respective contributions and
statistical modifications; no author endorses these changes.

The corpus and model manifests retain SHA256 values and original source
revisions. Research models use the existing KLM2 character five-gram and WLM1
segmented-word relation formats. They add no vocabulary tokens and do not remove
characters from the keyboard dictionary. Every experimental output is separate
from production pending the frozen qualification gates.

words.hk NCDOL1.0 examples are evaluation-only and do not train either model.
There is no retained UD treebank text in this new primary-model corpus.

The separate `tools/reports/clean-language-models-2026-10-16/guard-reference.zip`
is an evaluation reference, never training data or an APK asset. Its original
words.hk NCDOL1.0 and UD_Cantonese-HK CC BY-SA4.0 attribution, source revisions,
authors and linked licences remain in the
[phrase-relations notice](../phrase_relations/NOTICE.md) and prior referenced
evaluation notices. Other guard examples retain their Tatoeba/HKCanCor/project
credits. It contains no new reserve500 outcomes.
