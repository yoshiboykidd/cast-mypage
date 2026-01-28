import streamlit as st
from st_supabase_connection import SupabaseConnection
import gspread
from google.oauth2.service_account import Credentials
import datetime
import calendar

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとグループ | ポータル", page_icon="💖")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🛰 統合同期関数（管理者用） ---
def sync_all_data():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])

        # 店舗一覧
        shop_sheet = sh.worksheet("店舗一覧")
        shop_data = shop_sheet.get_all_records()
        if shop_data:
            for row in shop_data:
                row['shop_id'] = str(row['shop_id']).zfill(3)
            conn.table("shop_master").upsert(shop_data).execute()

        # キャスト名簿
        all_casts = []
        for sheet in sh.worksheets():
            if sheet.title == "店舗一覧": continue
            data = sheet.get_all_records()
            if data:
                for row in data:
                    row['login_id'] = str(row['login_id']).zfill(8)
                    row['home_shop_id'] = str(row['home_shop_id']).zfill(3)
                    row['password'] = str(row['password'])
                all_casts.extend(data)
        
        if all_casts:
            conn.table("cast_members").upsert(all_casts).execute()
            return len(shop_data), len(all_casts)
        return len(shop_data), 0
    except Exception as e:
        st.error(f"同期エラー: {e}")
        return None, None

# --- 3. 🔐 ログイン認証 ---
def check_password():
    def password_entered():
        input_id = str(st.session_state["login_id"]).zfill(8)
        user = conn.table("cast_members").select("*").eq("login_id", input_id).eq("password", st.session_state["password_input"]).execute()
        if user.data:
            st.session_state["password_correct"] = True
            st.session_state["user_info"] = user.data[0]
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 ログイン")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.error("⚠️ IDまたはパスワードが正しくありません")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    return True

# --- 4. サイドバー ---
with st.sidebar:
    with st.expander("⚙️ 管理設定"):
        admin_key = st.text_input("Admin Key", type="password")
        if admin_key == "karin10":
            if st.button("全データを最新に同期 🔄"):
                with st.spinner("同期中..."):
                    s_count, c_count = sync_all_data()
                    if s_count is not None:
                        st.success(f"同期成功！店舗:{s_count} / キャスト:{c_count}")

    if st.session_state.get("password_correct"):
        st.divider()
        st.write(f"👤 {st.session_state['user_info']['display_name']} さん")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

# --- 5. メインコンテンツ ---
if check_password():
    user = st.session_state["user_info"]
    
    # 共通データ取得
    shops = conn.table("shop_master").select("*").execute()
    shop_options = {item['shop_id']: item['shop_name'] for item in shops.data}
    shop_ids = sorted(list(shop_options.keys()))

    # タブ設定
    tab1, tab2, tab3 = st.tabs(["実績入力", "シフト確認", "シフト申請"])

    # --- 実績入力 ---
    with tab1:
        with st.form("input_form", clear_on_submit=True):
            st.subheader("📝 本日の実績報告")
            default_idx = shop_ids.index(user['home_shop_id']) if user['home_shop_id'] in shop_ids else 0
            selected_shop = st.selectbox("勤務店舗", options=shop_ids, format_func=lambda x: f"{x}: {shop_options[x]}", index=default_idx)
            amount = st.number_input("本日の給与", min_value=0, step=1000)
            work_date = st.date_input("稼働日")
            if st.form_submit_button("実績を保存 ✨"):
                conn.table("daily_earnings").insert({"cast_id": user['login_id'], "shop_id": selected_shop, "amount": amount, "date": work_date.isoformat()}).execute()
                st.success("保存しました！")

    # --- シフト確認 (カレンダー表示) ---
    with tab2:
        st.subheader("📅 出勤スケジュール")
        
        # カレンダー生成ロジック
        now = datetime.datetime.now()
        year, month = now.year, now.month
        st.write(f"### {year}年 {month}月")
        
        # 曜日ヘッダー
        cols = st.columns(7)
        days = ["月", "火", "水", "木", "金", "土", "日"]
        for i, d in enumerate(days):
            cols[i].write(f"**{d}**")
        
        # 月の初日の曜日と日数を取得
        month_calendar = calendar.monthcalendar(year, month)
        
        # カレンダーを描画
        for week in month_calendar:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].write("")
                else:
                    # ここに「シフトが入っているか」の判定を将来入れる
                    # 今はテストで「空のボタン」を表示
                    if cols[i].button(str(day), key=f"day_{day}", use_container_width=True):
                        st.write(f"{month}月{day}日の詳細予定はありません。")

    # --- シフト申請 ---
    with tab3:
        st.subheader("📝 シフト希望の提出")
        with st.form("req_form"):
            req_date = st.date_input("希望日")
            req_shop = st.selectbox("希望店舗", options=shop_ids, format_func=lambda x: f"{x}: {shop_options[x]}", key="req_shop_select")
            req_note = st.text_area("備考")
            if st.form_submit_button("申請を送信"):
                st.success("申請を受け付けました（テスト送信完了）")
