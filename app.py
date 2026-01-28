import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import calendar
import requests
from bs4 import BeautifulSoup

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

try:
    import jpholiday
except ImportError:
    jpholiday = None

# --- 2. 🛰 統合同期 & スクレイピング関数 ---

def sync_all_data():
    """スプレッドシートから店舗・名簿（HP表示名含む）を同期"""
    import gspread
    from google.oauth2.service_account import Credentials
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])

        # A. 店舗マスター
        shop_sheet = sh.worksheet("店舗一覧")
        shop_data = shop_sheet.get_all_records()
        if shop_data:
            for row in shop_data:
                row['shop_id'] = str(row['shop_id']).zfill(3)
            conn.table("shop_master").upsert(shop_data).execute()

        # B. キャスト名簿（「HP表示名」を読み込む）
        all_casts = []
        for sheet in sh.worksheets():
            if sheet.title == "店舗一覧": continue
            data = sheet.get_all_records()
            if data:
                for row in data:
                    row['login_id'] = str(row['login_id']).zfill(8)
                    row['home_shop_id'] = str(row['home_shop_id']).zfill(3)
                    # スプレッドシートの「HP表示名」をDBに保存
                    # row['hp_display_name'] はシートの列名と一致させる必要があります
                all_casts.extend(data)
        
        if all_casts:
            conn.table("cast_members").upsert(all_casts).execute()
            return len(shop_data), len(all_casts)
        return len(shop_data), 0
    except Exception as e:
        st.error(f"同期エラー: {e}")
        return None, None

def scrape_and_update_shifts():
    """公式HPから今日の出勤者を読み取り、シフトを自動登録する"""
    try:
        # 1. HPのHTMLを取得
        url = "https://ikekari.com/attend.php"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 2. HP上の名前をリストアップ（サイト構造に合わせて調整）
        # ikekari.comの構造に基づき、キャスト名のタグを抽出
        scraped_names = [tag.text.strip() for tag in soup.find_all(class_="name")]
        
        if not scraped_names:
            return "HPから名前を検出できませんでした。"

        # 3. DBから「HP表示名」と「ID」のペアを取得
        casts = conn.table("cast_members").select("login_id, hp_display_name, home_shop_id").execute()
        name_to_id = {c['hp_display_name']: (c['login_id'], c['home_shop_id']) for c in casts.data if c['hp_display_name']}

        # 4. 一致するキャストのシフトを登録
        today = datetime.date.today().isoformat()
        count = 0
        for name in scraped_names:
            if name in name_to_id:
                c_id, s_id = name_to_id[name]
                conn.table("shifts").upsert({
                    "date": today,
                    "cast_id": c_id,
                    "shop_id": s_id,
                    "status": "確定"
                }).execute()
                count += 1
        
        return f"本日のシフトを {count} 名分更新しました！"
    except Exception as e:
        return f"スクレイピング失敗: {e}"

# --- 3. 🔐 ログイン認証 ---
if "password_correct" not in st.session_state:
    st.title("🔐 ログイン")
    # 簡易版ログイン（実際はDB照合）
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

# サイドバー（管理者用ボタン）
with st.sidebar:
    st.header("Admin Menu")
    admin_key = st.text_input("Admin Key", type="password")
    if admin_key == "karin10":
        if st.button("名簿同期 🔄"):
            sync_all_data()
        if st.button("HPから本日のシフト取得 🌐"):
            msg = scrape_and_update_shifts()
            st.success(msg)
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

# 売上見込み表示
st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFDEE9 0%, #B5FFFC 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
        <span style="color: #666; font-size: 0.8em;">今日の売上 (見込み) ✨</span><br>
        <span style="font-size: 1.8em; font-weight: bold; color: #333;">¥ 28,500 GET!</span>
    </div>
    """, unsafe_allow_html=True)

# カレンダー表示
st.subheader("📅 カレンダー")
now = datetime.date.today()
year, month = now.year, now.month
cal = calendar.monthcalendar(year, month)

# 本人のシフト日をDBから取得
my_shifts = conn.table("shifts").select("date").eq("cast_id", user['login_id']).execute()
shift_days = [datetime.datetime.strptime(s['date'], "%Y-%m-%d").day for s in my_shifts.data]

# カレンダーHTML構築（視認性強化版）
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
            cur_date = datetime.date(year, month, day)
            is_hol = jpholiday.is_holiday(cur_date) if jpholiday else False
            d_color = "sat" if i==5 else "sun-hol" if i==6 or is_hol else "weekday"
            td_class = []
            if day == now.day: td_class.append("today-cell")
            if day in shift_days: td_class.append("has-shift")
            
            bar = '<div class="shift-bar"></div>' if day in shift_days else ''
            cal_html += f'<td class="{" ".join(td_class)}"><span class="day-num {d_color}">{day}</span>{bar}</td>'
    cal_html += "</tr></table>"

st.markdown(cal_html, unsafe_allow_html=True)

# 詳細エリア
st.divider()
st.subheader("📝 本日の予定")
with st.container(border=True):
    if now.day in shift_days:
        st.success("✅ 本日は出勤予定です")
    else:
        st.info("出勤予定はありません")
