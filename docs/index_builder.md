# index_builder

## 背景說明

這支程式主要用於 將環保法規的 JSON 資料進行嵌入、向量化處理，並儲存到 Redis 資料庫中，以支援後續的語意查詢與分析。下面是完整的功能與設計說明：

⸻

## 程式說明

### 一、匯入相關套件

from llama_index.core import VectorStoreIndex, Document, ...
import json

	•	使用 llama-index 處理文件建構、索引、嵌入、儲存與查詢。
	•	使用 redisvl 與 redis 套件進行 Redis-based 向量儲存與索引。

⸻

### 二、ollama_settings()

def ollama_settings():
    ...

	•	設定 LLM 與嵌入模型（Embedding Model）：
	•	LLM： llama3.1，設定提示語為「你是環境工程專家…」，強制以繁體中文技術回答。
	•	Embedding： quentinz/bge-large-zh-v1.5，支援中文理解。
	•	指定本機 Ollama API (base_url="http://172.20.31.7:55083/")。

⸻

### 三、load_documents(json_path)

def load_documents(json_path):
    ...

	•	從 JSON 檔讀入資料（text 及 metadata）。
	•	回傳 Document 物件清單，可用於後續建構索引。

⸻

### 四、build_index(json_path)

def build_index(json_path):
    ...

	•	建立基本的 VectorStoreIndex，不含儲存機制，適合測試用。

⸻

### 五、wrt_yaml(yaml, lawname)

def wrt_yaml(yaml, lawname):
    ...

	•	寫入 Redis 向量索引的 YAML schema：
	•	欄位包含：chapter, article, item, clause, points, LawName, text, vector 等。
	•	向量資料（vector）使用 HNSW、float32、cosine similarity。
	•	schema 是 Redis 向量搜尋的核心設定。

⸻

### 六、build_save(json_path)

def build_save(json_path):
    ...

## 步驟說明：

	1.	初始化
	•	使用者名稱 username 從路徑推斷。
	•	根據 json_path 建立 YAML schema 文件。
	2.	Redis 連線

redis_key = st.secrets["redis_key"]
REDIS_HOST = f"default:{redis_key}@172.20.31.1"
redis_client = Redis.from_url(...)

	•	使用密鑰連接 Redis 伺服器。
	•	指定 Redis host、port、namespace。

	3.	建立 Redis 向量儲存與索引空間

vector_store = RedisVectorStore(...)
storage_context = StorageContext.from_defaults(...)

	•	向量索引 (RedisVectorStore) 使用剛寫好的 YAML schema。
	•	文件儲存 (RedisDocumentStore) 與索引儲存 (RedisIndexStore) 分別指定命名空間（以 LawName 作為 key）。

	4.	切割文件（chunking）

parser = HierarchicalNodeParser.from_defaults(...)
nodes = parser(docs)

	•	將大型文件切成 2048、1024、512、256 token 的階層式段落，以利精準查詢。

	5.	建立多種索引

vector_index = VectorStoreIndex(...)
keyword_table_index = SimpleKeywordTableIndex(...)
summary_index = SummaryIndex(...)

	•	建立三種索引：
	•	向量索引：語意搜尋用。
	•	關鍵字索引：關鍵詞查詢。
	•	摘要索引：快速摘要（可選）。

	6.	儲存與回傳

storage_context.docstore.add_documents(nodes)
vector_index.set_index_id(lawname)
return vector_index

	•	將處理後的 nodes 儲存進 Redis。
	•	設定向量索引的 ID 為 lawname，便於後續呼叫與查詢。

⸻

## 結語：應用場景

這段程式碼整合了：
	•	文件讀取與轉換（JSON to Document）
	•	使用 Ollama LLM 與中文嵌入模型進行向量處理
	•	分段切割（chunking）
	•	多樣化索引結構（語意、關鍵字、摘要）
	•	儲存至 Redis（向量搜尋 + 資料持久化）

可應用於：
	•	法規查詢系統
	•	語意檢索平台
	•	環保法條智能問答

如需整合 Streamlit 或建立查詢介面，我也可以幫你擴充。需要嗎？