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

redis_key = st.secrets["redis_key"]
REDIS_HOST=f"default:{redis_key}@172.20.31.1"
r = Redis.from_url(f"redis://{REDIS_HOST}:6379", db=0, decode_responses=True)

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
                TextField("lawname"), 
                TextField("code"),
                TextField("code_seg"),
                TextField("keywords"),
                TextField("abstract")
                ], definition=IndexDefinition(prefix=["law*:"], index_type=IndexType.HASH))
            print("law_index 建立完成")
        except:
            print("law_index 建立失敗")
            return False
    return True

def single_srch(s,regset):
    from redis.commands.search.query import Query
    result_lst=[]
    for name in regset:
        q = Query(f'@lawname:"{name}" @code_seg:"{s}"').paging(0, 10000)
        res = r.ft("law_index").search(q)
        if len(res.docs)==0:continue
        result_lst.extend([doc.id for doc in res.docs])
    if len(result_lst)==0:
        return [f'not found by the string:{s}']
    else:
        return result_lst

def code_retrieval(input_str,regset):
    from functools import reduce  
    quotes="\"\'"
    boo1=any(i in input_str for i in quotes)
    delimiters=',;& ，、'
    boo2=any(i in input_str for i in delimiters)
    result_lst=[]
    if boo1 or boo2:
        if boo1:
            for s in quotes:
                input_str=input_str.replace(s,'')
            jb=jieba.lcut(input_str)
            if len(jb)==1:
                str_lst = jb
            else:
                for lawname in regset:
                    fname=f"json/{lawname}.csv"
                    df=pd.read_csv(fname)
                    for _, row in df.iterrows():
                        # 產生條文 key
                        code=row['codes']
                        if 'path_codes' in df.columns: code=row['path_codes']
                        if type(code) != str:continue
                        if input_str not in code:continue
                        result_lst.append(f"law:{lawname}:{row['chapter']}:{row['article']}:{row['clause']}:{row['item']}:{row['points']}")
                if len(result_lst)==0:
                    return [f'not found by the string:{s}']
                else:
                    return list(result_lst)

        if boo2:
            for s in delimiters:
                input_str=input_str.replace(s,' ')
            lst=input_str.split()
            str_lst=set()
            for i in lst:
                str_lst|=set(jieba.lcut(i))
        for s in str_lst:
            result_lst.append(set(single_srch(s,regset)))
        result_lst = reduce(set.intersection, result_lst)  
    else:
        str_lst = jieba.lcut(input_str)
        for s in str_lst:
            result_lst+=single_srch(s,regset)
    if len(result_lst)==0:
        return [f'not found by the string:{s}']
    else:
        return list(result_lst)

    
