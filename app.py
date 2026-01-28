import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. [CRITICAL] ページ設定とセッション初期化 (最上部) ---
st.set_page_config(page_title="かりんとポータル ver 2.90", page_icon="💖", layout="centered")

# セッションがリセットされないよう、初期値を固定 [cite: 2026-01-28]
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "user_info" not in st.session_state:
    st.session_state["user_info"] = None

# Supabase接続
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("データベース接続エラー。")
    st.stop()

# 祝日判定用
try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- 2. 🛰️ 同期ロジック (個別・自動削除・時間解析) ---
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
        time.sleep(0.1)
    status_placeholder.empty()
    return "同期完了✨", found_count

# --- 3. 🔑 ログイン画面制御 ---
if not st.session_state["password_correct"]:
    st.title("🔐 ログイン (ver 2.90)")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["user_info"] = user_res.data[0]
            st.session_state["password_correct"] = True
            with st.spinner("最新情報を取得中..."):
                sync_individual_shift(st.session_state["user_info"])
            st.rerun()
        else:
            st.error("IDまたはパスワードが違います")
    st.stop()

# ログイン後のユーザー
user = st.session_state["user_info"]

# --- 4. 🗓️ 日付選択ロジック (クエリパラメータ) ---
# ログイン状態が維持されたまま、URLパラメータを読み取る [cite: 2026-01-28]
query_date = st.query_params.get("d")
try:
    selected_date = datetime.date.fromisoformat(query_date) if query_date else datetime.date.today()
except:
    selected_date = datetime.date.today()

# --- 5. メインUI ---
st.title(f"かりんとポータル ver 2.90")

# キラキラ売上ヘッダー (選択された日に連動可能)
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">{selected_date.month}/{selected_date.day} の売上 ✨</span><br>
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
        time.sleep(0.5)
        st.rerun()

# --- 6. 🗓️ カレンダー描画 (セッション安全リンク) ---
try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_map = {s['date']: s['shift_time'] for s in shift_res.data}
except:
    shift_map = {}

now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)

# CSS: セル全体をタップ可能にし、選択状態を強調 [cite: 2026-01-28]
st.markdown("""
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 15px; }
    .calendar-table th { font-size: 0.7em; color: #999; text-align: center; padding-bottom: 5px; }
    .calendar-table td { vertical-align: top; height: 55px; border: 1px solid #f0f0f0; background-color: white; padding: 0; }
    .calendar-table td a { display: block; width: 100%; height: 100%; text-decoration: none; padding: 4px; color: inherit; }
    .day-num { font-size: 0.8em; font-weight: 800; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { width: 18px; height: 4px; background-color: #FF4B4B; border-radius: 10px; margin: 2px auto 0; }
    .today-cell { border: 2px solid #FF4B4B !important; }
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
            date_iso = cell_date.isoformat()
            is_hol = jpholiday.is_holiday(cell_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if (i==6 or is_hol) else "weekday"
            
            classes = []
            if cell_date == now: classes.append("today-cell")
            if cell_date == selected_date: classes.append("selected-cell")
            if date_iso in shift_map: classes.append("has-shift")
            
            # 【CRITICAL】hrefの先頭から / を除去し、?d= 形式にすることでセッションを保護 [cite: 2026-01-28]
            cal_html += f'<td class="{" ".join(classes)}"><a href="?d={date_iso}" target="_self"><div class="day-num {d_color}">{day}</div>{"<div class=\'shift-bar\'></div>" if date_iso in shift_map else ""}</a></td>'
    cal_html += "</tr>"
cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# --- 7. 🕒 選択された日の詳細表示 ---
wd_list = ["月", "火", "水", "木", "金", "土", "日"]
selected_wd = wd_list[selected_date.weekday()]
st.markdown(f"### {selected_date.month}/{selected_date.day}({selected_wd}) の予定 🗓️")

with st.container(border=True):
    date_key = selected_date.isoformat()
    if date_key in shift_map:
        st.info(f"🕒 **シフト：{shift_map[date_key]}**")
        st.write("📌 **状況：** 確定")
    else:
        st.write("この日の予定はありません。")

# サイドバー
with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
