# 粵語中英混合keyboard

原生 Android 離線鍵盤，目標裝置為 Samsung Galaxy Z Fold7／One UI 8.5。

## 0.6.23 更新

- Fold7 展開按鍵按第二張參考圖嘅高／闊比例調整鍵高，保留 0.6.22 分體位置、字母及字碼；數字同角落標示同步放大。
- Shift 改成較大嘅空心向上箭嘴，Backspace 改成較大嘅空心退格框連叉號。
- 沿用固定簽名同學習資料；版本碼 30。

## 0.6.22 更新

- Fold7 展開分體佈局按使用者參考圖調整：`QWERT｜YUIOP`、`ASDFG｜GHJKL`、`Shift＋ZXCV｜VBNM＋刪除`，兩邊均可按 G／V。
- 底排為 `?123 / 🌐 空白 . →`；加闊空白鍵並顯示輸入模式，英文字母移至字根鍵右上角。
- 沿用固定簽名、Windows 相容拆碼及學習資料；版本碼 29。

## 0.6.21 更新

- 補入由 Windows 10 22H2（19045.6466）系統字庫比對確認嘅 4,808 組倉頡拆碼，速成取首尾碼後亦補齊原本欠缺嘅 1,725 組對應；保留舊碼。
- 「丟」可用 `hgi`／速成 `hi`，「吞」可用 `hkr`／速成 `hr`；新增 34 個 Windows 符號。
- 沿用固定簽名及本機學習資料，版本碼升至 28。呢次覆蓋係所提供字庫檔案嘅比對結果，未代表所有 Windows 版本或實機候選排序一致。

## 0.6.20 更新

- 保留完整字庫，新增 6,124 組倉頡三代及舊習慣拆碼；速成同步接受首尾碼。例如「面」可用 `mwyl` 或 `mwsl`，「撐」可用 `qfbq` 或 `qfbh`。
- 以 Windows 輸入習慣相容為目標；公開碼表並非微軟原裝字庫，未經 Windows 全表逐項比對。
- 沿用 0.6.19 固定簽名及學習紀錄，版本碼升至 27。

## 0.6.19 更新

- 開啟本機學習後，已收錄詞組及聯想字按選取次數調整；保留既有單字及英文學習紀錄。
- 新增 23 個香港日常詞組，保留原有詞語權重；未收錄整句及上文不保存。
- 由 0.6.19 起建立新固定簽名；Gradle 建置及 APK 驗證會再次核對，版本碼升至 26。首次由舊簽名轉換需要重新安裝，之後版本沿用新金鑰原位更新。

## 0.6.9 更新

- 手寫入口改為離線筆劃：橫、豎、撇、點／捺、折；＊可代替不確定的一筆。
- 輸入開頭筆劃即可揀字，支援繁體及香港用字、不同筆順、候選展開、退格及清除。
- 移除手寫模型及原生辨識庫，減少安裝大小；保留剪貼簿圓形按鈕及圓角卡片更新。
- 筆劃字碼只保留於當前輸入階段，離開輸入框時清除。

## 0.5.1 更新

- 按鍵觸碰範圍覆蓋完整格子，視覺上仍保留按鍵間距；候選區保留固定高度，減少輸入期間的位置變動。
- 連續速成整句／中英混合／錯碼搜尋移至背景，快速打字不需等待搜尋；舊字碼或舊輸入框的搜尋結果不會覆蓋新候選。
- 完整字庫詞句優先於臨時拼組的句子；首字候選緊接第一個整句推薦。帶「›」的候選只確認該字，後續字碼保留，亦保留「逐字」選取。
- 字根區掃動遊標需更明確的水平拖動，減少普通打字被當成遊標操作。

整句推斷仍是有限離線模型，未保證任意句子都能正確排序。Samsung/Fold 真機觸碰及快速雙手輸入仍需試用。

## 0.5.0 更新

