import streamlit as st
from st_supabase_connection import SupabaseConnection

# --- 🔐 ログイン機能の定義 ---
def check_password():
    """パスワードが正しいかチェックする"""
    def password_entered():
        # Secretsに設定したパスワードと一致するか確認
        if st.session_state["password"] == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セッションからパスワードを削除して安全に
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 初回表示：パスワード入力画面
        st.title("🔐 関係者専用ページ")
        st.text_input(
            "パスワードを入力してください", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # パスワードが間違っている場合
        st.title("🔐 関係者専用ページ")
        st.text_input(
            "パスワードを入力してください", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 パスワードが違います")
        return False
    else:
        # パスワード正解
        return True

# --- メイン処理 ---
if check_password():
    # ここにこれまでの app.py の中身（st.set_page_config以降）をすべて入れます
    st.set_page_config(page_title="かりんとグループ | キャストポータル", page_icon="💖")
    
    # (中略：これまでのコードをここにインデントを下げて配置)
    
    st.success("ログイン成功！")
    # ... 以前のコード ...
