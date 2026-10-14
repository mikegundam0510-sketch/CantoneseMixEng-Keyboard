# Displayed-candidate phrase relation model

`relation_ranker.b64` (PRR2) contains a modified train-only POS lexicon and fitted
weights. These derived lexicon/weights and their encoded model are offered under
CC BY-SA4.0, https://creativecommons.org/licenses/by-sa/4.0/ . The complete
license is retained in `CC-BY-SA-4.0.txt`. This attribution concerns these data
assets; it does not change the surrounding application's source license.

UD_Cantonese-HK: Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
"Quantitative Comparative Syntax on the Cantonese-Mandarin Parallel Dependency
Treebank", Depling2017, pp266–275. Source:
https://github.com/UniversalDependencies/UD_Cantonese-HK at
68c3151c1181a7b67ef5c917570635bcccf7e4bf, CC BY-SA4.0.
Original source description and license are retained in `UD-README.md` and
`UD-LICENSE.txt`. Only the Missing Days and Temple interview training productions
contribute text/POS. The production-disjoint evaluation material does not train
this asset. This is a custom split, not an official UD benchmark result.

HKCanCor: Luke, K. K., & Wong, M. L. Y. (2015), The Hong Kong Cantonese Corpus,
https://github.com/fcbond/hkcancor , CC BY4.0,
https://creativecommons.org/licenses/by/4.0/ . Only the existing46 training
conversations contribute these pairs. The full HKCanCor license is also bundled.

Tatoeba contributors: https://tatoeba.org/ , CC BY2.0 France,
https://creativecommons.org/licenses/by/2.0/fr/ . The pinned Jyut Dictionary
source and attribution remain in the adjacent `tatoeba/NOTICE.txt`. The existing
training families contribute to this modification. Project-authored scenario
variants are synthetic, not measured Hong Kong usage frequency. Original authors
do not endorse this keyboard or these modifications.

The fitted2,165-feature model uses actual same-code top-five competitors from
5,381 training examples, with at least two source families supporting a feature.
Signed score corrections have strength1 and limit2. The existing first choice
and visible20-candidate membership remain protected. It does not ban dictionary
characters. Parameters, hashes and aggregate evaluation are recorded in
`RELATION_RANKER_REPORT.json`.

words.hk NCDOL1.0 dictionary examples are evaluation-only development material;
they never train this model or POS lexicon and are not bundled in the APK.
The independent500-example comparison has185→193 top-five hits and89→89 first
hits. This small result is not contemporary chat-frequency or physical Fold7
evidence. No private messages or phone learning records train this immutable
model; existing personalization remains on the device.
