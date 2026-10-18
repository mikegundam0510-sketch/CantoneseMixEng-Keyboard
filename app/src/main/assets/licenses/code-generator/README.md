# Direct code-conditioned generation weights

Modified model weights are offered under CC BY-SA 4.0. The full licence is
bundled at ../sentence-language/CC-BY-SA-4.0.txt. The code remains under the
repository GPL-3.0-or-later licence. Dictionary code facts retain the source
contribution terms in the bundled GPL/LGPL/MIT dictionary notices.

The 32-dimensional character GRU and16-dimensional code encoder derive from
the frozen teacher checkpoint in tools/data/code_generator/models/teacher.npz.
The teacher was initialized from the attributed sentence-language model,
then trained on legal code-conditioned TRAIN examples. No new text or fitting
is introduced by this binary export. It proposes strings only; existing
native scorers decide admission to at most two final candidate slots.

Credits: Kang Kwong Luke and May L. Y. Wong, HKCanCor (2015), CC BY4.0,
https://github.com/fcbond/hkcancor revision39aeadf920e0b5ca93d0ad7792c59e740e7bdd65;
Tatoeba contributors via Aaron H. K. Tan/Jyut Dictionary,2023-04-08 snapshot,
CC BY2.0 France; Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
UD Cantonese-HK (Depling2017), CC BY-SA4.0; Mozilla Common Voice Sentence
Collector contributors, donated read prompts under CC0; project-authored
synthetic examples. Authors do not endorse these modifications.

Full source URLs, terms, revisions and family exclusions remain in
tools/data/code_generator/NOTICE.md, tools/data/sentence_pretrain/NOTICE.md
and the bundled ../sentence-language/source-audit.json. No Common Voice
prompt cache, words.hk evaluation text or private phone learning record is
included in these assets. Editor/search history is local to each query.

Teacher SHA256:704eb0e81108f5a038621ba42bea8b9e925b64d30848235858b90f73709c3feb
Export SHA256:c1e552eafdb126acc28618e4fcb4e4e9debd4c7497ffb2a67c6a01c7a76c6914
The source, sealed evaluation and limitations are in
docs/CONSERVATIVE_TAIL_SUPPLEMENT.md and tools/data/tail_supplement/.
