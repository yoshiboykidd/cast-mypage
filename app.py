import streamlit as st
from st_supabase_connection import SupabaseConnection

# 【重要】掟：何よりも先にこれを書く
st.set_page_config(
    page_title="かりんとグループ | キャストポータル",
    page_icon="💖",
    layout="centered"
)

# --- 🔐 ログイン機能の定義 ---
def check_password():
    """パスワードが正しいかチェックする関数"""
    def password_entered():
        # Streamlit CloudのSecretsに設定したパスワードと比較
        if st.session_state["password"] == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セッションから一時パスワードを消去
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # まだパスワードを入力していない状態
        st.title("🔐 関係者専用ページ")
        st.text_input(
            "パスワードを入力してください", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # パスワードが間違っていた状態
        st.title("🔐 関係者専用ページ")
        st.text_input(
            "パスワードを入力してください", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 パスワードが違います")
        return False
    else:
        # パスワードが合っている状態
        return True

# --- メインロジック ---
if check_password():
    # ログイン成功後、ここから下のコードが実行されます
    
    # Supabase接続
    conn = st.connection("supabase", type=SupabaseConnection)

    # 画面表示
    st.title("💖 キャスト実績入力")
    
    # サイドバー（ログイン中の名前など）
    st.sidebar.title("👤 キャスト認証")
    cast_name = st.sidebar.text_input("名前またはIDを入力", value="TEST_001")
    
    st.write(f"お疲れ様です、**{cast_name}** さん！今日の頑張りを記録しましょう✨")

    # 入力フォーム
    with st.form("earnings_form", clear_on_submit=True):
        st.subheader("💰 本日の実績")
        work_date = st.date_input("稼働日")
        amount = st.number_input("本日の給与 (円)", min_value=0, step=1000)
        memo = st.text_area("内容メモ")
        submit_button = st.form_submit_button("この内容で保存する ✨")

    if submit_button:
        try:
            insert_data = {
                "cast_id": cast_name,
                "date": work_date.isoformat(),
                "amount": amount,
                "memo": memo
            }
            conn.table("daily_earnings").insert(insert_data).execute()
            st.success(f"保存しました！今日もお疲れ様でした 🌈")
            st.balloons()
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

    st.divider()

    # 履歴表示
    st.subheader("📅 最近の入力履歴")
    try:
        history = conn.table("daily_earnings").select("*").eq("cast_id", cast_name).order("date", desc=True).limit(5).execute()
        if history.data:
            for item in history.data:
                st.write(f"📅 {item['date']} | **¥{item['amount']:,}** | {item['memo'] or ''}")
    except:
        st.write("履歴が読み込めませんでした。")
