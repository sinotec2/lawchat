import streamlit as st
import streamlit.components.v1 as components
import jieba
from datetime import datetime, timezone, timedelta
from ldap3 import Server, Connection, ALL

import re

def copy_to_clipboard_ui(i,text,srch_str):
#    st.code(text, language="python")
     lst_srch=jieba.lcut(srch_str)
     for s in lst_srch:     
         text=text.replace(s,
            f"<span style='color:red;font-weight:bold'>{s}</span>"
        )
     text=f"<span style='color:blue;font-weight:bold'>{i}.</span>{text}"
     st.markdown(text, unsafe_allow_html=True)
  
def copy_to_clipboard_ui0(i,text):

    # JS 和 HTML
    st.text_area("📋 可複製內容", text, height=70, key=f"copy_area{i}")
    components.html(f"""
    <script>
    function copyToClipboard(text) {{
        navigator.clipboard.writeText(text).then(() => {{
            alert("👍");
        }});
    }}
    function appendToClipboard(text) {{
        navigator.clipboard.readText().then(existingText => {{
            navigator.clipboard.writeText(existingText + text).then(() => {{
                alert("👍");
            }});
        }}).catch(err => {{
            alert("無法讀取剪貼簿內容：" + err);
        }});
    }}
    </script>
    <button onclick="copyToClipboard(document.getElementById('copy_area{i}').value)">📋覆蓋</button>
    <button onclick="appendToClipboard(document.getElementById('copy_area{i}').value)">➕新增</button>
    """, height=100)

def get_latest_username(log_file):
    with open(log_file, 'r') as file:
        lines = [line for line in file if "/law_query/ HTTP/1.1" in line]

    current_time = datetime.now(timezone.utc)
    closest_username = None
    closest_time_diff = timedelta.max

    # 正則表達式模式
    pattern = r' - (\S+) \[(.*?)\]'

    for line in lines[-10:]:  # 只讀取最後10行
        match = re.search(pattern, line)
        if match:
            username = match.group(1)  # USERNAME
            timestamp_str = match.group(2)  # TIMESTAMP
            timestamp = datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S %z")
            
            # 計算時間差
            time_diff = abs(current_time - timestamp)
            if time_diff < closest_time_diff:
                closest_time_diff = time_diff
                closest_username = username

    return closest_username

def get_latest_username_csv(log_file):
    if 'connection' not in  st.session_state:
        st.session_state['connection']=False

    if not st.session_state['connection']:
        username=authenticate_user()
        if st.session_state['username'] and st.session_state['password'] and not username:
            return False
        return username
    else:
        if st.session_state['username'] and st.session_state['password'] and type(username)==str:
            return username
        return False

def ldap_login(username, password):
    BASE_DN = "dc=sinotech-eng,dc=com"
    if st.session_state['username'] and st.session_state['password'] and not st.session_state['connection']:
        user = f"uid={username},cn=users,cn=accounts,{BASE_DN}"
        server = Server('ldap://172.20.31.3', get_info=ALL)
        try:
            conn = Connection(server, user, password, auto_bind=True)
        except:
            with st.sidebar:
                st.error('無效的憑證')  # 顯示錯誤訊息
            return None
        return conn
    return None

# 從 session_state 中取得使用者憑證
def get_ldap_credentials():
    if 'username' not in st.session_state:
        st.session_state['username'] = False
    if 'password' not in st.session_state:
        st.session_state['password'] = False
    if not st.session_state['username']:
        with st.sidebar:
            st.session_state['username'] = st.text_input('使用者名稱') #,  key='username')
            if not st.session_state['password']:
                st.session_state['password'] = st.text_input('密碼', type='password') #, key='password')  # 密碼輸入框
    username = st.session_state['username']
    password = st.session_state['password']
    return username, password

# 驗證使用者登入
def authenticate_user():
    if not st.session_state['connection']:
        username, password=get_ldap_credentials()
        conn = ldap_login(username, password)
        if st.session_state['username'] and st.session_state['password']:
            if not conn:
                return False
            st.session_state['connection']=conn
            return username
        return None
    return  st.session_state['username']
