import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime

# --- 1. ページ構成（スマホ最適化） ---
st.set_page_config(page_title="かりんとポータル", layout="centered")

# --- 2. 接続設定 ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. 認証機能（ロジックのみ） ---
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
        st.header("🔐 ログイン")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.error("IDまたはパスワードが違います")
        st.text_input("ログインID (8桁)", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        st.button("ログイン", on_click=password_entered)
        return False
    return True

# --- 4. サイドバー構成（管理・共通機能） ---
with st.sidebar:
    st.title("Menu")
    with st.expander("⚙️ 管理設定"):
        admin_key = st.text_input("Admin Key", type="password")
        if admin_key == "karin10":
            st.button("店舗・名簿を同期 🔄")
            st.button("HPからシフト取得 🌐")
    
    if st.session_state.get("password_correct"):
        st.divider()
        st.write(f"USER: {st.session_state['user_info']['display_name']}")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

# --- 5. メイン画面（機能タブ） ---
if check_password():
    user = st.session_state["user_info"]
    
    # 店舗マスターの取得（プルダウン用）
    shops = conn.table("shop_master").select("*").execute()
    shop_options = {item['shop_id']: item['shop_name'] for item in shops.data}
    shop_ids = sorted(list(shop_options.keys()))

    # 【重要】スマホでの操作性を決める3つのタブ
    tab_earn, tab_shift, tab_req = st.tabs(["実績報告", "シフト確認", "シフト申請"])

    # --- A. 実績報告タブ ---
    with tab_earn:
        st.subheader("実績報告")
        with st.form("earn_form", clear_on_submit=True):
            # デフォルトで自分の本拠地を選択
            def_idx = shop_ids.index(user['home_shop_id']) if user['home_shop_id'] in shop_ids else 0
            st.selectbox("勤務店舗", options=shop_ids, format_func=lambda x: f"{x}: {shop_options[x]}", index=def_idx)
            st.number_input("本日の給与", min_value=0, step=1000)
            st.date_input("稼働日")
            st.text_area("備考")
            st.form_submit_button("報告を保存")

        st.divider()
        st.subheader("直近の履歴")
        # 履歴をシンプルな表で表示
        history = conn.table("daily_earnings").select("date, amount").eq("cast_id", user['login_id']).order("date", desc=True).limit(5).execute()
        if history.data:
            st.dataframe(history.data, use_container_width=True)

    # --- B. シフト確認タブ ---
    with tab_shift:
        st.subheader("確定シフト")
        # リスト形式のカレンダー：スマホで最も見やすい形式
        shifts = conn.table("shifts").select("*, shop_master(shop_name)")\
            .eq("cast_id", user['login_id'])\
            .gte("date", datetime.date.today().isoformat())\
            .order("date").execute()
        
        if shifts.data:
            for s in shifts.data:
                # 1つ1つの予定を独立したブロックで表示
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    c1.write(s['date'])
                    c2.write(f"**{s['shop_master']['shop_name']}**")
        else:
            st.info("確定したシフトはありません")

    # --- C. シフト申請タブ ---
    with tab_req:
        st.subheader("シフト申請")
        with st.form("req_form", clear_on_submit=True):
            st.date_input("出勤希望日")
            st.selectbox("希望店舗", options=shop_ids, format_func=lambda x: f"{x}: {shop_options[x]}", key="req_shop")
            st.text_area("メッセージ")
            st.form_submit_button("申請を送信")
