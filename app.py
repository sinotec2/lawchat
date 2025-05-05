import streamlit as st
from streamlit_searchbox import st_searchbox
from router_engine import init_router_engine
from extrat_kw import extract_keywords_from_query, make_pools, select_law, get_lname, get_lnames, laws_dict, get_mom, \
	 reverse_lookup, reverse_lookupV
from redis_es import get_all_keywords, get_laws_by_keyword, get_keywords_from_laws, get_laws_by_keywords, display_laws_table,\
         get_laws_by_word
from util_k import copy_to_clipboard_ui, get_latest_username
from redis_srch import  create_law_index_if_not_exists, code_retrieval
import json
import ast
import os
import subprocess
from datetime import datetime
from collections import defaultdict

def search_law(query: str):
    # 這裡是模擬篩選邏輯，可以很靈活自訂
    if st.session_state["regset"]:
        regset=st.session_state["regset"]
        return [item for item in regset if query in item]
    else:
        return None

def search_keyword(query: str) -> list:
    return [kw for kw in keywords_data if query in kw]
def now_on():
    now =  datetime.now()
    hour = now.hour
    # 判斷時間區段
    if 5 <= hour < 12:
        greeting = " 早安！有你真美好🌅！"
    elif 12 <= hour < 18:
        greeting = " 午安！保持好心情喔🌞！"
    elif 18 <= hour < 22:
        greeting = "🌇 晚上好！辛苦了！"
    else:
        greeting = "🌙 夜深了，記得休息喔！"
    return greeting, now.strftime("%A, %B %d, %Y %I:%M %p")

def rd_rec(username):
    entries = defaultdict(list)
    with open(f"data/{username}/search_his.log","r", encoding="utf-8") as f:
        for line in f:
            try:
                name, timestamp_str = line.rsplit(" ", 6)[0], line.strip('\n').rsplit(" ", 6)[-6:]
                timestamp = " ".join(timestamp_str)  # e.g., 'Sunday, April 20, 2025 07:04 PM'
                dt = datetime.strptime(timestamp, "%A, %B %d, %Y %I:%M %p")
                entries[name].append(dt)
            except Exception as e:
                print("解析錯誤：", line.strip(), e)
    # 依照出現次數及最新時間排序
    sorted_names = sorted(
        entries.items(),
        key=lambda x: (-len(x[1]), max(x[1])),
    )

    # 輸出名稱序列
    result_sequence = [name for name, _ in sorted_names]
    return result_sequence

def define_fields(tag):
    col11, col12, col13, col14 = st.columns(4)
    regset=[]
    if regulation:
        try:
            m, n, l, k=reverse_lookupV(regulation)
        except:
            m, n, l, k=(0, 0, 0, 0)
    else:
        m, n, l, k=(0, 0, 0, 0)
    with col11:
        min_m=min(m,len(laws)-1)+1
        field = st.selectbox(f"母法領域{tag}", ["所有領域"]+list(laws),index=min_m)
        st.session_state["regset"] = False
        if field:
            if "所有" in field:
                st.session_state["regset"]=all_laws["all"]
            else:
                with col12:
                    main_categories=laws[field]
                    min_n=min(n,len(main_categories)-1)+1
                    main_category = st.selectbox(f"主類別範圍{tag}", ["所有主類別"]+list(main_categories),index=min_n)
                    if main_category:
                        if "所有" in main_category:
                            st.session_state["regset"]=get_lnames(laws[field])["all"]
                        else:
                            with col13:
                                subcategories = main_categories[main_category]
                                subcats=list(subcategories)
                                min_l=min(l,len(subcats)-1)+1
                                sub_category = st.selectbox(f"子類別範圍{tag}", ["所有子類別"]+subcats,index=min_l)
                                if sub_category:
                                    if "所有" in sub_category:
                                        st.session_state["regset"]=get_lnames(subcategories)["all"]
                                    else:
                                        st.session_state["regset"] = get_lnames(subcategories[sub_category])["all"]
    return st.session_state["regset"] 
results=None
folder_path="/app/json/"
metadata_pool,keyword_pool=make_pools(folder_path)
laws=laws_dict()
mom=[i.strip().replace('\n','') for i in get_mom()]
if "username" not in st.session_state:
    st.session_state["username"] = False
#cmd="/usr/bin/curl -s -k -I -u yckuang:*** https://172.20.31.6/ICT.law_query/ -o ldap.json;grep X-LDAP-User ldap.json|cut -d' ' -f2"
#    st.session_state["username"] = subprocess.check_output(cmd,shell=True).decode('utf8').strip('\r\n')
st.session_state["username"] = get_latest_username('./access.log') 
username=st.session_state["username"] 


