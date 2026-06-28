# config/settings.py
# ============================================================
# 프로젝트 전체 공통 상수 — URL, 인증 토큰, 타임아웃
#
# [1차 Selenium 대응]
#   config/settings.py 와 1:1 대응.
#   차이점:
#     - Browser/WebDriver 관련 상수(DOWNLOAD_DIR 등) 없음
#     - 대기 시간이 "브라우저 요소 대기"가 아닌 "HTTP 응답 대기" 용도
#     - TEST_USER(id/pw) 대신 API_TOKEN 한 줄로 대체
#       → 로그인 UI 흐름이 없으므로 토큰을 직접 .env 에 저장해서 사용
# ============================================================

import os

from dotenv import load_dotenv  # .env 파일에서 환경변수 로드 (민감 정보 코드 분리)

# load_dotenv()는 프로젝트 루트의 .env 파일을 탐색해 os.environ 에 주입한다.
# 우선순위: .env 파일 < 이미 설정된 OS 환경변수
# → Jenkins 등 CI 환경에서 OS 환경변수로 주입하면 .env 값을 덮어쓰지 않고 그대로 사용됨
# → 즉, 로컬에서는 .env, CI에서는 Jenkins Credentials(OS 환경변수)로 동일한 코드가 동작
load_dotenv(
    override=False
)  # override=False: OS 환경변수가 있으면 .env 값이 덮어쓰지 않음

# ── Base URL ────────────────────────────────────────────────────────
#
# [1차 Selenium 대응]
#   settings.py 의 BASE_API_URL / ACCOUNTS_BASE_URL 과 동일
#
# BASE_API_URL : REST API 서버 루트 (JSON 응답)
# ACCOUNTS_URL : 인증 서버 루트 (토큰 발급 시 사용)

BASE_API_URL = (
    "https://api-community.elice.io"  # REST API 루트 (운영 서버, smoke/GET 전용)
)
ACCOUNTS_URL = "https://accounts.elice.io"  # 인증 서버 루트

# ── 타임아웃 (초) ────────────────────────────────────────────────────
#
# [1차 Selenium 대응]
#   SHORT_WAIT / DEFAULT_WAIT / LONG_WAIT 과 목적은 같지만 의미가 다르다.
#
#   Selenium : "브라우저 요소가 화면에 나타날 때까지 기다리는 시간"
#   API      : "서버가 HTTP 응답을 보낼 때까지 기다리는 시간 (CONNECT + READ)"
#
#   requests 라이브러리에 timeout=(CONNECT_TIMEOUT, READ_TIMEOUT) 형태로 넘긴다.
#   - CONNECT_TIMEOUT : TCP 연결 수립까지의 최대 대기 시간
#   - READ_TIMEOUT    : 연결 후 첫 바이트 도착까지의 최대 대기 시간
#
# LLM_READ_TIMEOUT : message API처럼 LLM 처리 시간이 긴 엔드포인트 전용
#   → 일반 READ_TIMEOUT(15초)으로는 타임아웃이 날 수 있어 별도 상수로 분리

CONNECT_TIMEOUT = 5  # 초 — TCP 연결 수립 제한
READ_TIMEOUT = 15  # 초 — 일반 API 응답 제한
LLM_READ_TIMEOUT = 60  # 초 — LLM 호출 API 응답 제한 (message 엔드포인트 전용)

# ── 인증 토큰 ────────────────────────────────────────────────────────
#
# [1차 Selenium 대응]
#   TEST_USER = {"id": ..., "pw": ...} 에서 API_TOKEN 단일 값으로 변경
#
#   왜 id/pw 대신 토큰인가?
#     Selenium : 브라우저 UI에서 이메일+비밀번호를 직접 입력해 로그인했다
#     API 테스트: 로그인 UI 흐름이 없다 → 토큰을 미리 발급받아 .env에 저장
#     conftest.py 의 auth_client fixture 가 이 토큰을 읽어 Bearer 헤더에 주입한다
#
#   .env 파일 예시:
#     API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
#     ENVIRONMENT=staging
#
#   CI(Jenkins) 에서는 Jenkins Credentials → withCredentials → OS 환경변수로 주입

API_TOKEN = os.getenv("API_TOKEN")  # Bearer 인증 토큰
ENVIRONMENT = os.getenv("ENVIRONMENT", "staging")  # 현재 실행 환경 (기본값: staging)

# ── Fail-fast 검증 ───────────────────────────────────────────────────
#
# 필수 환경변수가 없으면 테스트가 시작되자마자 알 수 없는 이유로 실패한다.
# settings.py 임포트 시점에 바로 터뜨려서 "왜 실패했는지"를 명확하게 알린다.
#
# [1차 Selenium 대응]
#   1차에서는 TEST_USER["id"] 가 None 이어도 로그인 시도까지 가서야 실패했다.
#   2차에서는 임포트 즉시 실패 → 원인을 바로 파악 가능

_REQUIRED = {
    "API_TOKEN": API_TOKEN,
}

for _name, _value in _REQUIRED.items():
    if not _value:
        raise EnvironmentError(
            f"[settings] 필수 환경변수 '{_name}' 가 설정되지 않았습니다.\n"
            f"  로컬  : 프로젝트 루트의 .env 파일에 {_name}=<값> 을 추가하세요.\n"
            f"  CI    : Jenkins Credentials 에 {_name} 을 등록하고 withCredentials 로 주입하세요."
        )

# ── 환경 판별 함수 ───────────────────────────────────────────────────
#
# destructive 테스트(생성/수정/삭제)는 운영 환경에서 절대 실행되면 안 된다.
# conftest.py 의 pytest_collection_modifyitems 에서 이 함수로 환경을 판별해
# 운영 환경이면 destructive 마커가 붙은 테스트를 자동 스킵한다.
#
# 사용 예시 (conftest.py):
#   if is_production():
#       item.add_marker(pytest.mark.skip(reason="운영 환경 — destructive 테스트 차단"))

_PRODUCTION_ENVIRONMENTS = {"production", "prod"}


def is_production() -> bool:
    """ENVIRONMENT 환경변수가 운영 환경을 가리키면 True 반환."""
    return ENVIRONMENT.lower() in _PRODUCTION_ENVIRONMENTS
