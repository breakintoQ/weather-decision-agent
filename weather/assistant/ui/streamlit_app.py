import json
import uuid
from dataclasses import asdict

import streamlit as st

from assistant.api.app import clear_session_memory, get_session_memory, handle_query


st.set_page_config(page_title="Weather Decision Assistant", page_icon="🌦️", layout="wide")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Weather Decision Assistant")
st.caption("多轮天气决策助手：支持短期记忆、天气、空气质量和生活建议。")

with st.sidebar:
    st.subheader("Session")
    st.text_input("Session ID", value=st.session_state.session_id, key="session_id")
    if st.button("清空当前会话记忆", use_container_width=True):
        clear_session_memory(st.session_state.session_id)
        st.session_state.messages = []
        st.rerun()

    st.subheader("Memory Window")
    st.json(get_session_memory(st.session_state.session_id))

col_chat, col_state = st.columns([1.2, 1.0])

with col_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("例如：北京明天适合骑行吗？")
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        state = handle_query(user_query, session_id=st.session_state.session_id)
        answer_lines = [state.final_answer.summary]
        if state.final_answer.tips:
            answer_lines.append("")
            answer_lines.extend([f"- {tip}" for tip in state.final_answer.tips])
        answer_text = "\n".join(answer_lines)

        st.session_state.messages.append({"role": "assistant", "content": answer_text})
        with st.chat_message("assistant"):
            st.markdown(answer_text)

        st.session_state["latest_state"] = asdict(state)
        st.rerun()

with col_state:
    st.subheader("Latest State")
    latest_state = st.session_state.get("latest_state")
    if latest_state:
        st.code(json.dumps(latest_state, ensure_ascii=False, indent=2), language="json")
    else:
        st.info("发送一条消息后，这里会显示完整状态。")