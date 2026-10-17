# Sentence-language tail reranker

`sentence_language.b64` is a modified causal character GRU checkpoint trained
first on attributed TRAIN text and then on same-code TRAIN candidate pairs.
Its derived mixed weights are offered under CC BY-SA 4.0:
https://creativecommons.org/licenses/by-sa/4.0/ . Full terms are in
`CC-BY-SA-4.0.txt`. Code retains the repository code licence. Source authors do
not endorse this keyboard or these modifications.

Source contributions retain these credits and terms:

- Common Voice Sentence Collector contributors: Cantonese read prompts donated
  to the public domain under CC0. These are read prompts, not conversations or
  measured Hong Kong chat frequencies. Source revision, download/terms URLs and
  hashes are in `source-audit.json`. No raw or derived prompt text is mirrored
  in these assets. CC0: https://creativecommons.org/publicdomain/zero/1.0/ .
- HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), The Hong Kong Cantonese
  Corpus: Design and Uses; https://github.com/fcbond/hkcancor at
  39aeadf920e0b5ca93d0ad7792c59e740e7bdd65, CC BY 4.0. Only the original
  46 TRAIN conversations. Full terms: adjacent `../HKCANCOR-CC-BY-4.0.txt`.
- Tatoeba contributors via Aaron H. K. Tan / Jyut Dictionary, snapshot
  2023-04-08: https://tatoeba.org/ , CC BY 2.0 France. Only frozen TRAIN
  translation families. Full source notice/terms: adjacent `../tatoeba/`.
- UD_Cantonese-HK: Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
  Quantitative Comparative Syntax on the Cantonese-Mandarin Parallel Dependency
  Treebank, Depling 2017, pp. 266–275;
  https://github.com/UniversalDependencies/UD_Cantonese-HK at
  68c3151c1181a7b67ef5c917570635bcccf7e4bf, CC BY-SA 4.0. Only the retained
  custom TRAIN productions. Original notice/terms: adjacent
  `../relations/UD-README.md` and `../relations/UD-LICENSE.txt`.
- Project-authored scenarios: repository licence; synthetic supervision, not
  private messages or observed usage frequencies. Existing dictionary/candidate
  source terms remain in the repository THIRD_PARTY_NOTICES.md and licences.
- Six reviewed OpenCC HKVariants glyph mappings normalize training text only;
  BYVoid and OpenCC contributors, Apache-2.0. Adjacent
  `../OPENCC-HKVARIANTS-NOTICE.txt` and `../OPENCC-HKVARIANTS-APACHE-2.0.txt`.

No words.hk/NCDOL example, private phone text or personal learning record is
fitted or bundled in this checkpoint. Personalization stays on the device.
`training-report.json` describes the fixed two-stage fit; it is not a measured
production accuracy result. The checkpoint SHA256 is
57c8997ac0ff6076a5bf9101f2ee007865618c638a110eca4b76b85e76383746.

The runtime keeps the original first choice and candidate membership, and only
reorders the existing alternatives using bounded evidence. Explicit personal
preferences and mixed input retain the established paths. Missing or corrupt
optional weights fall back to the original decoder.
