import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

# --- ✨ スマホで7列を強制するCSS（重要） ---
st.markdown("""
    <style>
    /* カラムの自動折り返しを禁止し、常に1/7の幅を維持する */
    [data-testid="column"] {
        width: calc(14.28% - 0.5rem) !important;
        flex: 1 1 calc(14.28% - 0.5rem) !important;
        min-width: calc(14.28% - 0.5rem) !important;
    }
    /* ボタンの余白を削ってカレンダーらしくする */
    .stButton > button {
        padding: 5px 0px !important;
        font-size: 0.8rem !important;
        border-radius: 5px !important;
    }
    /* 曜日ヘッダーのスタイル */
    .dow-header {
        text-align: center;
        font-weight: bold;
        font-size: 0.7rem;
        color: #FF4B4B;
    }
    /* 今日のハイライト */
    .today-marker {
        border: 2px solid #FF4B4B !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🔐 ログイン認証（プロトタイプ） ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    if st.button("テストログイン"):
        st.session_state["password_correct"] = True
        st.session_state["user_info"] = {"display_name": "ユキちゃん", "login_id": "00100001"}
        st.rerun()
    st.stop()

# --- 3. メイン画面構築 ---
user = st.session_state["user_info"]

# A. 売上見込みエリア（画像のデザインを意識）
st.markdown("""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. 【改善版】カレンダーエリア
st.subheader("📅 カレンダー")

now = datetime.datetime.now()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# 1. 曜日ヘッダー（ここが消えていたので追加）
cols_dow = st.columns(7)
weekdays = ["月", "火", "水", "木", "金", "土", "日"]
for i, wd in enumerate(weekdays):
    cols_dow[i].markdown(f"<div class='dow-header'>{wd}</div>", unsafe_allow_html=True)

# 2. カレンダーの日付グリッド
# どんなスマホでも強制的に7列で表示されます
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write("")
        else:
            # 今日の日付を特定
            is_today = (day == now.day)
            
            # ボタンを配置（タップで詳細切り替え）
            if cols[i].button(str(day), key=f"d_{day}", use_container_width=True):
                st.session_state["selected_date"] = day

# C. 今日のスケジュール詳細
st.divider()
selected_day = st.session_state.get("selected_date", now.day)
st.markdown(f"### 📝 {month}月{selected_day}日の予定")

with st.container(border=True):
    # 将来的にここを Supabase の shifts テーブルから取得するようにする
    st.write("**⏰ シフト：19:00 - 24:00**")
    st.write("📌 予約：1件 (20:30〜)")
    st.caption("※詳細は店舗掲示板を確認してください")

# D. お知らせエリア
st.divider()
st.subheader("📢 お知らせ")
st.info("重要：ドレスコードが変更になります 👗")
st.success("ユキちゃん「リピートNo.1」バッジおめでとう！ 🎊")
