# Streamlit & Nginx 도커 컨테이너 배포 가이드 (Docker Compose 사용)

이 가이드는 Nginx와 Streamlit 앱을 각각 독립된 도커 컨테이너로 실행하고, **Docker Compose**를 사용하여 이들을 함께 오케스트레이션(orchestration)하는 방법을 설명합니다. 이 방식은 각 서비스의 독립성을 높이고, 배포 및 관리를 자동화하며, 확장성을 확보하는 데 매우 유리합니다.

### 배포 원리 (Docker Compose)

Nginx와 Streamlit을 별도의 컨테이너로 실행하고, Docker가 제공하는 내부 네트워크를 통해 둘을 연결합니다.

1.  **사용자**는 웹 브라우저를 통해 서버의 80번 포트로 접속합니다.
2.  **Nginx 컨테이너**가 80번 포트에서 요청을 받습니다.
3.  **Docker 내부 네트워크**를 통해 Nginx 컨테이너는 **Streamlit 컨테이너**의 8501번 포트로 요청을 전달합니다. (이때 서비스 이름으로 컨테이너를 찾습니다.)
4.  **Streamlit 컨테이너**는 요청을 처리하여 응답을 Nginx 컨테이너로 보내고, Nginx는 최종 응답을 사용자에게 전달합니다.
5.  **Docker 볼륨(Volume)** 을 사용하여 컨테이너가 삭제되거나 재시작되어도 `history`와 `guide` 데이터가 서버(호스트)에 영구적으로 보존되도록 합니다.

---

### 1. 사전 준비물

