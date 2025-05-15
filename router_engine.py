from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine, QueryEngineTool
from llama_index.core.selectors import LLMSingleSelector
from index_builder import build_index, wrt_yaml
from llama_index.llms.ollama import Ollama
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.ollama import OllamaEmbedding

from llama_index.core import SimpleDirectoryReader, Settings
model = "llama3.1:latest"
model = "mistral:latest"
llm = Ollama(model=model, request_timeout=360.0, base_url="http://172.20.31.7:55083/",
        temperature=0.0,
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
Settings.llm = llm
#        model_name="nomic-embed-text:latest",
Settings.embed_model = OllamaEmbedding(
        model_name="quentinz/bge-large-zh-v1.5:latest",
        dimensionality=768,
        request_timeout=360.0,
        num_workers=10,
        base_url="http://172.20.31.7:55083/",)

def init_router_engine(username,lawname):
    from llama_index.core import Document, PropertyGraphIndex
    from llama_index.core.indices.property_graph import DynamicLLMPathExtractor
    from llama_index.vector_stores.redis import RedisVectorStore
    from llama_index.storage.docstore.redis import RedisDocumentStore
    from llama_index.storage.index_store.redis import RedisIndexStore

    from llama_index.core.indices.vector_store import VectorStoreIndex
    from llama_index.core import StorageContext
    from redisvl.schema import IndexSchema
    from redis_srch import open_conn
    from index_builder import load_documents
    import streamlit as st

    targets=["laws","summaries","keywords","graph"] 
    sources={i:i for i in targets[:3]}
    sources.update({"graph":"laws"})
    r=open_conn()
    redis_key = st.secrets["redis_key"]
    REDIS_HOST=f"default:{redis_key}@172.20.31.1"
    REDIS_PORT=6379
    kg_extractor = DynamicLLMPathExtractor(
         llm=llm,
         max_triplets_per_chunk=20,
         num_workers=4,
         allowed_entity_types=None,
         allowed_relation_types=None,
         allowed_relation_props=[],
         allowed_entity_props=[],
     )

    indices=[]
    for t,s in sources.items():
        pattern = f"{lawname}-{t}*"
        yaml=f'data/{username}/envlaws-{t}.yaml'
        res=wrt_yaml(yaml,f"{lawname}-{t}")
        keys = list(r.scan_iter(pattern))
        if len(keys)>3 :
            vector_store = RedisVectorStore(schema=IndexSchema.from_yaml(yaml),redis_client=r, overwrite=False)
            indices.append(VectorStoreIndex.from_vector_store(vector_store))
        else:
            vector_store = RedisVectorStore(schema=IndexSchema.from_yaml(yaml),redis_client=r, overwrite=True)
            namespace=f"{lawname}-{t}"
            storage_context = StorageContext.from_defaults(
                docstore=RedisDocumentStore.from_host_and_port(
                    host=REDIS_HOST, port=REDIS_PORT, namespace=namespace),
                index_store=RedisIndexStore.from_host_and_port(
                    host=REDIS_HOST, port=REDIS_PORT, namespace=namespace),
                vector_store=vector_store,)
            fname=f"data/{username}/{s}.json"    
            docs = load_documents(fname)
            if t in targets[:3]:
                index = VectorStoreIndex.from_documents(docs, storage_context=storage_context)
            elif t=='graph':
                index = PropertyGraphIndex.from_documents(docs,llm=llm,embed_kg_nodes=False,kg_extractors=[kg_extractor], storage_context=storage_context,show_progress=True,)
            indices.append(index)
    engines = [index.as_query_engine(similarity_top_k=3) for index in indices]
    descriptions=["查詢完整法條原文","查詢法條摘要","查詢關鍵詞相關資訊","查詢知識圖譜"]
    eng_des={e:d for e,d in zip(engines,descriptions)}
    tools = [QueryEngineTool.from_defaults(engine, description=description) for engine,description in eng_des.items()]
    engine = RouterQueryEngine(
        selector=LLMSingleSelector.from_defaults(llm=llm),
        query_engine_tools=tools,
        llm=llm
        )
    #retriever = VectorIndexRetriever(index=index, filters={"article": "第5條"})
    #engine = RetrieverQueryEngine(retriever=retriever, llm=llm)
    return engine
