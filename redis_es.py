import streamlit as st
from redis import Redis
import ast
import os
import re
from util_k import copy_to_clipboard_ui
import pandas as pd
import jieba

if 'r' not in st.session_state:
    redis_key = st.secrets["redis_key"]
    REDIS_HOST=f"default:{redis_key}@172.20.31.1"
    st.session_state.r = Redis.from_url(f"redis://{REDIS_HOST}:6379", db=0, decode_responses=True)
r = st.session_state.r

def get_laws_by_word(word,reg_set):
    s=set()
    for reg in reg_set:
        for key in r.scan_iter(f"law:{reg}:*"):
            if "keyword" in key:continue
            code = r.hget(key, "code") or ""        
            if len(code)==0 or word not in code:continue
    return s

def get_laws_by_keyword(keyword):
    s=set()
    for key in r.scan_iter(f"*:keyword:{keyword}"):
        s|= r.smembers(key)
    return s
def get_laws_by_keywords(keywords, mode="and"):
    """
    從 Redis 取得同時（AND）或任一（OR）關鍵詞符合的法規條文 ID。
    
    :param keywords: List of keywords，例如 ["交易", "抵換"]
    :param mode: "and" 為交集, "or" 為聯集
    :return: Set of law_ids
    """
    if not keywords:
        return set()

    result_sets = []

    for kw in keywords:
        s = set()
        for key in r.scan_iter(f"*:keyword:{kw}"):
            s |= r.smembers(key)
        result_sets.append(s)

    if mode == "and":
        return set.intersection(*result_sets)
    elif mode == "or":
        return set.union(*result_sets)
    else:
        raise ValueError("mode 只能是 'and' 或 'or'")

def parse_key(key):
    """
    將 Redis 的 key 拆成 lawname, article, clause
    範例 key: '空氣污染防制法施行細則:第三章防制:第19條:一、:1.0:0'
    """
    parts = key.replace('law:','').split(":")
    lawname = parts[0]
    article = parts[2] if len(parts) > 2 else ""
    clause = parts[3].replace('.0','') if len(parts) > 3 else ""
    item = parts[4].replace('.0','') if len(parts) > 4 else ""
    return lawname, article, clause, item

def display_laws_table(keys,srch_str):

    """
    根據條文 keys 顯示成 Streamlit 表格
    """

    i=1
    rows = []
    for key in keys:
        lawname, article, clause, item = parse_key(key)
        code = r.hget(key, "code") or ""
        rows.append({
            "no":i,
            "法規名稱": lawname,
            "條文": article,
#           "款": clause,
            "內容": code
        })
        i+=1

    if len(rows)==0:return False
    lawnames = [parse_key(key)[0] for key in keys]
    df=pd.DataFrame({'no':[i+1 for i in range(len(lawnames))],'lawname':lawnames})
    df=df.drop_duplicates()
    written=[]
    bn=[]
    for num in df.index:
        n=df.no[num]
        lawname=df.lawname[num]
        if lawname in written: continue
        written.append(lawname)
        bn.append(f"{n}.{lawname}")
    if bn:
        selected = st.selectbox("開啟法規", bn)
        if selected:
            st.session_state["regulation"]=selected.split('.')[1]
    view_type = st.radio("顯示方式", ["表格", "文字"], horizontal=True)
     
    if view_type == "文字":
         i=1
         for key in keys:
             klist=key.split(':')
             lname=klist[1]
             arts=klist[3]
             code = r.hget(key, "code") or ""
             copy_to_clipboard_ui(i,f"{lname}:{arts}:{code}",srch_str)
             i+=1
    else:
        st.dataframe(rows, use_container_width=True)
    return 
def open_law(buttname,lawname):
    if st.button(buttname, key=buttname):
        st.session_state["regulation"] = lawname
        return " "
    else:
        return "開"
    
def get_keywords_from_laws(law_ids):
    keyword_union = set()
    for law_id in law_ids:
        law_data = r.hgetall(f"{law_id}")
        if law_data:
            keywords = ast.literal_eval(law_data.get("keywords", "[]"))
            keyword_union.update(keywords)
    return keyword_union

def get_all_keywords(fname):
    with open(fname,'r', encoding='utf-8') as f:
        all_keywords=[i.split()[0] for i in f]
    return all_keywords

def display_laws_table_with_buttons(keys):
    for idx, key in enumerate(keys):
        lawname, article, clause, item = parse_key(key)
        code = r.hget(key, "code") or ""

        cols = st.columns([2, 2, 2, 6])  # 欄位分配

        with cols[0]:
            st.write(f"📘 {lawname}")
        with cols[1]:
            st.write(article)
        with cols[2]:
            st.write(clause)
        with cols[3]:
            # 按鈕名稱可顯示「選擇」等字樣，key 要唯一
            if st.button("➡️ 選擇", key=f"btn_{idx}"):
                st.session_state["regulation"] = lawname
                st.success(f"已選擇法規：{lawname}")

def chinese_to_num(chinese):  
    chi_num = {'零':0, '一':1, '二':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9}  
    if not chinese:  
        return 0  
    result = 0  
    if '十' in chinese:  
        parts = chinese.split('十')  
        if parts[0] == '':  
            result += 10  
        else:  
            result += chi_num[parts[0]] * 10  
        if len(parts) > 1 and parts[1]:  
            result += chi_num[parts[1]]  
    else:  
        result = chi_num.get(chinese, 0)  
    return result  

def extract_sort_keys(s):  
    parts = s.split(":")  
    tiao = re.search(r"第(\d+)條", parts[3])  
    tiao_num = int(tiao.group(1)) if tiao else 0  
    kuan_raw = parts[4].replace("、","")  
    xiang =  int(parts[5].replace('.0',''))
    if parts[4] == "0" and parts[5] == "0" and parts[6] == "0":  
        kuan_num = -1  
    else:  
        kuan_num = chinese_to_num(kuan_raw)  
    return (tiao_num, xiang, kuan_num)  

def get_codes_from(lawname, article):
    pattern = f"law:{lawname}:*:第*{article}*條:*"
    regex = re.compile(r'第\s*7\s*條')  
    keys = list(r.scan_iter(pattern))
    keys = [i for i in keys if regex.search(i)]
    if len(keys)==0:
        return f"找不到第{article}條，請再確認。"
    if len(keys)>1:
        keys = sorted(keys,key=extract_sort_keys) 

    rows = [f"{lawname}<br>"]
    for key in keys:
        lawname, article, clause, item = parse_key(key)
        code = r.hget(key, "code") or ""
        rows.extend([article, item, f"條文內容:{code}<br>"])
    return ''.join(rows)

def extract_law_and_article_from_query(regulation,text, law_list):  
    from cn2an import cn2an
    # 直接比對法規名稱  
    s=set(['品質標準','辦法',"法","規則","細則","標準","準則","規程"])
    if regulation in text:
        found_law = regulation
    else:
        found_law = None  
        if len(set(jieba.lcut(text))-s) == 0 :
            found_law = regulation    
        else:
            for law in law_list:  
                if law in text:  
                    found_law = law  
                    break  
    # 條號使用正則 ，如[第3條]、[第十五條]  
    article_match = re.search(r'第\s*[\d一二三四五六七八九十百零]+\s*條', text)
    article = str(int(cn2an(article_match.group(0).replace('第','').replace('條','').replace(' ',''),'smart'))) if article_match else None  
    return found_law, article
