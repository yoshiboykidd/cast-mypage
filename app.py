import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. [CRITICAL] ページ設定 ---
st.set_page_config(page_title="かりんとポータル ver 4.50", layout="centered")

# --- 2. 🔐 セッション永続化ガード (URL変更を排除) ---
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
    st.error("DB接続エラー。Secretsの設定を確認してください。")
    st.stop()

# --- 3. 🛰️ 同期ロジック (時間解析込) ---
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
    st.title("🔐 ログイン (ver 4.50)")
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

# --- 5. 🎨 [PRO HACK] 絶対に崩れない・スクロールしないCSS ---
st.markdown("""
<style>
    /* 1. カラムの余白を抹殺し、スマホでも強制的に横に7個並べる [cite: 2026-01-28] */
    [data-testid="stHorizontalBlock"] {
        gap: 0px !important;
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        overflow: hidden !important; /* 横スクロールを物理的に禁止 */
    }
    
    /* 2. 各列の幅を正確に1/7に固定 [cite: 2026-01-28] */
    [data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        width: 14.28% !important;
        padding: 1px !important;
    }

    /* 3. ボタンをスマホサイズに極限まで最適化 [cite: 2026-01-28] */
    div.stButton > button {
        border: 1px solid #eee !important;
        background-color: white !important;
        height: 42px !important; /* 高さを抑えて視認性向上 */
        width: 100% !important;
        padding: 0 !important;
        font-size: 11px !important; /* 画面を突き抜けない最小サイズ */
        border-radius: 4px !important;
        line-height: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 6. メインUI ---
# キラキラヘッダー
sel_d = st.session_state["selected_date"]
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em; font-weight: bold;">{sel_d.month}/{sel_d.day} の売上 ✨</span><br>
        <span style="font-size: 1.5em; font-weight: bold; color: #333;">¥ 28,500</span>
    </div>
    """, unsafe_allow_html=True)

# カレンダー見出しと同期
col_t, col_s = st.columns([6, 4])
with col_t: st.subheader("📅 スケジュール")
with col_s:
    if st.button("🔄 同期", use_container_width=True):
        sync_individual_shift(user)
        st.rerun()

# --- 7. 🗓️ カレンダー描画 ---
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
    w_cols[i].markdown(f"<div style='text-align:center; font-size:10px; color:{color};'>{wd}</div>", unsafe_allow_html=True)

# 日付グリッド
for week in cal:
    d_cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            cell_date = datetime.date(now.year, now.month, day)
            date_iso = cell_date.isoformat()
            
            # 出勤・曜日による装飾
            btn_label = str(day)
            if date_iso in shift_map: btn_label += "●"
            
            # 【絶対ログアウトしない】内部セッション書き換え方式 [cite: 2026-01-28]
            if d_cols[i].button(btn_label, key=f"d_{date_iso}", use_container_width=True):
                st.session_state["selected_date"] = cell_date
                st.rerun()

# --- 8. 🕒 詳細表示 ---
selected_date = st.session_state["selected_date"]
st.markdown(f"#### {selected_date.month}/{selected_date.day} の予定")

with st.container(border=True):
    date_key = selected_date.isoformat()
    if date_key in shift_map:
        st.info(f"🕒 シフト：{shift_map[date_key]}")
    else:
        st.write("予定はありません。")

with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
