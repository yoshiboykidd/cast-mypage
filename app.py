import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time
import re

# --- 1. ページ基本設定 ---
# ページ設定は最初の一回だけ実行
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

# --- 2. 🔐 ログイン認証（セッション維持重視） ---
# セッション状態を明示的に初期化
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔐 ログイン")
    input_id = st.text_input("ログインID (8桁)", key="login_id_input")
    input_pw = st.text_input("パスワード", type="password", key="password_input")
    
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["user_info"] = user_res.data[0]
            st.session_state["password_correct"] = True
            # ログイン直後のオートシンクは、ログイン成功時の1回だけ実行
            with st.spinner("最新のスケジュールを確認中..."):
                # ここに同期関数（後述）を入れる
                pass
            st.rerun()
        else:
            st.error("IDまたはパスワードが違います")
    st.stop()

# ログイン後のユーザー情報
user = st.session_state["user_info"]

# --- 3. 🗓️ 選択された日付の管理（URL連動） ---
# 現在のURLパラメータから日付を取得。なければ「今日」をデフォルトに。
# st.query_params はリロード時も保持される [cite: 2026-01-28]
query_d = st.query_params.get("d")
try:
    selected_date = datetime.date.fromisoformat(query_d) if query_d else datetime.date.today()
except:
    selected_date = datetime.date.today()

# --- 4. 🛰️ 同期ロジック（個別・自動削除・時間解析） ---

def sync_individual_shift(user_info):
    hp_name = user_info.get('hp_display_name')
    if not hp_name: return "HP表示名エラー", 0
    headers = {"User-Agent": "Mozilla/5.0"}
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

# --- 5. メインUI ---

# キラキラ売上ヘッダー（タップした日に連動するように後ほどDB化可能）
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">{selected_date.month}/{selected_date.day} の売上 ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# 同期ボタン
col_t, col_s = st.columns([6, 4])
with col_t:
    st.subheader("📅 スケジュール")
with col_s:
    if st.button("🔄 同期する", use_container_width=True):
        msg, count = sync_individual_shift(user)
        st.toast(msg)
        time.sleep(0.5)
        st.rerun()

# --- 6. 🗓️ カレンダー描画（セッション維持リンク） ---

try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_map = {s['date']: s['shift_time'] for s in shift_res.data}
except:
    shift_map = {}

now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)

# CSS: リンクを相対パスに変更してリロード時のログアウトを防ぐ
st.markdown("""
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 15px; }
    .calendar-table td { vertical-align: top; height: 55px; border: 1px solid #f0f0f0; background-color: white; position: relative; padding: 0; }
    .calendar-table td a { display: block; width: 100%; height: 100%; text-decoration: none; padding: 4px; color: inherit; }
    .day-num { font-size: 0.8em; font-weight: 800; position: absolute; top: 4px; left: 6px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); width: 18px; height: 4px; background-color: #FF4B4B; border-radius: 10px; }
    .today-cell { border: 2px solid #FF4B4B !important; z-index: 5; }
    .selected-cell { background-color: #FFF0F0 !important; box-shadow: inset 0 0 0 2px #FF4B4B; }
</style>
""", unsafe_allow_html=True)

cal_html = '<table class="calendar-table"><tr>'
for wd in ["月","火","水","木","金","土","日"]:
    cal_html += f'<th style="font-size:0.7em; color:#999;">{wd}</th>'
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
            
            # 【重要】hrefを相対パス "?d=..." にすることで、セッションを維持したままリロード [cite: 2026-01-28]
            cal_html += f'<td class="{" ".join(classes)}"><a href="?d={date_iso}" target="_self"><span class="day-num {d_color}">{day}</span>{"<div class=\'shift-bar\'></div>" if date_iso in shift_map else ""}</a></td>'
    cal_html += "</tr>"
cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# --- 7. 🕒 選択された日の詳細表示 ---
wd_list = ["月", "火", "水", "木", "金", "土", "日"]
selected_wd = wd_list[selected_date.weekday()]

st.markdown(f"### {selected_date.month}/{selected_date.day}({selected_wd}) の予定 🗓️")

with st.container(border=True):
    sel_date_iso = selected_date.isoformat()
    if sel_date_iso in shift_map:
        st_time = shift_map[sel_date_iso]
        st.info(f"🕒 **シフト：{st_time}**")
        st.write("📌 **状況：** 確定")
    else:
        st.write("この日のシフト予定はありません。")

# サイドバー
with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
