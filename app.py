import streamlit as st
from st_supabase_connection import SupabaseConnection
import gspread
from google.oauth2.service_account import Credentials

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとグループ | キャストポータル", page_icon="💖", layout="centered")

# Supabase接続
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. 🛰 Googleスプレッドシート同期関数 ---
def sync_cast_master():
    """Googleスプレッドシートから全店舗の名簿を取得し、Supabaseに同期する"""
    try:
        # 認証設定
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        
        # スプレッドシートをIDで開く
        sh = client.open_by_key(st.secrets["spreadsheet"]["id"])
        all_casts = []
        
        # 全シートをループ（店舗ごとにシートが分かれている前提）
        for sheet in sh.worksheets():
            # 「店舗一覧」シートは名簿ではないのでスキップ
            if sheet.title == "店舗一覧":
                continue
            
            # シートの全データを取得（1行目が見出し：login_id, password, display_name, home_shop_id）
            data = sheet.get_all_records()
            if data:
                all_casts.extend(data)
        
        if all_casts:
            # Supabaseのテーブルを一度クリアして、最新名簿をインサート（全件入れ替え）
            # 注意: 実績(daily_earnings)は消さず、名簿(cast_members)のみを更新
            conn.table("cast_members").delete().neq("login_id", "0").execute()
            conn.table("cast_members").insert(all_casts).execute()
            return len(all_casts)
        return 0
    except Exception as e:
        st.error(f"同期エラーが発生しました: {e}")
        return None

# --- 3. 🔐 ログイン認証ロジック ---
def check_password():
    """ユーザーがログインしているか確認し、ログイン画面またはコンテンツを表示する"""
    def password_entered():
        # DBからIDとPWが一致するユーザーを1件取得
        user = conn.table("cast_members") \
            .select("*") \
            .eq("login_id", st.session_state["login_id"]) \
            .eq("password", st.session_state["password_input"]) \
            .execute()

        if user.data:
            st.session_state["password_correct"] = True
            st.session_state["user_info"] = user.data[0] # キャスト情報を保存
            del st.session_state["password_input"] # 安全のため入力フォームのPWを削除
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 初回表示（未ログイン）
        st.title("🔐 かりんとグループ ログイン")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # パスワード間違い
        st.title("🔐 かりんとグループ ログイン")
        st.error("⚠️ IDまたはパスワードが正しくありません")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    return True

# --- 4. メインコンテンツ ---
if check_password():
    user = st.session_state["user_info"]
    
    # サイドバー：管理者用同期ボタンとログアウト
    with st.sidebar:
        st.write(f"👤 ログイン中: {user['display_name']} さん")
        st.divider()
        st.subheader("⚙️ 管理者メニュー")
        if st.button("名簿を最新に更新 🔄"):
            with st.spinner("スプレッドシートから全店舗データを同期中..."):
                count = sync_cast_master()
                if count is not None:
                    st.success(f"同期完了！全 {count} 名の名簿を更新しました。")
        
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

    # メイン画面：マイページ表示
    st.title(f"💖 {user['display_name']} さんのマイページ")
    
    # 店舗一覧をDBから取得（店舗プルダウン用）
    shops = conn.table("shop_master").select("*").execute()
    shop_options = {item['shop_id']: item['shop_name'] for item in shops.data}
    shop_ids = list(shop_options.keys())

    # 実績入力フォーム
    with st.form("earnings_form", clear_on_submit=True):
        st.subheader("📝 本日の実績報告")
        
        # デフォルトで自分の本拠地(home_shop_id)を選択状態にする
        default_idx = shop_ids.index(user['home_shop_id']) if user['home_shop_id'] in shop_ids else 0
        
        selected_shop_id = st.selectbox(
            "勤務店舗（ヘルプの場合は変更してください）",
            options=shop_ids,
            format_func=lambda x: f"{x}: {shop_options[x]}",
            index=default_idx
        )
        
        amount = st.number_input("給与（円）", min_value=0, step=1000)
        work_date = st.date_input("稼働日")
        memo = st.text_area("メモ（接客内容やヘルプ報告など）")
        
        if st.form_submit_button("実績を保存する ✨"):
            conn.table("daily_earnings").insert({
                "cast_id": user['login_id'],
                "shop_id": selected_shop_id,
                "amount": amount,
                "date": work_date.isoformat(),
                "memo": memo
            }).execute()
            st.success("実績を保存しました！お疲れ様でした。")
            st.balloons()

    # 履歴表示（直近10件）
    st.divider()
    st.subheader("📊 あなたの最近の実績")
    history = conn.table("daily_earnings") \
        .select("*") \
        .eq("cast_id", user['login_id']) \
        .order("date", desc=True) \
        .limit(10) \
        .execute()
    
    if history.data:
        # 表示用にデータを整理
        st.dataframe(history.data, use_container_width=True)
    else:
        st.info("まだ実績データがありません。")
