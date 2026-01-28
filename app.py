import streamlit as st
from st_supabase_connection import SupabaseConnection
import gspread
from google.oauth2.service_account import Credentials

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとグループ | ポータル", page_icon="💖")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🛰 統合同期関数（桁数強制修正版） ---
def sync_all_data():
    """スプレッドシートから店舗一覧と名簿の両方を同期する（0埋め対応）"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])

        # --- A. 店舗一覧の同期 ---
        shop_sheet = sh.worksheet("店舗一覧")
        shop_data = shop_sheet.get_all_records()
        if shop_data:
            for row in shop_data:
                # shop_idを必ず3桁の文字列(001など)に矯正
                row['shop_id'] = str(row['shop_id']).zfill(3)
            
            conn.table("shop_master").delete().neq("shop_id", "none").execute()
            conn.table("shop_master").insert(shop_data).execute()

        # --- B. キャスト名簿の同期 ---
        all_casts = []
        for sheet in sh.worksheets():
            if sheet.title == "店舗一覧":
                continue
            data = sheet.get_all_records()
            if data:
                for row in data:
                    # login_idを必ず8桁(00100001など)に矯正
                    row['login_id'] = str(row['login_id']).zfill(8)
                    # home_shop_idを必ず3桁(001など)に矯正
                    row['home_shop_id'] = str(row['home_shop_id']).zfill(3)
                    # パスワードなども念のため文字列に
                    row['password'] = str(row['password'])
                all_casts.extend(data)
        
        if all_casts:
            conn.table("cast_members").delete().neq("login_id", "none").execute()
            conn.table("cast_members").insert(all_casts).execute()
            return len(shop_data), len(all_casts)
        
        return len(shop_data), 0
    except Exception as e:
        st.error(f"同期エラー: {e}")
        return None, None

# --- 3. 🔐 ログイン認証 ---
def check_password():
    def password_entered():
        # 入力されたIDも8桁に揃えてから検索する（入力ミス対策）
        input_id = str(st.session_state["login_id"]).zfill(8)
        
        user = conn.table("cast_members") \
            .select("*") \
            .eq("login_id", input_id) \
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
        st.error("⚠️ IDまたはパスワードが正しくありません")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    return True

# --- 4. 管理メニュー（サイドバー） ---
with st.sidebar:
    with st.expander("⚙️ 管理設定"):
        admin_key = st.text_input("Admin Key", type="password")
        if admin_key == "karin10": # ここをご希望のPWに変更済み
            if st.button("全データを最新に同期 🔄"):
                with st.spinner("0埋め処理を適用して同期中..."):
                    s_count, c_count = sync_all_data()
                    if s_count is not None:
                        st.success(f"同期完了！店舗:{s_count} / キャスト:{c_count}")

    if st.session_state.get("password_correct"):
        st.divider()
        st.write(f"👤 {st.session_state['user_info']['display_name']} さん")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

# --- 5. メイン画面 ---
if check_password():
    user = st.session_state["user_info"]
    st.title(f"💖 {user['display_name']} さんのマイページ")
    
    shops = conn.table("shop_master").select("*").execute()
    shop_options = {item['shop_id']: item['shop_name'] for item in shops.data}
    shop_ids = sorted(list(shop_options.keys()))

    with st.form("input_form", clear_on_submit=True):
        default_idx = shop_ids.index(user['home_shop_id']) if user['home_shop_id'] in shop_ids else 0
        
        selected_shop = st.selectbox(
            "勤務店舗（ヘルプは変更してください）", 
            options=shop_ids, 
            format_func=lambda x: f"{x}: {shop_options[x]}", 
            index=default_idx
        )
        
        amount = st.number_input("本日の給与（円）", min_value=0, step=1000)
        work_date = st.date_input("稼働日")
        memo = st.text_area("メモ")
        
        if st.form_submit_button("実績を保存する ✨"):
            conn.table("daily_earnings").insert({
                "cast_id": user['login_id'],
                "shop_id": selected_shop,
                "amount": amount,
                "date": work_date.isoformat(),
                "memo": memo
            }).execute()
            st.success("実績を保存しました！お疲れ様でした。")
            st.balloons()

    # 自分の履歴表示
    st.divider()
    history = conn.table("daily_earnings").select("*").eq("cast_id", user['login_id']).order("date", desc=True).limit(5).execute()
    if history.data:
        st.subheader("📊 あなたの最近の履歴")
        st.table(history.data)
