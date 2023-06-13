from dotenv import load_dotenv
from firestore_utils import load_conversation_by_id, clear_user_history
from google_utils import sign_out_google, decode_token_from_params
import streamlit as st
from render_auth import render_auth
from render_body import render_body
from render_my_conversations import render_my_conversations
from utils import get_key_from_params, get_cid_from_session

load_dotenv()

DEFAULT_MODEL = "gpt-3.5-turbo"


def load_and_store_conversation(st, cid: str):
    conversation = load_conversation_by_id(cid).to_dict()
    if conversation:
        st.session_state["conversation"] = conversation
        st.session_state["model"] = get_model_from_conversation(conversation)


def get_model_from_conversation(conversation: dict) -> str:
    return conversation.get("model_name")


def controller():
    st.session_state["conversation_expanded"] = True

    token_dict = decode_token_from_params(st, "token")
    if token_dict:
        st.session_state["token"] = token_dict

    model_from_param = get_key_from_params(st, "model")
    if model_from_param:
        st.session_state["model"] = model_from_param

    cid = get_cid_from_session(st)
    if cid:
        load_and_store_conversation(st, cid)

    if "model" not in st.session_state:
        st.session_state["model"] = DEFAULT_MODEL
    if "saved_questions" not in st.session_state:
        st.session_state["saved_questions"] = []


def render_sidebar(sidebar):
    # Tính năng mới: lưu và tải câu hỏi
    sidebar.title("Danh sách câu hỏi")
    save_question_checkbox = sidebar.checkbox("Lưu câu hỏi")
    question_input = sidebar.text_input("Nhập câu hỏi:")

    if save_question_checkbox:
        if question_input:
            st.session_state["saved_questions"].append(question_input)
            question_input = ''

    if st.session_state["saved_questions"]:
        sidebar.markdown("### Các câu hỏi đã lưu:")
        for saved_question in st.session_state["saved_questions"]:
            if sidebar.button(saved_question):
                question_input = saved_question

    render_new_chat(sidebar)
    sidebar.divider()
    render_auth(st)
    render_profile(sidebar)
    sidebar.divider()
    render_history_menu(sidebar)


def render_new_chat(sidebar):
    button_models = {"GPT-3.5 Chat": "gpt-3.5-turbo", "GPT-4 Chat": "gpt-4"}
    for button_text, model_type in button_models.items():
        # if model in session_state is the same as the button, prefix button_text with a checked emoji
        if st.session_state.get("model") == model_type:
            button_text = "✓ " + button_text
            button_type = "primary"
        else:
            button_type = "secondary"

        if sidebar.button(
            button_text,
            key=f"button_{model_type}",
            use_container_width=True,
            type=button_type,
        ):
            reinitialize_chat(model_type)


def reinitialize_chat(model: str):
    st.session_state["conversation"] = DEFAULT_CONVERSATION
    st.session_state["model"] = model
    st.session_state["cid"] = None
    st.experimental_rerun()


def render_history_menu(sidebar):
    sidebar.write("## Chat History")
    sidebar.markdown(
        """
        <style>
            a.link-row:hover div, a.selected div {
                background-color: #666;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    render_my_conversations(st, sidebar)


def render_profile(sidebar):
    authentication_status = st.session_state.get(
        "authentication_status", "Not Authenticated"
    )
    if authentication_status == "Authenticated":
        user_info = st.session_state.get("user_info")
        if not user_info:
            return

        status = f"Signed in as {user_info.get('email')}"
        login_container = sidebar.empty()
        with login_container.expander(status):
            st.image(user_info.get("picture"), width=50)
            sign_out = st.button("Sign out", key="button_sign_out", type="secondary")

            placeholder = st.empty()
            with placeholder:
                clear_history = st.button(
                    "Clear History", key="button_clear_history", type="secondary"
                )

            if clear_history:
                clear_user_history(user_info["id"])
                placeholder.info("Chat history cleared", icon="✅")
                st.snow()
            st.write(
                "While it's useful to resume past conversations, sometimes you may want to clear your chat history."
            )

        if sign_out:
            sign_out_google(st, login_container)
            st.experimental_set_query_params()
            del st.session_state["token"]
            del st.session_state["user_info"]
            st.session_state["authentication_status"] = "Not Authenticated"


def render_sidebar(sidebar):
    render_new_chat(sidebar)
    sidebar.divider()
    render_auth(st)
    render_profile(sidebar)
    sidebar.divider()
    render_history_menu(sidebar)


def main():
    st.set_page_config(
        page_title="PushGPT Chat", page_icon=":robot_face:", layout="wide"
    )
    controller()
    render_sidebar(st.sidebar)
    render_body(st)


if __name__ == "__main__":
    main()

    with st.expander("Debug"):
        col1, col2 = st.columns(2)
        col1.write("Session State (w/o conversation, user_info))")
        # exclude conversation from session_state
        session_state = {
            k: v for k, v in st.session_state.items() if k != "conversation"
        }
        col1.write(session_state)
        col2.write("Conversation")
        col2.write(st.session_state.get("conversation"))
