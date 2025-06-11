import streamlit as st
from datetime import datetime
import json
import os
import base64 # [추가] 이미지 인코딩을 위해 임포트

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="Q&A 기반 가이드 생성 시스템")

# --- 파일 로드/저장 함수 ---
def load_chat_history(filename="history.json"):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

# --- 상태 관리 (Session State) 초기화 ---
if 'messages' not in st.session_state:
    st.session_state.messages = load_chat_history()
if 'qa_to_edit' not in st.session_state:
    st.session_state.qa_to_edit = None

# --- 챗봇 응답 생성 함수 (예시) ---
def get_chatbot_response(question):
    response_text = f"'{question}'에 대한 답변입니다. 이 답변은 예시로 생성되었습니다."
    source_url = "https://docs.streamlit.io"
    return response_text, source_url

# --------------------------------------------------------------------------
# UI 렌더링 함수 분리 (코드 재사용 및 가독성 향상)
# --------------------------------------------------------------------------

def render_chatbot_panel(container):
    """챗봇 UI를 그리는 함수. container는 st 또는 col1이 될 수 있음."""
    container.header("💬 챗봇")

    chat_container = container.container(height=500)
    for message in st.session_state.messages:
        with chat_container.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                st.info(f"출처: [{message['source']}]({message['source']})")
                if st.button("➕ 새로운 가이드로 저장", key=f"save_{message['timestamp']}_{container.__class__}"):
                    st.session_state.qa_to_edit = {
                        "prompt": message["prompt"],
                        "response": message["content"],
                        "source": message["source"]
                    }
                    st.rerun()

    with container.form(key=f"chat_form_{container.__class__}", clear_on_submit=True):
        form_cols = st.columns([5, 1])
        with form_cols[0]:
            prompt = st.text_input(
                "질문을 입력하세요...", 
                placeholder="여기에 메시지를 입력하고 '전송'을 누르세요.", 
                label_visibility="collapsed"
            )
        with form_cols[1]:
            submitted = st.form_submit_button("전송", use_container_width=True)

    if submitted and prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        response, source = get_chatbot_response(prompt)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "prompt": prompt,
            "source": source,
            "timestamp": timestamp
        })
        st.rerun()

def render_editor_panel(container):
    """오른쪽 편집 패널 UI를 그리는 함수."""
    with container:
        header_col, close_col = st.columns([0.9, 0.1], vertical_alignment="center")
        with header_col:
            st.header("✍️ 새로운 가이드 생성 및 저장")
        with close_col:
            if st.button("닫기", key="close_edit_panel", help="편집 패널 닫기"):
                st.session_state.qa_to_edit = None
                st.rerun()

        data = st.session_state.qa_to_edit
        st.subheader("1. 원본 Q&A 확인 및 수정")
        st.info(f"**원본 출처:** {data['source']}")

        edited_prompt = st.text_area("프롬프트 (질문)", value=data['prompt'], height=100, key="edited_prompt")
        edited_response = st.text_area("응답 (답변)", value=data['response'], height=200, key="edited_response")

        st.divider()
        st.subheader("2. 수정 사항 및 추가 정보 입력")
        reason_for_edit = st.text_input("수정 이유", placeholder="예: 답변이 너무 길어서 요약함", key="reason_for_edit")
        new_response = st.text_area("새로운 응답 (선택 사항)", placeholder="수정된 응답과 다른, 더 나은 답변이 있다면 입력하세요.", key="new_response")
        uploaded_image = st.file_uploader("이미지 추가 (선택 사항)", type=['png', 'jpg', 'jpeg'], key="uploaded_image")

        # [수정] "가이드에 저장" 버튼 클릭 시 JSON 저장 로직 추가
        if st.button("💾 가이드에 저장", type="primary"):
            
            # 1. 이미지 파일을 Base64 문자열로 인코딩
            image_b64_string = None
            if uploaded_image is not None:
                image_bytes = uploaded_image.getvalue()
                image_b64_string = base64.b64encode(image_bytes).decode('utf-8')

            # 2. 저장할 데이터를 딕셔너리로 정리
            guide_record = {
                "original_prompt": data['prompt'], "original_response": data['response'], "source": data['source'],
                "edited_prompt": edited_prompt, "edited_response": edited_response, "edit_reason": reason_for_edit,
                "new_alternative_response": new_response,
                "image_data_b64": image_b64_string, # Base64로 인코딩된 이미지 데이터 저장
                "save_timestamp": datetime.now().isoformat()
            }

            # 3. 기존 guide.json 파일을 읽고, 새 데이터를 추가한 후, 다시 저장
            guides = []
            if os.path.exists("guide.json"):
                with open("guide.json", 'r', encoding='utf-8') as f:
                    try:
                        guides = json.load(f)
                    except json.JSONDecodeError: # 파일이 비어있는 경우
                        guides = []
            
            guides.append(guide_record)

            with open("guide.json", 'w', encoding='utf-8') as f:
                json.dump(guides, f, ensure_ascii=False, indent=2)

            # 4. 완료 피드백
            st.success("가이드가 guide.json 파일에 성공적으로 저장되었습니다!")
            st.session_state.qa_to_edit = None
            st.balloons()
            st.rerun()

# --------------------------------------------------------------------------
# 메인 UI 레이아웃 설정
# --------------------------------------------------------------------------
title_col, nav_col = st.columns([0.8, 0.2], vertical_alignment="center")

with title_col:
    st.title("🤖 챗봇 Q&A 기반 가이드 생성 시스템")
    st.write("챗봇과 대화하고 유의미한 응답을 '새로운 가이드로 저장'하여 오른쪽 패널에서 편집 및 저장할 수 있습니다.")

with nav_col:
    if st.button("📚 가이드 페이지로 이동", use_container_width=True):
        st.switch_page("pages/guide.py")

st.divider()

if st.session_state.qa_to_edit is None:
    render_chatbot_panel(st)
else:
    col1, col2 = st.columns([1, 1])
    render_chatbot_panel(col1)
    render_editor_panel(col2)