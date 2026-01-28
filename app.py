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

# --- 2. 🛰️ 最強の同期ロジック（個別オートシンク + 時間解析 + 自動削除） ---

def sync_individual_shift(user_info):
    """
    1. HPに名前がある場合：最新の「時間」を解析してDB保存 [cite: 2026-01-28]
    2. HPに名前がない場合：その日のシフトをDBから削除（休み反映） [cite: 2026-01-28]
    """
    hp_name = user_info.get('hp_display_name')
    if not hp_name:
        return "HP表示名が設定されていません。", 0

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    base_url = "https://ikekari.com/attend.php"
    found_count = 0
    
    # 時間解析用正規表現 [cite: 2026-01-28]
    time_pattern = r"(\d{1,2}[:時]\d{0,2})\s*[-～〜]\s*(\d{1,2}[:時]\d{0,2}|LAST|last|ラスト|翌\d{1,2}[:時]\d{0,2})"
    
    status_placeholder = st.empty()
    
    for i in range(7):
        target_date = datetime.date.today() + datetime.timedelta(days=i)
        date_iso = target_date.isoformat()
        status_placeholder.caption(f"🔄 {target_date} の状況を確認中...")
        
        target_url = f"{base_url}?date_get={target_date.strftime('%Y/%m/%d')}"
        try:
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 名前を探す [cite: 2026-01-28]
            target_element = soup.find(string=re.compile(hp_name))
            
            if target_element:
                # 【出勤時】名前の周辺から時間を解析 [cite: 2026-01-28]
                container = target_element.find_parent().find_parent()
                container_text = container.get_text(strip=True)
                time_match = re.search(time_pattern, container_text)
                shift_time = time_match.group(0) if time_match else "時間未定"
                
                # DB保存 [cite: 2026-01-28]
                conn.table("shifts").upsert({
                    "date": date_iso,
                    "cast_id": user_info['login_id'],
                    "shop_id": user_info['home_shop_id'],
                    "status": "確定",
                    "shift_time": shift_time
                }).execute()
                found_count += 1
            else:
                # 【重要：休み時】HPに名前がなければDBから削除 [cite: 2026-01-28]
                conn.table("shifts").delete().eq("date", date_iso).eq("cast_id", user_info['login_id']).execute()
                
        except Exception as e:
            st.error(f"同期エラー ({target_date}): {e}")
        
        time.sleep(0.3)
    
    status_placeholder.empty()
    return f"最新の状況を同期しました✨", found_count

# --- 3. 🔐 ログイン認証 ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        user_res = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user_res.data:
            st.session_state["user_info"] = user_res.data[0]
            st.session_state["password_correct"] = True
            
            # ログイン時オートシンク
            with st.spinner("最新のスケジュールを確認中..."):
                sync_individual_shift(st.session_state["user_info"])
            
            st.rerun()
        else:
            st.error("認証失敗。IDまたはパスワードが違います")
    st.stop()

user = st.session_state["user_info"]

# --- 4. メインUI ---

# キラキラヘッダー [cite: 2026-01-28]
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# 同期ボタン [cite: 2026-01-28]
col_t, col_s = st.columns([6, 4])
with col_t:
    st.subheader("📅 スケジュール")
with col_s:
    if st.button("🔄 同期する", use_container_width=True):
        msg, count = sync_individual_shift(user)
        st.toast(msg)
        time.sleep(1)
        st.rerun()

# --- 5. 🗓️ カレンダー描画（スマホ対応HTML Table） ---

try:
    shift_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    shift_map = {s['date']: s['shift_time'] for s in shift_res.data}
except:
    shift_map = {}

now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)

# スタイル [cite: 2026-01-28]
st.markdown("""
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 15px; }
    .calendar-table th { font-size: 0.75em; color: #999; padding-bottom: 8px; text-align: center; }
    .calendar-table td { 
        vertical-align: top; height: 55px; border: 1px solid #f0f0f0; 
        background-color: white; position: relative; padding: 4px;
    }
    .day-num { font-size: 0.8em; font-weight: 800; position: absolute; top: 4px; left: 6px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { 
        position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); 
        width: 18px; height: 4px; background-color: #FF4B4B; border-radius: 10px; 
    }
    .today-cell { border: 2px solid #FF4B4B !important; z-index: 5; }
</style>
""", unsafe_allow_html=True)

cal_html = '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
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
            
            is_shift_day = cell_date_str in shift_map
            classes = ["today-cell"] if cell_date == now else []
            if is_shift_day: classes.append("has-shift")
            
            class_str = f'class="{" ".join(classes)}"' if classes else ""
            bar = '<div class="shift-bar"></div>' if is_shift_day else ''
            cal_html += f'<td {class_str}><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr>"
cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# --- 6. 🕒 今日の詳細 ---
st.markdown("### 今日のスケジュール 🗓️")
with st.container(border=True):
    today_str = now.isoformat()
    if today_str in shift_map:
        st_time = shift_map[today_str]
        st.info(f"🕒 **本日のシフト：{st_time}**")
        st.write("📌 **予約状況：** 本日1件（20:30〜）")
    else:
        st.write("本日の予定はありません。ゆっくり休んでくださいね。")

# サイドバー
with st.sidebar:
    st.write(f"👤 {user['hp_display_name']} さん")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
