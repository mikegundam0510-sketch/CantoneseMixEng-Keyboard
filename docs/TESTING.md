# Device acceptance checklist

Automated checks do not replace these device tests. Samsung-specific behaviour is unverified until tested on the target phone.

- Enable IME, select it, type in the app test field, Samsung Notes, a browser, and a messaging app.
- Quick: `of` includes 你, `vd` includes 好, `ha` includes 香, `eu` includes 港. Check Space chooses the first candidate, taps choose another, and raw-English button commits the code.
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
- Airplane mode: Chinese and English lookup still work. Check app permissions: no network / audio / accessibility permission. Verify no personal text is printed in logs.

## 0.2.0 acceptance additions

- Type `ofvdrf` by tapping the IME (ADB `input text` bypasses the IME). First sentence candidate should be 你好嗎; Space or candidate tap commits it once.
- Repeat; tap 逐字, select 你. Editor should contain 你 plus composing `vdrf`; remaining codes must still be selectable. Also try one-code characters, unknown phrases, raw English and backspace.
- Check 嗰 (`rr`), 嘅 (`ru`), 喺 (`rf`) through candidate scrolling/paging. Select an alternative repeatedly and verify learned ordering after reopening.
- Open all 9 Emoji categories; scroll each grid and category strip. Select and delete skin-tone, family, flag, heart and keycap sequences. Backspace should remove one complete bundled Emoji and preserve adjacent text.
- Verify recent Emoji order, limit 40, persistence, disabling and clearing. Sensitive editors must neither read nor update recents.
- Cover width: gray background, white letter keys, readable radicals above capitals, no branding on space. Inner width >= 600dp: balanced split rows and center gap. Test dark mode and long candidate phrases in both widths.
- Verify launcher, settings and system IME list all show 粵語中英混合keyboard.
- The debug-only KeyboardPreviewActivity provides a local editor for UI smoke tests; it has no launcher shortcut and is omitted from release builds.

## 0.3.0 acceptance additions

- Fresh install defaults to Quick + English, with Cangjie off. Existing preferences remain intact when the signature permits updating.
- Type `mm`, expand candidates, scroll past the first 30 choices and select one. It should commit once and return to the letter keyboard. Long-press a candidate and check its per-character Quick codes, including supplementary characters. Dismiss the dialog, change editors and hide the keyboard: no orphaned window should remain.
- Type `of`, choose 你, then choose the association 好嗎. Text should be 你好嗎, with no repeated 你. Space after a selected word must insert a space instead of choosing an association. Disable associations; move the cursor; hide/reopen the keyboard; enter punctuation: old associations must disappear when context no longer matches. Private editors never show associations.
- Add `hk` → 香港 🇭🇰 from settings. Type `hk` in normal text and choose the shortcut. Edit it, try a duplicate shortcut, cancel a deletion, then confirm deletion. Reject invalid or oversized codes/phrases without changing other entries. Disabled shortcuts and private editors must suppress them.
- In EN mode type `teh`: a suggested `the` must require a tap; Space must leave `teh ` unchanged. Type `hel` and select hello. Check mixed case, unknown names, raw-English selection and correction disabled. Email/URL/password fields continue direct literal input.
- From Tools manually test Paste, Select all, Copy and Cut, including selected text and editors that reject context-menu actions. Confirm no clipboard history is created. Password fields disable Tools.
- Check the Tools menu and long-code dialogs on cover/inner screens, landscape and one-hand modes. Check keyboard row labels at increased font size. These window, rendering and accessibility checks are not covered by JVM tests.
- Test startup and suggestion response on the target phone with the larger English wordlist. Wordlist suggestions can include uncommon words; no claim of AI-quality ranking or grammar correction is made.
