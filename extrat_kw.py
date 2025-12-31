import difflib
from rapidfuzz import process, fuzz
import re
import jieba
import os, sys
import json
import ast
import pandas as pd
import shutil  
import streamlit as st

jieba.load_userdict('air_dict.txt')

def make_pools(folder_path):
    parentnames,chaps,arts,atts,names=set(),set(),set(),set(),set()
    for file in os.listdir(folder_path):
        if file.endswith('.json'):
            fname=os.path.join(folder_path, file)
            names|=set([file.split('.')[0]])
            try:
                with open(fname,'r') as f:
                    data=json.load(f)
                    if "parentname" in data:
                        parentnames|=set([data["parentname"]])
                    if "attachment" in data:
                        atts|=set(ast.literal_eval(data["attachment"]))
            except:
                sys.exit(fname)


    for file in os.listdir(folder_path):
        if file.endswith('.csv'):
            fname=os.path.join(folder_path, file)             
            df=pd.read_csv(fname)
            if any(c not in df.columns for c in ['chapter','article']):continue
            chaps|=set([i for i in df.chapter if type(i)==str and len(i)>1])
            arts|=set([i for i in df.article if type(i)==str and len(i)>1])
    metadata_pool = {
    "parentname": parentnames,
    "chapter": chaps,
    "article": arts,
    "attachment": atts,
    "LawName": names,
    }
    with open('air_dict.txt','r') as f:
        keyword_pool=[i.split()[0] for i in f]
    return metadata_pool, keyword_pool

# 重新執行剛剛的模糊推薦模組程式碼

# 工具：將中文數字轉為阿拉伯數字（支援一到十）
chinese_to_arabic = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
}

def convert_chinese_numerals(text):
    """簡易轉換中文數字（只處理一到十）"""
    for ch, num in chinese_to_arabic.items():
        text = text.replace(ch, str(num))
    return text

def normalize(text):
    """清理、標準化詞條（轉換全形符號、中文數字、移除空格）"""
    text = convert_chinese_numerals(text)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[（）()、，：:；;]', '', text)  # 移除常見符號
    return text

def suggest_keywords(user_input, keyword_pool, topn=5, score_cutoff=60):
    norm_input = normalize(user_input)
    abbr={
    '空污':'空氣污染',
    '空品':'空氣品質',
    }
    for a in abbr:
        norm_input=norm_input.replace(a,abbr[a])
    norm_pool = {kw: normalize(kw) for kw in keyword_pool}
    reversed_pool = {v: k for k, v in norm_pool.items()}  # 用於找回原詞

    # rapidfuzz 比對標準化後的詞
    results = process.extract(norm_input, norm_pool.values(), scorer=fuzz.ratio, limit=topn, score_cutoff=score_cutoff)
    return [reversed_pool[match] for match, score, _ in results]+[i for i in keyword_pool if norm_input in i]

def extract_keywords_from_query(query, metadata_pool, keyword_pool, topn=3):
    """
    query: 使用者輸入的自然語言指令
    metadata_pool: 從所有 node 收集的可用欄位與值，如：
        {
            "章": ["總則", "第2章 排放標準", ...],
            "條": ["第1條", "第2條", ...],
            ...
        }
    回傳 dict，例如：{'條': '第5條', '附件名稱': '放流水標準表'}
    """
    stopwords = set(["請", "的", "一下", "幫我", "相關", "規定", "解釋", "說明", "是什麼", "一下"])

    result = {}
    # Step 1: jieba 斷詞 + 停用詞過濾
    seg_list = jieba.lcut(query)
    filtered_words = [w for w in seg_list if w not in stopwords and len(w) > 1]
    sug_words=[]
    for word in filtered_words:
        ss=set(suggest_keywords(word, keyword_pool, topn=topn))
        if len(ss)==0:continue
        sug_words.append( ss)
    if len(sug_words)>1:
        sug_words=set.union(*sug_words)
    elif len(sug_words)==1:
        sug_words=sug_words[0]
    else:
        return None
    # Step 2: 每個欄位嘗試模糊比對
    for field, possible_values in metadata_pool.items():
        matched = set([word for word in sug_words if word in possible_values or any([(word in i) for i in possible_values])])
        if matched:
            # 取第一個相符結果
            values=set()
            for word in matched:
                exact=set(word) & possible_values
                partial=set([value for value in possible_values if word in value])
                if (len(exact)==0 or len(excat)>5) and (len(partial)==0 or len(partial)>5):continue
                values|=exact|partial
            result[field] = list(values)
    return result

