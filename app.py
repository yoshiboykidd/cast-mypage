import streamlit as st
import calendar
from datetime import datetime

# ページ設定
st.set_page_config(page_title="Cast My Page", layout="wide")

# --- プロフェッショナルCSS（強制グリッド制御） ---
st.markdown("""
    <style>
    /* 1. 全体の余白削除 */
    .block-container { padding: 1rem 0.5rem !important; }
    
    /* 2. ヘッダーのレイアウト（タイトルと同期ボタン） */
    .cal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding: 0 10px;
    }

    /* 3. カレンダーグリッド本体 */
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr); /* 強制7列 */
        gap: 4px;
        width: 100%;
    }

    /* 4. 曜日と日付の共通スタイル */
    .grid-item {
        text-align: center;
        padding: 8px 0;
        font-size: 0.8rem;
        border: 1px solid #eee;
        border-radius: 4px;
        background: white;
    }
    
    .weekday { font-weight: bold; border: none; background: transparent; }
    .sun { color: #ff4b4b; }
    .sat { color: #1c83e1; }

    /* 5. 日付枠の固定（スマホで縦に伸びるのを防ぐ） */
    .date-cell {
        min-height: 50px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
    }

    /* Streamlit標準ボタンの調整 */
    div.stButton > button {
        width: 100%;
        padding: 0;
        height: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 同期ロジック ---
if "last_sync" not in st.session_state:
    st.session_state["last_sync"] = "未同期"

def sync():
    st.session_state["last_sync"] = datetime.now().strftime("%H:%M")
    st.toast("データを同期しました")

# --- レイアウト作成 ---

# 1. ヘッダー部分（画像のイメージを再現）
st.markdown(f"""
    <div class="cal-header">
        <h3 style="margin:0;">📅 スケジュール</h3>
    </div>
""", unsafe_allow_html=True)

# 同期ボタンはStreamlitの機能を使うため、列を分けて配置
col_spacer, col_btn = st.columns([7, 3])
with col_btn:
    if st.button("🔄 同期"):
        sync()
    st.caption(f"最終: {st.session_state['last_sync']}")

# 2. 曜日ヘッダー
week_days = ["月", "火", "水", "木", "金", "土", "日"]
day_cols = st.columns(7)
for i, d in enumerate(week_days):
    color_class = "sun" if i == 6 else "sat" if i == 5 else ""
    day_cols[i].markdown(f"<div class='weekday {color_class}' style='text-align:center; font-weight:bold;'>{d}</div>", unsafe_allow_html=True)

# 3. カレンダー日付部分
now = datetime.now()
cal = calendar.monthcalendar(now.year, now.month)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                # 枠をコンテナで作成し、高さをCSSで制御
                with st.container(border=True):
                    color_style = "color:#ff4b4b;" if i == 6 else "color:#1c83e1;" if i == 5 else ""
                    st.markdown(f"<div style='text-align:center; font-weight:bold; {color_style}'>{day}</div>", unsafe_allow_html=True)
                    # ここに予定がある場合のアイコンなどを入れる
            else:
                st.write("") # 空白
