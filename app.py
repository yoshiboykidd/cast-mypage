import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. ページ基本設定 & バージョン管理 ---
st.set_page_config(page_title="キャストマイページ ver 1.1", page_icon="💖", layout="centered")
st.title("💖 キャストマイページ ver 1.1")
conn = st.connection("supabase", type=SupabaseConnection)

try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- ✨ インタラクティブ・フレームCSS ---
st.markdown("""
    <style>
    /* 7列をスマホでも強制維持 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        width: 14.28% !important;
        min-width: 0 !important;
        flex: 1 1 0% !important;
    }
    /* ボタンをカレンダーの「枠」としてデザイン */
    .stButton > button {
        width: 100% !important;
        height: 60px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        border: 1px solid #f0f0f0 !important;
        background-color: white !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important;
        transition: all 0.2s;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }
    /* 出勤日の枠（ピンク） */
    .has-shift button {
        background-color: #FFF9FA !important;
        border: 1px solid #FFD1D9 !important;
    }
    /* 選択中の枠（赤太枠） */
    .selected-day button {
        border: 2px solid #FF4B4B !important;
        background-color: #FFF0F2 !important;
        box-shadow: 0 0 8px rgba(255,75,75,0.2) !important;
    }
    /* 今日の枠（点線または細い色枠） */
    .is-today button {
        background-color: #F0F7FF !important;
    }
    /* 曜日ラベル */
    .wd-label { text-align: center; font-size: 0.7em; font-weight: bold; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🛰 同期関数（1,500名対応・個人最適化版） ---
def sync_personal_shift(login_id, hp_name, shop_id):
    """自分のデータだけをリフレッシュ取得"""
    try:
        today = datetime.date.today()
        conn.table("shifts").delete().eq("cast_id", login_id).gte("date", today.isoformat()).lte("date", (today + datetime.timedelta(days=7)).isoformat()).execute()
        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://ikekari.com/attend.php"
        count = 0
        for i in range(7):
            t_date = today + datetime.timedelta(days=i)
            res = requests.get(f"{base_url}?date_get={t_date.strftime('%Y/%m/%d')}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            target = soup.find(string=re.compile(re.escape(hp_name.strip())))
            if target:
                container = "".join([p.get_text() for p in list(target.parents)[:3]])
                time_m = re.search(r'(\d{1,2}[:：]\d{2}.{0,5}\d{1,2}[:：]\d{2})|(\d{1,2}[:：]\d{2}.{0,2}[〜~])', container)
                tm = time_m.group(0) if time_m else "時間未定"
                conn.table("shifts").insert({"date": t_date.isoformat(), "cast_id": login_id, "shop_id": shop_id, "shift_time": tm, "status": "確定"}).execute()
                count += 1
            time.sleep(0.1)
        return count
    except: return 0

# --- 3. 🔐 ログイン認証 ---
if "user_info" not in st.session_state:
    input_id = st.text_input("ID")
    input_pw = st.text_input("PW", type="password")
    if st.button("ログイン"):
        r = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if r.data:
            st.session_state["user_info"] = r.data[0]
            st.rerun()
    st.stop()

# --- 4. メイン画面 ---
user = st.session_state["user_info"]
now = datetime.date.today()

# 状態管理
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

# A. 売上見込み
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. ヘッダー & 同期
c1, c2 = st.columns([0.7, 0.3])
with c1: st.subheader("📅 カレンダー")
with c2:
    if st.button("🔄 同期"):
        cnt = sync_personal_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
        st.toast(f"{cnt}件更新完了")
        st.rerun()

# シフトデータ取得
try:
    s_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    s_map = {s['date']: s['shift_time'] for s in s_res.data}
except: s_map = {}

# C. カレンダー描画（インタラクティブ版）
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# 曜日ラベル
cols_h = st.columns(7)
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    color = "#FF3B30" if i==6 else "#007AFF" if i==5 else "#999"
    cols_h[i].markdown(f"<div class='wd-label' style='color:{color};'>{wd}</div>", unsafe_allow_html=True)

# 日付ボタン
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            d_obj = datetime.date(year, month, day)
            d_str = d_obj.isoformat()
            is_s = d_str in s_map
            is_sel = (st.session_state.selected_date == d_str)
            
            # クラス判定
            cls = "has-shift" if is_s else ""
            if is_sel: cls += " selected-day"
            if d_obj == now: cls += " is-today"
            
            # 表示テキスト（数字とドット）
            label = f"{day}\n●" if is_s else str(day)
            
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if cols[i].button(label, key=f"btn_{d_str}"):
                st.session_state.selected_date = d_str
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            cols[i].empty()

# D. 予定詳細エリア
st.divider()
sel_d = datetime.date.fromisoformat(st.session_state.selected_date)
st.markdown(f"### 📝 {sel_d.month}月{sel_d.day}日の予定")

with st.container(border=True):
    if st.session_state.selected_date in s_map:
        st.success(f"⏰ 出勤予定：{s_map[st.session_state.selected_date]}")
        st.info("🏢 勤務店舗：池袋西口店")
    else:
        st.write("この日の出勤予定はありません")
