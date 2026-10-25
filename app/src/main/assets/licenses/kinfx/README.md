# KINFX Cantonese word selection

Source: https://github.com/Kinfxhk/kinfx-ime
Reviewed revision: 438d89283cab793148b04ebbe756e228153213c8

kinfx_words.tsv adds 504 previously absent word surfaces with source counts >= 3000,
length 2–5, and characters already supported by this app's dictionary. The source
counts are corpus weights, not measured Hong Kong phone typing frequency.

Word selection/frequencies originate from rime-cantonese's essay-cantonese.txt,
CC BY 4.0. Copyright GONG Chen, Ayaka Mikazuki, chaaklau, LeiMaau,
laubonghaudoi, tanxpyox, William915, szc126, Bing Jeung, Henry Chan,
graphemecluster and other rime-cantonese contributors; KINFX contributors.
https://github.com/rime/rime-cantonese
See UPSTREAM-LEXICON-NOTICE.txt and CC-BY-4.0.txt for attribution/terms.

Changes: deduplicate the four bundled phrase lists, retain only common supported
surfaces, discard upstream code columns, and match all native Quick aliases at
runtime. No Microsoft candidate order/table, English/name lexicon, Lua runtime
or desktop-specific implementation is imported. Our optional third-key top-out
is implemented independently for Android and uses this app's personal ranking.
The upstream notice also describes LGPL-3.0 code columns; their terms are retained
in LGPL-3.0.txt for provenance, although those columns are not redistributed.

SOURCE.json records input/output hashes and filtering. Reproduce with:
python tools/import_kinfx_words.py --source /path/to/pinned/kinfx-ime \
  --native-facts /path/to/native-facts.tsv
NativeFacts.java in tools/strong_teacher exports native dictionary coverage.
