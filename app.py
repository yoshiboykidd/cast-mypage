import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. ページ基本設定 & バージョン管理 ---
st.set_page_config(page_title="キャストマイページ ver 1.11", page_icon="💖", layout="centered")
st.markdown("<h5 style='text-align:center; color:#FF4B4B;'>💖 キャストマイページ ver 1.11</h5>", unsafe_allow_html=True)
conn = st.connection("supabase", type=SupabaseConnection)

try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- ✨ 【重要】枠崩れを絶対に許さない最強CSS ---
st.markdown("""
    <style>
    /* 1. 7列の横並びを強制（スマホでの縦積みを禁止） */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px !important; /* 枠同士の隙間を最小限に */
    }
    [data-testid="column"] {
        width: 14.28% !important;
        flex: 1 1 14.28% !important;
        min-width: 0 !important;
        padding: 0 !important;
    }
    
    /* 2. ボタンを「きれいな枠」に変える */
    .stButton > button {
        width: 100% !important;
        height: 52px !important; /* HTMLテーブルに近い高さ */
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 4px !important;
        border: 1px solid #f0f0f0 !important;
        background-color: white !important;
        font-size: 0.8rem !important;
        line-height: 1.2 !important;
        display: block !important;
    }

    /* 3. シフトがある日のデザイン */
    .has-shift button {
        background-color: #FFF5F7 !important;
        border-bottom: 3px solid #FF4B4B !important; /* 下線で出勤を強調 */
    }

    /* 4. 選択中の日のデザイン */
    .selected-day button {
        border: 2px solid #FF4B4B !important;
        background-color: #FFF0F2 !important;
        z-index: 10;
    }

    /* 5. 曜日のラベル */
    .wd-label { text-align: center; font-size: 0.7rem; font-weight: bold; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🛰 同期関数（ ver 1.11 仕様） ---
def sync_personal_shift(login_id, hp_name, shop_id):
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
    st.markdown("### 🔐 Login")
    in_id = st.text_input("ログインID")
    in_pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        r = conn.table("cast_members").select("*").eq("login_id", in_id.zfill(8)).eq("password", in_pw).execute()
        if r.data:
            st.session_state["user_info"] = r.data[0]
            st.rerun()
    st.stop()

# --- 4. メイン画面 ---
user = st.session_state["user_info"]
now = datetime.date.today()

# 状態管理（選択された日付）
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

# 売上見込み
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="font-size: 1.5em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# ヘッダー
c1, c2 = st.columns([0.7, 0.3])
with c1: st.markdown("**📅 スケジュール**")
with c2:
    if st.button("🔄 同期", key="sync"):
        cnt = sync_personal_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
        st.toast(f"{cnt}件更新完了")
        st.rerun()

# シフト取得
try:
    s_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    s_map = {s['date']: s['shift_time'] for s in s_res.data}
except: s_map = {}

# --- 🗓️ カレンダー描画（ ver 1.11 安定版） ---
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# 曜日ヘッダー
cols_h = st.columns(7)
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    color = "#FF3B30" if i==6 else "#007AFF" if i==5 else "#999"
    cols_h[i].markdown(f"<div class='wd-label' style='color:{color};'>{wd}</div>", unsafe_allow_html=True)

# 日付ボタンの配置
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
            if is_sel: cls = "selected-day" # 選択を最優先
            
            # ラベル（出勤日は●を表示）
            label = f"{day}\n●" if is_s else str(day)
            
            # 枠を描画
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if cols[i].button(label, key=f"btn_{year}_{month}_{day}"):
                st.session_state.selected_date = d_str
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            cols[i].empty()

# D. 予定詳細
st.divider()
sel_d = datetime.date.fromisoformat(st.session_state.selected_date)
st.markdown(f"**📝 {sel_d.month}/{sel_d.day} の詳細**")

with st.container(border=True):
    if st.session_state.selected_date in s_map:
        st.success(f"⏰ **出勤：{s_map[st.session_state.selected_date]}**")
        st.caption("🏢 勤務店舗：池袋西口店")
    else:
        st.write("予定なし")
