FROM python:3.9-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 파일 복사 및 설치 (코드 복사 전에 실행하여 Docker 캐시 활용)
# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install streamlit pandas scikit-learn matplotlib seaborn
# 4. 프로젝트 파일 전체를 작업 디렉토리로 복사
COPY . .

# 5. Streamlit이 사용할 포트 노출
EXPOSE 8501
