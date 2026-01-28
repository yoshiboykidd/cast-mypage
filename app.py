import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")

# Supabase接続
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("Supabaseへの接続に失敗しました。Secretsの設定を確認してください。")
    st.stop()

# 祝日判定用ライブラリ
try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- 2. 🔐 ログイン認証（以前のコードを維持） ---
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

user = st.session_state["user_info"]

# --- 3. 🛰 シフト一括取得関数 ---
def scrape_multi_day_shifts():
    try:
        casts = conn.table("cast_members").select("login_id, hp_display_name, home_shop_id").execute()
        name_map = {c['hp_display_name']: (c['login_id'], c['home_shop_id']) for c in casts.data if c['hp_display_name']}
        
        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://ikekari.com/attend.php"
        logs = []
        total_found = 0
        
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            target_url = f"{base_url}?date_get={target_date.strftime('%Y/%m/%d')}"
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            page_text = BeautifulSoup(res.text, 'html.parser').get_text()
            
            found_today = 0
            for hp_name, (c_id, s_id) in name_map.items():
                if hp_name in page_text:
                    conn.table("shifts").upsert({
                        "date": target_date.isoformat(),
                        "cast_id": c_id,
                        "shop_id": s_id,
                        "status": "確定"
                    }).execute()
                    found_today += 1
            logs.append(f"📅 {target_date}: {found_today}名")
            total_found += found_today
            time.sleep(0.3)
        return logs, total_found
    except Exception as e:
        return [f"エラー: {e}"], 0

# --- 4. サイドバー (管理メニュー) ---
with st.sidebar:
    st.header("Admin Menu")
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key == "karin10":
        if st.button("🌐 1週間分の一括同期"):
            with st.spinner("同期中..."):
                logs, count = scrape_multi_day_shifts()
                for log in logs: st.caption(log)
                st.success(f"計 {count} 件更新！")
    
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# --- 5. メインUI ---
# キラキラ売上ヘッダー
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# カレンダー描画
st.subheader("📅 スケジュール")

# データ取得
try:
    shift_res = conn.table("shifts").select("date").eq("cast_id", user['login_id']).execute()
    shift_date_list = [s['date'] for s in shift_res.data]
except:
    shift_date_list = []

now = datetime.date.today()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# CSS設定（テーブルをスマホでも固定するためのプロ仕様）
st.markdown("""
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 15px; }
    .calendar-table th { font-size: 0.7em; color: #999; padding-bottom: 8px; text-align: center; }
    .calendar-table td { 
        vertical-align: top; 
        height: 60px; /* 少し高さを出して押しやすく */
        border: 1px solid #f0f0f0; 
        background-color: white; 
        position: relative; 
        padding: 4px;
    }
    .day-num { font-size: 0.8em; font-weight: 800; position: absolute; top: 4px; left: 6px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { 
        position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); 
        width: 16px; height: 4px; background-color: #FF4B4B; border-radius: 10px; 
    }
    .today-cell { border: 2px solid #FF4B4B !important; z-index: 10; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# テーブル開始
cal_html = '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    c = "sat" if i==5 else "sun-hol" if i==6 else "weekday"
    cal_html += f'<th>{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0:
            cal_html += "<td></td>"
        else:
            cell_date = datetime.date(year, month, day)
            cell_date_str = cell_date.isoformat()
            
            is_hol = jpholiday.is_holiday(cell_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if (i==6 or is_hol) else "weekday"
            is_shift_day = cell_date_str in shift_date_list
            
            classes = []
            if cell_date == now: classes.append("today-cell")
            if is_shift_day: classes.append("has-shift")
            
            class_str = f'class="{" ".join(classes)}"' if classes else ""
            bar = '<div class="shift-bar"></div>' if is_shift_day else ''
            
            cal_html += f'<td {class_str}><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr>"
cal_html += "</table>"

st.markdown(cal_html, unsafe_allow_html=True)

# 予定詳細表示
st.markdown("### 今日のスケジュール 🗓️")
with st.container(border=True):
    if now.isoformat() in shift_date_list:
        st.info("🕒 シフト：19:00 - 24:00\n\n📌 予約：1件 (20:30〜)")
    else:
        st.write("本日の予定はありません。ゆっくり休んでくださいね。")
