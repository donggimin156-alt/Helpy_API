# conftest.py
# ============================================================
# 프로젝트 전체 공통 fixture + 마커 기반 안전 가드
#
# [1차 Selenium 대응]
#   conftest.py 와 동일한 역할이지만 내용이 크게 단순해진다.
#
#   1차에서 conftest 가 했던 일:
#     - Firefox 드라이버 생성/종료 (driver, driver_module, tools_driver)
#     - 로그인 처리 (login, login_module, do_login_cached)
#     - 토큰 배너 닫기 (close_token_banner)
#     - FHC 번호 기준 테스트 정렬 (pytest_collection_modifyitems)
#
#   2차에서 conftest 가 하는 일:
#     - HTTP 세션 생성/종료 + 토큰 주입 (auth_client) ← 1차의 driver + login 통합
#     - 운영 환경에서 destructive 테스트 자동 차단 (pytest_collection_modifyitems)
#
#   줄어든 이유:
#     - 브라우저 실행·종료 없음 → 드라이버 fixture 불필요
#     - UI 로그인 절차 없음 → 토큰 한 줄로 인증 완료
#     - 다운로드 경로 설정 없음 → tools_driver 불필요
# ============================================================

import uuid

import pytest

from api.base_client import BaseClient
from api.chatroom_api import ChatroomApi
from api.message_api import MessageApi
from api.model_activation_api import ModelActivationApi
from api.model_api import ModelApi
from config.settings import API_TOKEN, BASE_API_URL, is_production

# ── 인증 클라이언트 fixture ────────────────────────────────────────
#
# [1차 Selenium 대응]
#   1차의 login_module fixture 와 대응:
#
#   1차:
#     @pytest.fixture(scope="module")
#     def login_module(driver_module):
#         _wait = WebDriverWait(driver_module, DEFAULT_WAIT)
#         do_login_cached(driver_module, _wait)   # UI 로그인 → 쿠키 주입
#         return driver_module, _wait
#
#   2차:
#     @pytest.fixture(scope="session")
#     def auth_client():
#         client = BaseClient(BASE_API_URL)
#         client.set_token(API_TOKEN)              # .env 토큰 → 헤더 주입
#         yield client
#
#   차이점 1 — scope: module → session
#     1차는 모듈마다 로그인을 했다(do_login_cached 로 최대한 재사용).
#     2차는 토큰이 만료되지 않는 한 세션 전체에서 한 번만 세팅하면 충분하다.
#
#   차이점 2 — return vs yield
#     1차는 return 으로 (driver, wait) 튜플을 넘겼다.
#     2차는 yield 로 client 를 넘기고, 테스트 종료 후 세션을 닫는다.
#     (yield 이후 = teardown = 1차의 driver.quit() 에 해당)


@pytest.fixture(scope="session")
def auth_client():
    """
    인증된 HTTP 클라이언트를 제공한다. 세션 전체에서 한 번만 생성된다.

    [1차 Selenium 대응]
      driver_module + login_module 두 fixture 를 하나로 통합한 것.
      - driver_module : 브라우저 인스턴스 생성/종료
      - login_module  : 로그인 실행 + (driver, wait) 반환
      →  auth_client  : HTTP 세션 생성 + 토큰 주입 + 세션 종료

    사용 예시 (test 파일):
      def test_get_models(auth_client):
          response = auth_client.get("/api/v1/models")
          assert response.status_code == 200
    """
    client = BaseClient(BASE_API_URL)  # HTTP 세션 생성 (1차의 driver 생성에 해당)
    client.set_token(API_TOKEN)  # Bearer 토큰 주입 (1차의 do_login 에 해당)
    yield client  # 테스트에 client 를 넘김
    client.close()  # 세션 종료 (1차의 driver.quit() 에 해당)


# ── 리소스별 API 클라이언트 fixture (session scope) ──────────────────
#
# [1차 Selenium 대응]
#   1차: driver_module fixture 가 각 모듈마다 브라우저를 열었다.
#   2차: model_api / chatroom_api / message_api fixture 가
#        세션 전체에서 HTTP 클라이언트를 한 번만 생성한다.
#
# scope="session" 이유:
#   토큰이 만료되지 않는 한 하나의 클라이언트로 세션 전체를 커버할 수 있다.
#   (1차의 driver_module 이 모듈 단위 재사용이었다면, 2차는 세션 단위로 더 효율적)


@pytest.fixture(scope="session")
def model_api():
    """ModelApi 인스턴스 — 세션 전체에서 재사용."""
    client = ModelApi(BASE_API_URL)
    client.set_token(API_TOKEN)
    yield client
    client.close()


@pytest.fixture(scope="session")
def chatroom_api():
    """ChatroomApi 인스턴스 — 세션 전체에서 재사용."""
    client = ChatroomApi(BASE_API_URL)
    client.set_token(API_TOKEN)
    yield client
    client.close()


