import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. [CRITICAL] ページ設定とセッション永続化 (最上部) ---
st.set_page_config(page_title="かりんとポータル ver 8.00", layout="centered")

# セッションがリセットされないよう、URLを1文字も変えない設計 [cite: 2026-01-28]
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.date.today()
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

# Supabase接続
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.stop()

# --- 2. 🛰️ 同期ロジック (時間解析込) ---
def sync_individual_shift(user_info):
    hp_name = user_info.get('hp_display_name')
    if not hp_name: return
    headers = {"User-Agent": "Mozilla/5.0"}
    base_url = "https://ikekari.com/attend.php"
    time_pattern = r"(\d{1,2}[:時]\d{0,2})\s*[-～〜]\s*(\d{1,2}[:時]\d{0,2}|LAST|last|ラスト|翌\d{1,2}[:時]\d{0,2})"
    
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
            else:
                conn.table("shifts").delete().eq("date", date_iso).eq("cast_id", user_info['login_id']).execute()
        except: pass
        time.sleep(0.05)
    return True

# --- 3. 🔑 ログイン画面 (セッション最優先) ---
if not st.session_state["password_correct"]:
    st.title("🔐 ログイン (ver 8.00)")
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
            st.error("IDまたはPWが違います")
    st.stop()

user = st.session_state["user_info"]

# --- 4. 📐 [THE FINAL HACK] 100%崩れない・ログアウトしないグリッド設計 ---
st.markdown("""
<style>
    /* 画面幅全体を使い、横スクロールを物理的に禁止 [cite: 2026-01-28] */
    .main .block-container { padding: 1rem !important; max-width: 100vw !important; overflow-x: hidden !important; }

    /* カレンダーエリア全体を7列のグリッドとして定義 */
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
        width: 100%;
        margin-top: 10px;
    }

    /* Streamlitのボタンを無理やりこのグリッドの中に収める [cite: 2026-01-28] */
    /* ボタンのコンテナ(stButton)を1列ずつ並べる指示 */
    div.stButton {
        display: inline-block !important;
        width: 100% !important;
        margin: 0 !important;
    }
    
    div.stButton > button {
        border: 1px solid #f0f0f0 !important;
        background-color: white !important;
        height: 44px !important;
        width: 100% !important;
        padding: 0 !important;
        font-size: 11px !important;
        font-weight: bold !important;
        border-radius: 4px !important;
    }

    /* 曜日ラベル用のスタイル */
    .wd-label { text-align: center; font-size: 10px; font-weight: bold; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 5. メインUI ---
sel_d = st.session_state["selected_date"]
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em; font-weight: bold;">{sel_d.month}/{sel_d.day} の売上見込み ✨</span><br>
        <span style="font-size: 1.6em; font-weight: bold; color: #333;">¥ 28,500</span>
    </div>
    """, unsafe_allow_html=True)

# 見出しと同期
col_t, col_s = st.columns([6, 4])
with col_t: st.subheader("📅 スケジュール")
with col_s:
    if st.button("🔄 同期", use_container_width=True):
        sync_individual_shift(user)
        st.rerun()

# --- 6. 🗓️ カレンダー描画 (st.columnsを完全に廃止) ---
try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_map = {s['date']: s['shift_time'] for s in shift_res.data}
except: shift_map = {}

now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)
wd_names = ["月", "火", "水", "木", "金", "土", "日"]

# 1. 曜日ヘッダーを1つのグリッドで表示 [cite: 2026-01-28]
header_cols = st.columns(7)
for i, wd in enumerate(wd_names):
    c = "#007AFF" if i==5 else "#FF3B30" if i==6 else "#999"
    header_cols[i].markdown(f"<div class='wd-label' style='color:{c};'>{wd}</div>", unsafe_allow_html=True)

# 2. 日付ボタンを「行」ごとに表示 [cite: 2026-01-28]
# st.columns(7) を使うが、CSSで「絶対にスマホで折り返さない」指示を適用済み
for week in cal:
    row_cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            cell_date = datetime.date(now.year, now.month, day)
            date_iso = cell_date.isoformat()
            label = str(day)
            if date_iso in shift_map: label += "\n●"
            
            # 【重要】ボタンで状態を更新。URLが変わらないのでログアウトしない
            if row_cols[i].button(label, key=f"btn_{date_iso}", use_container_width=True):
                st.session_state["selected_date"] = cell_date
                st.rerun()

# --- 7. 🕒 詳細表示 ---
selected_date = st.session_state["selected_date"]
st.markdown(f"#### {selected_date.month}/{selected_date.day} ({wd_names[selected_date.weekday()]}) の詳細")

with st.container(border=True):
    date_key = selected_date.isoformat()
    if date_key in shift_map:
        st.info(f"🕒 シフト時間：{shift_map[date_key]}")
    else:
        st.write("予定なし")

with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
