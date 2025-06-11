import streamlit as st
from datetime import datetime
import json
import os
import glob
import shutil

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="상담 관리 시스템")

# --- 사이드바 네비게이션 숨기기 ---
hide_pages_nav_css = """
    <style> [data-testid="stSidebarNav"] {display: none;} </style>
"""
st.markdown(hide_pages_nav_css, unsafe_allow_html=True)


# --- 상수 정의 ---
HISTORY_DIR = "history"
GUIDE_DIR = "guide"
ATTACHMENT_DIR = os.path.join(GUIDE_DIR, "attachments")
GUIDE_FILE_PATH = os.path.join(GUIDE_DIR, "guide.json") # [핵심 수정] 단일 가이드 파일 경로

os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(GUIDE_DIR, exist_ok=True)
os.makedirs(ATTACHMENT_DIR, exist_ok=True)

# --- 헬퍼 함수: 파일 처리 (History) ---
def get_history_files():
    # [핵심 수정] 최신순으로 정렬하기 위해 reverse=True 추가
    return sorted(glob.glob(os.path.join(HISTORY_DIR, "history*.json")), reverse=True)

def load_data(filepath):
    """범용 JSON 로더"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return None
    return None

def save_history_data(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_new_history(counselor_name="담당자 미지정"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filepath = os.path.join(HISTORY_DIR, f"history{timestamp}.json")
    new_data = {
        "title": f"새 상담 ({timestamp})", "summary": "이곳에 상담 요약을 작성하세요.",
        "counselor_name": counselor_name, "start_time": datetime.now().isoformat(),
        "end_time": None, "messages": []
    }
    save_history_data(new_filepath, new_data)
    return new_filepath

# --- 헬퍼 함수: 단일 파일에 가이드 저장 ---
def save_new_guide(guide_data):
    """새로운 가이드 데이터를 단일 guide.json 파일에 추가합니다."""
    guides = load_data(GUIDE_FILE_PATH)
    if guides is None or not isinstance(guides, list):
        guides = [] # 파일이 없거나 내용이 잘못된 경우 새로 시작

    guides.append(guide_data) # 새 가이드를 리스트에 추가

    with open(GUIDE_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(guides, f, ensure_ascii=False, indent=2)

# --- 상태 관리 ---
if 'current_history_file' not in st.session_state:
    history_files = get_history_files()
    st.session_state.current_history_file = history_files[0] if history_files else None

if 'current_counselor' not in st.session_state:
    st.session_state.current_counselor = "담당자A"

if 'editing_guide' not in st.session_state:
    st.session_state.editing_guide = False
if 'guide_editor_data' not in st.session_state:
    st.session_state.guide_editor_data = None

# --------------------------------------------------------------------------
# 사이드바
# --------------------------------------------------------------------------
st.sidebar.title("🗂️ 상담 목록")
st.sidebar.text_input(
    "현재 상담원 이름", key="current_counselor",
    help="새로운 상담/가이드를 저장할 때 이 이름으로 담당자가 설정됩니다."
)
if st.sidebar.button("➕ 새 상담 시작하기", use_container_width=True):
    new_file = create_new_history(counselor_name=st.session_state.current_counselor)
    st.session_state.current_history_file = new_file
    st.session_state.editing_guide = False
    st.rerun()

st.sidebar.divider()
nav_container = st.sidebar.container(height=350)
history_files = get_history_files()
for history_file in history_files:
    data = load_data(history_file)
    if data:
        title = data.get('title', os.path.basename(history_file))
        counselor = data.get('counselor_name', '미지정')
        button_label = f"{title} (담당: {counselor})"
        is_current = (history_file == st.session_state.current_history_file)
        if nav_container.button(button_label, use_container_width=True, disabled=is_current):
            st.session_state.current_history_file = history_file
            st.session_state.editing_guide = False
            st.rerun()

# 사이드바에 선택된 상담의 제목 수정 기능 추가
if st.session_state.current_history_file:
    st.sidebar.divider()
    st.sidebar.header("✍️ 상담 제목 수정")
    
    current_data_for_edit = load_data(st.session_state.current_history_file)
    if current_data_for_edit:
        with st.sidebar.form(key="title_edit_form"):
            new_title = st.text_input(
                "수정할 제목", 
                value=current_data_for_edit.get('title', ''), 
                label_visibility="collapsed"
            )
            if st.form_submit_button("💾 제목 저장", use_container_width=True):
                current_data_for_edit['title'] = new_title
                save_history_data(st.session_state.current_history_file, current_data_for_edit)
                st.rerun()

# --- 챗봇 UI 함수 ---
def display_chat_interface(chat_data):
    counselor_name = chat_data.get('counselor_name', '미지정')
    st.header(f"💬 챗봇 대화 (담당: {counselor_name})")
    
    chat_container = st.container(height=600)
    messages = chat_data.get('messages', [])
    for i, message in enumerate(messages):
        with chat_container.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("source"):
                st.caption(f"출처: {message['source']}")
            
            if message["role"] == "assistant" and i > 0:
                prompt_message = messages[i-1]
                if prompt_message["role"] == "user":
                    if st.button(f"가이드에 추가", key=f"guide_btn_{i}"):
                        st.session_state.editing_guide = True
                        st.session_state.guide_editor_data = {
                            "prompt": prompt_message["content"],
                            "response": message["content"],
                            "source": message.get("source", "출처 없음")
                        }
                        st.rerun()

    with st.form(key="chat_form", clear_on_submit=True):
        prompt = st.text_input("질문", placeholder="메시지를 입력하세요...", label_visibility="collapsed")
        submitted = st.form_submit_button("전송", use_container_width=True)

    if submitted and prompt:
        def get_chatbot_response(question):
            return f"'{question}'에 대한 답변입니다. 이 답변은 예시입니다.", "https://docs.streamlit.io"
        chat_data['messages'].append({"role": "user", "content": prompt})
        response, source = get_chatbot_response(prompt)
        chat_data['messages'].append({
            "role": "assistant", "content": response, "source": source,
            "timestamp": datetime.now().isoformat()
        })
        save_history_data(st.session_state.current_history_file, chat_data)
        st.rerun()

# --------------------------------------------------------------------------
# 메인 패널 UI
# --------------------------------------------------------------------------
title_col, button_col = st.columns([0.8, 0.2])
with title_col:
    st.title("🤖 상담 시스템")
with button_col:
    st.write("") 
    st.page_link("pages/guide.py", label="📚 가이드로 이동", use_container_width=True)


if not st.session_state.current_history_file:
    st.info("새 상담을 시작하거나 사이드바에서 기존 상담을 선택해주세요.")
    st.stop()

current_data = load_data(st.session_state.current_history_file)
if current_data is None:
    st.error(f"{st.session_state.current_history_file} 파일을 불러오는 데 실패했습니다.")
    st.session_state.current_history_file = None
    st.stop()

if st.session_state.editing_guide:
    main_col, guide_col = st.columns([1, 1])
    with main_col:
        display_chat_interface(current_data)
else:
    display_chat_interface(current_data)

# --- 가이드 편집 패널 ---
if st.session_state.editing_guide and st.session_state.guide_editor_data:
    with guide_col:
        st.header("📝 새 가이드 생성")
        data = st.session_state.guide_editor_data
        
        with st.form(key="guide_editor_form"):
            with st.container(height=600):
                st.subheader("질문 (원본)")
                st.text_area("prompt", value=data["prompt"], disabled=True, height=100)
                st.subheader("답변 (원본)")
                st.text_area("original_response", value=data["response"], disabled=True, height=150)
                st.caption(f"원본 출처: {data.get('source', '정보 없음')}")
                st.divider()
                st.subheader("답변 (가이드용)")
                new_response = st.text_area("response_for_guide", value=data["response"], height=200, help="가이드에 저장될 표준 답변으로 수정하세요.")
                st.subheader("원인/분석")
                cause_options = [
                    "선택하세요", "단순 문의", "기능 사용법 문의", "오류/버그 리포트", 
                    "계정/인증 문제", "정책/규정 문의", "개선 제안", "기타 (직접 입력)"
                ]
                selected_cause = st.selectbox("원인 분류", options=cause_options, label_visibility="collapsed")
                custom_cause = ""
                if selected_cause == "기타 (직접 입력)":
                    custom_cause = st.text_input("기타 원인을 직접 입력하세요:", placeholder="상세 원인 입력...")
                st.subheader("참고 파일")
                uploaded_file = st.file_uploader("가이드에 참고할 파일을 첨부하세요.")

            form_cols = st.columns(2)
            save_guide = form_cols[0].form_submit_button("💾 가이드 저장", use_container_width=True, type="primary")
            cancel_edit = form_cols[1].form_submit_button("❌ 취소", use_container_width=True)

        if save_guide:
            final_cause = selected_cause
            if selected_cause == "기타 (직접 입력)":
                final_cause = custom_cause if custom_cause else "기타 (내용 없음)"
            if final_cause == "선택하세요":
                st.warning("원인/분석 분류를 선택해주세요.")
            else:
                file_path = None
                if uploaded_file is not None:
                    file_path = os.path.join(ATTACHMENT_DIR, uploaded_file.name)
                    with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                
                new_guide_content = {
                    "prompt": data["prompt"], "response": new_response, "cause": final_cause,
                    "attachment_path": file_path, "counselor_name": st.session_state.current_counselor,
                    "created_at": datetime.now().isoformat(), "original_source": data.get('source', '정보 없음')
                }
                save_new_guide(new_guide_content)
                st.success(f"가이드가 성공적으로 저장되었습니다!")
                st.session_state.editing_guide = False
                st.session_state.guide_editor_data = None
                st.rerun()
        if cancel_edit:
            st.session_state.editing_guide = False
            st.session_state.guide_editor_data = None
            st.rerun()
