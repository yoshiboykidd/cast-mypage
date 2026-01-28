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
    /* カレンダーの7列をスマホでも強制維持 */
    [data-testid="column"] {
        width: calc(14.28% - 0.2rem) !important;
        flex: 1 1 calc(14.28% - 0.2rem) !important;
        min-width: calc(14.28% - 0.2rem) !important;
        padding: 0 !important;
    }
    /* 同期ボタンのスタイル */
    .sync-btn button {
        background-color: #FFF0F2 !important;
        color: #FF4B4B !important;
        border: 1px solid #FF4B4B !important;
        border-radius: 20px !important;
        font-size: 0.7em !important;
        height: 30px !important;
    }
    /* カレンダーマスの高さと配置 */
    .calendar-table td { height: 50px; position: relative; vertical-align: top; border: 1px solid #f8f8f8; }
    .day-num { font-size: 0.7em; font-weight: bold; position: absolute; top: 3px; left: 5px; }
    .shift-bar { position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%); width: 18px; height: 4px; background-color: #FF4B4B; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 🛰 マイシフト専用・同期関数 ---

def sync_my_personal_shift(login_id, hp_name, shop_id):
    """自分のシフトだけを今後7日間分、HPから取得して更新する"""
    try:
        today = datetime.date.today()
        # 自分の今後7日間のデータのみを一旦削除（リフレッシュ）
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
            
            # HPのテキスト全体から自分の名前を検索
            page_text = soup.get_text()
            if hp_name in page_text:
                # 名前が見つかった場合、周辺から時間を抽出
                name_element = soup.find(string=re.compile(re.escape(hp_name)))
                time_match = re.search(r'(\d{1,2}:\d{2}.{1,7}\d{1,2}:\d{2})|(\d{1,2}:\d{2}〜)', str(name_element.parent))
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
        st.error(f"同期に失敗しました: {e}")
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
            st.error("IDまたはパスワードが違います")
    st.stop()

# --- 4. メイン画面 ---
user = st.session_state["user_info"]
now = datetime.date.today()

# 売上見込み表示
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
        <span style="color: #666; font-size: 0.8em; font-weight: bold;">今日の売上見込み ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500</span>
    </div>
    """, unsafe_allow_html=True)

# 📅 カレンダーヘッダーと【同期ボタン】の配置
header_col1, header_col2 = st.columns([0.7, 0.3])
with header_col1:
    st.subheader("📅 予定")
with header_col2:
    st.markdown('<div class="sync-btn">', unsafe_allow_html=True)
    if st.button("🔄 同期"):
        with st.spinner("同期中"):
            cnt = sync_my_personal_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
            st.toast(f"{cnt}件のシフトを更新しました！", icon="✨")
            time.sleep(1)
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# カレンダー表示
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# シフト情報取得
shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
shift_dict = {s['date']: s['shift_time'] for s in shift_res.data}

# 曜日ラベル
cols_h = st.columns(7)
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    color = "#FF3B30" if i==6 else "#007AFF" if i==5 else "#999"
    cols_h[i].markdown(f"<div style='text-align:center; font-size:0.7em; color:{color};'>{wd}</div>", unsafe_allow_html=True)

# カレンダー日付ボタン
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day != 0:
            cell_date = datetime.date(year, month, day)
            date_str = cell_date.isoformat()
            is_shift = date_str in shift_dict
            
            # デザイン判定
            is_selected = (st.session_state.selected_date == date_str)
            label = f"{day}\n●" if is_shift else str(day)
            
            if cols[i].button(label, key=f"d_{date_str}", use_container_width=True):
                st.session_state.selected_date = date_str
                st.rerun()
        else:
            cols[i].write("")

# スケジュール詳細
st.divider()
sel_date = datetime.date.fromisoformat(st.session_state.selected_date)
st.markdown(f"### 📝 {sel_date.month}月{sel_date.day}日の詳細")

with st.container(border=True):
    if st.session_state.selected_date in shift_dict:
        st.success(f"✅ 出勤：{shift_dict[st.session_state.selected_date]}")
        st.write("🏢 池袋西口店")
    else:
        st.info("この日の出勤予定はありません")
