from llama_index.core import VectorStoreIndex, Document
import json

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core import StorageContext,load_index_from_storage

def ollama_settings():
    from llama_index.llms.ollama import Ollama
    from llama_index.embeddings.ollama import OllamaEmbedding
    Settings.llm = Ollama(model="llama3.1:latest", request_timeout=360.0, base_url="http://l40.sinotech-eng.com:55083/",
        temperature=0.2,
        system_prompt="""You are an expert on
        the environmental engineering and your
        job is to answer technical questions.
        Assume that all questions are related
        to the environmental engineering. Keep
        your answers technical and based on
        facts – do not hallucinate features.
        Answer questions in tradition chinese.
        """,
        )
    Settings.embed_model = OllamaEmbedding(
        model_name="nomic-embed-text:latest",
        dimensionality=768,
        request_timeout=360.0,
        base_url="http://l40.sinotech-eng.com:55083/",)
    return True

def load_documents(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    docs = [Document(text=item["text"]) for item in data] #所有訊息
    docs = [Document(text=item["text"], metadata=item.get("metadata", {})) for item in data] #取得metadata
    return docs

def build_index(json_path):
    docs = load_documents(json_path)
    return VectorStoreIndex.from_documents(docs)

def wrt_yaml(yaml,lawname):
    col=['id','chapter', 'article', 'item', 'clause', 'points','LawName','parentname','LawDate','fullpath','doc_id']
    with open(yaml,'w') as f:
        f.write(f"index:\n  name: {lawname}\n  prefix: {lawname}/vector\n  key_separator: _\n  storage_type: hash\n")
        f.write(f"fields:\n")
        for c in col:
            f.write(f"- name: {c}\n  type: tag\n  attrs:\n    sortable: false\n")
        f.write(f"- name: text\n  type: text\n  attrs:\n    sortable: false\n")
        f.write(f"- name: vector\n  type: vector\n  attrs:\n    dims: 768\n    algorithm: hnsw\n    datatype: float32\n    distance_metric: cosine\nversion: 0.1.0\n")
    return True

def build_save(json_path):

    from llama_index.core import SummaryIndex
    from llama_index.core import SimpleKeywordTableIndex
    from llama_index.storage.docstore.redis import RedisDocumentStore
    from llama_index.storage.index_store.redis import RedisIndexStore
    from llama_index.core.node_parser import HierarchicalNodeParser
    from llama_index.vector_stores.redis import RedisVectorStore
    from redisvl.schema import IndexSchema

    from redis import Redis
    parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[2048, 1024, 512, 256,], chunk_overlap=64)
    redis_key = st.secrets["redis_key"]
    REDIS_HOST=f"default:{redis_key}@172.20.31.1"
    redis_client = Redis.from_url(f"redis://{REDIS_HOST}:6379")
    username=json_path.split('/')[1]
    yaml=f'data/{username}/envlaws.yam'

    docs=load_documents(json_path)
    lawname=docs[0].metadata[ 'LawName']
    res=wrt_yaml(yaml,lawname)
    vector_store = RedisVectorStore(schema=IndexSchema.from_yaml(yaml),redis_client=redis_client, overwrite=True)
    REDIS_PORT=6379
    storage_context = StorageContext.from_defaults(
            docstore=RedisDocumentStore.from_host_and_port(
                host=REDIS_HOST, port=REDIS_PORT, namespace=lawname
            ),
            index_store=RedisIndexStore.from_host_and_port(
               host=REDIS_HOST, port=REDIS_PORT, namespace=lawname
            ),
            vector_store=vector_store,
               )
    nodes = parser(docs)
    vector_index = VectorStoreIndex(nodes, storage_context=storage_context)
    keyword_table_index = SimpleKeywordTableIndex(
            nodes, storage_context=storage_context)
    summary_index = SummaryIndex(nodes, storage_context=storage_context)
    storage_context.docstore.add_documents(nodes)
    vector_index.set_index_id(lawname)


    return vector_index
