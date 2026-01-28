import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- ✨ スマホ用・レイアウト崩れ防止CSS（最重要） ---
st.markdown("""
    <style>
    /* 1. 7列を強制的に横並びにする（折り返し禁止） */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        width: 14.28% !important;
        min-width: 0 !important;
        flex: 1 1 0% !important;
    }
    /* 2. ボタンを正方形に近いカレンダー風にする */
    .stButton > button {
        width: 100% !important;
        height: 55px !important;
        padding: 0 !important;
        border-radius: 8px !important;
        border: 1px solid #f0f0f0 !important;
        background-color: #fff !important;
        line-height: 1.2 !important;
        display: block !important;
    }
    /* 3. 出勤日と選択日の色分け */
    .has-shift button {
        background-color: #FFF5F7 !important;
        color: #FF4B4B !important;
    }
    .selected-day button {
        border: 2px solid #FF4B4B !important;
        background-color: #FFF0F2 !important;
    }
    /* 4. 日付数字とドットのサイズ */
    .day-text { font-size: 0.8rem; font-weight: bold; }
    .dot-text { font-size: 0.6rem; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🛰 巡回同期関数（既存の正確なロジックを継承） ---
def sync_my_personal_shift(login_id, hp_name, shop_id):
    try:
        today = datetime.date.today()
        conn.table("shifts").delete().eq("cast_id", login_id).gte("date", today.isoformat()).lte("date", (today + datetime.timedelta(days=7)).isoformat()).execute()
        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://ikekari.com/attend.php"
        found_count = 0
        for i in range(7):
            t_date = today + datetime.timedelta(days=i)
            res = requests.get(f"{base_url}?date_get={t_date.strftime('%Y/%m/%d')}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            target_element = soup.find(string=re.compile(re.escape(hp_name.strip())))
            if target_element:
                container_text = "".join([p.get_text() for p in list(target_element.parents)[:3]])
                time_match = re.search(r'(\d{1,2}[:：]\d{2}.{0,5}\d{1,2}[:：]\d{2})|(\d{1,2}[:：]\d{2}.{0,2}[〜~〜-])', container_text)
                shift_time = time_match.group(0) if time_match else "時間未定"
                conn.table("shifts").insert({"date": t_date.isoformat(), "cast_id": login_id, "shop_id": shop_id, "shift_time": shift_time, "status": "確定"}).execute()
                found_count += 1
            time.sleep(0.2)
        return found_count
    except Exception as e:
        return 0

# --- 3. 🔐 ログイン認証（簡易版） ---
if "user_info" not in st.session_state:
    st.title("💖 キャストポータル")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["user_info"] = user_res.data[0]
            st.rerun()
    st.stop()

# --- 4. メイン画面レイアウト ---
user = st.session_state["user_info"]
now = datetime.date.today()

# A. 売上見込みカード（デザイン重視）
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        <span style="color: #666; font-size: 0.8em; font-weight: bold;">今日の売上見込み ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500</span>
    </div>
    """, unsafe_allow_html=True)

# B. スケジュール・同期ボタン
h_col1, h_col2 = st.columns([0.65, 0.35])
with h_col1:
    st.subheader("📅 スケジュール")
with h_col2:
    if st.button("🔄 同期", use_container_width=True):
        with st.spinner("更新中"):
            cnt = sync_my_personal_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
            st.toast(f"{cnt}件の予定を同期しました！")
            st.rerun()

# C. カレンダー表示（ボタン形式）
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

# DBからシフト取得
shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
shift_dict = {s['date']: s['shift_time'] for s in shift_res.data}

year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# 曜日ヘッダー
cols_h = st.columns(7)
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    color = "#FF3B30" if i==6 else "#007AFF" if i==5 else "#999"
    cols_h[i].markdown(f"<div style='text-align:center; font-size:0.65rem; color:{color}; font-weight:bold;'>{wd}</div>", unsafe_allow_html=True)

# カレンダー本体
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            d_obj = datetime.date(year, month, day)
            d_str = d_obj.isoformat()
            is_shift = d_str in shift_dict
            is_selected = (st.session_state.selected_date == d_str)
            
            # クラス判定（CSS適用用）
            btn_class = "has-shift" if is_shift else ""
            if is_selected: btn_class += " selected-day"
            
            # ボタン表示内容
            dot = "●" if is_shift else ""
            label = f"{day}\n{dot}"
            
            # ボタンの配置
            st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
            if cols[i].button(label, key=f"btn_{d_str}"):
                st.session_state.selected_date = d_str
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            cols[i].empty()

# D. 選択された日の詳細表示
st.divider()
sel_d = datetime.date.fromisoformat(st.session_state.selected_date)
st.markdown(f"#### 📝 {sel_d.month}月{sel_d.day}日の予定")

with st.container(border=True):
    if st.session_state.selected_date in shift_dict:
        st.success(f"⏰ 出勤予定時間：**{shift_dict[st.session_state.selected_date]}**")
        st.info("🏢 勤務店舗：池袋西口店")
    else:
        st.write("この日の出勤予定はありません。")
