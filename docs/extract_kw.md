# extract_kw.py

## 背景說明

感謝你提供完整程式碼！以下是我對這段程式的 整體功能說明與邏輯架構整理，幫助你確認其運作與是否有可優化之處：

⸻

## 程式說明

### 整體目的：

這段程式的主要目的是建構一個法規查詢推薦系統，從本地資料夾中匯總法規的中英文名稱、章節條文等欄位，並提供自然語言模糊查詢與推薦，整合後輸出成特定格式供後續應用（如向量搜尋、聊天互動等）。

⸻

### 模組拆解與功能：

1. 初始化與關鍵字資料建構

`jieba.load_userdict('air_dict.txt')`

- 載入自訂斷詞字典，提升關鍵詞切分精度。

`def make_pools(folder_path):`

- 目的：建立法規欄位池 (`metadata_pool`) 與關鍵詞池 (`keyword_pool`)
- 從 JSON、CSV 中提取欄位值（如法規名稱、章節、條文、附件）建構集合。
- 結果回傳：

```js
metadata_pool: {
    "parentname": {...},
    "chapter": {...},
    "article": {...},
    "attachment": {...},
    "LawName": {...},
}

keyword_pool: [...從斷詞字典取出詞條首詞...]
```


⸻

2. 輸入正規化與模糊比對工具

```python
def convert_chinese_numerals(text)
def normalize(text)
def suggest_keywords(user_input, keyword_pool, ...)
```

- 中文數字轉換：「第五條」變「5條」等。
- 符號/空格正規化：提升比對準確度。
- suggest_keywords：用 rapidfuzz 模糊比對 normalized 詞條與關鍵詞池，找出近似詞或完全包含的詞。

⸻

3. 輸入查詢詞解析與對應欄位值推論

`def extract_keywords_from_query(query, metadata_pool, keyword_pool, topn=3)`

- 步驟說明：
	1.	斷詞（用 jieba + 停用詞過濾）
	2.	每個詞用 suggest_keywords 模糊找可能關鍵詞
	3.	把推薦詞與 metadata_pool 中的各欄位做模糊包含比對
	4.	回傳可能的匹配欄位值，格式如下：

```js
{
  "article": ["第5條"],
  "attachment": ["放流水標準表"]
}
```

⸻

4. 特定法規選取後的資料轉換（法規節點→欄位向量格式）

`def select_law(fixed_path, lawname, username)`

- 將特定法規（以 lawname.json 與 lawname.csv 表示）轉換為三類資料：
- 條文全文：`laws.json`
- 條文摘要：`summaries.json`
- 條文關鍵詞：`keywords.json`
- 結構範例：

```js
{
  "text": "第5條 放流水標準",
  "metadata": {
    "chapter": "第2章 排放標準",
    "item": "item內容",
    "article": "第5條",
    ...
  }
}
```

⸻

5. 資料結構展平與法規名取得

```python
def get_lnames(in_laws)
def get_lname(json_name, src_dir)
```

- 用來攤平 nested 的法規資料結構，方便查找法規清單。
- 若本地無對應 JSON 則從來源資料夾自動補齊。

⸻

6. 法規目錄結構定義

`def laws_dict()`

- 以巢狀 dict 方式定義法規分類、子分類、法規名稱。
- 目前支援：空污相關、室內空氣品質、固定污染源、移動污染源、特殊行業、環評、生態與噪音等。

⸻

### 系統整體流程圖

```bash
          使用者輸入查詢
                   |
        ------------------------
        |                      |
 jieba 斷詞 + 停用詞過濾     使用者點選法規
        |                      |
 模糊推薦關鍵詞 (rapidfuzz)   select_law(lawname)
        |                      |
 關鍵詞對應 metadata 欄位     -> 建立 laws.json, summaries.json 等
        |                      |
   擷取章/條/附件等元素        |
        |                      |
    回傳建議查詢 metadata      |
```

⸻

### 優化建議：

	1.	`extract_keywords_from_query()` 中 matched 過濾過於保守

`if (len(exact)==0 or len(excat)>5) ...`

- excat 應為 exact，且邏輯判斷可調整為更清楚的匹配策略（例如 confidence score）。

	2.	select_law 的欄位處理順序可以簡化
- 目前程式多次重複將 metadata 套入各欄位，建議可封裝成獨立函數以提升維護性。
	3.	keyword_pool 應考慮去除重複與空值

```python
keyword_pool=[i.split()[0] for i in f if i.strip()]
```

	4.	加強中文數字轉換支援更多結構（如「十一」、「二十」等）
- 可改為更完整的中文數字 parser 或用 cn2an 套件。

⸻