def select_law(fixed_path,lawname,username):
    file = f"{lawname}.json"
    json_path = os.path.join(fixed_path, file)
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    fname = os.path.join(fixed_path, f"{lawname}.csv")
    df=pd.read_csv(fname) 
    code,abst,kwds=[],[],[]
    keys=["chapter","item","article","clause","points","attachment","LawName"]
    lawname=data["LawName"]
    atts=''
    if "attachment" in data and len(data["attachment"])>3:
        atts=data["attachment"]
    for i in df.index:
        att=""
        if '附件' in df.iloc[i,4] or '附表' in df.iloc[i,4]:att=atts
        vals=[str(k) for k in list(df.iloc[i,[0,5,1,2,3]])+[att]+[lawname]]
        codei=f"{df.iloc[i,4]}"
        art=str(df.article[i])
        if '第' in art and '條' in art:
            art=art.replace(' ','')
        if "tables" in data and art in data["tables"]:
            codei+=data["tables"][art]
        code.append({"text":codei,"metadata":{k:v for k,v in zip(keys,vals)}})
        abst.append({"text":f"{df.iloc[i,6]}","metadata":{k:v for k,v in zip(keys,vals)}})
        kwds.append({"text":f"{df.iloc[i,7]}","metadata":{k:v for k,v in zip(keys,vals)}})
    folder_path = f"./data/{username}"
    os.system(f"mkdir -p {folder_path}")
    with open(os.path.join(folder_path,'laws.json'),'w',encoding='utf-8') as f:
        json.dump(code, f, ensure_ascii=False)
    with open(os.path.join(folder_path,'summaries.json'),'w',encoding='utf-8') as f:
        json.dump(abst, f, ensure_ascii=False)
    with open(os.path.join(folder_path,'keywords.json'),'w',encoding='utf-8') as f:
        json.dump(kwds, f, ensure_ascii=False)
    return True

def get_lnames(in_laws):
    if type(in_laws) == dict:
        data = {i:[] for i in in_laws.keys()}
        for i in in_laws:
            if type(in_laws[i]) == dict:
                for j in in_laws[i]:
                    if type(in_laws[i][j]) == dict:
                        for k in in_laws[i][j]:
                            data[i]+=in_laws[i][j][k]
                    elif type(in_laws[i][j]) == list:
                        data[i]+=in_laws[i][j]
            elif type(in_laws[i]) == list:
                data[i]+=in_laws[i]
    elif type(in_laws) == list:
        data={'all':in_laws}
    if 'all' not in data:
        ll=[]
        for i,l in data.items():
            ll+=l
        data.update({'all':ll})
    return data

def get_lname(json_name,src_dir):
    path_user=os.path.dirname(json_name)
    os.makedirs(path_user, exist_ok=True)
    his_file=os.path.join(path_user,"search_his.log")
    if os.path.exists(his_file):
        with open(his_file,'r') as f:
            lines=f.read().split('\n')
        LawName=lines[-2].split()[0]
        return LawName
    for file in os.listdir(src_dir):  
        if file.endswith('s.json'):  
            source=os.path.join(src_dir,file)
            target=os.path.join(path_user,file)
            shutil.copy(source, target)
    with open(json_name,'r', encoding='utf-8') as f:
        data = json.load(f)
    return data[0]["metadata"]["LawName"]