st.set_page_config(page_title="法規查詢小助手", layout="wide")
st.title("📚環保法規查詢小助手⚖️")

#load the old law name from history json
if "regulation" not in st.session_state:
    st.session_state["regulation"] = get_lname(f"/app/data/{username}/laws.json",folder_path)
if "show_laws" not in st.session_state:
    st.session_state["show_laws"] = False
if "regset" not in st.session_state:
    st.session_state["regset"] = False

def toggle_laws():
    st.session_state["show_laws"] = not st.session_state["show_laws"]

# 根據狀態決定按鈕顯示文字
button_label_laws = "📖 展開條文" if not st.session_state["show_laws"] else "❌ 收起條文"

regulation=st.session_state["regulation"]

field_dir={"all":"json","所有領域":"json","空污相關法規":"air","環評、生態與噪音法規":"eia","土壤與毒性物質相關法規":"soil","廢棄物相關法規":"waste","水污染相關法規":"water"}
field, main_category, sub_categor=reverse_lookup(regulation)
fname=f"/app/json/all_keywords_{field_dir[field]}.txt"
all_keywords=get_all_keywords(fname)
all_laws=get_lnames(laws)
keywords_data=all_keywords

with open(os.path.join(folder_path, f"{regulation}.json"), 'r', encoding='utf-8') as f:
    data = json.load(f)
st.markdown('#### 🌳開啟法規')
mode = st.radio(label="",  options=["下拉選單", "關鍵字搜尋", "模糊篩選","曾經開啟","直接開啟" ], horizontal=True)

# 擇一顯示並設定 session_state["regulation"]
if mode == "下拉選單":
#tree selections
    col1, col2, col3, col4 = st.columns(4)

    if regulation:
        m, n, l, k=reverse_lookupV(regulation)
    else:
        m, n, l, k=(0, 0, 0, 0)

    with col1:
        min_m=min(m,len(laws)-1)
        field = st.selectbox("請選擇領域",list(laws) ,index=min_m)
    with col2:
        if field:
            laws_field=laws[field]
            lst=list(laws_field)
            min_n=min(m,len(lst)-1)
            main_category = st.selectbox("主類別", lst,index=min_n)
    with col3:
        subcategories = laws_field[main_category]
        subcats=subcategories
        if type(subcategories)==dict:subcats=list(subcategories)
        min_l=min(n,len(subcats)-1)
        sub_category = st.selectbox("主類別下之子類別", subcats,index=min_l)
    with col4:
        if laws_field[main_category][sub_category]:
            lst=laws_field[main_category][sub_category]
            min_k=min(l,len(lst)-1)
            st.session_state["regulation"] = st.selectbox("子類別下之法規", lst,index=min_k)
elif mode == "關鍵字搜尋":
    st.session_state["regset"]=define_fields("🌿")
    if st.session_state["regset"]:
        regset=st.session_state["regset"]
    st.markdown("法規名稱中的關鍵字")
    if regset and len(regset)>0:
        result = st_searchbox(search_law, key="law_search", placeholder="接輸入關鍵字(部分)")
        if result is not None:
            st.session_state["regulation"] = result
elif mode == "模糊篩選":
    query = st.text_input(f"請輸入主題😊")
    if st.checkbox("啟用 法規名稱模糊篩選"):
        if query:
            res=extract_keywords_from_query(query, metadata_pool,keyword_pool)
            if res and "LawName" in res:
                st.write(res["LawName"])
                st.session_state["regulation"]=res["LawName"][0]
                regulation=st.session_state["regulation"]
                field, main_category, sub_categor=reverse_lookup(regulation)
                st.write(f"為您開啟{main_category}-{sub_categor}-{regulation}")            
            else:
                st.markdown(f"你確定有法規名稱包含**{query}**😜")            
elif mode == "曾經開啟":
    his_seq = []
    if username:
        his_seq = rd_rec(username)
    his_selected = st.selectbox("您曾選擇", his_seq)
    if his_selected: 
        st.session_state["regulation"]=his_selected
elif mode == "直接開啟":
    dir_selected = st.text_input("貼上法規名稱")
    if dir_selected:
        if dir_selected in all_laws['all']: 
            st.session_state["regulation"]=dir_selected
            regulation = st.session_state["regulation"]
            field="all" #, main_category, sub_categor=reverse_lookup(regulation)
        else:
            st.markdown(f"你確定有法規名稱包含**{dir_selected}**😜")            
dir_mods= ["關鍵字搜尋", "全文搜尋", ]# "模糊篩選" ,
st.markdown('#### 🎣直接搜尋條文')
mode = st.radio(label="",  options=dir_mods, horizontal=True)
if mode == "全文搜尋":
    res=create_law_index_if_not_exists()
    regset=define_fields("🐟")
    word = None
    word = st.text_input("搜尋字串")
    if word:
