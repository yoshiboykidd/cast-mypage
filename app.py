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

# --- 2. 🛰 巡回スクレイピング関数（URL形式修正版） ---

def scrape_multi_day_shifts():
    """今日から7日間分のページを巡回してシフトを更新する"""
    try:
        # DBからマッピング用名簿を取得
        casts = conn.table("cast_members").select("login_id, hp_display_name, home_shop_id").execute()
        name_map = {c['hp_display_name']: (c['login_id'], c['home_shop_id']) for c in casts.data if c['hp_display_name']}
        
        if not name_map:
            return "先に名簿同期（ボタン1）を行ってください。"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        base_url = "https://ikekari.com/attend.php"
        total_found = 0
        
        # 今日から7日分ループ
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            # 💡 指定されたURL形式 (YYYY/MM/DD) に変換
            url_date_str = target_date.strftime("%Y/%m/%d")
            db_date_str = target_date.isoformat() # DB保存用 (YYYY-MM-DD)
            
            target_url = f"{base_url}?date_get={url_date_str}"
            
            res = requests.get(target_url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            html_text = res.text
            
            found_in_day = 0
            for hp_name, (c_id, s_id) in name_map.items():
                if hp_name in html_text:
                    # DBへ保存
                    conn.table("shifts").upsert({
                        "date": db_date_str,
                        "cast_id": c_id,
                        "shop_id": s_id,
                        "status": "確定"
                    }).execute()
                    found_in_day += 1
            
            total_found += found_in_day
            time.sleep(0.3) # サーバー負荷軽減
            
        return f"今後1週間分をスキャンし、合計 {total_found} 件のシフトを更新しました！"
        
    except Exception as e:
        return f"エラー: {e}"

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
        if st.button("1. 名簿同期 🔄"):
            # (名簿同期ロジックは前回同様)
            st.info("同期中...")
        if st.button("2. 1週間分のシフトを一括取得 🌐"):
            with st.spinner("7日間分を巡回中..."):
                msg = scrape_multi_day_shifts()
                st.success(msg)
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# --- 5. UI（画像デザインの完全再現） ---

# A. 今日の売上カード（グラデーションとプログレスバー）
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333; text-shadow: 1px 1px 2px white;">¥ 28,500 GET!</span>
        <div style="background-color: rgba(255,255,255,0.6); padding: 8px; border-radius: 15px; margin-top: 10px; font-size: 0.8em; color: #444;">
            ✨ 本数：3本 / 目標：5本 🔥
        </div>
        <div style="background-color: rgba(255,255,255,0.6); padding: 8px; border-radius: 15px; margin-top: 5px; font-size: 0.8em; color: #444;">
            ✨ 今月の目標：65%達成 (¥65万 / ¥100万) 💖
        </div>
    </div>
    """, unsafe_allow_html=True)

# B. カレンダーエリア
st.subheader("📅 スケジュール")
now = datetime.date.today()
cal = calendar.monthcalendar(now.year, now.month)

# 本人の全シフト取得
my_shifts = conn.table("shifts").select("date").eq("cast_id", user['login_id']).execute()
shift_days = [datetime.datetime.strptime(s['date'], "%Y-%m-%d").day for s in my_shifts.data]

# カレンダーHTML
cal_style = """
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .calendar-table td { vertical-align: top; height: 50px; border: 1px solid #fdfdfd; background-color: white; position: relative; padding: 4px; border-radius: 8px; }
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
        if day == 0: cal_html += "<td></td>"
        else:
            cur_date = datetime.date(now.year, now.month, day)
            is_hol = jpholiday.is_holiday(cur_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if i==6 or is_hol else "weekday"
            td_class = ["today-cell"] if day == now.day else []
            if day in shift_days: td_class.append("has-shift")
            
            bar = '<div class="shift-bar"></div>' if day in shift_days else ''
            cal_html += f'<td class="{" ".join(td_class)}"><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr>"
cal_html += "</table>"
st.markdown(cal_html, unsafe_allow_html=True)

# C. スケジュール詳細（画像のデザインを反映）
st.markdown("### 今日のスケジュール 🗓️")
with st.container(border=True):
    if now.day in shift_days:
        st.markdown("""
            <div style="color: #555;">
                <span style="font-size: 0.9em;">🕒 シフト：19:00 - 24:00</span><br>
                <span style="font-size: 1.1em; font-weight: bold;">予約：20:30〜 90分 (田中様)</span><br>
                <span style="font-size: 0.8em; color: #888;">お店：池袋西口店</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("本日の出勤予定はありません。ゆっくり休んでくださいね！")
