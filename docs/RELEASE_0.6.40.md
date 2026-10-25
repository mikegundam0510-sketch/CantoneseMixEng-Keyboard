# CantoneseMixEng Keyboard 0.6.40

VersionCode 47；Android 8.0+；沿用 applicationId `hk.kaiboard.android`、舊輸入法入口及
0.6.19 起固定簽名，適合覆蓋現有同簽名版本。不要先移除 App 或清除資料。

## 頂字後還原

第三碼頂字後，按一次刪除可將最近一次自動上屏的字還原為原碼，保留後面已輸入的碼。
例如個人排序令 `of` 頂成「係」，打入下一碼 `z` 後，`係z` 可一鍵還原成 `ofz`。
多個完整兩碼及單碼尾段一起處理；Unicode 擴充字使用 Android 的 UTF-16 位置。
原有 ↶ 重選操作亦可呼叫相同還原流程。還原後暫停該段頂字，讓使用者改碼或選字；
確認候選、開始新的輸入段或切換輸入欄後恢復正常。還原本身不增加或懲罰個人學習。

只有游標、原有文字及正在輸入的碼仍吻合，才替換自動上屏段和後面未確認碼。
先標記完整組字區再一次替換；不先刪除文字。輸入欄拒絕標記／替換時保留文字，
同一次刪除不會再退回普通刪字操作。沒有可靠位置、游標移開、選取文字或內容已改時，
不還原其他位置的文字。記錄只留在目前輸入工作階段，沒有新增持久儲存或網絡權限。

## 隨本版提供的字詞輸入

上一輪未發佈的字詞候選及同碼學習亦包含在本 APK：
第三碼頂字預設開啟，字庫常用詞、已學詞及英文前綴保留等選；自動砌句預設關閉。
學習沿用原有開關（預設關閉），只計確認的字詞，不將單字選擇串成整句。
加入 KINFX／rime-cantonese 篩選的 504 個新增詞，保留原生拆碼及來源授權。
完整倉頡請關閉頂字或速成。詳見 [字詞輸入](WORD_USAGE_INPUT.md)。

## 驗證

- 完整 267 項 JVM 單元測試通過，0 失敗／0 跳過；包含 10 項新增服務層還原測試。
- Lint 0 錯誤／25 警告，debug、Android 測試包及 release 建置通過。
- Android 12 軟件模擬器：21 項原生文字欄還原、空白鍵游標、升級識別及私隱測試通過。
  最終還原測試使用原生 EditText／EditableInputConnection，避免依賴視窗啟動與動畫，
  已對真正 release 包再驗證；服務操作另由 JVM 的編輯器協定測試覆蓋。
- 最終下載用 release APK 成功覆蓋安裝，18 項 Android 還原、識別、私隱及實際資料保留測試全部通過。
  五個實際設定／學習檔案再次核對一致。輸入法選擇在安裝後、啟動 instrumentation 前核對；
  instrumentation 會停止目標 App，之後的系統暫時切換不當作安裝資料流失。
- 同一模擬器先以 `adb install -r` 從固定簽名 0.6.39／46 更新至 0.6.40／47 debug，
  五個實際設定／學習 XML 檔案的 SHA256 全部一致，系統選用輸入法保持不變。
- APK、內部 debug／測試包及 0.6.39 基線皆通過固定簽名驗證，並核對 package／版本碼。

未使用 Fold7 或第三方通訊 App 實機驗證；以上不代表整句命中率、手機延遲或版面已全面驗收。
GitHub Release API 在本雲端回覆 Forbidden；本次提供已簽名 APK 檔案，不宣稱已建立 GitHub Release。

本機產物：`dist/0.6.40/CantoneseMixEng-Keyboard-0.6.40.apk`，校驗檔 `SHA256SUMS.txt`。
大小 12,525,150 bytes，SHA256：
`1a1938a638c9c24f5992d7ec09726996dde7c34fb553080743f496c5ecacb3fd`。
APK 內版本控制資料記錄來源提交 `6b88690f9e242dac60209167c4d5fb4e9bcd72b5`。
完整摘要見 [驗證報告](../tools/reports/release-0.6.40.json)。
重現建置需沿用保留的持久金鑰設定，再執行：

```sh
source /workspace/android-environment/activate.sh
KAI_REQUIRE_STABLE_SIGNING=true ./gradlew --offline --no-daemon --max-workers=2 \
  testDebugUnitTest lintDebug assembleDebug assembleDebugAndroidTest assembleRelease
python tools/verify_apk_signing.py app/build/outputs/apk/release/app-release.apk
```