def laws_dict():
    laws = {}
    laws.update({"空污相關法規": {  
    "母法與行政": {
        "空污母法": [
            "空氣污染防制法",
            "空氣污染防制法施行細則",
            "空氣品質標準",
            "環境基本法",
        ],
        "排放管理": [
            "公私場所固定污染源申請改善排放空氣污染物總量及濃度管理辦法",
            "公私場所固定污染源空氣污染物排放量申報管理辦法",
            "固定污染源戴奧辛排放標準",
            "固定污染源有害空氣污染物排放標準",
            "固定污染源空氣污染物實際削減量差額認可保留抵換及交易辦法",
        ],
        "罰則與獎勵": [
            "公私場所固定污染源違反空氣污染防制法應處罰鍰額度裁罰準則",
            "公私場所違反空氣污染防制法行為揭弊者法律扶助辦法",
            "違反空氣污染防制法按次處罰通知限期改善補正或申報執行準則",
            "違反空氣污染防制法義務所得利益核算及推估辦法",
        ],
        "費用管理": [
            "固定污染源空氣污染防制規費收費標準",
            "空氣污染防制基金收支保管及運用辦法",
            "空氣污染防制費收費辦法",
            "公私場所固定污染源空氣污染防制設備空氣污染防制費減免辦法",
        ],
        "管理單位": [
            "空氣污染防制專責單位或專責人員設置及管理辦法",
            "總量管制區空氣污染物抵換來源拍賣作業辦法",
            "易致空氣污染之物質使用許可證管理辦法",
            "空氣污染物及噪音檢查人員證書費收費標準",
            "行政院環境保護署提供空氣品質監測儀器校驗服務規費收費標準",
        ],
        "緊急應變與測站": [
            "空氣品質嚴重惡化採取緊急防制措施期間電業調整燃氣用量核可程序辦法",
            "空氣品質嚴重惡化警告發布及緊急防制辦法",
            "空氣污染突發事故緊急應變措施計畫及警告通知作業辦法",
            "空氣污染行為管制執行準則",
            "特殊性工業區緩衝地帶及空氣品質監測設施設置標準",
            "空氣品質監測站設置及監測準則",
        ],
    },
    "室內空氣品質管理": {
        "室內空品法規": [
            "室內空氣品質標準",
            "室內空氣品質管理法",
            "室內空氣品質管理法施行細則",
            "室內空氣品質維護管理專責人員設置管理辦法",
            "違反室內空氣品質管理法罰鍰額度裁罰準則",
            "公告場所室內空氣品質檢驗測定管理辦法",
        ]
    },
    "固定污染源管理": {
        "固定源法規": [
            "固定污染源空氣污染物排放標準",
            "固定污染源自行或委託檢測及申報管理辦法",
            "固定污染源設置操作及燃料使用許可證管理辦法",
            "固定污染源空氣污染物連續自動監測設施管理辦法",
            "固定污染源管理資訊公開及工商機密審查辦法",
            "固定污染源逸散性粒狀污染物空氣污染防制設施管理辦法",
            "既存固定污染源污染物排放量認可準則",
            "三級防制區既存固定污染源應削減污染物排放量準則",
            "公私場所固定污染源復工試車評鑑及管理辦法",
            "公私場所固定污染源燃料混燒比例成分及防制設施管制標準",
        ]
    },
    "移動污染源管理": {
        "檢驗管理": [
            "機動車輛排放空氣污染物及噪音檢驗測定機構管理辦法",
            "機車排放空氣污染物檢驗站設置及管理辦法",
            "汽油及替代清潔燃料引擎汽車排放空氣污染物檢驗站設置及管理辦法",
            "交通工具排放空氣污染物審查費證書費收費標準",
            "交通工具排放空氣污染物檢驗處理及委託辦法",
            "使用中移動污染源排放空氣污染物不定期檢驗辦法",
            "汽車空氣污染物驗證核章辦法",
        ],
        "燃料管理": [
            "移動污染源燃料成分管制標準",
            "移動污染源燃料販賣進口許可及管理辦法",
            "酒精汽油生質柴油及再生油品之生產輸入摻配銷售業務管理辦法",
        ],
        "排放標準": [
            "移動污染源空氣污染物排放標準",
        ],
        "設備管理": [
            "移動污染源空氣污染防制設備管理辦法",
        ],
        "違規處罰": [
            "移動污染源違反空氣污染防制法裁罰準則",
        ],
        "補助措施": [
            "大型柴油車調修燃油控制系統或加裝空氣污染防制設備補助辦法",
            "老舊車輛汰舊換新空氣污染物減量補助辦法",
        ],
    },
    "特殊行業管制": {
        "民生行業": [
            "乾洗作業空氣污染防制設施管制標準",
            "廢棄物焚化爐空氣污染物排放標準",
            "揮發性有機物空氣污染管制及排放標準",
            "餐飲業空氣污染防制設施管理辦法",
            "熱風乾燥機粒狀污染物排放標準",
        ],
        "電子製造及塗裝業": [
            "光電材料及元件製造業空氣污染管制及排放標準",
            "半導體製造業空氣污染管制及排放標準",
            "氯乙烯及聚氯乙烯製造業空氣污染物管制及排放標準",
            "汽車製造業表面塗裝作業空氣污染物排放標準",
            "聚氨基甲酸酯塗布業揮發性有機物空氣污染管制及排放標準",
            "膠帶製造業揮發性有機物空氣污染管制及排放標準",
        ],
        "鋼鐵冶煉": [
            "煉鋼及鑄造電爐粒狀污染物管制及排放標準",
            "鋼鐵業燒結工場空氣污染物排放標準",
            "鉛二次冶煉廠空氣污染物排放標準",
        ],
        "礦冶及窯業": [
            "水泥業空氣污染物排放標準",
            "玻璃業空氣污染物排放標準",
            "瀝青拌合業粒狀污染物排放標準",
            "磚瓦窯業開放式隧道窯粒狀污染物排放標準",
            "陶瓷業空氣污染物排放標準",
        ],
        "鍋爐及電力業": [
            "電力設施空氣污染物排放標準",
            "鍋爐空氣污染物排放標準",
        ],
        "廢棄物焚化爐": [
            "廢棄物焚化爐戴奧辛管制及排放標準",
            "中小型廢棄物焚化爐戴奧辛管制及排放標準",
        ],
        "營建工程": [
            "營建工程空氣污染防制設施管理辦法"
        ],
    },
    }  })      
    laws.update({"環評、生態與噪音法規": {  
    "母法及作業規定": {  
        "環評母法準則": [
        "環境影響評估法", 
        "環境影響評估法施行細則", 
        "開發行為應實施環境影響評估細目及範圍認定標準",
        "環境影響評估書件審查收費辦法",
        "環境部環境影響評估審查委員會組織規程",
        "違反環境影響評估法按日連續處罰執行準則",
        "開發行為環境影響評估作業準則",
        ],
    },
    "類別規定": {  
        "特殊項目環評": [
        "政府政策環境影響評估作業辦法",
        "科學園區申請變更環境影響說明書或評估書審查作業辦法",
        "軍事秘密及緊急性國防工程環境影響評估作業辦法",
        "營造業購置自動化設備或技術及防治污染設備或技術適用投資抵減辦法",
    ],  
    },
    "生態方面法規": {  
        "保育相關": [  
            "野生動物保育法", 
            "野生動物保育法施行細則", 
            "原住民族基於傳統文化及祭儀需要獵捕宰殺利用野生動物管理辦法", 
            "保育類或具危險性野生動物飼養繁殖管理辦法", 
        ],  
        "委員會設置": [  
            "海洋委員會海洋野生動物保育諮詢委員會設置辦法",
            "農業部陸域野生動物保育諮詢委員會設置辦法",
        ],  
        "捐助、獎勵與買賣": [  
            "海洋野生動物保育捐助專戶管理及運用辦法", 
            "取締或舉發違反野生動物保育法案件獎勵辦法",
            "營利性野生動物飼養繁殖買賣加工管理辦法",
        ]},  
    "噪音管理法規": {  
    "噪音母法及罰則": [  
        "噪音管制法",  
        "噪音管制法施行細則",  
        "噪音管制法規費收費標準",  
        "違反噪音管制法按日連續處罰執行準則"  
    ],  
    "機動車輛相關法規": [  
        "使用中機動車輛噪音妨害安寧檢舉辦法",  
        "使用中機動車輛噪音管制辦法",  
        "機動車輛噪音管制標準",  
        "機動車輛噪音驗證核可準則",  
        "機動車輛車型噪音審驗合格證明核發廢止及噪音抽驗檢驗處理辦法"  
    ],  
    "航空噪音相關法規": [  
        "民用航空器噪音管制標準",  
        "民用航空器噪音管制辦法",  
        "國營航空站噪音補償金分配及使用辦法",  
        "機場周圍地區航空噪音防制辦法",  
        "軍用機場噪音防制補償經費分配使用辦法"  
    ],  
    "環境噪音管制標準和作業準則": [  
        "噪音管制區劃定作業準則",  
        "噪音管制標準",  
        "陸上運輸系統噪音管制標準",  
        "易發生噪音設施設置及操作許可辦法",  
        "軍事機關及其所屬單位之場所工程設施及機動車輛航空器等裝備噪音管制辦法",
    ]  }          
    }  })      
    laws.update({"土壤與毒性物質相關法規": {  
    "土壤污染相關法規": {  
        "土壤污染管制標準與評估": [  
            "土壤污染管制標準",  
            "土壤污染評估調查人員管理辦法",  
            "土壤污染評估調查及檢測作業管理辦法",  
            "土壤污染評估調查及檢測資料審查收費標準"  
        ],  
        "土壤及地下水污染整治": [  
            "土壤及地下水污染整治法",  
            "土壤及地下水污染整治法施行細則",  
            "土壤及地下水污染整治基金收支保管及運用辦法",  
            "土壤及地下水污染整治基金補助研究及模場試驗專案作業辦法",  
            "土壤及地下水污染整治場址環境影響與健康風險評估辦法",  
            "土壤及地下水污染整治費收費辦法"  
        ],  
        "地下水污染管制": [  
            "地下水污染監測標準",  
            "地下水污染管制標準",  
            "防止貯存系統污染地下水體設施及監測設備設置管理辦法"  
        ],  
        "其他管理辦法": [  
            "土壤及地下水污染場址初步評估暨處理等級評定辦法",  
            "辦理土壤及地下水污染場址整治目標公聽會作業準則",  
            "污染土地關係人之善良管理人注意義務認定準則"  
        ],  
        "檢驗測定相關": [  
            "土壤底泥及地下水污染物檢驗測定品質管制準則",  
            "土壤污染監測標準"  
        ]  
    },  
    "毒性物質相關法規": {  
        "毒性及關注化學物質管理法及其相關規定": [  
            "毒性及關注化學物質管理法",  
            "毒性及關注化學物質管理法施行細則",  
            "毒性及關注化學物質管理法規費收費標準"  
        ],  
        "運作管理": [  
            "中央研究院運作毒性及關注化學物質管理辦法",  
            "軍事機關運作毒性及關注化學物質管理辦法",  
            "毒性及關注化學物質運作人投保責任保險辦法",  
            "毒性及關注化學物質運作獎勵辦法",  
            "毒性及關注化學物質運作與釋放量紀錄管理辦法",  
            "毒性及關注化學物質運送管理辦法"  
        ],  
        "許可登記管理": [  
            "毒性及關注化學物質許可登記核可管理辦法",  
            "申請解除毒性化學物質限制或禁止事項審核辦法"  
        ],  
        "災害預防及應變": [  
            "毒性及關注化學物質危害預防及應變計畫作業辦法",  
            "毒性及關注化學物質應變器材與偵測警報設備管理辦法",  
            "毒性及關注化學物質災害事故應變車輛管理辦法",  
            "毒性及關注化學物質災害潛勢資料公開辦法",  
            "毒性及關注化學物質災害與懸浮微粒物質災害救助種類及標準"  
        ],  
        "標示管理": [  
            "毒性及關注化學物質標示與安全資料表管理辦法"  
        ],  
        "事故調查": [  
            "毒性及關注化學物質事故調查處理報告作業準則"  
        ],  
        "輻射污染": [  
            "嚴重污染環境輻射標準",  
            "放射性污染建築物事件防範及處理辦法"  
        ],  
        "食品污染": [  
            "食品中原子塵或放射能污染容許量標準",  
            "食品中污染物質及毒素衛生標準"  
        ],  
     }  
    }})      
    laws.update({"廢棄物相關法規": {  
        "普遍對象": {
        "一般廢棄物管理": [  
            "一般廢棄物回收清除處理辦法",  
            "一般廢棄物掩埋場降低溫室氣體排放獎勵辦法",  
            "一般廢棄物清除處理費徵收辦法"  
        ],  
        "事業廢棄物管理": [  
            "事業廢棄物清理計畫書審查管理辦法",  
            "事業廢棄物清理計畫書審查費收費標準",  
            "事業廢棄物處理設施餘裕處理容量許可管理辦法",  
            "事業廢棄物貯存清除處理方法及設施標準",  
            "事業廢棄物輸入輸出管理辦法",  
            "廢棄物輸入輸出許可申請收費標準",
            "事業自行清除處理事業廢棄物許可管理辦法",
            "環境部事業廢棄物再利用管理辦法",  
        ],  
        "回收管理": [  
            "回收廢棄物變賣所得款項提撥比例及運用辦法",  
            "應回收廢棄物回收清除處理補貼申請審核管理辦法",  
            "應回收廢棄物回收處理業管理辦法",  
            "應回收廢棄物稽核認證作業辦法",  
            "應回收廢棄物責任業者管理辦法"  
        ],  
        "設施管理": [  
            "指定公營事業設置廢棄物清除處理設施管理辦法",  
            "依促進民間參與公共建設法設置之廢棄物清除處理設施管理辦法",  
            "公民營廢棄物清除處理機構申請許可案件收費標準",  
            "公民營廢棄物清除處理機構許可管理辦法",  
            "經濟部輔導設置事業廢棄物清除處理設施管理辦法",  
            "衛生主管機關輔導設置醫療廢棄物清除處理設施管理辦法",
            "營建廢棄物共同清除處理機構管理辦法",  
            "農業廢棄物共同清除處理機構管理辦法",
            "醫療廢棄物共同清除處理機構管理辦法",
        ],  
        },  
        "特殊及放射性廢棄物": {
        "特殊行業廢棄物管理": [  
            "交通事業廢棄物再利用管理辦法",  
            "公共下水道污水處理廠事業廢棄物再利用管理辦法",  
            "共通性事業廢棄物再利用管理辦法",  
            "菸酒事業廢棄物再利用管理辦法",  
            "農業事業廢棄物再利用管理辦法",  
            "通訊傳播事業廢棄物再利用管理辦法",  
            "醫療事業廢棄物再利用管理辦法",  
            "餐館業事業廢棄物再利用管理辦法",
            "易燃性廢棄物再利用工廠申報管理辦法",  
            "營建事業廢棄物再利用管理辦法",
        ],  
        "放射性廢棄物管理": [  
            "一定活度或比活度以下放射性廢棄物管理辦法",  
            "放射性廢棄物處理設施運轉人員資格管理辦法",  
            "放射性廢棄物處理貯存及其設施安全管理規則",  
            "放射性廢棄物處理貯存最終處置設施建造執照申請審核辦法",  
            "放射性廢棄物運作許可辦法",  
            "低放射性廢棄物最終處置及其設施安全管理規則",  
            "低放射性廢棄物最終處置設施場址禁置地區之範圍及認定標準",  
            "低放射性廢棄物最終處置設施場址設置條例",  
            "天然放射性物質衍生廢棄物管理辦法",  
            "高放射性廢棄物最終處置及其設施安全管理規則"  
        ], 
        "有害事業廢棄物管理": [  
            "有害事業廢棄物認定標準",
            "有害事業廢棄物檢測及紀錄管理辦法",
        ], 
        },  
        "個別主管機關": {
        "教育及科技園區": [  
            "教育機構事業廢棄物共同清除處理機構管理辦法",  
            "教育部事業廢棄物再利用管理辦法",  
            "科學園區事業廢棄物再利用管理辦法",  
            "科學園區廢棄物共同清除處理機構管理辦法"  
        ],  
        "經濟部管理": [  
            "經濟部事業廢棄物共同清除處理機構管理辦法",  
            "經濟部事業廢棄物再利用產品環境監測管理辦法",  
            "經濟部事業廢棄物再利用管理辦法",  
            "經濟部事業廢棄物再利用許可審查規費收費標準"  
        ],  
        },
        "清理": {
        "廢棄物清理法相關": [  
            "廢棄物清理法",  
            "廢棄物清理法施行細則",  
            "違反廢棄物清理法所得利益認定及核算辦法",  
            "違反廢棄物清理法按日連續處罰執行準則",  
            "違反廢棄物清理法罰鍰額度裁罰準則",
        ],  
        "清除機具及人員管理": [  
            "廢棄物及剩餘土石方清除機具處理設施或設備扣留作業辦法",
            "廢棄物清理專業技術人員管理辦法",
        ],  
        },
    }})      
    laws.update({"水污染相關法規": {  
        "水污染防治法及其相關規定": {  
        "水污染法及及準則": [
            "水污染防治法",  
            "水污染防治法施行細則",  
            "違反水污染防治法按次處罰通知限期改善或補正執行準則",  
            "違反水污染防治法罰鍰額度裁罰準則",  
            "違反水污染防治法義務所得利益核算及推估辦法"  
        ],  
        },
        "水污染防治費管理": {  
        "水污費法規": [
            "事業及污水下水道系統水污染防治費收費辦法",  
            "水污染防治費中央與地方分配辦法",  
            "水污染防治費費率審議委員會設置辦法",  
            "水污染防治基金收支保管及運用辦法"  
        ],  
        },
        "水污染防治措施管理": {  
        "水措法規": [
            "水污染防治措施及檢測申報管理辦法",  
            "水污染防治措施計畫及許可申請審查管理辦法",
            "水污染防治各項許可申請收費標準",  
        ],  
        },
        "海洋及船舶": {  
            "海洋污染防治": [  
                "海洋污染防治法",  
                "海洋污染防治法施行細則",  
                "海洋污染清除處理辦法",  
                "海洋污染涉及軍事事務檢查鑑定辦法",  
                "海洋污染防治各項許可申請收費辦法",  
                "陸上污染源廢（污）水排放於特定海域許可辦法"  
            ],  
            "船舶污染防治": [  
                "船舶安全營運與防止污染管理規則"  
            ]  
        },  
        "專責及促參": {  
            "專責人員管理": [  
                "廢（污）水處理專責人員違反水污染防治法罰鍰額度裁罰準則"  
            ],  
            "民間參與公共建設": [  
                "民間參與環境污染防治設施公共建設接管營運辦法"  
            ]  
        }  
    }})      
    laws.update({"採購與契約相關法規": {  
        "政府採購法規": {  
            "採購相關法案": [
                "政府採購法",
                "政府採購法施行細則",
                "政府採購公告及公報發行辦法",
                "採購文件保存作業準則",
                "採購人員倫理準則",
            ],  
            "採購作業與程序辦法": [
                "中央機關未達公告金額採購招標辦法",
                "中央機關未達公告金額採購監辦辦法",
                "機關採購工作及審查小組設置及作業辦法",
                "採購評選委員會組織準則",
                "採購評選委員會審議規則",
                "電子採購作業辦法",
                "機關主會計及有關單位會同監辦採購辦法",
            ],  
            "特殊類型採購": [
                "古蹟歷史建築紀念建築及聚落建築群修復或再利用採購辦法",
                "九二一地震災區歷史建築修復工程採購辦法",
                "考古遺址調查研究發掘採購辦法",
                "文化藝術採購辦法",
                "法人或團體接受機關補助辦理藝文採購監督管理辦法",
                "科學技術研究發展採購監督管理辦法",
                "特別採購招標決標處理辦法",
                "國外採購財物辦法",
            ],  
            "機關採購策略與對象優先辦法":[
                "扶助中小企業參與政府採購辦法",
                "經濟部創新產品或服務優先採購辦法",
                "機關優先採購環境保護產品辦法",
                "優先採購身心障礙福利機構團體或庇護工場生產物品及服務辦法",
                "機關指定地區採購房地產作業辦法",
                "外國廠商參與非條約協定採購處理辦法",
                "機關辦理涉及國家安全採購之廠商資格限制條件及審查作業辦法",
            ],  
           "申訴、調解、稽核與委員會規範_爭議與監督制度":[
               "採購申訴審議收費辦法",
               "採購申訴審議委員會組織準則",
               "採購申訴審議規則",
               "採購履約爭議調解收費辦法",
               "採購履約爭議調解規則",
               "採購履約爭議調解暨收費規則",
               "採購稽核小組作業規則",
               "採購稽核小組組織準則",
               "採購專業人員資格考試訓練發證及管理辦法",
            ],
            "國防與軍事相關採購法案": [
                "新式戰機採購特別條例",
                "海空戰力提升計畫採購特別條例",
                "執行海空戰力提升計畫一定金額以上採購辦法",
                "軍事機關軍品採購辦法",
                "志願役退除役軍人法人或團體優先承包國防部特殊軍事安全或技術勞務採購處理辦法",
                "特殊軍事採購適用範圍及處理辦法",
            ],  
            "自由貿易港區與租稅優惠相關辦法":[
                "營利事業於自由貿易港區從事貨物採購輸入儲存或運送免徵營利事業所得稅辦法",
                "營利事業於國際機場園區內之自由貿易港區從事貨物採購輸入儲存或運送免徵營利事業所得稅辦法",
            ],  
        },  
        "採購相關標準規範": {
            "公共工程委員會標準規範": [
                "公共工程勞務採購契約範本",  
                "公共工程技術服務契約範本",  
                "公共工程專案管理契約範本",  
                "公共工程投標須知範本",  
                "公共工程統包工程採購契約範本",  
                "公共工程資訊服務採購契約範本",  
            ],  
            "經濟部產業發展署": [
                "經濟部產業發展署投標須知範本",  
                "經濟部產業發展署113年度委辦契約書範本",  
                "經濟部產業發展署計畫構想書範本",  
                "經濟部產業發展署廠商評選須知範本",  
            ],  
            "臺北市政府": [
                "臺北市政府投標須知範本",  
                "臺北市政府需求說明書範本",  
                "臺北市政府勞務採購契約範本",  
                "臺北市政府勞務評選須知範本",  
            ],  
            "環境部環境管理署": [
                "環境部環境管理署投標須知範本",  
                "環境部環境管理署專業技術或資訊服務委辦類採購契約書補充條款範本",  
		"環境部環境管理署專業(技術或資訊)服務投標須知補充規定",
                "環境部環境管理署投標須知資訊系統相關補充規定範本",  
                "環境部環境管理署勞務採購契約範本",  
		"環境部環境管理署評選作業須知範本",
            ],  
        },
        "契約審查": {  
            "投標前契約審查表": [
                "附表-契約書(投標前)審查要項檢查表－公共工程",
                "附表-契約書(投標前)審查要項檢查表－民間工程",
            ],  
        },
    }})      
    return laws

