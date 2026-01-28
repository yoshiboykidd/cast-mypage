import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="かりんとポータル", page_icon="💖", layout="centered")

# --- 2. データベース接続 ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. 管理用：データ同期関数（枠組みのみ） ---
def sync_all_data():
    return 0, 0 # UI確認用のため処理はスキップ

# --- 4. 🔐 ログイン認証（UI確認用：常にTrueにするか、既存ロジックを維持） ---
def check_password():
    # テストをスムーズにするため、一度ログインしたらセッションを維持
    if "password_correct" not in st.session_state:
        st.title("🔐 ログイン")
        st.caption("テスト用：ID/PWは何でもログイン可能です（UI確認用）")
        st.text_input("ログインID", key="login_id")
        st.text_input("パスワード", type="password", key="password_input")
        if st.button("ログイン"):
            st.session_state["password_correct"] = True
            # ダミーのユーザー情報
            st.session_state["user_info"] = {
                "display_name": "テスト キャスト",
                "home_shop_id": "001",
                "login_id": "00100001"
            }
            st.rerun()
        return False
    return True

# --- 5. サイドバー ---
with st.sidebar:
    st.header("メニュー")
    with st.expander("⚙️ 管理設定"):
        st.text_input("Admin Key", type="password")
        st.button("全データを同期 🔄")
        st.button("HPからシフト取得 🌐")
    
    if st.session_state.get("password_correct"):
        st.divider()
        st.write(f"USER: {st.session_state['user_info']['display_name']}")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()

# --- 6. メインコンテンツ ---
if check_password():
    user = st.session_state["user_info"]
    
    # 店舗マスターのダミー（DBがない場合用）
    shop_options = {"001": "池袋西口店", "002": "赤坂店", "003": "五反田店"}
    shop_ids = list(shop_options.keys())

    # スマホで見やすい3タブ構造
    tab_earn, tab_shift, tab_req = st.tabs(["実績報告", "シフト確認", "シフト申請"])

    # --- タブA: 実績報告 ---
    with tab_earn:
        st.subheader("📝 本日の実績報告")
        with st.form("earn_form"):
            st.selectbox("勤務店舗", options=shop_ids, format_func=lambda x: f"{x}: {shop_options[x]}")
            st.number_input("本日の給与 (円)", min_value=0, step=1000, value=15000)
            st.date_input("稼働日", value=datetime.date.today())
            st.text_area("メモ (任意)")
            st.form_submit_button("報告を保存する ✨")

        st.divider()
        st.subheader("📊 直近の履歴")
        # 履歴の見た目確認用サンプル
        sample_history = [
            {"date": "2026-01-27", "amount": 18000, "shop": "池袋西口店"},
            {"date": "2026-01-26", "amount": 12000, "shop": "赤坂店"},
        ]
        st.table(sample_history)

    # --- タブB: シフト確認（ダミーデータ表示） ---
    with tab_shift:
        st.subheader("📅 確定シフト")
        st.caption("※以下は表示イメージです（実際のデータではありません）")
        
        # スマホで最も見やすい「カード型リスト」のフレームワーク
        dummy_shifts = [
            {"date": "2026-01-28", "shop": "池袋西口店", "time": "19:00 - LAST", "status": "確定"},
            {"date": "2026-01-29", "shop": "赤坂店", "time": "20:00 - 05:00", "status": "確定"},
            {"date": "2026-01-31", "shop": "五反田店", "time": "18:00 - LAST", "status": "確認中"},
        ]

        for s in dummy_shifts:
            # 枠（Container）を使って1日分をひとまとめにする
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                
                # 左側：日付を強調
                d = datetime.datetime.strptime(s['date'], "%Y-%m-%d")
                col1.markdown(f"### {d.day}")
                col1.caption(f"{d.month}月")
                
                # 右側：詳細情報
                col2.markdown(f"**🏢 {s['shop']}**")
                col2.write(f"⏰ {s['time']}")
                
                # ステータスによって色を変えるなどの視認性向上
                if s['status'] == "確定":
                    col2.success(s['status'])
                else:
                    col2.warning(s['status'])

    # --- タブC: シフト申請 ---
    with tab_req:
        st.subheader("📝 シフト希望の提出")
        with st.form("req_form"):
            st.date_input("出勤希望日")
            st.selectbox("希望店舗", options=shop_ids, format_func=lambda x: f"{x}: {shop_options[x]}")
            st.multiselect("希望時間", ["18:00〜", "19:00〜", "20:00〜", "LASTまで", "終電まで"])
            st.text_area("備考・メッセージ")
            st.form_submit_button("申請を送信 📤")
