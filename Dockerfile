# Dockerfile
# ============================================================
# pytest 실행 환경 전용 이미지
#
# 이 Dockerfile 의 목적:
#   테스트를 실행하는 *환경*(Python + 의존성)을 컨테이너화한다.
#   테스트 *대상*(스테이징 서버)은 외부에 별도로 존재하며,
#   이 컨테이너가 외부 서버에 HTTP 요청을 보내는 방식으로 동작한다.
#
#   ⚠️ Docker 는 테스트 실행 환경일 뿐 — 테스트 대상 DB/서버를 Docker 로 띄우는 용도가 아님.
#
# 사용법 (로컬):
#   docker build -t helpychat-api-test .
#   docker run --env-file .env helpychat-api-test
#
# Jenkins 에서는 Jenkinsfile 의 docker.image().inside() 블록으로 실행한다.
# ============================================================

FROM python:3.11-slim

# 작업 디렉터리 설정
WORKDIR /app

# 의존성 먼저 복사 → 소스 변경 시 캐시 재사용
COPY config/requirements.txt ./config/requirements.txt
RUN pip install --no-cache-dir -r config/requirements.txt

# 프로젝트 전체 복사
COPY . .

# 기본 실행 명령: 전체 테스트 실행 (Jenkins 에서 오버라이드 가능)
# -m "not destructive" 를 추가하면 파괴적 테스트 제외
CMD ["pytest", "-v", "--alluredir=allure-results"]