#       st.write(regset)
        results=code_retrieval(word,regset)
        if results:
            if "not found" in results[0]:
                s="not found" 
                st.markdown(f"<span style='color:red;font-weight:bold'>{s}</span>", unsafe_allow_html=True)
            else:
                s=len(results)
                st.markdown(f"找到<span style='color:red;font-weight:bold'>{s}</span>筆", unsafe_allow_html=True)
                view_type = st.radio("顯示方式", ["表格", "文字"], horizontal=True)
                display_laws_table([i for i in results if "not found" not in i],view_type,word)
         
elif mode == "關鍵字搜尋":
    # 第一個關鍵詞搜尋框
    keywords_data=all_keywords
    col21, col22, co2l, col24 = st.columns(4)
    with col21:
        kw1 = st_searchbox(search_keyword, key="keyword_search1", placeholder="輸入關鍵字")
    with col22:
        if kw1:
            related_law_ids = get_laws_by_keyword(kw1)
            second_keywords = get_keywords_from_laws(related_law_ids)
            second_keywords.discard(kw1)
            keywords_data = [kw for kw in all_keywords if kw in second_keywords]
            results = get_laws_by_keywords(set([kw1]+[kw1]), mode="and")         
           
            kw2 = st_searchbox(search_keyword, key="keyword_search2", placeholder=f"輸入關鍵字如:{keywords_data[0]}")
            if kw1 and kw2:
                results = get_laws_by_keywords(set([kw1,kw2]), mode="and")
    if results:
        s=len(results)
        st.markdown(f"找到<span style='color:red;font-weight:bold'>{s}</span>筆", unsafe_allow_html=True)
        view_type = st.radio("顯示方式", ["表格", "文字"], horizontal=True)
        kw=kw1
        if kw2:kw=kw1+kw2
        display_laws_table(results,view_type,kw)
pass_txt="""
elif mode == "模糊篩選":
    query = st.text_input(f"請輸入主題😊")
    if st.checkbox("啟用 法規條文模糊篩選"):
        if query:
            res=extract_keywords_from_query(query, metadata_pool,keyword_pool)
            if "LawName" in res:
                st.write(res["LawName"])
                st.session_state["regulation"]=res["LawName"][0]
                regulation=st.session_state["regulation"]
                field, main_category, sub_categor=reverse_lookup(regulation)
                st.write(f"為您開啟{main_category}-{sub_categor}-{regulation}")
            else:
                st.write(f"再多一點提示囉!😜")
"""
st.markdown('#### 🦙詢問llama')
regulation=st.session_state["regulation"]
query = st.text_input(f"請輸入你的問題(目前資料庫：{regulation})😊")

if st.session_state["regulation"]:
    regulation=st.session_state["regulation"]
    with open(os.path.join(folder_path, f"{regulation}.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)
    with st.sidebar:
        if username:
            greeting,timestamp=now_on()
            st.write(f"{username}{greeting}")
            os.system(f"mkdir -p data/{username}")
            with open(f"data/{username}/search_his.log","a", encoding="utf-8") as f:
                f.write(f"{regulation} {timestamp}\n")

        st.sidebar.header("法規資訊")
        st.sidebar.subheader("名稱")
        st.sidebar.write(data["LawName"])
        st.sidebar.subheader("摘要")
        st.sidebar.write(data["abstract"])
        st.sidebar.subheader("條文")
        # 當按下按鈕就切換狀態
        st.button(button_label_laws, on_click=toggle_laws)
        # 根據狀態顯示條文內容
        if st.session_state["show_laws"]:
            for i in range(len(data["codes"])):
                d=f"第 {i+1} 條"
                if d not in data["codes"].keys(): continue
                st.sidebar.write(f"**{d}**",data["codes"][d])
    result=select_law(folder_path,regulation,username)            
    router_engine = init_router_engine(username,regulation)

f="""
if st.checkbox("啟用 Metadata 精準篩選"):
    selected_arts = st.text_input("指定條文（例如：第5條）")
    selected_lawname = st.text_input("指定法規名稱")

    filters = {}
    if selected_arts:
        filters["article"] = selected_arts
    if selected_lawname:
        filters["LawName"] = selected_lawname

    if query:
#        response = router_engine.query(query) #, filters=filters)
        with st.spinner("查詢中..."):
            st.markdown("### 回覆內容")
            resp = router_engine.query(query)
            st.write(resp.response)
else:
"""
if query:
    with st.spinner("查詢中..."):
        st.markdown("### 回覆內容")
        resp = router_engine.query(query)
        st.write(resp.response)
