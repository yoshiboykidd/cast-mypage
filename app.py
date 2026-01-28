import streamlit as st
import calendar
from datetime import datetime

# --- ページ設定 ---
st.set_page_config(page_title="Cast My Page - Schedule", layout="wide")

# --- カスタムCSS（枠の形を整える） ---
st.markdown("""
    <style>
    /* カレンダーの日付枠のスタイル */
    [data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 100px !important; /* 枠の最小高さを固定 */
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        align-items: center;
        padding: 5px !important;
    }
    /* 日付数字のスタイル */
    .date-text {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 5px;
    }
    /* 曜日のヘッダー */
    .weekday-header {
        text-align: center;
        font-weight: bold;
        padding: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- ヘッダー部分 ---
col_title, col_sync = st.columns([8, 2])

with col_title:
    st.title("📅 スケジュール")

with col_sync:
    # 同期ボタン（画像のイメージに合わせる）
    if st.button("🔄 同期", use_container_width=True):
        st.toast("データを同期しました")

# --- カレンダー計算ロジック ---
now = datetime.now()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)
week_days = ["月", "火", "水", "木", "金", "土", "日"]

# --- 曜日ヘッダーの表示 ---
header_cols = st.columns(7)
for i, day_name in enumerate(week_days):
    color = "#FF4B4B" if i == 6 else "#1C83E1" if i == 5 else "inherit"
    header_cols[i].markdown(f"<div class='weekday-header' style='color:{color};'>{day_name}</div>", unsafe_allow_html=True)

# --- カレンダー本体（日付枠） ---
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                # 月の範囲外の空セル
                st.write("")
            else:
                # 枠線ありのコンテナを作成
                with st.container(border=True):
                    # 日付表示（日曜は赤、土曜は青）
                    color = "#FF4B4B" if i == 6 else "#1C83E1" if i == 5 else "inherit"
                    st.markdown(f"<div class='date-text' style='color:{color};'>{day}</div>", unsafe_allow_html=True)
                    
                    # --- ここにシフト情報や予定を追加 ---
                    # 例：特定の日のボタンなど
                    # if st.button("編集", key=f"btn_{day}", size="small"):
                    #     pass
                    # ----------------------------------

# --- フッター（必要に応じて） ---
st.divider()
st.caption(f"{year}年{month}月のスケジュールを表示中")
