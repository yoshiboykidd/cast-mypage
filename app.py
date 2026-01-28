import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- ✨ 「枠」と「デザイン」を整える魔法のCSS ---
st.markdown("""
    <style>
    /* 1. 全体のカラム設定（7列固定） */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important; /* 枠と枠の間の隙間 */
        margin-bottom: 4px !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        width: 14.28% !important;
        min-width: 0 !important;
        flex: 1 1 0% !important;
    }

    /* 2. ボタン（枠）のデザイン */
    .stButton > button {
        width: 100% !important;
        height: 55px !important; /* 高さを揃えて正方形に近く */
        padding: 0 !important;
        border-radius: 6px !important;
        border: 1px solid #eeeeee !important; /* 基本の枠線 */
        background-color: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.1s ease;
    }

    /* 3. 出勤日の枠（ピンク） */
    .has-shift button {
        background-color: #FFF9FA !important;
        border: 1px solid #FFD1D9 !important;
    }

    /* 4. 選択中の枠（赤太枠） */
    .selected-day button {
        border: 2px solid #FF4B4B !important;
        background-color: #FFF0F2 !important;
    }

    /* 5. 曜日ラベルの色 */
    .wd-label { text-align: center; font-size: 0.65rem; font-weight: bold; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🛰 同期関数（1,500名の運用を支える軽量版） ---
def sync_my_shift(login_id, hp_name, shop_id):
    """自分のデータだけを同期"""
    try:
        today = datetime.date.today()
        conn.table("shifts").delete().eq("cast_id", login_id).gte("date", today.isoformat()).lte("date", (today + datetime.timedelta(days=7)).isoformat()).execute()
        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://ikekari.com/attend.php"
        found = 0
        for i in range(7):
            t_date = today + datetime.timedelta(days=i)
            res = requests.get(f"{base_url}?date_get={t_date.strftime('%Y/%m/%d')}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            target = soup.find(string=re.compile(re.escape(hp_name.strip())))
            if target:
                text = "".join([p.get_text() for p in list(target.parents)[:3]])
                m = re.search(r'(\d{1,2}[:：]\d{2}.{0,5}\d{1,2}[:：]\d{2})|(\d{1,2}[:：]\d{2}.{0,2}[〜~])', text)
                tm = m.group(0) if m else "時間未定"
                conn.table("shifts").insert({"date": t_date.isoformat(), "cast_id": login_id, "shop_id": shop_id, "shift_time": tm, "status": "確定"}).execute()
                found += 1
            time.sleep(0.1)
        return found
    except: return 0

# --- 3. 🔐 ログイン認証 ---
if "user_info" not in st.session_state:
    st.title("💖 Cast My Page") #
    id_in = st.text_input("ID")
    pw_in = st.text_input("PW", type="password")
    if st.button("ログイン"):
        r = conn.table("cast_members").select("*").eq("login_id", id_in.zfill(8)).eq("password", pw_in).execute()
        if r.data:
            st.session_state["user_info"] = r.data[0]
            st.rerun()
    st.stop()

# --- 4. メイン画面 ---
user = st.session_state["user_info"]
now = datetime.date.today()

# 同期ボタン
c1, c2 = st.columns([0.7, 0.3])
with c1: st.subheader("📅 スケジュール")
with c2:
    if st.button("🔄 同期", key="sync"):
        cnt = sync_my_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
        st.toast(f"{cnt}件の予定を更新しました")
        st.rerun()

# 状態管理
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

# シフト取得
s_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
s_map = {s['date']: s['shift_time'] for s in s_res.data}

# カレンダー表示
cal = calendar.monthcalendar(now.year, now.month)
wd_list = ["月","火","水","木","金","土","日"]
cols_h = st.columns(7)
for i, wd in enumerate(wd_list):
    color = "#FF3B30" if i==6 else "#007AFF" if i==5 else "#999"
    cols_h[i].markdown(f"<div class='wd-label' style='color:{color};'>{wd}</div>", unsafe_allow_html=True)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            d_obj = datetime.date(now.year, now.month, day)
            d_str = d_obj.isoformat()
            is_s = d_str in s_map
            is_sel = (st.session_state.selected_date == d_str)
            
            # クラス判定
            cls = "has-shift" if is_s else ""
            if is_sel: cls += " selected-day"
            
            label = f"{day}\n●" if is_s else str(day)
            
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            if cols[i].button(label, key=f"d_{d_str}"):
                st.session_state.selected_date = d_str
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            cols[i].empty()

# 詳細
st.divider()
sel = datetime.date.fromisoformat(st.session_state.selected_date)
st.markdown(f"#### 📝 {sel.month}/{sel.day} の詳細")
with st.container(border=True):
    if st.session_state.selected_date in s_map:
        st.success(f"⏰ 出勤予定：{s_map[st.session_state.selected_date]}")
        st.info("🏢 勤務店舗：池袋西口店")
    else:
        st.write("この日の出勤予定はありません")