def fields_dict():
    laws=laws_dict()
    law_field={}
    for f in laws.keys():
        for m in laws[f].keys():
            for s in laws[f][m].keys():
                law_field.update({i:f for i in laws[f][m][s]})
    return law_field
def get_mom():
    mom=f"""
    '空氣污染防制法',
    """.replace("'","").split(',')
    mom2=f"""
    '環境基本法',
    '環境影響評估法',
    '水污染防治法',
    '廢棄物清理法',
    '土壤及地下水污染整治法',
    '毒性及關注化學物質管理法',
    '溫室氣體減量及管理法',
    '噪音管制法',
    '室內空氣品質管理法',
    '低放射性廢棄物最終處置設施場址設置條例',
    '工廠管理輔導法',
    '放射性物料管理法',
    '民用航空法',
    '海洋污染防治法',
    '游離輻射防護法',
    '災害防救法',
    '石油管理法',
    '科學園區設置管理條例',
    '船舶防止污染國際公約',
    '規費法',
    '野生動物保育法',
    '食品安全衛生管理法'
    """.replace("'","").split(',')
    return mom
def reverse_lookup(regulation_name):
    laws = laws_dict()
    for field, main_category in laws.items():
        for subcategory, itms in main_category.items():
            if type(itms)==list:
                if regulation_name in itms:
                    return field, subcategory, None
            else:   
                for item, reg_list in itms.items():
                    if regulation_name in reg_list:
                        return field, subcategory, item
    return None, None, None

