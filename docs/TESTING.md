# Device acceptance checklist

Automated checks do not replace these device tests. Samsung-specific behaviour is unverified until tested on the target phone.

- Enable IME, select it, type in the app test field, Samsung Notes, a browser, and a messaging app.
- Quick: `of` includes 你, `vd` includes 好, `ha` includes 香, `eu` includes 港. Check Chinese Space pages candidates, 選字 selects the current page first candidate, taps select another, and the 英文／中文 control explicitly sets the current segment.
- Cangjie: disable Quick; `onf` includes 你. Disable Cangjie and verify `onf` no longer produces 你.
- Pick a non-first Chinese candidate repeatedly. Re-enter the same code, close/reopen keyboard, restart app: chosen character should move forward and persist. Clear learning: restore default ranking. Disable learning: use default ranking without deleting saved history.
- Test an editor with `IME_FLAG_NO_PERSONALIZED_LEARNING`: no personalised ordering and no new learning. Check text, visible-text, web, and numeric password variations: no candidates and no new learning.
- English `hello`, mixed uppercase, unknown names; symbols and Emoji; candidate paging for `mm`; shift tap and long-press; repeated Backspace; selected text replacement; emoji surrogate-pair deletion.
- Start composition then tap in another part of text: old candidates disappear and no stale composition is inserted. Switch apps, hide keyboard, open settings, rotate screen while composing.
- Verify multiline Return vs Search / Next / Done / Send. First Return during composition commits literal code without sending a message.
- Email and URL fields default to direct English. Numeric and phone fields show numeric layout. Confirm browser and custom editors accept input.
- Drag space left/right, including cancellation: move cursor without adding a space. Hold delete then close keyboard: repeat must stop.
- Dark / light / system themes, number row, 3 key heights, both single-hand modes, landscape. Test Samsung gesture and button navigation, increased display/font size, split screen, and Fold cover/inner screens if available.
- Target device: Galaxy Z Fold7 on One UI 8.5 (user-provided configuration). Check automatic split letter rows on the inner display (available width >= 600dp), normal rows on the cover display, split toggle off, and single-hand override. Fold/unfold with keyboard visible and during composition; verify no stale candidates or lost committed text. Multiwindow should follow the available width, not the physical screen size.
- TalkBack: keys have spoken labels; candidate selection, Space and Delete have click actions.
- AI instructions: keyboard picker works. On compatible Samsung device, manually select text and check for Galaxy AI; no claim that the keyboard directly invokes Samsung AI.
- Airplane mode: Chinese and English lookup still work. Check app permissions: no network / accessibility permission; audio permission is requested only for explicit system voice recognition. Verify no personal text is printed in logs.

## 0.2.0 acceptance additions

- Type `ofvdrf` by tapping the IME (ADB `input text` bypasses the IME). First sentence candidate should be 你好嗎; 選字 or candidate tap commits it once.
- Repeat; tap 逐字, select 你. Editor should contain 你 plus composing `vdrf`; remaining codes must still be selectable. Also try one-code characters, unknown phrases, raw English and backspace.
- Check 嗰 (`rr`), 嘅 (`ru`), 喺 (`rf`) through candidate scrolling/paging. Select an alternative repeatedly and verify learned ordering after reopening.
- Open all 9 Emoji categories; scroll each grid and category strip. Select and delete skin-tone, family, flag, heart and keycap sequences. Backspace should remove one complete bundled Emoji and preserve adjacent text.
- Verify recent Emoji order, limit 40, persistence, disabling and clearing. Sensitive editors must neither read nor update recents.
- Cover width: gray background, white letter keys, readable radicals above capitals, no branding on space. Inner width >= 600dp: balanced split rows and center gap. Test dark mode and long candidate phrases in both widths.
- Verify launcher, settings and system IME list all show 粵語中英混合keyboard.
- The debug-only KeyboardPreviewActivity provides a local editor for UI smoke tests; it has no launcher shortcut and is omitted from release builds.


## 0.5.0 acceptance additions

- Type `onaovrrovMcdonaldrh`: choose 今日食唔食Mcdonald呀 with brand casing preserved. Test other known/custom English words inside Quick code sequences, with manual English/Chinese fallback for ambiguous input.
- Type hello and Space: confirm `hello ` once; hellp offers hello but Space retains `hellp `. Learn an unknown explicit English word, restart, then remove it through settings.
- Select a sentence, press ↶, choose 分段改選 and replace only one character. Verify all other text remains. Moving cursor, changing editor, typing more or altering the committed suffix must disable ↶.
- Long-press a candidate to pin/unpin. Verify persistence after editor/app restart and delete pins/custom words in settings. Check no-personalized-learning and password fields ignore personal data.
- After 開, type oa: verify contextual 會 preference. Disable context ranking and compare.
- Type od: separately offered adjacent-key correction includes 你; selecting it learns the corrected of mapping. Exact candidates remain available. Disable Quick correction and verify the extra strip disappears.
- Long-press comma/period and choose punctuation; keyboard/editor focus should remain stable.
- Swipe left/right across letter keys: cursor moves without key insertion. Check short taps still type, vertical motion does not begin cursor movement, candidate swipes only scroll candidates, and Shift/Delete long presses still work. Test selected text, Emoji, pending composition, both Fold displays, split and single-hand layouts.
- Try direct voice with permission allowed/denied and an available/unavailable speech provider; verify real yue-HK and mixed-language results on Samsung hardware.

## 0.5.1 touch and latency checks

- Tap the outer edge and the gap inside each full key cell: code must be inserted once. Repeat with alternating fingers on Samsung/Fold hardware, both display sizes and one-hand layouts.
- Rapidly tap a continuous Quick sentence while candidates are searching: no missing, duplicated or reordered code. Compare key positions before/after candidate/repair rows update.
- Exact prefix choices appear after the leading sentence suggestion. Select a candidate marked ›: only that prefix commits and every remaining code is preserved.
- Change editors, reset text, erase code or choose a prefix before a search completes: previous results must not overwrite current candidates.
- Try arbitrary names and unusual clauses: whole-dictionary phrase preference is not a guarantee of sentence accuracy; verify manual prefix/segment choices remain available.
