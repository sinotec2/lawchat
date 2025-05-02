import streamlit as st
import streamlit.components.v1 as components
import jieba
from datetime import datetime, timezone, timedelta

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
        lines = file.readlines()

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