def reverse_lookupV(regulation_name):
    laws = laws_dict()
    for field, main_category in laws.items():
        for subcategory, itms in main_category.items():
            if type(itms)==list:
                if regulation_name in itms:
                    return list(laws).index(field), list(main_category).index(subcategory), itms.index(regulation_name), 0
            else:   
                for item, reg_list in itms.items():
                    if regulation_name in reg_list:
                        return list(laws).index(field), list(main_category).index(subcategory), list(itms).index(item),reg_list.index(regulation_name)
    return None, None, None, None

def search_keyword(query: str, keyword_data:list):
    # 這裡是模擬篩選邏輯，可以很靈活自訂
    return [item for item in keyword_data if query in item]

def selector_raptor(query):
    field_raptor=raptor_dicts()[0]
    field_raptor.update({None:None})
    kws={
	"air":"空氣污染 空污 空氣汙染 空氣 空品 空".split(),
	"water":"水量 水質 河川 流域 放流 水措".split(),
	"sw":"土水 土壤 地下水 廢棄 回收 毒 有害".split(),
	"eia":"環評 評估 認定 監測 環保事項 補充調查 現地 追蹤 開發".split(),
	}
    for k in kws.keys():
        if any(v in query for v in kws[k]): return k	
    lst=[]
    for i in range(5):
        lst.extend(ask_mistral(query,field_raptor))
    slaw=set(lst)
    a=[(lst.count(i),i) for i in slaw]
    a.sort
    raptor=a[0][1]
    if raptor not in field_raptor.values():raptor=None
    return  raptor

