import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

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

# A. 売上見込みエリア（画像のデザインを反映）
st.markdown("""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. 【改善版】絶対に崩れないカレンダー
st.subheader("📅 カレンダー")

now = datetime.datetime.now()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# HTMLでカレンダーを直接記述（これが一番確実です）
cal_html = f"""
<style>
    .calendar-table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed; /* これで列幅を均等に固定 */
    }}
    .calendar-table th {{
        text-align: center;
        font-size: 0.8em;
        color: #FF4B4B;
        padding: 5px 0;
    }}
    .calendar-table td {{
        text-align: center;
        padding: 8px 0;
        border: 1px solid #eee;
        font-size: 0.9em;
        background-color: white;
        border-radius: 5px;
    }}
    .today-cell {{
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: bold;
    }}
</style>
<table class="calendar-table">
    <tr>
        <th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th>土</th><th style="color:red;">日</th>
    </tr>
"""

for week in cal:
    cal_html += "<tr>"
    for day in week:
        if day == 0:
            cal_html += "<td></td>"
        else:
            style_class = "today-cell" if day == now.day else ""
            cal_html += f'<td class="{style_class}">{day}</td>'
    cal_html += "</tr>"

cal_html += "</table>"

# HTMLを埋め込む
st.markdown(cal_html, unsafe_allow_html=True)

# C. 今日のスケジュール詳細
st.divider()
st.markdown(f"### 📝 本日の予定")

with st.container(border=True):
    # ここに将来 shifts テーブルのデータを表示する
    st.write("**⏰ シフト：19:00 - 24:00**")
    st.write("📌 予約：1件 (20:30〜)")
    st.caption("店舗：池袋西口店")

# D. お知らせエリア
st.divider()
st.subheader("📢 お知らせ")
st.info("重要：ドレスコードが変更になります 👗")
st.success("ユキちゃん「リピートNo.1」バッジおめでとう！ 🎊")

# --- 4. サイドバーメニュー ---
with st.sidebar:
    st.title("Menu")
    st.button("🏠 ホーム")
    st.button("📝 実績報告")
    st.button("📤 シフト申請")
