import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

# 祝日判定ライブラリのインポート試行
try:
    import jpholiday
except ImportError:
    jpholiday = None

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

# A. 売上見込み
st.markdown("""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. 【修正版】カレンダー
st.subheader("📅 カレンダー")

now = datetime.date.today()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# --- テスト用：シフト日 ---
shift_days = [28, 30, 31]

# CSS定義（数字を左上に、色を曜日に合わせる）
cal_style = """
<style>
    .calendar-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    .calendar-table th {
        text-align: center;
        font-size: 0.75em;
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    .calendar-table td {
        vertical-align: top;
        height: 55px;
        border: 1px solid #f0f0f0;
        background-color: white;
        position: relative;
        padding: 4px;
    }
    .day-num {
        font-size: 0.7em; /* 数字を小さく */
        font-weight: bold;
        position: absolute;
        top: 2px;
        left: 4px;
    }
    /* 曜日ごとの色指定 */
    .weekday { color: #333; }
    .sat { color: #007AFF; }
    .sun-hol { color: #FF3B30; }

    /* シフトドット */
    .has-shift::after {
        content: '●';
        color: #FF4B4B;
        font-size: 10px;
        position: absolute;
        bottom: 8px;
        left: 50%;
        transform: translateX(-50%);
    }
    /* 今日を強調 */
    .today-cell {
        background-color: #FFF0F2 !important;
        box-shadow: inset 0 0 0 2px #FF4B4B;
    }
</style>
"""

# HTML構築
cal_html = cal_style + '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月", "火", "水", "木", "金", "土", "日"]):
    color_class = "weekday"
    if i == 5: color_class = "sat"
    if i == 6: color_class = "sun-hol"
    cal_html += f'<th class="{color_class}">{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0:
            cal_html += "<td></td>"
        else:
            current_date = datetime.date(year, month, day)
            is_holiday = jpholiday.is_holiday(current_date) if jpholiday else False
            
            # 文字色の判定
            day_color = "weekday"
            if i == 5: day_color = "sat"
            if i == 6 or is_holiday: day_color = "sun-hol"
            
            # セルのクラス
            td_classes = []
            if day == now.day: td_classes.append("today-cell")
            if day in shift_days: td_classes.append("has-shift")
            td_class_str = f'class="{" ".join(td_classes)}"' if td_classes else ""
            
            cal_html += f'<td {td_class_str}><span class="day-num {day_color}">{day}</span></td>'
    cal_html += "</tr>"

cal_html += "</table>"

# 重要：ここがHTMLとして表示させるための命令です
st.markdown(cal_html, unsafe_allow_html=True)

# C. 本日の予定
st.divider()
st.markdown(f"### 📝 本日の予定")
with st.container(border=True):
    if now.day in shift_days:
        st.success("✅ 本日は出勤予定です")
        st.write("**⏰ 19:00 - 24:00**")
        st.write("🏢 池袋西口店")
    else:
        st.info("本日の出勤予定はありません")
