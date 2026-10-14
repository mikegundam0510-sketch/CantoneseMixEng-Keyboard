# Phrase relation training and evaluation sources

Training uses the already attributed HKCanCor and Tatoeba training split,
project-authored examples, and a custom source split of UD_Cantonese-HK.
The train-only POS lexicon and fitted model are modifications; the original
authors do not endorse this keyboard.

* HKCanCor: Luke, K. K., & Wong, M. L. Y. (2015), The Hong Kong Cantonese Corpus,
  https://github.com/fcbond/hkcancor , CC BY4.0,
  https://creativecommons.org/licenses/by/4.0/ . The58 conversation files retain
  the existing46 training/12 excluded split. The2,000 additional examples are
  new to pairwise ranking training, not a new recording or previously unseen
  text for the old character language model.
* UD_Cantonese-HK: Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
  "Quantitative Comparative Syntax on the Cantonese-Mandarin Parallel Dependency
  Treebank", Depling2017, pp266–275. Source
  https://github.com/UniversalDependencies/UD_Cantonese-HK at
  `68c3151c1181a7b67ef5c917570635bcccf7e4bf`, CC BY-SA4.0,
  https://creativecommons.org/licenses/by-sa/4.0/ . Original source description
  and license are retained in `UD-README.md` and `UD-LICENSE.txt`. Missing Days
  and the Temple interview contribute train-only POS/text. What Day supplies
  validation; the2016 Legislative Council proceeding supplies independent
  test examples. This is a custom production-disjoint split, not a result on
  the official UD benchmark. No video/audio is downloaded. Derived lexicon,
  fitted weights and their encoded model are offered under CC BY-SA4.0.
* Tatoeba: Tatoeba contributors, CC BY2.0 France,
  https://creativecommons.org/licenses/by/2.0/fr/ , from the previously pinned
  Jyut Dictionary release. Its full attribution remains in the existing
  corpus/model notices. Project-authored variants are synthetic examples, not
  measured Hong Kong usage frequency.

words.hk reviewed public dictionary examples are **evaluation-only**, under
the Non-Commercial Open Data License1.0. They never train a model or POS lexicon
and never enter the APK. See ../daily_prefix/NOTICE.txt and
../daily_prefix/LICENSE-EXAMPLES.txt for the retained full data license and
Hong Kong Lexicography Limited attribution. The mirror's MIT parser license
does not replace the dictionary data license. This new test sample extends the
same fixed source-family hash ordering beyond the800 already observed examples.

No private chats, phone editor text or personal learning records are training
data for this immutable model. Existing phone personalization stays local.
