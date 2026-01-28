import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

# --- ✨ スマホ用固定グリッドCSS ---
# これを入れることで、スマホでもカレンダーの7列が崩れません
st.markdown("""
    <style>
    .cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 4px;
        text-align: center;
    }
    .cal-day {
        padding: 8px 0;
        background-color: #f8f9fa;
        border-radius: 8px;
        font-size: 0.8em;
        cursor: pointer;
    }
    .cal-header {
        font-weight: bold;
        color: #FF4B4B;
        padding-bottom: 5px;
    }
    .today {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🔐 ログイン認証（プロトタイプ用） ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    if st.button("テストログイン"):
        st.session_state["password_correct"] = True
        st.session_state["user_info"] = {"display_name": "ユキちゃん", "login_id": "00100001"}
        st.rerun()
    st.stop()

# --- 3. メインレイアウト ---
user = st.session_state["user_info"]

# A. 売上カード（見込み）
with st.container(border=True):
    st.caption("今日の売上 (見込み) ✨")
    st.markdown("<h2 style='text-align: center; margin:0;'>¥ 28,500</h2>", unsafe_allow_html=True)
    st.progress(0.65)

# B. 【固定グリッドカレンダー】
st.subheader("📅 カレンダー")

now = datetime.datetime.now()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# カレンダーのヘッダー（月火水木金土日）
cols = st.columns(7)
days_header = ["月", "火", "水", "木", "金", "土", "日"]
for i, d in enumerate(days_header):
    cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#FF4B4B;'>{d}</div>", unsafe_allow_html=True)

# カレンダーの日付部分（ボタン形式でタップ可能に）
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write("")
        else:
            # 今日の日付を強調
            is_today = (day == now.day)
            label = f"**{day}**" if is_today else str(day)
            
            # use_container_widthで横幅いっぱいにボタンを広げる
            if cols[i].button(label, key=f"d_{day}", use_container_width=True):
                st.session_state["selected_date"] = day

# C. 今日のスケジュール（カレンダーの下に配置）
st.subheader("📝 スケジュール詳細")
selected_day = st.session_state.get("selected_date", now.day)

with st.container(border=True):
    st.write(f"**{month}月{selected_day}日 の予定**")
    # ここに shifts テーブル等のデータを紐付ける
    st.info(f"⏰ シフト：19:00 - 24:00\n\n📌 予約：1件 (20:30〜)")

# D. お知らせエリア
st.divider()
with st.expander("📢 お店からのお知らせ"):
    st.write("・明日のドレスコードについて")
    st.write("・新店オープンのお知らせ")

# --- 4. サイドバーメニュー ---
with st.sidebar:
    st.title("Menu")
    st.button("🏠 ホーム", use_container_width=True)
    st.button("📝 実績報告", use_container_width=True)
    st.button("📤 シフト申請", use_container_width=True)
