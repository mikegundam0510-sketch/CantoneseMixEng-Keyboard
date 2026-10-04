# 0.6.4 candidate and key spacing update

Continuous Quick decoding previously considered dictionary symbols (for example ｛, ♂ and ∮) as sentence tokens. The offline language model skips non-Han text, so these tokens could outrank actual Chinese words. Chinese lattice and repair options now accept Han text only; explicit standalone dictionary symbol lookup remains available.

Reproduction: `mtjnmyqv` previously ranked `研究一｛女` first. This fix removes symbol-containing sentences. The exact Quick codes for `研究一下` are `mt / jn / m / my` (`mtjnmmy`), which already rank that phrase first and are covered by a regression test. The screenshot's different code sequence is not silently replaced with this phrase.

Standard / taller / tallest key faces are now 44 / 50 / 56dp, with a one-time migration from 40 / 46 / 52dp preserving the selected tier. Compact landscape faces increase from 36 to 40dp. Fold split keys retain width-based scaling and receive the same proportional increase. Radical baselines move from 8dp to 12dp above the bottom. The extra key height preserves space between the Latin legend and radical while increasing the radical's bottom clearance.

Local Java production-code reproduction verified the reported input has no symbol-containing sentences and `mtjnmmy` ranks `研究一下` first. Android layout, migration and full regression verification run through GitHub Actions; physical Samsung touch and text appearance require device acceptance.

## Hong Kong usage

Added authored everyday chat/work fragments covering local time words, requests, action particles, pronouns and confirmations (for example 幫我睇下, 唔該晒, 等陣先, 研究下 and 改返). The asset generator preserves the same additions. These priorities are editorial choices, not claimed corpus frequencies.

The trained offline decoder now applies a small bounded bonus for matching authored HK fragments, including matches crossing a word or committed-context boundary. It retains exact-code matching, punctuation boundaries and the existing 48-path beam. Single-character context ranking leaves dictionary symbols behind Han choices. No input history or network service is added.

Eight unlisted sentences composed from the fragments are tested, including 我想研究一下, 你幫我睇下, 唔該幫我改返 and 等陣先再試下. The original 120 held-out corpus cases remain separate from these authored examples. General first-choice accuracy is still imperfect.