1.  **리눅스 서버**: Docker와 Docker Compose가 설치된 리눅스 서버.
    * [Docker 공식 문서](https://docs.docker.com/engine/install/ubuntu/)를 참고하여 Docker를 설치하세요.
    * [Docker Compose 공식 문서](https://docs.docker.com/compose/install/)를 참고하여 Docker Compose를 설치하세요.
2.  **프로젝트 코드**: 배포할 `app.py`, `pages/`, `requirements.txt` 파일들.

---

### 2. 배포 절차

#### 1단계: 프로젝트 폴더 구조화

서버에 아래와 같은 구조로 폴더와 파일을 구성합니다. 이것이 배포의 최종적인 모습입니다.

```
my-dockerized-app/
├── app/
│   ├── app.py
│   ├── requirements.txt
│   ├── pages/
│   │   └── guide.py
│   ├── history/       # (데이터 저장을 위한 빈 폴더)
│   └── guide/         # (데이터 저장을 위한 빈 폴더)
│       └── attachments/
│
├── nginx/
│   └── nginx.conf     # (Nginx 설정 파일)
│
└── docker-compose.yml # (Docker Compose 설정 파일)
```

1.  `my-dockerized-app` 이라는 메인 폴더를 만듭니다.
2.  그 안에 `app` 폴더와 `nginx` 폴더를 만듭니다.
3.  `app` 폴더 안에는 Streamlit 관련 파일(`app.py`, `pages/`, `requirements.txt`)과 데이터 저장을 위한 빈 폴더(`history`, `guide`)를 위치시킵니다.
4.  `nginx` 폴더 안에는 아래에서 작성할 `nginx.conf` 파일을 위치시킵니다.
5.  최상위 폴더(`my-dockerized-app`)에는 아래에서 작성할 `docker-compose.yml` 파일을 위치시킵니다.

#### 2단계: Nginx 설정 파일 작성

`nginx/nginx.conf` 파일을 생성하고 아래 내용을 입력합니다.
* **중요**: `proxy_pass` 부분에 컨테이너의 IP 주소 대신 **서비스 이름**(`http://streamlit-app:8501`)을 사용합니다. Docker Compose가 이 이름을 올바른 컨테이너 IP로 자동 변환해 줍니다.

**`nginx/nginx.conf` 파일 내용:**

```nginx
server {
    listen 80;
    server_name your_domain.com; # 여기에 도메인 또는 IP 주소 입력

    location / {
        proxy_pass http://streamlit-app:8501; # docker-compose.yml에 정의된 서비스 이름
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3단계: Docker Compose 파일 작성

프로젝트의 최상위 경로에 `docker-compose.yml` 파일을 생성하고 아래 내용을 입력합니다. 이 파일이 두 컨테이너를 정의하고 연결하는 핵심 역할을 합니다.

**`docker-compose.yml` 파일 내용:**

```yaml
version: '3.8'

services:
  # Streamlit 앱 서비스 정의
  streamlit-app:
    # Docker 이미지를 직접 빌드합니다.
    build:
      context: ./app  # 'app' 폴더를 빌드 컨텍스트로 사용
      dockerfile: Dockerfile
    # 컨테이너 이름을 지정합니다.
    container_name: streamlit_service
    # 데이터 영속성을 위해 호스트와 컨테이너의 폴더를 연결합니다. (볼륨 매핑)
    volumes:
      - ./app/history:/app/history
      - ./app/guide:/app/guide
    # 내부 네트워크에서만 8501 포트를 노출합니다.
    expose:
      - "8501"

  # Nginx 서비스 정의
  nginx:
    # Docker 이미지를 직접 빌드합니다.
    build:
      context: ./nginx # 'nginx' 폴더를 빌드 컨텍스트로 사용
      dockerfile: Dockerfile
    container_name: nginx_service
    # 호스트의 80번 포트와 컨테이너의 80번 포트를 연결합니다.
    ports:
      - "80:80"
    # streamlit-app 서비스가 먼저 시작된 후에 nginx 서비스를 시작합니다.
    depends_on:
      - streamlit-app
```

#### 4단계: 각 서비스의 Dockerfile 생성

이제 `docker-compose.yml`에서 참조하는 각 서비스의 `Dockerfile`을 생성합니다.

**1. Streamlit 앱 Dockerfile (`app/Dockerfile`)**
`app` 폴더 안에 `Dockerfile`을 생성하고 아래 내용을 입력합니다.

```dockerfile
# 베이스 이미지 선택
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 파일을 컨테이너에 복사
COPY requirements.txt ./

# 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 코드를 컨테이너에 복사
COPY . .

# 앱 실행 (8501 포트 노출)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**2. Nginx Dockerfile (`nginx/Dockerfile`)**
`nginx` 폴더 안에 `Dockerfile`을 생성하고 아래 내용을 입력합니다.

```dockerfile
# 베이스 이미지 선택
FROM nginx:latest

# 호스트의 nginx.conf 파일을 컨테이너의 설정 위치로 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

#### 5단계: 애플리케이션 빌드 및 실행

모든 파일 작성이 완료되었으면, `docker-compose.yml` 파일이 있는 최상위 경로에서 아래 명령어를 실행합니다.

```bash
# 컨테이너를 빌드하고 백그라운드에서 실행 (-d: detached mode)
sudo docker-compose up --build -d
```

* `--build`: 이미지가 없을 경우 새로 빌드합니다. 코드가 변경될 때마다 이 옵션을 사용해야 합니다.
* `-d`: 컨테이너를 백그라운드에서 실행합니다.

이제 `http://<your_domain.com>` 또는 `http://<서버_IP_주소>` 로 접속하면 Nginx를 통해 Streamlit 앱이 정상적으로 표시됩니다.

---

### 관리 명령어

* **로그 확인**: `sudo docker-compose logs -f`
* **서비스 중지 및 컨테이너 삭제**: `sudo docker-compose down`
* **서비스 재시작**: `sudo docker-compose restart`
* **코드 수정 후 재배포**: `sudo docker-compose up --build -d`

이 방법을 사용하면 **Docker 볼륨 매핑**을 통해 데이터가 호스트 서버의 `app/history` 및 `app/guide` 폴더에 직접 저장되므로, 컨테이너를 재시작하거나 삭제해도 데이터가 안전하게 보존됩니다.
