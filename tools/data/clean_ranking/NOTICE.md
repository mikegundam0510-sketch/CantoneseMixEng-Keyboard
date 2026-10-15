# Clean TRAIN spans and research models

This is a modified, code-admitted derivative of the previously attributed TRAIN
data. Retain the complete source credits/licences in
[`../joint_ranking/NOTICE.md`](../joint_ranking/NOTICE.md),
[`../phrase_relations/NOTICE.md`](../phrase_relations/NOTICE.md),
[`../tatoeba_corpus/NOTICE.md`](../tatoeba_corpus/NOTICE.md) and their linked
original notices. The authors do not endorse this keyboard or modifications.

- HKCanCor: K. K. Luke and May L. Y. Wong (2015), *The Hong Kong Cantonese
  Corpus: Design and Uses*, CC BY 4.0. Only the original46 TRAIN conversations
  are admitted; the excluded12 are not read for training.
- Tatoeba contributors, via Aaron H. K. Tan / Jyut Dictionary: CC BY 2.0 France,
  snapshot2023-04-08. Only previously frozen TRAIN translation families are used.
  Han spans are attributed to the original record ID, group and raw text.
- Retained UD_Cantonese-HK derivatives: Wong, Gerdes, Leung and Lee (2017),
  CC BY-SA 4.0, original custom TRAIN productions only.
- Retained project-authored templates: repository licence; synthetic, not
  observed typing frequencies.

The six reviewed one-to-one glyph mappings are a subset of OpenCC's
`HKVariants.txt`, BYVoid and OpenCC contributors, Apache-2.0. Full source,
SHA256, URL and licence are retained in `orthography/`. Unicode NFC supplies
canonical normalization. Historical HKCanCor forms such as𡃉/𠻺/𠸏/𡁵 have **no**
approved replacement here; pronunciation alone never licenses substitution.
No mapping is applied to editor/user text or evaluation answers.

Derived mixed research weights and models are offered under CC BY-SA 4.0.
`character-codes.tsv` records facts from the bundled dictionary's actual Java
ordering, using the already attributed dictionary/frequency assets; its companion
JSON pins those sources. Original dictionary licences remain under
`app/src/main/assets/licenses/`. It does not change or redistribute a new
keyboard character set.

words.hk examples are evaluation-only NCDOL1.0 material. No dictionary example
trains these models or enters the APK. Existing fresh500 stays separate and is
not decoded unless the frozen qualification gates pass. No phone text or private
learning records are collected. These are older public corpus examples, not new
recordings, independent speakers, or current Hong Kong typing-frequency data.

`provenance.jsonl` records the original text, source file/utterance or Tatoeba
record/group, original code-point span, explicit transformations, retained-row
origin, old/new code and maximum actual cold character rank. Every non-Han
boundary resets a span; no surrounding Han is joined across punctuation, English,
digits or missing-speech markers. Legacy retained rows are explicitly marked.
Choosing a rank<=24 code proves basic character-option admission, not beam
survival, display membership, accuracy or device font support.

`repair/` contains TRAIN-labelled shadow reconstructions only. They never enter
ordinary inference. Column definitions match
[`../structured_ranking/NOTICE.md`](../structured_ranking/NOTICE.md).
