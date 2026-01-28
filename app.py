import streamlit as st
from st_supabase_connection import SupabaseConnection
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとグループ | ポータル", page_icon="💖", layout="centered")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🛰 統合同期関数（管理者用） ---
def sync_all_data():
    """スプレッドシートから店舗・名簿を上書き同期する"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])

        # A. 店舗一覧の同期
        shop_sheet = sh.worksheet("店舗一覧")
        shop_data = shop_sheet.get_all_records()
        if shop_data:
            for row in shop_data:
                row['shop_id'] = str(row['shop_id']).zfill(3)
            conn.table("shop_master").upsert(shop_data).execute()

        # B. キャスト名簿の同期
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

# --- 4. サイドバー（管理メニュー & ログアウト） ---
with st.sidebar:
    with st.expander("⚙️ 管理設定"):
        admin_key = st.text_input("Admin Key", type="password")
        if admin_key == "karin10":
