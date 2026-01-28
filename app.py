import streamlit as st
import calendar
from datetime import datetime

# --- 1. ページ設定 ---
st.set_page_config(page_title="Cast My Page", layout="wide")

# --- 2. 超省スペース＆レスポンシブCSS ---
st.markdown("""
    <style>
    /* 全体の余白を削る */
    .block-container {
        padding-top: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* 7列を強制し、横スクロールを禁止する */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 2px !important; /* 列間の隙間を最小に */
    }
    [data-testid="column"] {
        flex: 1 1 0% !important; /* 全ての列を均等に圧縮 */
        min-width: 0 !important;
    }
    
    /* 日付枠のサイズ調整 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 60px !important; /* 高さを少し抑える */
        padding: 1px !important;
        margin-bottom: 2px !important;
    }
    
    /* 文字サイズの最適化（スマホで溢れないように） */
    .date-text {
        font-weight: bold;
        font-size: min(3vw, 14px); /* 画面幅に合わせて変化 */
        text-align: center;
    }
    .weekday-header {
        text-align: center;
        font-size: min(2.5vw, 12px);
        font-weight: bold;
        padding-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 同期ロジックの再構築 ---
# セッション状態の初期化
if "schedule_data" not in st.session_state:
    st.session_state["schedule_data"] = {}
if "last_sync" not in st.session_state:
    st.session_state["last_sync"] = "未同期"

def handle_sync():
    """
    同期ボタンが押された時の処理
    ここにスプレッドシート(Google Sheets)からの読み込みコードを記述します。
    """
    # 接続例: conn = st.connection("gsheets", type=GSheetsConnection)
    # 暫定的に現在時刻を記録
    st.session_state["last_sync"] = datetime.now().strftime("%m/%d %H:%M")
    st.toast("スプレッドシートから最新データを取得しました！")

# --- 4. ヘッダー (タイトルと同期ボタン) ---
col_h1, col_h2 = st.columns([6, 4])
with col_h1:
    st.write(f"### 📅 {datetime.now().month}月")

with col_h2:
    # 以前の「同期」ボタンを復活
    if st.button("🔄 同期", use_container_width=True):
        handle_sync()
    st.caption(f"最終: {st.session_state['last_sync']}")

# --- 5. カレンダー描画 ---
now = datetime.now()
cal = calendar.monthcalendar(now.year, now.month)
week_days = ["月", "火", "水", "木", "金", "土", "日"]

# 曜日ヘッダー
header_cols = st.columns(7)
for i, day_name in enumerate(week_days):
    color = "#FF4B4B" if i == 6 else "#1C83E1" if i == 5 else "#555"
    header_cols[i].markdown(f"<div class='weekday-header' style='color:{color};'>{day_name}</div>", unsafe_allow_html=True)

# 日付グリッド
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                with st.container(border=True):
                    color = "#FF4B4B" if i == 6 else "#1C83E1" if i == 5 else "inherit"
                    st.markdown(f"<div class='date-text' style='color:{color};'>{day}</div>", unsafe_allow_html=True)
                    
                    # 出勤データなどがあればここに表示
                    # st.markdown("<div style='font-size:8px; text-align:center;'>出勤</div>", unsafe_allow_html=True)
            else:
                # 空白セルを維持してレイアウト崩れを防ぐ
                st.write("")
