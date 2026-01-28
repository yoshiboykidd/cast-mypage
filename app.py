import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

# 祝日判定（jpholidayがインストールされている場合）
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

# A. 売上見込み（ご提示いただいた画像イメージを反映）
st.markdown("""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        <span style="color: #666; font-size: 0.8em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. 【視認性強化版】カレンダー
st.subheader("📅 カレンダー")

now = datetime.date.today()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# --- 💡 シフト情報のマッピング（実際はDBから取得） ---
# 例：28日, 30日, 31日にシフトがある場合
shift_days = [28, 30, 31]

# スタイル定義
cal_style = """
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; border: none; }
    .calendar-table th { text-align: center; font-size: 0.75em; padding: 10px 0; }
    .calendar-table td { vertical-align: top; height: 50px; border: 1px solid #f8f8f8; background-color: white; position: relative; padding: 4px; }
    
    /* 日付数字：左上に小さく */
    .day-num { font-size: 0.7em; font-weight: 800; position: absolute; top: 3px; left: 5px; }
    
    /* 曜日色分け */
    .weekday { color: #222; }
    .sat { color: #007AFF; }
    .sun-hol { color: #FF3B30; }

    /* 【視覚強化】シフトがある日のスタイル */
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar {
        position: absolute;
        bottom: 6px;
        left: 50%;
        transform: translateX(-50%);
        width: 18px;
        height: 4px;
        background-color: #FF4B4B;
        border-radius: 10px;
    }

    /* 今日のハイライト */
    .today-cell { box-shadow: inset 0 0 0 2px #FF4B4B; border-radius: 4px; }
</style>
"""

cal_html = cal_style + '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月", "火", "水", "木", "金", "土", "日"]):
    c = "weekday"
    if i == 5: c = "sat"
    if i == 6: c = "sun-hol"
    cal_html += f'<th class="{c}">{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0:
            cal_html += "<td></td>"
        else:
            cur_date = datetime.date(year, month, day)
            is_hol = jpholiday.is_holiday(cur_date) if jpholiday else False
            
            # 色判定
            d_color = "weekday"
            if i == 5: d_color = "sat"
            if i == 6 or is_hol: d_color = "sun-hol"
            
            # セルの装飾
            td_classes = []
            if day == now.day: td_classes.append("today-cell")
            if day in shift_days: td_classes.append("has-shift")
            
            td_class_str = f'class="{" ".join(td_classes)}"' if td_classes else ""
            
            # 出勤日の場合はバーを表示
            inner_html = f'<span class="day-num {d_color}">{day}</span>'
            if day in shift_days:
                inner_html += '<div class="shift-bar"></div>'
            
            cal_html += f'<td {td_class_str}>{inner_html}</td>'
    cal_html += "</tr>"

cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# C. 詳細エリア
st.divider()
st.markdown(f"### 📝 本日の予定")
with st.container(border=True):
    if now.day in shift_days:
        st.success("✅ 本日は出勤予定です")
        st.write("**⏰ 19:00 - 24:00**")
        st.write("🏢 池袋西口店")
    else:
        st.info("本日の出勤予定はありません")
