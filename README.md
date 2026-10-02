# Kaiboard Android

為 Android / Samsung 手機開發的原生離線鍵盤，操作概念參考 [Kaiboard](https://kaiboard.app/)。這是獨立實作，並非 Kaiboard 或 Samsung 官方產品，沒有使用其私有程式碼或品牌圖像。

## 第一版功能

- **速成預設開啟**：由倉頡五代基礎碼表產生首尾碼，可橫向滑動及翻頁選字。
- **倉頡＋速成＋英文混合候選**：三者可獨立開關；保留原英文輸入的按鈕一直可用。
- **本機選字學習**：同一字碼及輸入法組合中，常選中文字優先；可停用及清除。
- 內置常用 Emoji、數字與標點、系統／深／淺主題、左／右單手模式、按鍵高度與數字列設定。
- **Fold 大螢幕排列**：可用寬度達 600dp 時字母列自動分體，外屏維持正常排列；可停用，單手模式時亦不分體。目標裝置為 Galaxy Z Fold7／One UI 8.5，仍需實機驗證。
- 空白鍵左右滑動移動游標、長按刪除、長按 Shift 鎖定大寫。
- 依輸入欄顯示搜尋／傳送／完成鍵；密碼欄不顯示候選字、不學習。
- **Samsung AI 說明入口**：說明系統文字選取選單的 Writing Assist，並可開啟鍵盤選擇器。

## 安裝

支援 Android 8.0（API 26）以上。Samsung One UI 實機仍需驗證。

1. 安裝 `Kaiboard-Android-0.1.0-debug.apk`。
2. 開啟 **Kaiboard Android**，按「啟用 Kaiboard」，在系統開啟此鍵盤。
3. 返回 App，按「選擇預設鍵盤」，選擇 Kaiboard Android。
4. 在試打欄或其他 App 輸入：`of → 你`、`vd → 好`、`ha → 香`、`eu → 港`。

Samsung 設定位置通常為「設定 → 一般管理 → 鍵盤清單及預設」。啟用第三方鍵盤時 Android 會顯示系統標準提示。

### 混合輸入方式

- 預設速成候選優先，其次為倉頡，再加入基本英文補全。相同字不重複顯示。
- 點中文字即上屏；空白鍵選第一個候選字。要保留英文，點選候選列左方 **英文／原字碼**。
- 點工具列「混合」切換成純英文。網址／電郵欄預設純英文。
- 有超過 30 個候選字時，按右側頁碼箭嘴翻頁；每頁可橫向捲動。
- 學習只記錄選中的單一中文字、字碼、模式及次數，最多 2,000 筆；同次數保持字庫原排序。
- 鍵盤關閉時，尚未選字的字碼會以原文字保留，不自動猜字。
- Enter 有未完成字碼時先保留原字；再按一次才執行搜尋／傳送／換行。

## Samsung Galaxy AI

此專案**沒有內置或直接調用 Samsung Writing Assist API**。工具列的「AI 說明」會顯示使用步驟。

支援 Galaxy AI 的 One UI 7 或以上裝置可能可在長按選取文字後，經系統選單啟用 Writing Assist。功能因裝置、地區、帳戶、語言及使用中的 App 而異；若未見選項，可切換到 Samsung Keyboard 使用其 AI 功能。這不是所有 Samsung 裝置都可用的承諾。

參考：[Samsung One UI 更新說明](https://doc.samsungmobile.com/SM-S711B/028494231223/wel.html)／[Samsung Writing Assist](https://www.samsung.com/us/support/answer/ANS10000943/)。

## 建置 APK

使用 JDK 17、Android SDK 35、Build Tools 35.0.0、Gradle 8.13。Gradle Wrapper 已包含。

```bash
./gradlew testDebugUnitTest lintDebug assembleDebug
```

Windows：

```bat
gradlew.bat testDebugUnitTest lintDebug assembleDebug
```

用 Android Studio 開啟根目錄亦可建置。設定 `ANDROID_HOME`，或在本機 `local.properties` 設定 `sdk.dir`。首次建置需要下載依賴；**安裝後鍵盤打字不需要網絡**。

APK：`app/build/outputs/apk/debug/app-debug.apk`。Debug APK 用於測試；正式發佈需使用自己保存的 release signing key。不同環境的 debug key 不同，如出現簽章不符，需先移除舊版（會清除本機學習記錄）或使用相同簽章重新建置。

GitHub Actions 在 push／pull request 後執行測試、Lint、建置，並上載 APK 與測試結果。

## 私隱

- Manifest 沒有 `INTERNET`、剪貼簿監控、錄音或無障礙服務權限。
- 不紀錄整段輸入文字，沒有分析服務或遙測。
- 開啟本機學習時，只保留被選取的中文字及字碼次數；關閉學習會停止使用／更新資料，清除按鈕可刪除資料。
- 密碼欄與 `IME_FLAG_NO_PERSONALIZED_LEARNING` 欄位不讀取或寫入學習資料。
- `allowBackup=false`，設定與學習記錄不參與 Android 備份。
- Samsung AI 的帳戶、連線及資料處理由 Samsung 功能本身管理。

## 範圍與限制

這是可建置的初版，並非原版 Kaiboard 全功能移植。英文是約二百字的基本前綴補全，沒有 AI、自動糾錯或完整英文字典。中文採用基礎單字碼表，沒有詞組聯想、倉頡擴展字庫、筆畫或拼音輸入。速成次序不保證與 Windows／iOS／Samsung 相同，學習可調整常選字優先次序。Emoji 為常用清單，刪除按 Unicode code point 處理，複合 Emoji 可能要按多次。

自動測試覆蓋實際字庫的完整速成映射、已知字、混合輸入、去重、英文大小寫及學習排序。裝置上的鍵盤互動仍需依 [手動測試清單](docs/TESTING.md) 驗證，尤其 Samsung 導航列、摺疊屏及 Galaxy AI 選單。

## 字庫及授權

字庫來自 [rime/rime-cangjie](https://github.com/rime/rime-cangjie)，固定版本 `52d90a1b1312e74042b38c1cbc8142defbc53171` 的 `cangjie5.base.dict.yaml`，原檔保留。首尾碼索引於啟動時在記憶體生成，碼表內容沒有修改。

字庫檔標註 GPL，上游 repository 同時包含 LGPL-3.0 及 AUTHORS；原署名與兩份授權全文均包含在 App 與原始碼。此專案新程式碼採 GPL-3.0-or-later；見 `LICENSE` 及 `THIRD_PARTY_NOTICES.md`。原始碼 ZIP 可重新建置整個 App。
