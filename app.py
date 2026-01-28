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

# --- ✨ スマホ用・横7列死守＆デザインCSS ---
st.markdown("""
    <style>
    [data-testid="column"] {
        width: calc(14.28% - 0.2rem) !important;
        flex: 1 1 calc(14.28% - 0.2rem) !important;
        min-width: calc(14.28% - 0.2rem) !important;
    }
    .stButton > button {
        height: 48px !important;
        padding: 0 !important;
        font-size: 0.8rem !important;
        background-color: white !important;
        border: 1px solid #f8f8f8 !important;
        border-radius: 8px !important;
    }
    .has-shift button { background-color: #FFF5F7 !important; border-bottom: 3px solid #FF4B4B !important; }
    .today-cell button { border: 2px solid #FF4B4B !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🛰 巡回同期関数（時間解析・強化版） ---

def sync_my_personal_shift(login_id, hp_name, shop_id):
    try:
        today = datetime.date.today()
        # 自分の今後7日間のデータをリフレッシュ
        conn.table("shifts").delete().eq("cast_id", login_id).gte("date", today.isoformat()).lte("date", (today + datetime.timedelta(days=7)).isoformat()).execute()

        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://ikekari.com/attend.php"
        found_count = 0
        
        for i in range(7):
            target_date = today + datetime.timedelta(days=i)
            url_date_str = target_date.strftime("%Y/%m/%d")
            res = requests.get(f"{base_url}?date_get={url_date_str}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # --- 💡 解析ロジック強化 ---
            # 1. ページ内のすべてのテキストから名前を探す
            # 2. 名前が見つかったら、その「周辺（親の親まで）」のテキストを抜き出す
            target_element = soup.find(string=re.compile(re.escape(hp_name.strip())))
            
            if target_element:
                # 3階層上まで遡って、そのエリア全体のテキストを取得（時間を見逃さないため）
                container_text = ""
                parent = target_element.parent
                for _ in range(3):
                    if parent:
                        container_text += parent.get_text() + " "
                        parent = parent.parent
                
                # 時間のパターンを抽出 (19:00〜, 20:00〜24:00, 19-24など)
                # 全角「〜」や「：」にも対応
                time_pattern = r'(\d{1,2}[:：]\d{2}.{0,5}\d{1,2}[:：]\d{2})|(\d{1,2}[:：]\d{2}.{0,2}[〜~〜-])'
                time_match = re.search(time_pattern, container_text)
                shift_time = time_match.group(0) if time_match else "時間未定"

                conn.table("shifts").insert({
                    "date": target_date.isoformat(),
                    "cast_id": login_id,
                    "shop_id": shop_id,
                    "shift_time": shift_time,
                    "status": "確定"
                }).execute()
                found_count += 1
            time.sleep(0.2)
        return found_count
    except Exception as e:
        st.error(f"同期エラー: {e}")
        return 0

# --- 3. 🔐 ログイン認証 ---
if "password_correct" not in st.session_state:
    st.title("💖 キャストポータル")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["password_correct"] = True
            st.session_state["user_info"] = user_res.data[0]
            st.rerun()
        else:
            st.error("認証失敗")
    st.stop()

# --- 4. メインレイアウト ---
user = st.session_state["user_info"]
now = datetime.date.today()

# 同期ボタン（メイン画面に配置）
col_t1, col_t2 = st.columns([0.7, 0.3])
with col_t1:
    st.subheader("📅 スケジュール")
with col_t2:
    if st.button("🔄 同期"):
        with st.spinner("同期中"):
            cnt = sync_my_personal_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
            st.toast(f"{cnt}件の予定を更新！", icon="✨")
            time.sleep(1)
            st.rerun()

# カレンダー表示
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# DBからシフト取得（エラー回避付）
try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_dict = {s['date']: s['shift_time'] for s in shift_res.data}
except:
    shift_dict = {}

# 曜日ヘッダー
cols_h = st.columns(7)
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    color = "#FF3B30" if i==6 else "#007AFF" if i==5 else "#999"
    cols_h[i].markdown(f"<div style='text-align:center; font-size:0.7em; color:{color};'>{wd}</div>", unsafe_allow_html=True)

# 日付選択の初期化
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

# カレンダーボタン
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            d_obj = datetime.date(year, month, day)
            d_str = d_obj.isoformat()
            is_shift = d_str in shift_dict
            
            # クラス付与
            btn_class = "has-shift" if is_shift else ""
            if d_obj == now: btn_class += " today-cell"
            
            # ラベル
            label = f"**{day}**\n●" if is_shift else str(day)
            
            st.markdown(f'<div class="{btn_class}">', unsafe_allow_html=True)
            if cols[i].button(label, key=f"btn_{d_str}", use_container_width=True):
                st.session_state.selected_date = d_str
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            cols[i].write("")

# --- 5. 詳細エリア ---
st.divider()
sel_date = datetime.date.fromisoformat(st.session_state.selected_date)
st.markdown(f"### 📝 {sel_date.month}/{sel_date.day} の予定")

with st.container(border=True):
    if st.session_state.selected_date in shift_dict:
        st.success(f"⏰ 出勤時間: {shift_dict[st.session_state.selected_date]}")
        st.write("🏢 勤務店舗: 池袋西口店")
    else:
        st.info("出勤予定はありません")
