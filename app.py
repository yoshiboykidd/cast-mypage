import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup
import time

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- 2. 🛰 巡回スクレイピング関数（未来対応版） ---

def scrape_multi_day_shifts():
    """今日から7日間分のページを巡回してシフトを更新する"""
    try:
        # DBからマッピング用名簿を取得
        casts = conn.table("cast_members").select("login_id, hp_display_name, home_shop_id").execute()
        name_map = {c['hp_display_name']: (c['login_id'], c['home_shop_id']) for c in casts.data if c['hp_display_name']}
        
        if not name_map:
            return "先に名簿同期を行ってください。"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        base_url = "https://ikekari.com/attend.php"
        total_found = 0
        
        # 今日から7日分ループ
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.isoformat() # YYYY-MM-DD
            
            # HPのURL形式に合わせてパラメータを付与（?date=2026-01-28 など）
            # ※実際のURL形式が ?day= や ?d= の場合はここを調整します
            target_url = f"{base_url}?date={date_str}"
            
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html_text = res.text
            
            found_in_day = 0
            for hp_name, (c_id, s_id) in name_map.items():
                if hp_name in html_text:
                    conn.table("shifts").upsert({
                        "date": date_str,
                        "cast_id": c_id,
                        "shop_id": s_id,
                        "status": "確定"
                    }).execute()
                    found_in_day += 1
            
            total_found += found_in_day
            # サーバー負荷軽減のため、1ページごとに少し待機
            time.sleep(0.5)
            
        return f"7日間分をスキャンし、合計 {total_found} 件のシフトを更新しました！"
        
    except Exception as e:
        return f"エラー: {e}"

# --- 3. 🔐 ログイン認証（既存通り） ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    input_id = st.text_input("ログインID (8桁)")
    input_pw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        user = conn.table("cast_members").select("*").eq("login_id", input_id.zfill(8)).eq("password", input_pw).execute()
        if user.data:
            st.session_state["password_correct"] = True
            st.session_state["user_info"] = user.data[0]
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
        if st.button("1週間分のシフトを一括取得 🌐"):
            with st.spinner("1週間分を巡回中..."):
                msg = scrape_multi_day_shifts()
                st.success(msg)
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# --- 5. UI（カレンダー表示） ---
# (前回のカレンダー表示ロジックを継続)
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

st.subheader("📅 カレンダー")
now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)

# DBから本人のシフトを全取得
my_shifts = conn.table("shifts").select("date").eq("cast_id", user['login_id']).execute()
shift_days = [datetime.datetime.strptime(s['date'], "%Y-%m-%d").day for s in my_shifts.data]

# CSS & HTML 構築（省略せず反映）
cal_style = """
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .calendar-table td { vertical-align: top; height: 50px; border: 1px solid #f8f8f8; background-color: white; position: relative; padding: 4px; }
    .day-num { font-size: 0.7em; font-weight: 800; position: absolute; top: 3px; left: 5px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #222; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { position: absolute; bottom: 6px; left: 50%; transform: translateX(-50%); width: 18px; height: 4px; background-color: #FF4B4B; border-radius: 10px; }
    .today-cell { box-shadow: inset 0 0 0 2px #FF4B4B; border-radius: 4px; }
</style>
"""
cal_html = cal_style + '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    c = "sat" if i==5 else "sun-hol" if i==6 else "weekday"
    cal_html += f'<th style="font-size:0.7em; padding:5px 0;" class="{c}">{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0: cal_html += "<td></td>"
        else:
            cur_date = datetime.date(now.year, now.month, day)
            is_hol = jpholiday.is_holiday(cur_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if i==6 or is_hol else "weekday"
            td_class = []
            if day == now.day: td_class.append("today-cell")
            if day in shift_days: td_class.append("has-shift")
            bar = '<div class="shift-bar"></div>' if day in shift_days else ''
            cal_html += f'<td class="{" ".join(td_class)}"><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr>"
cal_html += "</table>"

st.markdown(cal_html, unsafe_allow_html=True)