- 中英混合分段候選，例如 `onaovrrovMcdonaldrh` →「今日食唔食Mcdonald呀」。中文碼和英文詞分開保留，英文大小寫不會自動改動。
- 已識別或指定的英文段，按空白鍵確認原詞並加入一個空格。英文補全及單次拼字修正由使用者選取才替換。有歧義可按候選列「英文／中文」指定該段；完成後恢復自動判斷。
- 工具列 ↶ 重新選字：還原最近一次完成的選字及原字碼。只在原輸入框、游標及文字仍然一致時可用；開始新輸入、改動或移動游標後停用。重選會撤回該次學習。
- 長按候選可分段改選，亦可在 ↶ 後按「分段改選」，只替換指定中文字或英文詞，其他部分保留。
- 參考上文排序候選（例如「開」後輸入 `oa` 優先提供「會」），上文不保存。
- 本機學習英文詞；設定支援新增自訂英文詞或中文詞字碼、刪除英文學習詞、管理及清除自訂詞／置頂候選。長按候選可置頂或取消置頂。
- 長按逗號／句號選常用標點。
- 速成一個相鄰按鍵錯碼的修正候選融合到同一列，長按可查看修正字碼，不取代正確配碼候選，不自動改字，可在設定停用。
- 在字根按鍵區左右掃動游標，保留空白鍵游標手勢；候選列仍用於橫向瀏覽。Shift／刪除保留自身長按操作。未選字碼會先保留為原字再移動游標。

中英文仍有字碼歧義，有限離線字詞模型不保證每句首選正確。分段改選限當前候選或最近一次可重選的輸入，不是任意舊文字的重新轉換。Samsung/Fold 真機及語音效果仍需試用確認。

## 0.4.0 更新

- 常用字預設排序使用 20,461 個單字頻率資料，並補充香港常用字優先次序；保留本機選字學習及全部冷門字。
- 連續速成按最多四字上文的離線五元字模型及詞組排序，兼顧香港口語和書面中文；`ofonaovrmrq` 首選「你今日食咗咩」。這是統計離線語言模型，不保證每句首選正確。
- 收起候選列可左右滑動瀏覽全部候選，保留空格翻頁及展開選字。
- 空白鍵使用置中線條圖示，保留無障礙說明及滑動游標。
- 咪掣直接呼叫手機的預設語音辨識服務，不需切換 Samsung Keyboard。首次需允許咪高峰，再返回輸入框按咪。中文模式請求廣東話 `yue-HK`，英文模式請求 `en-HK`；實際語言、離線與混合辨識能力取決於手機服務，未完成 Samsung/Fold 真機測試。
- 語音服務可能需要網絡及由供應商處理音訊；App 不保存錄音。離開輸入框、切換鍵盤或開始打字會取消收音，防止結果寫入其他輸入框。

## 0.2.0 更新

- **連續速成**：輸入 `ofvdrf` 可選「你好嗎」。原有 80,000 個詞組加上約 111,000 個粵語詞／片段，配合五元字模型組句，支援一碼字及不同長度字碼拆分。
- **逐字改選**：按「逐字」先選首字，餘下字碼保留。適合人名、口語或未收錄句子。
- **3,773 款 Emoji**：Unicode 15.1 fully-qualified 清單，包括膚色及組合款式；9 個分類、可捲動列表、最多 40 個最近使用記錄。可關閉或清除最近記錄。
- **灰底白鍵**：字根左上、英文字母下方，功能鍵較深；另有高對比深色模式。預設顯示數字列，空白鍵只有符號，沒有品牌字樣。
- **Fold 排列**：外屏緊湊排列，大螢幕可左右分體，中間留白對齊；可停用或選擇單手模式。
- App、設定頁、系統鍵盤清單名稱統一為「粵語中英混合keyboard」。

保留倉頡五代、基本英文補全、本機常選字排序、空白鍵滑動游標、長按刪除及 Shift 大寫鎖定。支援 Android 8.0（API 26）或以上。

## 安裝與試打

1. 解壓 GitHub Actions 的最新 APK ZIP，安裝當中的 `app-debug.apk`。
2. 開啟 App，按「啟用鍵盤」，在系統啟用。
3. 返回 App，按「選擇預設鍵盤」，選擇「粵語中英混合keyboard」。

| 字詞 | 速成碼 |
|---|---|
| 你好嗎 | `ofvdrf` |
| 你好 | `ofvd` |
| 香港 | `haeu` |
| 唔該 | `rryo` |
| 嗰 | `rr` |
| 嘅 | `ru` |
| 喺／嗎 | `rf` |

同碼可對應多個字，所以整句候選仍可能需要改選。候選列可左右捲動；超過 30 個候選可翻頁。中文段按空白鍵翻頁，「選字」選取本頁首個候選；英文段按空白鍵確認原詞及空格。候選列「英文／中文」指定當前段，工具列 ↶ 還原最近一次選字。

連續速成可於設定關閉。一次最多保留 48 個字母，達上限會先選當前首個候選再繼續輸入。Enter 遇到未完成字碼時先保留原字，再按才執行傳送／搜尋／換行。關閉鍵盤或切換模式時未選字碼亦保留為原文。

