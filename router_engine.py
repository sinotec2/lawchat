from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.query_engine.router_query_engine import RouterQueryEngine, QueryEngineTool, ToolMetadata
from llama_index.core.selectors import LLMSingleSelector
from index_builder import build_index, wrt_yaml
from llama_index.llms.ollama import Ollama
from llama_index.core.retrievers import VectorIndexRetriever
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
embed_model = OllamaEmbedding(
        model_name="quentinz/bge-large-zh-v1.5:latest",
        dimensionality=768,
        request_timeout=360.0,
        num_workers=10,
        base_url="http://172.20.31.7:55083/",)
Settings.embed_model = embed_model

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

    from llama_index.packs.raptor import RaptorPack
    import nest_asyncio
    nest_asyncio.apply()
    from llama_index.llms.openai import OpenAI
    from llama_index.core.selectors.pydantic_selectors import (
        PydanticMultiSelector,
        PydanticSingleSelector,
    )

    from qdrant_client import QdrantClient, AsyncQdrantClient
    from llama_index.vector_stores.qdrant import QdrantVectorStore

    client = QdrantClient(host="localhost", port=6333)
    aclient = AsyncQdrantClient(host="localhost", port=6333)

    targets=["laws","summaries","keywords","graph"] 
    sources={i:i for i in targets[:3]}
    sources.update({"graph":"laws"})
    r=open_conn()
    redis_key = st.secrets["redis_key"]
    api_key = st.secrets["openai_key"]
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
        keys = yaml #list(r.scan_iter(pattern))
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
    vector_storeR={}
    engines=[]
    field_dir={"空氣污染相關法規":"air","環評、生態與噪音法規":"eia", "水質及水污染相關法規":"water","土壤、毒性物質與廢棄物相關法規":"sw",}
    names=field_dir.values()
    descriptions=field_dir.keys()
    for d in names:
        vector_storeR.update({d: QdrantVectorStore( client=client, aclient=aclient, collection_name=f"{d}_raptor")})
        engines.append(RetrieverQueryEngine.from_args(RaptorPack([],vector_store=vector_storeR[d],llm=llm,embed_model=embed_model).retriever,llm=llm))
    tools = [QueryEngineTool(
             query_engine=engine, 
             metadata=ToolMetadata(
                 name=name, 
                 description=description)
              ) for engine,name, description in zip(engines, names, descriptions)]
    engines=[index.as_query_engine(similarity_top_k=2) for index in indices]
    descriptions=[f"查詢{lawname}完整法條原文",f"查詢{lawname}-法條摘要",f"查詢{lawname}關鍵詞相關資訊",f"查詢{lawname}知識圖譜"]
    tools.extend([QueryEngineTool.from_defaults(engine, name=name, description=description) for engine,name, description in zip(engines,names,descriptions)])
    llm2 = OpenAI(model="gpt-4o-mini", api_key=api_key)
    #selector = PydanticMultiSelector.from_defaults(llm=llm2)
    selector = PydanticSingleSelector.from_defaults(llm=llm2)
    engine = RouterQueryEngine(
        selector=selector, #LLMSingleSelector.from_defaults(llm=llm),
        query_engine_tools=tools,
        llm=llm
        )
    #retriever = VectorIndexRetriever(index=index, filters={"article": "第5條"})
    return engine

def init_graph_engine(username,lawname):
    from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore 
    from llama_index.core import Document, PropertyGraphIndex
    from llama_index.core.indices.property_graph import DynamicLLMPathExtractor

    from llama_index.core.indices.vector_store import VectorStoreIndex
    from llama_index.core import StorageContext
    from index_builder import load_documents
    import streamlit as st

    targets=["laws","summaries","keywords","graph"] 
    sources={i:i for i in targets[:3]}
    sources.update({"graph":"laws"})

    password = st.secrets["redis_key"]
    graph_store = Neo4jPropertyGraphStore(
       username="neo4j",
       password=password,
       url="bolt://172.20.31.1:7687",
       database=lawname  # 這裡才是指定namespace
    )

    kg_extractor = DynamicLLMPathExtractor(
         llm=llm,
         max_triplets_per_chunk=20,
         num_workers=4,
         allowed_entity_types=None,
         allowed_relation_types=None,
         allowed_relation_props=[],
         allowed_entity_props=[],
    )

    t='graph'
    s=sourcesC[t]
    yaml=f'data/{username}/envlaws-{t}.yaml'
    res=wrt_yaml(yaml,f"{lawname}-{t}")
    fname=f"data/{username}/{s}.json"    
    documents = load_documents(fname)
    index = PropertyGraphIndex.from_documents(
        documents,
        llm=llm,
        embed_model=embed_model,
        embed_kg_nodes=True,
        kg_extractors=[kg_extractor], 
        property_graph_store=graph_store,
    show_progress=True,
    )
    return engine
