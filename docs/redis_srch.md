# redis_srch

## 背景說明

這段程式碼是用 Streamlit + Redis Stack（含 RedisSearch） 建立的法律條文全文搜尋模組，主要包含：
	•	Redis 索引建立（全文檢索用）
	•	使用 jieba 中文斷詞
	•	Redis Search 查詢條文
	•	返回查詢結果

⸻
## 程式說明

### 一、模組匯入與連線設定

import streamlit as st
import ast, os, pandas as pd, jieba
from redis import Redis
from redis.commands.search.query import Query
from redis.commands.search.field import TextField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

功能說明：
	•	jieba：中文斷詞
	•	redis.commands.search.*：Redis Stack 搜尋索引功能
	•	Streamlit：網頁介面前端
	•	ast：字串轉成 Python 結構（備用）

⸻

二、Redis 連線函數

def open_conn():
    if 'r' not in st.session_state:
        redis_key = st.secrets["redis_key"]
        REDIS_HOST = f"default:{redis_key}@172.20.31.1"
        st.session_state.r = Redis.from_url(f"redis://{REDIS_HOST}:6379", db=0, decode_responses=True)
    return st.session_state.r

功能說明：
	•	從 Streamlit 的 secrets.toml 中取得 Redis 密碼。
	•	初始化 Redis，並存在 st.session_state，避免重複連線。

⸻

### 三、建立 Redis Search 索引

def create_law_index_if_not_exists():
    r = open_conn()
    idx_lst = r.execute_command("FT._LIST")
    if "law_index" not in idx_lst:
        try:
            r.ft("law_index").create_index([
                TagField("lawname"), 
                TextField("code"),
                TextField("code_seg"),
                TextField("keywords"),
                TextField("abstract")
            ], definition=IndexDefinition(prefix=["law:"], index_type=IndexType.HASH))
            print("law_index 建立完成")
        except:
            print("law_index 建立失敗")
            return False
    return True

功能說明：
	•	建立名為 law_index 的 Redis 全文索引（使用 Redis Stack）。
	•	索引的欄位有：
	•	lawname：法規名稱（Tag 欄位）
	•	code：條文原始內容
	•	code_seg：條文分詞（可用於斷詞查詢）
	•	keywords：關鍵詞集合
	•	abstract：條文摘要
	•	若已存在索引則略過。

⸻

### 四、單詞查詢條文（全文檢索）

def single_srch(s, regset):
    law_tag_str = " | ".join([f"{name}" for name in regset])
    q = Query(f"@lawname:{{ {law_tag_str} }} @code_seg:{s}").paging(0, 1000)
    ...
    res = r.ft("law_index").search(q)

功能說明：
	•	根據使用者輸入的字詞 s，在 code_seg 欄位中搜尋。
	•	限定只查詢在指定的法規集合 regset 中的資料（用 @lawname:{...} 限制）。
	•	高亮顯示查詢字詞（以紅色 span 標註）【程式雖標註但未實際回傳 highlighed 文本】。
	•	回傳符合的 Redis key IDs。

⸻

### 五、整體查詢主函式（斷詞 + 多次查詢）

def code_retrieval(input_str, regset):
    str_lst = jieba.lcut(input_str)
    result_lst = []
    for s in str_lst:
        result_lst += single_srch(s, regset)
    return result_lst

## 功能說明：
	•	將輸入字串 input_str 用 jieba 進行中文斷詞。
	•	對每個詞分別執行查詢（single_srch）。
	•	回傳所有條文 ID 清單。

⸻

## 結構總覽：

函式名稱	功能
open_conn()	建立 Redis 連線
create_law_index_if_not_exists()	建立 Redis 全文索引（若尚未存在）
single_srch(s, regset)	查詢特定詞出現的條文
code_retrieval(input_str, regset)	對輸入字串做斷詞並查詢條文


⸻

## 建議補強功能
	•	結果排序（例如依照相關度、條文順序）
	•	限制查詢結果筆數、分頁機制
	•	加入條文內容（而非只傳回 ID）
	•	支援多詞合併查詢（ex. "空氣 污染" 而非逐字拆開）

需要我幫你整合這段搜尋模組到一個 Streamlit 頁面介面上嗎？或者你要做更進一步的說明（例如圖形化查詢流程）？