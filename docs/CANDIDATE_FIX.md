# 0.6.4 candidate and key spacing update

Continuous Quick decoding previously considered dictionary symbols (for example ｛, ♂ and ∮) as sentence tokens. The offline language model skips non-Han text, so these tokens could outrank actual Chinese words. Chinese lattice and repair options now accept Han text only; explicit standalone dictionary symbol lookup remains available.

Reproduction: `mtjnmyqv` previously ranked `研究一｛女` first. This fix removes symbol-containing sentences. The exact Quick codes for `研究一下` are `mt / jn / m / my` (`mtjnmmy`), which already rank that phrase first and are covered by a regression test. The screenshot's different code sequence is not silently replaced with this phrase.

Standard / taller / tallest key faces are now 44 / 50 / 56dp, with a one-time migration from 40 / 46 / 52dp preserving the selected tier. Compact landscape faces increase from 36 to 40dp. Fold split keys retain width-based scaling and receive the same proportional increase. Radical baselines move from 8dp to 12dp above the bottom. The extra key height preserves space between the Latin legend and radical while increasing the radical's bottom clearance.

Local Java production-code reproduction verified the reported input has no symbol-containing sentences and `mtjnmmy` ranks `研究一下` first. Android layout, migration and full regression verification run through GitHub Actions; physical Samsung touch and text appearance require device acceptance.
