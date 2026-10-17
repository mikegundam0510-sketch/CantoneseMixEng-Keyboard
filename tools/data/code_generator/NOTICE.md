# Code-conditioned generation research

Code retains the repository GPL-3.0-or-later licence. Mixed derived weights and
public TRAIN pair modifications are offered under CC BY-SA 4.0, with original
source contribution terms and attribution retained. Full terms:
[`app/src/main/assets/licenses/sentence-language/CC-BY-SA-4.0.txt`](../../../../app/src/main/assets/licenses/sentence-language/CC-BY-SA-4.0.txt).

- HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), The Hong Kong Cantonese
  Corpus, https://github.com/fcbond/hkcancor at
  39aeadf920e0b5ca93d0ad7792c59e740e7bdd65, CC BY 4.0, original TRAIN families.
- Tatoeba contributors via Aaron H. K. Tan / Jyut Dictionary, snapshot
  2023-04-08, CC BY 2.0 France; frozen TRAIN translation families.
- UD_Cantonese-HK: Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
  Depling 2017, CC BY-SA 4.0, retained custom TRAIN productions.
- Common Voice Sentence Collector contributors: Cantonese read prompts donated
  under CC0. These are not conversation recordings or measured chat frequency.
  Pinned source and contribution-term URLs/hashes remain in
  [`sentence_pretrain/source-audit.json`](../sentence_pretrain/source-audit.json).
  No raw or derived CV prompt text is mirrored in Git or app assets.
- Project-authored examples: repository licence; synthetic supervision.

Full credits, source revisions, original split definitions and licence texts
remain in [sentence_pretrain](../sentence_pretrain/NOTICE.md),
[clean_ranking](../clean_ranking/NOTICE.md),
[current_search](../current_search/NOTICE.md) and their linked notices.
Authors do not endorse these modifications.

`codes.json` records learned-character first/last Quick-code facts from the
unchanged bundled Cangjie dictionary. Original dictionary/source terms remain
in [THIRD_PARTY_NOTICES.md](../../../../THIRD_PARTY_NOTICES.md) and bundled
GPL/LGPL/MIT dictionaries' notices. It does not change the app dictionary.

The local corpus contains attributed TRAIN text and deterministic code/context
views, with original family splits. It remains under ignored `.native/` because
it contains Common Voice text. Only its hashes/counts are published here.
`pairs.jsonl.gz` is a byte-identical public-data copy of the frozen comparison
cache and contains HKCanCor, Tatoeba, UD and authored examples, with no CV text.
Rows record original family/domain/split, context, full input code, correct and
actual competing sentence, source identity and wrong/missing/protected origin.
These are current-engine errors on public TRAIN data, not phone user records.

words.hk/NCDOL examples are evaluation-only and never fitted or packaged. All
such result text retains the original attribution/terms in
[`daily_prefix/NOTICE.txt`](../daily_prefix/NOTICE.txt) and
[`daily_prefix/LICENSE.txt`](../daily_prefix/LICENSE.txt). The unused
prefix-language reserve500 remains excluded from fitting and undecoded.
