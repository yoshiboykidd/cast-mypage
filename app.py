import streamlit as st
import calendar
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="Cast My Page", layout="wide")

# --- 1. 強制7列表示 & デザイン調整のCSS ---
st.markdown("""
    <style>
    /* スマホでも強制的に7列並べる設定 */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 0.5rem !important;
    }
    [data-testid="column"] {
        width: 14.2% !important; /* 100/7 */
        min-width: 0px !important;
        flex-shrink: 0 !important;
    }
    
    /* 枠の形を整える */
    [data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 80px !important;
        padding: 2px !important;
    }
    .date-text {
        font-weight: bold;
        font-size: 0.9rem;
        text-align: center;
    }
    .weekday-header {
        text-align: center;
        font-size: 0.8rem;
        font-weight: bold;
        padding: 5px 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. データ同期ロジック（土台） ---
def sync_schedule_data():
    """
    ここにGoogleスプレッドシートやSupabaseからの読み込み処理を記述します。
    """
    # 実際の実装例：
    # conn = st.connection("gsheets", type=GSheetsConnection)
    # df = conn.read(worksheet="Schedule")
    st.session_state["last_sync"] = datetime.now().strftime("%H:%M:%S")
    st.toast("最新のスケジュールを同期しました！")

# --- 3. ヘッダー ---
col_h1, col_h2 = st.columns([7, 3])
with col_h1:
    st.subheader("📅 スケジュール")

with col_h2:
    # 同期ボタンの実行
    if st.button("🔄 同期", use_container_width=True):
        sync_schedule_data()

# 同期時刻の表示
if "last_sync" in st.session_state:
    st.caption(f"最終同期: {st.session_state['last_sync']}")

# --- 4. カレンダー表示 ---
now = datetime.now()
cal = calendar.monthcalendar(now.year, now.month)
week_days = ["月", "火", "水", "木", "金", "土", "日"]

# 曜日ヘッダー
header_cols = st.columns(7)
for i, day_name in enumerate(week_days):
    color = "#FF4B4B" if i == 6 else "#1C83E1" if i == 5 else "inherit"
    header_cols[i].markdown(f"<div class='weekday-header' style='color:{color};'>{day_name}</div>", unsafe_allow_html=True)

# カレンダー本体
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                with st.container(border=True):
                    color = "#FF4B4B" if i == 6 else "#1C83E1" if i == 5 else "inherit"
                    st.markdown(f"<div class='date-text' style='color:{color};'>{day}</div>", unsafe_allow_html=True)
                    
                    # --- データがある場合に表示する例 ---
                    # if has_shift(day):
                    #     st.markdown("<div style='font-size:0.7rem; color:orange; text-align:center;'>出勤</div>", unsafe_allow_html=True)
