import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import jpholiday # 祝日判定用

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

# A. 売上見込み（画像デザイン反映）
st.markdown("""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. 【詳細カスタマイズ版】カレンダー
st.subheader("📅 カレンダー")

now = datetime.date.today()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# --- テスト用：シフト日 ---
shift_days = [28, 30, 31]

# HTML/CSS構築
cal_html = f"""
<style>
    .calendar-table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }}
    .calendar-table th {{
        text-align: center;
        font-size: 0.7em;
        padding: 5px 0;
    }}
    .calendar-table td {{
        vertical-align: top; /* 左上に配置するために必須 */
        padding: 5px;
        border: 1px solid #f0f0f0;
        height: 45px; /* 枠の高さを固定 */
        background-color: white;
        position: relative;
    }}
    .day-num {{
        font-size: 0.75em;
        font-weight: bold;
        display: block;
        text-align: left;
    }}
    /* 土曜:青 / 日祝:赤 / 平日:黒 の色指定 */
    .sat {{ color: #007AFF; }}
    .sun-hol {{ color: #FF3B30; }}
    .weekday {{ color: #333; }}

    /* シフトドット */
    .has-shift::after {{
        content: '●';
        color: #FF4B4B;
        font-size: 8px;
        position: absolute;
        bottom: 5px;
        left: 50%;
        transform: translateX(-50%);
    }}
    /* 今日のハイライト（枠を薄いピンクに） */
    .today-cell {{
        background-color: #FFF0F2 !important;
        border: 2px solid #FF4B4B !important;
    }}
</style>
<table class="calendar-table">
    <tr>
        <th class="weekday">月</th><th class="weekday">火</th><th class="weekday">水</th>
        <th class="weekday">木</th><th class="weekday">金</th><th class="sat">土</th><th class="sun-hol">日</th>
    </tr>
"""

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0:
            cal_html += "<td></td>"
        else:
            current_date = datetime.date(year, month, day)
            is_holiday = jpholiday.is_holiday(current_date)
            
            # クラス判定
            day_class = "weekday"
            if i == 5: day_class = "sat" # 土曜
            if i == 6 or is_holiday: day_class = "sun-hol" # 日曜または祝日
            
            td_classes = []
            if day == now.day: td_classes.append("today-cell")
            if day in shift_days: td_classes.append("has-shift")
            
            td_class_str = f'class="{" ".join(td_classes)}"' if td_classes else ""
            
            cal_html += f"""
                <td {td_class_str}>
                    <span class="day-num {day_class}">{day}</span>
                </td>
            """
    cal_html += "</tr>"

cal_html += "</table>"
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

# D. サイドバー
with st.sidebar:
    st.title("Menu")
    st.button("🏠 ホーム", use_container_width=True)
    st.button("📝 実績報告", use_container_width=True)
