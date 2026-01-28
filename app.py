import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🔐 ログイン認証（簡易版） ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    # 実際はここでDB照合
    if st.button("テストログイン"):
        st.session_state["password_correct"] = True
        st.session_state["user_info"] = {"display_name": "ユキちゃん", "login_id": "00100001"}
        st.rerun()
    st.stop()

# --- 3. メイン画面の構築（画像のデザインを反映） ---
user = st.session_state["user_info"]

# --- A. ヘッダーエリア ---
col_head1, col_head2 = st.columns([4, 1])
col_head1.title(f"✨ {user['display_name']} さん")
col_head2.button("⚙️")

# --- B. 今日の売上カード（見込み） ---
with st.container(border=True):
    st.write("今日の売上 (見込み) ✨")
    st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>¥ 28,500 GET!</h1>", unsafe_allow_html=True)
    st.progress(0.65, text="今月の目標: 65%達成")

st.divider()

# --- C. 【新設】カレンダー表示エリア（スケジュールの「上」に配置） ---
st.subheader("📅 カレンダー")
# 月間カレンダーのデータ作成
now = datetime.datetime.now()
cal = calendar.monthcalendar(now.year, now.month)

# 7列でカレンダーを表示
rows = len(cal)
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write("")
        else:
            # シフトがある日を想定してボタンを配置
            # 将来的にシフトがある日は色を変えるなどの処理を追加
            if cols[i].button(str(day), key=f"cal_{day}", use_container_width=True):
                st.session_state["selected_date"] = day

# --- D. 今日のスケジュール ---
st.subheader("📝 スケジュール詳細")
selected_day = st.session_state.get("selected_date", now.day)
with st.container(border=True):
    st.write(f"**{now.month}月{selected_day}日の予定**")
    # ダミーデータ（本来はDBから取得）
    st.info("⏰ シフト：19:00 - 24:00\n\n📌 予約：20:30〜 90分 (田中様)")

# --- E. お知らせ・稼げるヒミツ ---
st.divider()
st.subheader("📢 お店からのお知らせ")
with st.expander("重要：ドレスコードが変わります 👗"):
    st.write("来月より衣装の規定が変更になります。詳細は...")

with st.expander("明日のまかないはオムライスだよ 😋"):
    st.write("楽しみにしていてね！")

# --- 4. ナビゲーション（下部ボタンの代わり） ---
with st.sidebar:
    st.title("MENU")
    if st.button("🏠 ホーム", use_container_width=True): pass
    if st.button("📝 実績報告", use_container_width=True): pass
    if st.button("📤 シフト申請", use_container_width=True): pass
    st.divider()
    if st.button("🚪 ログアウト", use_container_width=True):
        st.session_state.clear()
        st.rerun()
