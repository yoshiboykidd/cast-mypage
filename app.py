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

# Supabase接続
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("データベース接続エラー。設定を確認してください。")
    st.stop()

# 祝日判定用（任意）
try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- 2. 📅 選択された日付の管理（クエリパラメータ対応） ---
# URLの ?d=YYYY-MM-DD を読み取る
query_params = st.query_params
default_date = datetime.date.today()

if "d" in query_params:
    try:
        selected_date = datetime.date.fromisoformat(query_params["d"])
    except:
        selected_date = default_date
else:
    selected_date = default_date

# --- 3. 🛰️ 同期ロジック（個別・自動削除・時間解析） ---

def sync_individual_shift(user_info):
    hp_name = user_info.get('hp_display_name')
    if not hp_name: return "HP表示名エラー", 0

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    base_url = "https://ikekari.com/attend.php"
    time_pattern = r"(\d{1,2}[:時]\d{0,2})\s*[-～〜]\s*(\d{1,2}[:時]\d{0,2}|LAST|last|ラスト|翌\d{1,2}[:時]\d{0,2})"
    
    found_count = 0
    status_placeholder = st.empty()
    
    for i in range(7):
        target_date = datetime.date.today() + datetime.timedelta(days=i)
        date_iso = target_date.isoformat()
        status_placeholder.caption(f"🔄 {target_date} を確認中...")
        
        try:
            res = requests.get(f"{base_url}?date_get={target_date.strftime('%Y/%m/%d')}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            target_element = soup.find(string=re.compile(hp_name))
            
            if target_element:
                container = target_element.find_parent().find_parent()
                time_match = re.search(time_pattern, container.get_text(strip=True))
                shift_time = time_match.group(0) if time_match else "時間未定"
                
                conn.table("shifts").upsert({
                    "date": date_iso, "cast_id": user_info['login_id'],
                    "shop_id": user_info['home_shop_id'], "status": "確定", "shift_time": shift_time
                }).execute()
                found_count += 1
            else:
                conn.table("shifts").delete().eq("date", date_iso).eq("cast_id", user_info['login_id']).execute()
        except: pass
        time.sleep(0.2)
    
    status_placeholder.empty()
    return "同期完了✨", found_count

# --- 4. 🔐 ログイン認証 ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["user_info"] = user_res.data[0]
            st.session_state["password_correct"] = True
            with st.spinner("最新のスケジュールを確認中..."):
                sync_individual_shift(st.session_state["user_info"])
            st.rerun()
        else:
            st.error("IDまたはパスワードが違います")
    st.stop()

user = st.session_state["user_info"]

# --- 5. メインUI ---

# 売上ヘッダー
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# ヘッダーと同期
col_t, col_s = st.columns([6, 4])
with col_t:
    st.subheader("📅 スケジュール")
with col_s:
    if st.button("🔄 同期する", use_container_width=True):
        msg, count = sync_individual_shift(user)
        st.toast(msg)
        time.sleep(1)
        st.rerun()

# --- 6. 🗓️ カレンダー描画（タップ対応版） ---

try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_map = {s['date']: s['shift_time'] for s in shift_res.data}
except:
    shift_map = {}

now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)

# スタイル（リンクをセル全体に広げる）
st.markdown("""
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 15px; }
    .calendar-table th { font-size: 0.75em; color: #999; padding-bottom: 8px; text-align: center; }
    .calendar-table td { 
        vertical-align: top; height: 55px; border: 1px solid #f0f0f0; 
        background-color: white; position: relative; padding: 0; /* paddingを0にしてリンクを広げる */
    }
    .calendar-table td a {
        display: block; width: 100%; height: 100%; text-decoration: none; padding: 4px; color: inherit;
    }
    .day-num { font-size: 0.8em; font-weight: 800; position: absolute; top: 4px; left: 6px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { 
        position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); 
        width: 18px; height: 4px; background-color: #FF4B4B; border-radius: 10px; 
    }
    .today-cell { border: 2px solid #FF4B4B !important; z-index: 5; }
    .selected-cell { background-color: #FFF0F0 !important; box-shadow: inset 0 0 0 2px #FF4B4B; }
</style>
""", unsafe_allow_html=True)

cal_html = '<table class="calendar-table"><tr>'
for wd in ["月","火","水","木","金","土","日"]:
    cal_html += f'<th>{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0:
            cal_html += "<td></td>"
        else:
            cell_date = datetime.date(now.year, now.month, day)
            cell_date_str = cell_date.isoformat()
            is_hol = jpholiday.is_holiday(cell_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if (i==6 or is_hol) else "weekday"
            
            classes = []
            if cell_date == now: classes.append("today-cell")
            if cell_date == selected_date: classes.append("selected-cell")
            if cell_date_str in shift_map: classes.append("has-shift")
            
            class_str = f'class="{" ".join(classes)}"' if classes else ""
            bar = '<div class="shift-bar"></div>' if cell_date_str in shift_map else ''
            
            # リンクを生成（target="_self" で同じタブで開く）
            link_url = f"/?d={cell_date_str}"
            cal_html += f'<td {class_str}><a href="{link_url}" target="_self"><span class="day-num {d_color}">{day}</span>{bar}</a></td>'
    cal_html += "</tr>"
cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# --- 7. 🕒 選択された日のスケジュール詳細表示 ---
# 曜日を取得
wd_list = ["月", "火", "水", "木", "金", "土", "日"]
selected_wd = wd_list[selected_date.weekday()]

st.markdown(f"### {selected_date.month}/{selected_date.day}({selected_wd}) の予定 🗓️")

with st.container(border=True):
    sel_date_str = selected_date.isoformat()
    if sel_date_str in shift_map:
        st_time = shift_map[sel_date_str]
        st.info(f"🕒 **シフト：{st_time}**")
        st.write("📌 **状況：** 確定")
    else:
        st.write("予定はありません。")

# サイドバー
with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
