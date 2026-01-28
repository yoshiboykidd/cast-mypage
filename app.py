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

# --- 2. 🛰 巡回同期関数（リフレッシュ機能付き） ---
def sync_personal_shift(login_id, hp_name, shop_id):
    """自分のデータだけをリフレッシュして取得"""
    try:
        today = datetime.date.today()
        # 1. 重複防止のため、今日から1週間分を一旦消去
        conn.table("shifts").delete().eq("cast_id", login_id).gte("date", today.isoformat()).lte("date", (today + datetime.timedelta(days=7)).isoformat()).execute()

        headers = {"User-Agent": "Mozilla/5.0"}
        base_url = "https://ikekari.com/attend.php"
        count = 0
        
        for i in range(7):
            t_date = today + datetime.timedelta(days=i)
            url_str = t_date.strftime("%Y/%m/%d")
            res = requests.get(f"{base_url}?date_get={url_str}", headers=headers, timeout=10)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 名前と時間を高精度に検索
            target = soup.find(string=re.compile(re.escape(hp_name.strip())))
            if target:
                container = "".join([p.get_text() for p in list(target.parents)[:3]])
                time_m = re.search(r'(\d{1,2}[:：]\d{2}.{0,5}\d{1,2}[:：]\d{2})|(\d{1,2}[:：]\d{2}.{0,2}[〜~])', container)
                tm = time_m.group(0) if time_m else "時間未定"
                
                conn.table("shifts").insert({
                    "date": t_date.isoformat(),
                    "cast_id": login_id,
                    "shop_id": shop_id,
                    "shift_time": tm,
                    "status": "確定"
                }).execute()
                count += 1
            time.sleep(0.2)
        return count
    except:
        return 0

# --- 3. 🔐 ログイン認証 ---
if "user_info" not in st.session_state:
    st.title("🔐 ログイン")
    uid = st.text_input("ログインID (8桁)")
    upw = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        res = conn.table("cast_members").select("*").eq("login_id", uid.zfill(8)).eq("password", upw).execute()
        if res.data:
            st.session_state["user_info"] = res.data[0]
            st.rerun()
    st.stop()

# --- 4. メイン画面 ---
user = st.session_state["user_info"]
now = datetime.date.today()

# A. 売上見込みカード（きれいなデザインを継承）
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 20px; border-radius: 20px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px;">
        <span style="color: #666; font-size: 0.9em; font-weight: bold;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 2em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# B. 同期ボタン（サイドバーではなくメインに配置）
h1, h2 = st.columns([0.7, 0.3])
with h1: st.subheader("📅 スケジュール")
with h2:
    if st.button("🔄 同期"):
        with st.spinner("同期中..."):
            cnt = sync_personal_shift(user['login_id'], user['hp_display_name'], user['home_shop_id'])
            st.success(f"{cnt}件更新！")
            time.sleep(1)
            st.rerun()

# 状態管理（選択した日付を記憶）
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now.isoformat()

# DBからシフト取得
try:
    s_res = conn.table("shifts").select("date, shift_time").eq("cast_id", user['login_id']).execute()
    s_map = {s['date']: s['shift_time'] for s in s_res.data}
except: s_map = {}

# --- 🗓️ カレンダー描画（CSSとHTMLテーブル） ---
cal_style = """
<style>
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .calendar-table td { 
        vertical-align: top; height: 55px; border: 1px solid #f8f8f8; 
        background-color: white; position: relative; padding: 4px; border-radius: 8px; 
    }
    .day-num { font-size: 0.75em; font-weight: 800; position: absolute; top: 5px; left: 7px; }
    .sat { color: #007AFF; } .sun-hol { color: #FF3B30; } .weekday { color: #444; }
    .has-shift { background-color: #FFF5F7 !important; }
    .shift-bar { 
        position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%); 
        width: 22px; height: 5px; background-color: #FF4B4B; border-radius: 10px; 
    }
    .today-cell { border: 2px solid #FF4B4B !important; }
</style>
"""

cal = calendar.monthcalendar(now.year, now.month)
cal_html = cal_style + '<table class="calendar-table"><tr>'
for i, wd in enumerate(["月","火","水","木","金","土","日"]):
    c = "sat" if i==5 else "sun-hol" if i==6 else "weekday"
    cal_html += f'<th style="font-size:0.75em; color:#999; padding-bottom:8px;">{wd}</th>'
cal_html += "</tr>"

for week in cal:
    cal_html += "<tr>"
    for i, day in enumerate(week):
        if day == 0: cal_html += "<td></td>"
        else:
            c_date = datetime.date(now.year, now.month, day)
            c_str = c_date.isoformat()
            is_hol = jpholiday.is_holiday(c_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if i==6 or is_hol else "weekday"
            
            is_s = c_str in s_map
            td_class = ["today-cell"] if c_date == now else []
            if is_s: td_class.append("has-shift")
            
            bar = '<div class="shift-bar"></div>' if is_s else ''
            cal_html += f'<td class="{" ".join(td_class)}"><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr>"
cal_html += "</table>"

st.markdown(cal_html, unsafe_allow_html=True)

# C. 予定の切り替え（セレクトボックスで詳細を確認）
st.divider()
# シフトがある日だけを選択肢にする
target_dates = sorted(s_map.keys())
if target_dates:
    selected = st.selectbox("詳細を見たい日を選択", target_dates, format_func=lambda x: f"{x} のシフトを表示")
    with st.container(border=True):
        st.write(f"⏰ **出勤時間：{s_map[selected]}**")
        st.write("🏢 **店舗：池袋西口店**")
else:
    st.info("現在、1週間以内のシフトはありません。「同期」を押してください。")
