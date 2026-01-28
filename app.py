import streamlit as st
from st_supabase_connection import SupabaseConnection
import gspread
from google.oauth2.service_account import Credentials

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとグループ | ポータル", page_icon="💖")

# Supabase接続
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🛰 同期関数（管理者用） ---
def sync_cast_master():
    """スプレッドシートから全店舗の名簿を読み込み、Supabaseを更新する"""
    try:
        # 認証設定（Secretsから読み込み）
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        
        # スプレッドシートをIDで開く
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])
        all_casts = []
        
        # 「店舗一覧」以外の全シートを巡回して名簿を収集
        for sheet in sh.worksheets():
            if sheet.title == "店舗一覧":
                continue
            data = sheet.get_all_records()
            if data:
                all_casts.extend(data)
        
        if all_casts:
            # 既存の名簿を削除（login_idが0以外の全件）してから新しくインサート
            conn.table("cast_members").delete().neq("login_id", "0").execute()
            conn.table("cast_members").insert(all_casts).execute()
            return len(all_casts)
        return 0
    except Exception as e:
        st.error(f"同期中にエラーが発生しました: {e}")
        return None

# --- 3. 🔐 ログイン認証ロジック ---
def check_password():
    """ユーザーがログインしているか確認する"""
    def password_entered():
        # DBからIDとPWが一致するユーザーを検索
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
        st.title("🔐 かりんとグループ ログイン")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 かりんとグループ ログイン")
        st.error("⚠️ IDまたはパスワードが正しくありません")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    return True

# --- 4. サイドバー（管理メニュー & ログアウト） ---
with st.sidebar:
    # 管理者用隠しメニュー（合言葉で展開）
    with st.expander("⚙️ 管理設定"):
        admin_key = st.text_input("Admin Key", type="password")
        if admin_key == "karin10": # あなたが決めた合言葉
            if st.button("名簿を最新に更新 🔄"):
                with st.spinner("同期中..."):
                    count = sync_cast_master()
                    if count is not None:
                        st.success(f"{count} 名を同期完了しました！")
    
    # ログイン中のユーザー情報を表示
    if st.session_state.get("password_correct"):
        st.divider()
        st.write(f"👤 {st.session_state['user_info']['display_name']} さん")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

# --- 5. メインコンテンツ ---
if check_password():
    user = st.session_state["user_info"]
    st.title(f"💖 {user['display_name']} さんのマイページ")
    
    # 店舗マスター取得（プルダウン用）
    shops = conn.table("shop_master").select("*").execute()
    shop_options = {item['shop_id']: item['shop_name'] for item in shops.data}
    shop_ids = list(shop_options.keys())

    # 実績入力フォーム
    with st.form("earnings_form", clear_on_submit=True):
        st.subheader("📝 本日の実績報告")
        
        # 自分の home_shop_id をデフォルト選択にする
        default_idx = 0
        if user['home_shop_id'] in shop_ids:
            default_idx = shop_ids.index(user['home_shop_id'])
        
        # ここでエラーが出ていたので慎重に記述
        selected_shop_id = st.selectbox(
            "勤務店舗（ヘルプの場合は変更してください）",
            options=shop_ids,
            format_func=lambda x: f"{x}: {shop_options[x]}",
            index=default_idx
        )
        
        amount = st.number_input("本日の給与 (円)", min_value=0, step=1000)
        work_date = st.date_input("稼働日")
        memo = st.text_area("メモ (接客内容やヘルプ報告など)")
        
        if st.form_submit_button("実績を保存する ✨"):
            conn.table("daily_earnings").insert({
                "cast_id": user['login_id'],
                "shop_id": selected_shop_id,
                "amount": amount,
                "date": work_date.isoformat(),
                "memo": memo
            }).execute()
            st.success("保存しました！今日も一日お疲れ様でした。")
            st.balloons()

    # 履歴表示
    st.divider()
    st.subheader("📊 最近の入力履歴（直近10件）")
    history = conn.table("daily_earnings") \
        .select("*") \
        .eq("cast_id", user['login_id']) \
        .order("date", desc=True) \
        .limit(10) \
        .execute()
    
    if history.data:
        st.table(history.data)
    else:
        st.info("実績データはまだありません。")
