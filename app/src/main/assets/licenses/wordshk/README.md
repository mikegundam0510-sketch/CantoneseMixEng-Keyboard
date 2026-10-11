# words.hk 粵典：公開詞表及頻率匯出

來源頁：<https://words.hk/faiman/analysis/>。用戶於 2026-10-11 提供該頁 HTML 及三份 JSON 匯出；程式未能直接連線 words.hk。

該頁在 character usage frequency、word frequency list、words.hk word list 各段明確寫明：

> Data License: public domain. Credits to words.hk appreciated.
> 授權：公有領域。

本專案致謝 words.hk 粵典，採用這三項公開匯出。來源 URL、原始檔 SHA-256、篩選方式、匯入數量及限制見 `SOURCE.json`。

此授權說明只涵蓋上述資料集。文章總覽頁寫明開放資料政策不包括粵文庫文章；本次未匯入文章全文、完整詞典釋義或例句，也未用工具程式的授權代替資料授權。

重現：保留三份符合記錄 SHA-256 的原始 JSON，從專案根目錄執行：

```
python3 tools/import_wordshk.py /path/to/charcount.json /path/to/existingwordcount.json /path/to/wordslist.json
```

重跑會先移除自己產生的補充段再重建，保留原有字碼及較高詞權重。詞頻以未斷詞的書面語料計數，不代表當代香港人聊天機率；未出現的詞不等於無效，字頻調整不移除任何字庫項目。
