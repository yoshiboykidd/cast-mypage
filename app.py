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

# B. 【改善版】シフトがわかるカレンダー
st.subheader("📅 カレンダー")

now = datetime.datetime.now()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# --- 💡 テスト用：シフトが入っている日（実際はDBから取得） ---
# 例：28日、30日、31日にシフトがあるとする
shift_days = [28, 30, 31]

# HTML/CSSでカレンダーを構築
cal_html = f"""
<style>
    .calendar-table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }}
    .calendar-table th {{
        text-align: center;
        font-size: 0.8em;
        color: #FF4B4B;
        padding: 5px 0;
    }}
    .calendar-table td {{
        text-align: center;
        padding: 10px 0;
        border: 1px solid #f0f0f0;
        font-size: 0.9em;
        background-color: white;
        position: relative; /* ドットを配置するために必要 */
    }}
    /* シフトがある日の印（ピンクのドット） */
    .has-shift::after {{
        content: '●';
        color: #FF4B4B;
        font-size: 8px;
        position: absolute;
        bottom: 2px;
        left: 50%;
        transform: translateX(-50%);
    }}
    /* 今日のハイライト */
    .today-cell {{
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: bold;
        border-radius: 5px;
    }}
</style>
<table class="calendar-table">
    <tr>
        <th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th style="color:#007AFF;">土</th><th style="color:red;">日</th>
    </tr>
"""

for week in cal:
    cal_html += "<tr>"
    for day in week:
        if day == 0:
            cal_html += "<td></td>"
        else:
            classes = []
            if day == now.day:
                classes.append("today-cell")
            if day in shift_days:
                classes.append("has-shift")
            
            class_str = f'class="{" ".join(classes)}"' if classes else ""
            cal_html += f'<td {class_str}>{day}</td>'
    cal_html += "</tr>"

cal_html += "</table>"

# カレンダーの表示
st.markdown(cal_html, unsafe_allow_html=True)

# C. 本日の予定（カレンダーの下）
st.divider()
st.markdown(f"### 📝 本日の予定")

with st.container(border=True):
    # シフトがあるかないかで表示を分ける
    if now.day in shift_days:
        st.success("✅ 本日は出勤予定です")
        st.write("**⏰ 19:00 - 24:00**")
        st.write("🏢 池袋西口店")
        st.caption("📌 予約あり：20:30〜 田中様")
    else:
        st.info("本日の出勤予定はありません")

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
