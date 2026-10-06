# Windows missing-code repair — 0.6.21

Append the 4,808 Cangjie associations missing from 0.6.20 when compared with
the user's Windows 10 22H2, build 19045.6466 system files. Keep the complete
old dictionary as an unchanged prefix. This repairs explicit code reachability;
it does not claim a general improvement to sentence ranking.

Examples: 丟/hgi (Quick hi), 吞/hkr (Quick hr), 產/yhhqm and 彥/yhhhh.
The original 丟/mgi, 吞/mkr, 產/ykmhm and 彥/ykmhh remain valid. Add 34
previously absent symbols, including € and box-drawing characters. All 1,725
missing Quick associations are covered by deriving first/last codes from these
Cangjie additions; no independent Quick-only aliases are necessary.

Final dictionary: 144,164 unique character/code pairs, 103,976 distinct
characters/symbols. Supplement checksum and original file hashes are pinned in
tools/windows_ime_compat_source.json and the bundled provenance report.
tools/prepare_cangjie_data.py applies the supplement on regeneration, verifies
its checksum and addition count, and fails if the source baseline changes.

File comparison validates every single-character association in the supplied
new/legacy Cangjie main tables (27,604 each), Cangjie extension (32,222),
legacy Quick main table (27,061) and Quick extension (31,935). After the
supplement, all five tables have zero missing associations. Extension records
may be subject to enabled Windows character-set settings. The upload did not
contain a separate new Quick system table, and live Windows/Android typing or
candidate order has not been tested. Raw Windows files and decoded full tables
remain outside the repository and APK.

Two JVM tests cover common Windows codes, preservation of old codes, mode
disabling, and every one of the 4,808 additions through CandidateEngine in both
Cangjie and Quick modes. Existing exhaustive full-code, prefix and Quick tests
continue to apply. Version code 28 / 0.6.21 uses the pinned 0.6.19 signer and
keeps existing learning preferences unchanged.

Validation: all 98 JVM tests pass with zero failures/errors/skips. The release
APK builds and its certificate matches the persistent pin. Compared with
20898f2, candidate results remain 33/39/39 (top 1/5/8) on 40 development
cases and 61/97/105 on 120 held-out cases. Reproduce with
`bash tools/context_accuracy.sh 20898f2 /tmp/windows-code-context-evidence`.
No real-device update or keyboard typing result is claimed.
