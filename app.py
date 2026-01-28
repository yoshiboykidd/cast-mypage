import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. [CRITICAL] ページ設定 ---
st.set_page_config(page_title="かりんとポータル ver 3.30", page_icon="💖", layout="centered")

# --- 2. 🔐 セッション永続化ガード ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.date.today()

# Supabase接続
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("DB接続エラー。Secretsを確認してください。")
    st.stop()

# --- 3. 🛰️ 同期ロジック ---
def sync_individual_shift(user_info):
    hp_name = user_info.get('hp_display_name')
    if not hp_name: return "HP名未設定", 0
    headers = {"User-Agent": "Mozilla/5.0"}
    base_url = "https://ikekari.com/attend.php"
    time_pattern = r"(\d{1,2}[:時]\d{0,2})\s*[-～〜]\s*(\d{1,2}[:時]\d{0,2}|LAST|last|ラスト|翌\d{1,2}[:時]\d{0,2})"
    found_count = 0
    
    for i in range(7):
        target_date = datetime.date.today() + datetime.timedelta(days=i)
        date_iso = target_date.isoformat()
        try:
            res = requests.get(f"{base_url}?date_get={target_date.strftime('%Y/%m/%d')}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            target_element = soup.find(string=re.compile(hp_name))
            if target_element:
                container = target_element.find_parent().find_parent()
                time_match = re.search(time_pattern, container.get_text(strip=True))
                shift_time = time_match.group(0) if time_match else "時間未定"
                conn.table("shifts").upsert({
                    "date": date_iso, "cast_id": user_info['login_id'],
                    "shop_id": user_info['home_shop_id'], "status": "確定", "shift_time": shift_time
                }).execute()
                found_count += 1
            else:
                conn.table("shifts").delete().eq("date", date_iso).eq("cast_id", user_info['login_id']).execute()
        except: pass
        time.sleep(0.05)
    return "同期完了", found_count

# --- 4. 🔑 ログイン画面 ---
if not st.session_state["password_correct"]:
    st.title("🔐 ログイン (ver 3.30)")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["user_info"] = user_res.data[0]
            st.session_state["password_correct"] = True
            sync_individual_shift(st.session_state["user_info"])
            st.rerun()
        else:
            st.error("認証失敗")
    st.stop()

user = st.session_state["user_info"]

# --- 5. メインUI ---
st.title(f"かりんとポータル ver 3.30")

# キラキラヘッダー
sel_d = st.session_state["selected_date"]
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em; font-weight: bold;">{sel_d.month}/{sel_d.day} の売上見込み ✨</span><br>
        <span style="font-size: 1.5em; font-weight: bold; color: #333;">¥ 28,500</span>
    </div>
    """, unsafe_allow_html=True)

# 同期ボタン
col_t, col_s = st.columns([6, 4])
with col_t: st.subheader("📅 スケジュール")
with col_s:
    if st.button("🔄 同期", use_container_width=True):
        sync_individual_shift(user)
        st.rerun()

# --- 6. 🗓️ カレンダー描画 (超凝縮・横スクロール禁止版) ---
st.markdown("""
<style>
    /* 1. カラムの余白を極限まで削る [cite: 2026-01-28] */
    [data-testid="stHorizontalBlock"] {
        gap: 2px !important;
    }
    [data-testid="column"] {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    
    /* 2. ボタンを画面幅に合わせて縮小させる [cite: 2026-01-28] */
    div.stButton > button {
        border: 1px solid #eee !important;
        background-color: white !important;
        height: 45px !important;
        width: 100% !important;
        padding: 0 !important;
        font-size: 3.5vw !important; /* スマホ画面幅に合わせた流動サイズ */
        line-height: 1 !important;
    }
    
    /* 3. 選択中などの特殊スタイル [cite: 2026-01-28] */
    .st-emotion-cache-ke6u7 { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_map = {s['date']: s['shift_time'] for s in shift_res.data}
except: shift_map = {}

now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)
week_days = ["月", "火", "水", "木", "金", "土", "日"]

# 曜日（超省スペース）
w_cols = st.columns(7)
for i, wd in enumerate(week_days):
    color = "#007AFF" if i==5 else "#FF3B30" if i==6 else "#888"
    w_cols[i].markdown(f"<div style='text-align:center; font-size:2.5vw; color:{color};'>{wd}</div>", unsafe_allow_html=True)

# 日付グリッド
for week in cal:
    d_cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            cell_date = datetime.date(now.year, now.month, day)
            date_iso = cell_date.isoformat()
            
            # ラベル（出勤は「点」ではなく「*」など短い記号に）
            label = f"{day}"
            if date_iso in shift_map: label += " *" 
            
            # 日曜・土曜の装飾
            if i == 6: label = f"r{day}" # 赤っぽく見える工夫
            
            if d_cols[i].button(label, key=f"d_{date_iso}", use_container_width=True):
                st.session_state["selected_date"] = cell_date
                st.rerun()

# --- 7. 🕒 詳細表示 ---
selected_date = st.session_state["selected_date"]
st.markdown(f"#### {selected_date.month}/{selected_date.day} の予定")

with st.container(border=True):
    date_key = selected_date.isoformat()
    if date_key in shift_map:
        st.info(f"🕒 シフト：{shift_map[date_key]}")
    else:
        st.write("予定なし")

with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