def ask_mistral(query,law_dict):
    import requests
    base_url = "http://172.20.31.7:55080"
    model_name = "mistral:latest"
    prompt= f"""
    你是一個聰明、又很有耐心的律師，我會給你一段法律相關的問題，請按照符合度的優先順序，建議我繼續開啟哪(些)個類別的搜尋引擎，
    請回答英文的名稱(序列)就好，不要有別的解釋或建議、不要有索引值以外的客套話，不可以有超出索引範圍的答案，至多限定有2個答案。
    以下是我已經建好的索引：{law_dict}。
    以下是我的詢問：{query}。
    """

    response = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model_name,
            "prompt": prompt,
            "max_tokens": 2048,
            "temperature": 0.0,
            "stream": False  # 設為 False 代表一次回傳完整結果
        }
    )
    if response.status_code == 200:
        result = response.json()
        msg=result.get("response", "無回應")
    else:
        msg=f"錯誤：{response.status_code} - {response.text}"
    if type(msg)==str and ' ' in msg:
        for s in "[]',"+'"':
            msg=msg.replace(s,'')
        msg=msg.split()
    if None in msg and len(msg)>1:
        msg=[x for x in msg if x is not None]
    return msg

def raptor_dicts():
    field_raptor={"空氣污染相關法規":"air","環評、生態與噪音法規":"eia", "水質及水污染相關法規":"water","土壤、毒性物質與廢棄物相關法規":"sw","採購與契約相關法規":"proc"}
    raptor_field={j:i for i,j in field_raptor.items()}
    return field_raptor, raptor_field