Samsung 設定一般為「設定 → 一般管理 → 鍵盤清單及預設」。若新舊測試 APK 簽章不同，需先卸載舊版再安裝，舊版學習記錄及設定會清除。

## 私隱與學習

字碼及候選可離線運作；App 沒有網絡權限、遙測或剪貼簿監控。語音由系統辨識服務處理，只有按咪後才收音，不保存錄音；服務供應商可能使用網絡。學習預設關閉；開啟後儲存單一中文字的字碼及次數（最多 2,000 筆）、已收錄中文詞組的選取次數（最多 1,000 詞），以及英文詞及次數（最多 500 詞）。詞組次數用於候選和聯想字排序，只學習內置詞庫中最長 8 字的詞組；上文及未收錄整句不保存。由新簽名的 0.6.19 起，往後相同簽名更新會沿用學習設定及紀錄。首次由舊簽名轉換未能保證保留資料。使用者自行新增的自訂詞及置頂候選另存（合共最多 500 筆），可個別刪除或清除全部。Emoji 記錄可另外關閉／清除。

密碼欄不顯示候選或學習；`IME_FLAG_NO_PERSONALIZED_LEARNING` 欄位不使用或更新學習／Emoji 記錄。資料排除於 Android 雲端備份及裝置轉移。

## Samsung AI

「AI 說明」提供 Writing Assist 系統使用步驟與鍵盤選擇器，**不是內置 AI**。沒有直接調用 Samsung 私有引擎。可在支援裝置選取文字後查看系統 Galaxy AI 選單，或切換 Samsung Keyboard。實際支援視 One UI、地區、帳戶與 App 而定，尚未在實體 Fold7／One UI 8.5 驗證。

## 建置

JDK 17、Android SDK 35、Build Tools 35.0.0；已含 Gradle 8.13 Wrapper。

```bash
./gradlew testDebugUnitTest lintDebug assembleDebug
```

Windows 使用 `gradlew.bat`，或用 Android Studio 開啟根目錄。設定 `ANDROID_HOME` 或 `local.properties` 的 `sdk.dir`。首次建置要下載依賴，打字可離線。APK 位於 `app/build/outputs/apk/debug/app-debug.apk`。GitHub Actions 會建置及上載 APK／報告。正式發佈應使用自己保存的 release signing key。

## 限制與驗證

連續速成使用有限搜尋及統計五元字語言模型，未包含大型神經網絡模型，不保證每句首選正確。英文使用內置常用詞及本機自訂／學習詞，支援補全及由使用者確認的單次拼字修正，未有完整字典或自動替換；未加入筆畫、拼音或倉頡擴展字庫。

Emoji 由系統字型顯示，舊 Android 可能缺少部分圖案。清單內複合 Emoji（膚色、國旗、家庭等）可整個刪除；Emoji 15.1 未收錄的新組合可能需多次刪除。

見 [BUILD_VERIFICATION.md](docs/BUILD_VERIFICATION.md) 及 [TESTING.md](docs/TESTING.md)。Android 模擬器不能代替 Samsung 真機驗證。

## 資料與授權

程式碼 GPL-3.0-or-later，見 LICENSE 及 [第三方署名](THIRD_PARTY_NOTICES.md)。

- rime/rime-cangjie：`52d90a1b1312e74042b38c1cbc8142defbc53171`。
- rime/rime-essay：`054920de4f54c9e5994276a96a4fc2a35cb51aa3`，加上本專案香港常用詞。
- Unicode Emoji 15.1，包含 Unicode 授權全文。

`tools/prepare_language_data.py` 可由上述版本的 `essay.txt` 與 `emoji-test.txt` 重建可閱讀的 TSV 資料，不需在 App 執行時下載。


### 0.6.0 source preview (no APK yet)

One candidate strip, with no separate code preview or repair strip. Candidates share plain text styling and broad tap areas; swipe horizontally or expand for more. The per-character selector is inside the expanded panel. Exact candidates retain their metadata when a repair produces the same text. Only repairs scoring substantially above the best exact sentence are promoted; the first exact choices stay ahead and repairs never silently change text.

The mode button can switch URI/browser fields from English to Chinese; editor restarts preserve the user's selection. Password and numeric fields retain their input policy.

The bundled model uses up to four preceding Han characters, stops at punctuation/English boundaries, and does not save context. Training sources, pinned revisions, source hashes and held-out probability evaluation are in `app/src/main/assets/MODEL_REPORT.json`; see `docs/OFFLINE_MODEL.md` for reproduction and limits.