@pytest.fixture(scope="session")
def message_api():
    """MessageApi 인스턴스 — 세션 전체에서 재사용."""
    client = MessageApi(BASE_API_URL)
    client.set_token(API_TOKEN)
    yield client
    client.close()


@pytest.fixture(scope="session")
def model_activation_api():
    """ModelActivationApi 인스턴스 — 세션 전체에서 재사용."""
    client = ModelActivationApi(BASE_API_URL)
    client.set_token(API_TOKEN)
    yield client
    client.close()


# ── 데이터 생성/정리 fixture (function scope) ──────────────────────
#
# [1차 Selenium 대응]
#   1차: 테스트마다 UI 로 데이터를 직접 생성했다.
#   2차: fixture 가 API 로 데이터를 생성(setup) → yield → 삭제(teardown) 한다.
#
# 원칙 1: fixture 체인으로 리소스 간 의존성 해결
#   created_chatroom 이 created_model 을 파라미터로 받아
#   model_id 를 자동으로 주입한다.
#
# 원칙 2: teardown 에서 404 안전 처리
#   이미 삭제된 리소스를 다시 삭제해도 예외가 발생하지 않는다.
#   (raise_for_status() 를 쓰지 않으므로 404 응답도 그냥 통과)
#
# 원칙 3: uuid 로 이름을 고유하게 만들어 충돌·잔여 데이터 방지


@pytest.fixture
def created_model(model_api):
    """
    테스트에 사용할 모델을 반환한다. (기존 모델 목록에서 첫 번째 조회)

    POST /model 에 key/endpoint 필수 필드가 있으나 값을 알 수 없으므로
    GET /model 목록에서 첫 번째 기존 모델을 사용한다.
    생성하지 않으므로 teardown 삭제 없음.
    """
    response = model_api.list_models()
    assert response.status_code == 200, (
        f"[fixture] 모델 목록 조회 실패: {response.status_code}"
    )
    models = response.json()
    assert len(models) > 0, "[fixture] 사용 가능한 모델이 없습니다"
    return models[0]


@pytest.fixture
def created_chatroom(chatroom_api, created_model):
    """
    테스트용 챗방을 생성하고 테스트 종료 후 삭제한다.
    created_model fixture 에 의존 → model_id 를 자동으로 주입받는다.

    [1차 Selenium 대응]
      1차: 챗방 생성 UI 를 직접 조작.
      2차: POST /chatroom 단일 요청.

    Yields
    ------
    dict
        생성된 챗방의 응답 본문(JSON).
        예) {"id": "...", "model_id": "...", ...}
    """
    payload = {
        "model_id": created_model["id"],
        # TODO: name 필드 존재 여부 확인
        "name": f"test-chatroom-{uuid.uuid4()}",
    }
    response = chatroom_api.create_chatroom(payload)
    assert response.status_code in (200, 201), (
        f"[fixture] 챗방 생성 실패: {response.status_code} {response.text}"
    )
    chatroom = response.json()
    yield chatroom

    # teardown
    chatroom_id = chatroom.get("id")
    if chatroom_id:
        chatroom_api.delete_chatroom(chatroom_id)


# ── 운영 환경 destructive 테스트 자동 차단 ─────────────────────────
#
# [1차 Selenium 대응]
#   1차의 pytest_collection_modifyitems 는 FHC 번호 기준 테스트 정렬이었다.
#   2차의 pytest_collection_modifyitems 는 환경 안전 가드로 목적이 달라진다.
#
# 왜 필요한가?
#   destructive 테스트(생성·수정·삭제)는 스테이징에서만 실행해야 한다.
#   운영 환경에서 실수로 pytest 를 실행해도 파괴적인 테스트가 돌지 않게 막는다.
#
# 2중 방어 구조 (V4 설계 원칙 10):
#   1차 방어 (수동): pytest -m "not destructive" 로 실행 시 명시적 제외
#   2차 방어 (자동): ENVIRONMENT=production 이면 코드가 자동 스킵 처리
#   → 실수로 -m 옵션을 빼먹어도 운영 환경에선 destructive 테스트가 절대 실행 안 됨


def pytest_collection_modifyitems(items):
    """
    수집된 테스트 목록을 순회하며 조건에 맞는 테스트에 skip 마커를 추가한다.

    [1차 Selenium 대응]
      1차: FHC 번호 오름차순 정렬
      2차: 운영 환경에서 destructive 마커 테스트 자동 스킵
    """
    if not is_production():
        return  # 운영 환경이 아니면 아무것도 하지 않음

    skip_marker = pytest.mark.skip(reason="운영 환경 — destructive 테스트 자동 차단")

    for item in items:
        if item.get_closest_marker("destructive"):
            item.add_marker(skip_marker)
