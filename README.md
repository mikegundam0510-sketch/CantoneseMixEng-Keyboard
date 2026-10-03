# 粵語中英混合keyboard

原生 Android 離線鍵盤，目標裝置為 Samsung Galaxy Z Fold7／One UI 8.5。

## 0.3.0 更新

以速成及中英混合為主，首次安裝預設關閉倉頡；已有使用者的輸入法設定保留。

- **展開全部候選**：點「展開」顯示可捲動選字網格；長按候選查各字的速成碼。長按展開鍵仍可換頁。
- **離線聯想詞**：選「你」後可點「好嗎」，只加入缺少的部分。前文只在記憶體，收起鍵盤、移動至不同前文或加入符號時清除，可關閉。
- **自訂短語**：於設定手動新增、修改或刪除最多 100 組快捷碼，如 `hk` → 香港。私人欄位不顯示。
- **英文補全及拼字建議**：198,308 字離線詞庫；中英混合及 EN 模式均可選英文候選。拼字建議要點選先替換；EN 模式空白鍵保留原字再加空格。
- **文字工具**：「工具」提供貼上、全選、複製、剪下、短語設定及 Samsung AI 說明；沒有剪貼簿監控或歷史。

功能範圍與下次接續記錄見 [FEATURE_SCOPE.md](docs/FEATURE_SCOPE.md)。尚未核實 Kaiboard 官方全部功能清單，並非宣稱完整複製其引擎或選字順序。

## 0.2.0 更新

- **連續速成**：輸入 `ofvdrf` 可選「你好嗎」。80,000 個離線詞組配合字頻組句，支援一碼字及不同長度字碼拆分。
- **逐字改選**：按「逐字」先選首字，餘下字碼保留。適合人名、口語或未收錄句子。
- **3,773 款 Emoji**：Unicode 15.1 fully-qualified 清單，包括膚色及組合款式；9 個分類、可捲動列表、最多 40 個最近使用記錄。可關閉或清除最近記錄。
- **灰底白鍵**：字根左上、英文字母下方，功能鍵較深；另有高對比深色模式。預設顯示數字列，空白鍵只有符號，沒有品牌字樣。
- **Fold 排列**：外屏緊湊排列，大螢幕可左右分體，中間留白對齊；可停用或選擇單手模式。
- App、設定頁、系統鍵盤清單名稱統一為「粵語中英混合keyboard」。

保留倉頡五代、基本英文補全、本機常選字排序、空白鍵滑動游標、長按刪除及 Shift 大寫鎖定。支援 Android 8.0（API 26）或以上。

## 安裝與試打

1. 安裝 `Cantonese-Mixed-Keyboard-0.3.0-debug.apk`。
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

同碼可對應多個字，所以整句候選仍可能需要改選。候選列可左右捲動，點「展開」可看全部候選；長按展開鍵翻頁。混合模式空白鍵選首個候選；「英文」保留整段原字碼。「中 · EN」切換純英文，EN 模式空白鍵保留原字再加空格。沒有輸入字碼時，空白鍵會加空格，不會自行選聯想詞。

連續速成可於設定關閉。一次最多保留 48 個字母，達上限會先選當前首個候選再繼續輸入。Enter 遇到未完成字碼時先保留原字，再按才執行傳送／搜尋／換行。關閉鍵盤或切換模式時未選字碼亦保留為原文。

Samsung 設定一般為「設定 → 一般管理 → 鍵盤清單及預設」。若新舊測試 APK 簽章不同，需先卸載舊版再安裝，舊版學習記錄及設定會清除。

## 私隱與學習

沒有網絡權限、遙測、錄音或剪貼簿監控，資料均內置。學習只儲存選取的單一中文字、字碼及次數，最多 2,000 筆。選整句時拆成單字學習，**不保存整句**。可停用及清除，Emoji 記錄可另外關閉／清除。

密碼欄不顯示候選或學習；`IME_FLAG_NO_PERSONALIZED_LEARNING` 欄位不使用或更新學習／Emoji 記錄。資料排除於 Android 雲端備份及裝置轉移。

自訂短語只儲存你手動新增的內容，不從編輯器自動收集文字；密碼及 `IME_FLAG_NO_PERSONALIZED_LEARNING` 欄位不顯示短語或聯想詞。工具的貼上／複製／剪下由你手動執行，沒有剪貼簿歷史。聯想詞的最近中文字只在記憶體，收起鍵盤時清除。

## Samsung AI

「工具 → Samsung AI 說明」提供 Writing Assist 系統使用步驟與鍵盤選擇器，**不是內置 AI**。沒有直接調用 Samsung 私有引擎。可在支援裝置選取文字後查看系統 Galaxy AI 選單，或切換 Samsung Keyboard。實際支援視 One UI、地區、帳戶與 App 而定，尚未在實體 Fold7／One UI 8.5 驗證。

## 建置

JDK 17、Android SDK 35、Build Tools 35.0.0；已含 Gradle 8.13 Wrapper。

```bash
./gradlew testDebugUnitTest lintDebug assembleDebug
```

Windows 使用 `gradlew.bat`，或用 Android Studio 開啟根目錄。設定 `ANDROID_HOME` 或 `local.properties` 的 `sdk.dir`。首次建置要下載依賴，打字可離線。APK 位於 `app/build/outputs/apk/debug/app-debug.apk`。GitHub Actions 會建置及上載 APK／報告。正式發佈應使用自己保存的 release signing key。

## 限制與驗證

連續速成是有限搜尋的離線字詞引擎，並非 AI 語言模型，不保證每句首選正確。聯想詞每個首字最多檢索 64 個高頻詞組，顯示最多 12 個後綴。英文是一般詞表補全與一個編輯距離的拼字建議，沒有語法檢查、語境模型或自動替換；未加入筆畫、拼音或倉頡擴展字庫。

Emoji 由系統字型顯示，舊 Android 可能缺少部分圖案。清單內複合 Emoji（膚色、國旗、家庭等）可整個刪除；Emoji 15.1 未收錄的新組合可能需多次刪除。

見 [BUILD_VERIFICATION.md](docs/BUILD_VERIFICATION.md) 及 [TESTING.md](docs/TESTING.md)。Android 模擬器不能代替 Samsung 真機驗證。

## 資料與授權

程式碼 GPL-3.0-or-later，見 LICENSE 及 [第三方署名](THIRD_PARTY_NOTICES.md)。

- rime/rime-cangjie：`52d90a1b1312e74042b38c1cbc8142defbc53171`。
- rime/rime-essay：`054920de4f54c9e5994276a96a4fc2a35cb51aa3`，加上本專案香港常用詞。
- Unicode Emoji 15.1，包含 Unicode 授權全文。
- Wordnik 英文詞表：MIT，`46e6215d0f90356afe9c8ba4be347e7e98cb425c`，保留完整署名與授權。

`tools/prepare_language_data.py` 可由上述版本的 `essay.txt` 與 `emoji-test.txt` 重建可閱讀的 TSV 資料，不需在 App 執行時下載。

`tools/prepare_english_data.py` 可由指定版本的 `wordlist-20210729.txt` 重建英文詞庫，會檢查來源 SHA-256。
