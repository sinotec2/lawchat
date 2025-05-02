import streamlit as st
import ast
import os
import pandas as pd
import jieba

from redis import Redis
from redis.commands.search.query import Query
from redis.commands.search.field import TextField, TagField

from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from redis.exceptions import ResponseError

def open_conn():
    if 'r' not in st.session_state:
        redis_key = st.secrets["redis_key"]
        REDIS_HOST=f"default:{redis_key}@172.20.31.1"
        st.session_state.r = Redis.from_url(f"redis://{REDIS_HOST}:6379", db=0, decode_responses=True)
    return st.session_state.r


# 在 app 初始化時執行一次即可
def create_law_index_if_not_exists():

    r = open_conn()
    idx_lst=r.execute_command("FT._LIST")
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

def single_srch(s,regset):
    from redis.commands.search.query import Query
    law_tag_str = " | ".join([f"{name}" for name in regset])
    q = Query(f"@lawname:{{ {law_tag_str} }} @code_seg:{s}").paging(0, 1000)
    redis_key = st.secrets["redis_key"]
    REDIS_HOST=f"default:{redis_key}@172.20.31.1"
    r = Redis.from_url(f"redis://{REDIS_HOST}:6379", db=0, decode_responses=True)#open_conn()
    res = r.ft("law_index").search(q)
    if len(res.docs)==0:
        return [f'not found by the string:{s}']
    result_lst=[]
    for doc in res.docs:
        lst=doc.id.split(':') 
        red_code=doc.code.replace(s,
            f"<span style='color:red;font-weight:bold'>{s}</span>"
        )
        result_lst.append(doc.id) #[lst[i] for i in [1,3]]+[red_code]) 
    return result_lst

def code_retrieval(input_str,regset):
    str_lst = jieba.lcut(input_str)
    result_lst=[]
    for s in str_lst:
        result_lst+=single_srch(s,regset)
    return result_lst

    
