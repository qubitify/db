import streamlit as st
import json
import os
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide", page_title="가이드 뷰어")

# --- 사이드바 네비게이션 숨기기 ---
hide_pages_nav_css = """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
"""
st.markdown(hide_pages_nav_css, unsafe_allow_html=True)

# --- 상수 정의 ---
GUIDE_DIR = "guide"
GUIDE_FILE_PATH = os.path.join(GUIDE_DIR, "guide.json")
ATTACHMENT_DIR = os.path.join(GUIDE_DIR, "attachments")
os.makedirs(ATTACHMENT_DIR, exist_ok=True)


# --- 상태 관리 초기화 ---
if 'editing_guide_id' not in st.session_state:
    st.session_state.editing_guide_id = None
if 'adding_new_guide' not in st.session_state:
    st.session_state.adding_new_guide = False

# --- 헬퍼 함수 ---
def get_all_guides():
    """guide.json 파일에서 모든 가이드 목록을 불러옵니다."""
    if not os.path.exists(GUIDE_FILE_PATH):
        return []
    with open(GUIDE_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            guides = json.load(f)
            if isinstance(guides, list):
                return sorted(guides, key=lambda x: x.get('created_at', ''), reverse=True)
            return []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

def save_all_guides(guides):
    """모든 가이드 목록을 guide.json 파일에 저장합니다."""
    with open(GUIDE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(guides, f, ensure_ascii=False, indent=2)

# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

# --- 타이틀 및 홈 버튼 ---
title_col, button_col = st.columns([0.8, 0.2])
with title_col:
    st.title("📚 가이드 목록")
with button_col:
    st.write("") # 버튼 위치 조정을 위한 공백
    st.page_link("app.py", label="🏠 상담 시스템으로 돌아가기", use_container_width=True)

st.divider()

# --- [핵심 수정] 새 가이드 추가 버튼 ---
if st.button("지식베이스에 추가하기", use_container_width=True):
    st.session_state.adding_new_guide = True
    st.session_state.editing_guide_id = None # 다른 수정창 닫기
    st.rerun()

# --- [핵심 수정] 새 가이드 추가 폼 ---
if st.session_state.adding_new_guide:
    st.subheader("✍️ 새 가이드 직접 추가")
    with st.form(key="new_guide_form"):
        new_prompt = st.text_input("질문 (Prompt)")
        new_response = st.text_area("답변 (Response)", height=150)
        cause_options = ["단순 문의", "기능 사용법 문의", "오류/버그 리포트", "계정/인증 문제", "정책/규정 문의", "개선 제안", "기타"]
        new_cause = st.selectbox("원인/분석", options=cause_options)
        new_uploaded_file = st.file_uploader("참고 파일 첨부")
        
        form_cols = st.columns(2)
        if form_cols[0].form_submit_button("💾 새 가이드 저장", use_container_width=True, type="primary"):
            if new_prompt and new_response:
                all_guides = get_all_guides()
                file_path = None
                if new_uploaded_file is not None:
                    file_path = os.path.join(ATTACHMENT_DIR, new_uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(new_uploaded_file.getbuffer())

                new_guide_content = {
                    "prompt": new_prompt, "response": new_response, "cause": new_cause,
                    "attachment_path": file_path, "counselor_name": "수동 추가",
                    "created_at": datetime.now().isoformat(), "original_source": "수동 입력"
                }
                all_guides.insert(0, new_guide_content) # 최신순이므로 맨 앞에 추가
                save_all_guides(all_guides)
                st.session_state.adding_new_guide = False
                st.success("새 가이드가 성공적으로 추가되었습니다.")
                st.rerun()
            else:
                st.warning("질문과 답변은 필수 입력 항목입니다.")

        if form_cols[1].form_submit_button("❌ 취소", use_container_width=True):
            st.session_state.adding_new_guide = False
            st.rerun()
    st.divider()


all_guides = get_all_guides()

if not all_guides and not st.session_state.adding_new_guide:
    st.info("아직 생성된 가이드가 없습니다. 상담 시스템에서 가이드를 추가하거나, 위 버튼을 눌러 직접 추가해주세요.")
    st.stop()

# 검색 기능 및 목록 표시
if not st.session_state.adding_new_guide: # 새 가이드 추가 중에는 목록 숨기기
    search_term = st.text_input("가이드 검색", placeholder="질문, 답변, 원인 내용으로 검색...")

    for index, guide_data in enumerate(all_guides):
        prompt = guide_data.get("prompt", "")
        response = guide_data.get("response", "")
        cause = guide_data.get("cause", "")
        
        search_content = f"{prompt} {response} {cause}".lower()
        if search_term.lower() not in search_content:
            continue
        
        # --- 수정 모드 ---
        if st.session_state.editing_guide_id == guide_data.get('created_at'):
            st.subheader(f"✍️ 가이드 수정: {prompt[:30]}...")
            with st.container(border=True):
                st.markdown("**원본 내용**")
                st.text_input("원본 질문", value=prompt, disabled=True)
                st.text_area("원본 답변", value=response, disabled=True, height=150)
                st.caption(f"원본 출처: {guide_data.get('original_source', '정보 없음')}")
            st.divider()

            with st.form(key=f"edit_form_{guide_data.get('created_at')}"):
                edited_response = st.text_area("답변 수정", value=response, height=200)
                
                cause_options = ["단순 문의", "기능 사용법 문의", "오류/버그 리포트", "계정/인증 문제", "정책/규정 문의", "개선 제안", "기타"]
                try:
                    current_cause_index = cause_options.index(cause) if cause in cause_options else cause_options.index("기타")
                except ValueError:
                    current_cause_index = 0
                edited_cause = st.selectbox("원인/분석 수정", options=cause_options, index=current_cause_index)
                
                st.subheader("첨부 파일")
                current_attachment = guide_data.get("attachment_path")
                if current_attachment and os.path.exists(current_attachment):
                    st.caption(f"현재 파일: {os.path.basename(current_attachment)}")
                else:
                    st.caption("현재 첨부된 파일 없음")
                
                edited_uploaded_file = st.file_uploader("새 파일 첨부 (기존 파일 대체)", key=f"uploader_{guide_data.get('created_at')}")
                st.divider()

                form_cols = st.columns(2)
                if form_cols[0].form_submit_button("💾 변경사항 저장", use_container_width=True, type="primary"):
                    all_guides[index]['response'] = edited_response
                    all_guides[index]['cause'] = edited_cause
                    if edited_uploaded_file:
                        file_path = os.path.join(ATTACHMENT_DIR, edited_uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(edited_uploaded_file.getbuffer())
                        all_guides[index]['attachment_path'] = file_path
                    
                    save_all_guides(all_guides)
                    st.session_state.editing_guide_id = None
                    st.success("가이드가 성공적으로 수정되었습니다.")
                    st.rerun()

                if form_cols[1].form_submit_button("❌ 취소", use_container_width=True):
                    st.session_state.editing_guide_id = None
                    st.rerun()
            st.divider()

        # --- 일반 보기 모드 ---
        else:
            with st.expander(f"**Q. {prompt}**"):
                st.markdown(f"#### A. 답변")
                st.info(response)
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1: st.markdown(f"**원인/분석**"); st.write(cause)
                with col2: st.markdown(f"**담당자**"); st.write(guide_data.get("counselor_name", "미지정"))
                with col3:
                    st.markdown(f"**생성일**")
                    created_at_str = guide_data.get("created_at")
                    if created_at_str: st.write(datetime.fromisoformat(created_at_str).strftime("%Y-%m-%d %H:%M"))
                    else: st.write("날짜 정보 없음")

                attachment_path = guide_data.get("attachment_path")
                if attachment_path and os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as file:
                        st.download_button(label=f"📁 파일 다운로드 ({os.path.basename(attachment_path)})", data=file, file_name=os.path.basename(attachment_path), use_container_width=True)
                
                st.markdown("---")
                btn_cols = st.columns([0.1, 0.1, 0.8])
                if btn_cols[0].button("✏️ 수정", key=f"edit_{guide_data.get('created_at')}"):
                    st.session_state.editing_guide_id = guide_data.get('created_at')
                    st.session_state.adding_new_guide = False # 새 가이드 추가 모드 끄기
                    st.rerun()

                if btn_cols[1].button("🗑️ 삭제", key=f"delete_{guide_data.get('created_at')}"):
                    guides_to_keep = [g for g in all_guides if g.get('created_at') != guide_data.get('created_at')]
                    save_all_guides(guides_to_keep)
                    st.success("가이드가 삭제되었습니다.")
                    st.rerun()
