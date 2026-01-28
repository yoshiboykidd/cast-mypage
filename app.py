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

# --- 2. 🛰 巡回スクレイピング関数（正確な日付紐付け版） ---

def scrape_multi_day_shifts():
    """HPから今後1週間のシフトを取得し、正確な日付でDB保存する"""
    try:
        casts = conn.table("cast_members").select("login_id, hp_display_name, home_shop_id").execute()
        name_map = {c['hp_display_name']: (c['login_id'], c['home_shop_id']) for c in casts.data if c['hp_display_name']}
        
        if not name_map:
            return "名簿同期を行ってください。", 0

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        base_url = "https://ikekari.com/attend.php"
        logs = []
        total_found = 0
        
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            url_date_str = target_date.strftime("%Y/%m/%d")
            db_date_str = target_date.isoformat() # DBには '2026-01-28' 形式で保存
            
            target_url = f"{base_url}?date_get={url_date_str}"
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            page_text = soup.get_text()
            
            found_names_today = []
            for hp_name, (c_id, s_id) in name_map.items():
                if hp_name in page_text:
                    conn.table("shifts").upsert({
                        "date": db_date_str, # 正確な日付で保存
                        "cast_id": c_id,
                        "shop_id": s_id,
                        "status": "確定"
                    }).execute()
                    found_names_today.append(hp_name)
            
            logs.append(f"📅 {url_date_str}: {len(found_names_today)}名検出")
            total_found += len(found_names_today)
            time.sleep(0.3)
            
        return logs, total_found
    except Exception as e:
        return [f"エラー: {e}"], 0

# --- 3. 🔐 ログイン認証 ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
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

# --- 4. メイン画面 ---
user = st.session_state["user_info"]

with st.sidebar:
    st.header("Admin Menu")
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key == "karin10":
        if st.button("2. 1週間分のシフトを一括取得 🌐"):
            with st.spinner("一括取得中..."):
                logs, count = scrape_multi_day_shifts()
                for log in logs: st.caption(log)
                st.success(f"合計 {count} 件更新！")
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# --- 5. UI（キラキラデザイン再現） ---
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# --- 🗓️ カレンダー描画ロジック（修正の核心） ---
st.subheader("📅 スケジュール")
now = datetime.date.today()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# DBから本人の全シフトを「日付文字列」のリストとして取得
try:
    shift_res = conn.table("shifts").select("date").eq("cast_id", user['login_id']).execute()
    # shift_date_list = ['2026-01-28', '2026-01-29', ...]
    shift_date_list = [s['date'] for s in shift_res.data]
except:
    shift_date_list = []

# CSS設定
cal_style = """
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .calendar-table td { vertical-align: top; height: 50px; border: 1px solid #f8f8f8; background-color: white; position: relative; padding: 4px; border-radius: 8px; }
    .day-num { font-size: 0.7em; font-weight: 800; position: absolute; top: 4px; left: 6px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); width: 20px; height: 4px; background-color: #FF4B4B; border-radius: 10px; }
    .today-cell { box-shadow: inset 0 0 0 2px #FF4B4B; }
</style>
"""

cal_html = cal_style + '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    c = "sat" if i==5 else "sun-hol" if i==6 else "weekday"
    cal_html += f'<th style="font-size:0.75em; color:#999; padding-bottom:5px;">{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0:
            cal_html += "<td></td>"
        else:
            # 💡 ここで「そのマスの日付」を正確に生成
            cell_date = datetime.date(year, month, day)
            cell_date_str = cell_date.isoformat() # '2026-01-28'
            
            # 祝日・色判定
            is_hol = jpholiday.is_holiday(cell_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if i==6 or is_hol else "weekday"
            
            # シフトがあるかどうかの判定（日付文字列で完全一致チェック）
            is_shift_day = cell_date_str in shift_date_list
            
            td_classes = []
            if cell_date == now: td_classes.append("today-cell")
            if is_shift_day: td_classes.append("has-shift")
            
            td_class_str = f'class="{" ".join(td_classes)}"' if td_classes else ""
            bar = '<div class="shift-bar"></div>' if is_shift_day else ''
            
            cal_html += f'<td {td_class_str}><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr>"
cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# 予定詳細
st.markdown("### 今日のスケジュール 🗓️")
with st.container(border=True):
    if now.isoformat() in shift_date_list:
        st.info("🕒 シフト：19:00 - 24:00\n\n📌 予約：1件 (20:30〜)")
    else:
        st.write("本日の予定はありません。ゆっくり休んでくださいね。")
