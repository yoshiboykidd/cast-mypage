import streamlit as st
from st_supabase_connection import SupabaseConnection
import gspread
from google.oauth2.service_account import Credentials

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとグループ | 管理ポータル", page_icon="💖")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🛰 統合同期関数（管理者用） ---
def sync_all_data():
    """スプレッドシートから店舗一覧と名簿の両方を同期する"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])

        # --- A. 店舗一覧の同期 ---
        shop_sheet = sh.worksheet("店舗一覧")
        shop_data = shop_sheet.get_all_records()
        if shop_data:
            # 型変換: shop_idを必ず文字列(001など)として扱う
            for row in shop_data:
                row['shop_id'] = str(row['shop_id']).zfill(3)
            
            # 店舗マスターを更新
            conn.table("shop_master").delete().neq("shop_id", "none").execute()
            conn.table("shop_master").insert(shop_data).execute()
            st.write("✅ 店舗リストの更新完了")

        # --- B. キャスト名簿の同期 ---
        all_casts = []
        for sheet in sh.worksheets():
            if sheet.title == "店舗一覧":
                continue
            data = sheet.get_all_records()
            if data:
                for row in data:
                    # home_shop_idも3桁の文字列に統一
                    row['home_shop_id'] = str(row['home_shop_id']).zfill(3)
                    # login_idも文字列として保持
                    row['login_id'] = str(row['login_id'])
                all_casts.extend(data)
        
        if all_casts:
            # キャスト名簿を更新
            conn.table("cast_members").delete().neq("login_id", "0").execute()
            conn.table("cast_members").insert(all_casts).execute()
            return len(shop_data), len(all_casts)
        
        return len(shop_data), 0
    except Exception as e:
        st.error(f"同期エラー: {e}")
        return None, None

# --- 3. 🔐 ログイン認証（前回同様） ---
def check_password():
    def password_entered():
        user = conn.table("cast_members") \
            .select("*") \
            .eq("login_id", st.session_state["login_id"]) \
            .eq("password", st.session_state["password_input"]) \
            .execute()
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
        st.error("⚠️ IDまたはパスワードが違います")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    return True

# --- 4. 管理メニュー ---
with st.sidebar:
    with st.expander("⚙️ 管理設定"):
        admin_key = st.text_input("Admin Key", type="password")
        if admin_key == "karin10":
            if st.button("全データを最新に同期 🔄"):
                with st.spinner("店舗と名簿を同期中..."):
                    s_count, c_count = sync_all_data()
                    if s_count is not None:
                        st.success(f"同期完了！店舗:{s_count}件 / キャスト:{c_count}名")

    if st.session_state.get("password_correct"):
        st.divider()
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

# --- 5. メイン画面 ---
if check_password():
    user = st.session_state["user_info"]
    st.title(f"💖 {user['display_name']} さんのマイページ")
    
    # 店舗プルダウン作成
    shops = conn.table("shop_master").select("*").execute()
    shop_options = {item['shop_id']: item['shop_name'] for item in shops.data}
    shop_ids = list(shop_options.keys())

    with st.form("input_form"):
        # 自分の店を初期選択
        default_idx = shop_ids.index(user['home_shop_id']) if user['home_shop_id'] in shop_ids else 0
        
        st.selectbox("勤務店舗", options=shop_ids, format_func=lambda x: f"{x}:{shop_options[x]}", index=default_idx, key="selected_shop")
        amount = st.number_input("本日の給与", min_value=0, step=1000)
        work_date = st.date_input("稼働日")
        
        if st.form_submit_button("実績を保存 ✨"):
            conn.table("daily_earnings").insert({
                "cast_id": user['login_id'],
                "shop_id": st.session_state.selected_shop,
                "amount": amount,
                "date": work_date.isoformat()
            }).execute()
            st.success("保存しました！")
