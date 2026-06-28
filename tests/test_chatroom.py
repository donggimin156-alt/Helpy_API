# tests/test_chatroom.py
# ============================================================
# /chatroom 엔드포인트 기능 테스트 (핵심 케이스 위주)
#
# 커버리지:
#   CREATE (POST /chatroom)      — 성공 / 검증 실패 / 인증 실패
#   LIST   (GET  /chatroom)      — 성공
#   GET    (GET  /chatroom/{id}) — 성공 / 404
#   DELETE (DELETE /chatroom/{id}) — 성공(삭제 후 404 재확인) / 404
#
# 의존성:
#   챗방은 model_id 가 필수이므로 created_model fixture 에 의존한다.
#   created_chatroom fixture 는 created_model 을 내부적으로 사용한다.
#
# [1차 Selenium 대응]
#   1차: 챗방 생성 UI 폼 조작 → 목록 화면 확인
#   2차: POST /chatroom → 상태코드 + 응답 본문으로 확인
# ============================================================

import uuid

import allure
import pytest

from schemas.chatroom_schema import ChatroomListItem, ChatroomResponse


def _no_auth_chatroom_api():
    """토큰을 주입하지 않은 ChatroomApi 인스턴스를 반환한다."""
    from api.chatroom_api import ChatroomApi
    from config.settings import BASE_API_URL

    return ChatroomApi(BASE_API_URL)


# ════════════════════════════════════════════════════════════
# CREATE — POST /chatroom
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 생성 - 성공")
@pytest.mark.smoke
@pytest.mark.destructive
def test_create_chatroom_success(chatroom_api, created_model, request):
    """
    model_id 포함 올바른 데이터로 POST /chatroom → 200 또는 201 + 스키마 검증.

    created_model fixture 로 model_id 를 주입받는다.
    """
    payload = {
        "model_id": created_model["id"],
        "name": f"test-chatroom-{uuid.uuid4()}",
        # TODO: 실제 API 로 필수/선택 필드 확인
    }

    with allure.step("POST /chatroom 요청"):
        response = chatroom_api.create_chatroom(payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code in (200, 201)  # TODO: 실제 API로 확인

    body = response.json()

    created_id = body.get("id")
    if created_id:
        request.addfinalizer(lambda: chatroom_api.delete_chatroom(created_id))

    with allure.step("응답 스키마 검증"):
        ChatroomResponse(**body)

    with allure.step("model_id 일치 확인"):
        assert body.get("model_id") == created_model["id"]


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 생성 - 검증 실패")
@pytest.mark.regression
@pytest.mark.destructive
@pytest.mark.parametrize(
    "payload,expected_status",
    [
        ({}, 422),  # 빈 페이로드 → model_id 없음
        ({"name": "no-model"}, 422),  # model_id 누락
        ({"model_id": ""}, 422),  # 빈 model_id  TODO: 400 vs 422 확인
    ],
)
def test_create_chatroom_validation_error(chatroom_api, payload, expected_status):
    """필수 필드(model_id) 누락 → 422."""
    with allure.step(f"잘못된 payload 로 POST /chatroom: {payload}"):
        response = chatroom_api.create_chatroom(payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == expected_status  # TODO: 실제 API로 확인


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 생성 - 인증 실패")
@pytest.mark.regression
def test_create_chatroom_unauthorized():
    """토큰 없이 POST /chatroom → 401 또는 403."""
    no_auth = _no_auth_chatroom_api()

    with allure.step("인증 없이 POST /chatroom 요청"):
        # 인증 오류는 비즈니스 검증 전에 발생하므로 model_id 는 임의 값 사용
        response = no_auth.create_chatroom({"model_id": "any", "name": "test"})

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO: 실제 API로 확인


# ════════════════════════════════════════════════════════════
# LIST — GET /chatroom
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 목록 조회 - 성공")
@pytest.mark.smoke
def test_list_chatrooms_success(chatroom_api):
    """GET /chatroom → 200 + 목록 스키마 검증."""
    with allure.step("GET /chatroom 요청"):
        response = chatroom_api.list_chatrooms()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200

    with allure.step("응답 스키마 검증"):
        body = response.json()
        [ChatroomListItem(**item) for item in body]


# ════════════════════════════════════════════════════════════
# GET single — GET /chatroom/{id}
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 단건 조회 - 성공")
@pytest.mark.smoke
@pytest.mark.destructive
def test_get_chatroom_success(chatroom_api, created_chatroom):
    """GET /chatroom/{id} → 200 + 스키마 검증 + id 일치 확인."""
    chatroom_id = created_chatroom["id"]

    with allure.step(f"GET /chatroom/{chatroom_id} 요청"):
        response = chatroom_api.get_chatroom(chatroom_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200

    with allure.step("응답 스키마 + id 검증"):
        body = response.json()
        validated = ChatroomResponse(**body)
        assert validated.id == chatroom_id


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 단건 조회 - 존재하지 않음")
@pytest.mark.regression
def test_get_chatroom_not_found(chatroom_api):
    """존재하지 않는 ID 로 GET /chatroom/{id} → 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"  # TODO: ID 형식 확인

    with allure.step(f"존재하지 않는 ID 로 GET /chatroom/{fake_id} 요청"):
        response = chatroom_api.get_chatroom(fake_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == 409  # 실제 API: 없는 ID → 409


# ════════════════════════════════════════════════════════════
# DELETE — DELETE /chatroom/{id}
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 삭제 - 성공")
@pytest.mark.regression
@pytest.mark.destructive
def test_delete_chatroom_success(chatroom_api, created_chatroom):
    """
    DELETE /chatroom/{id} → 200 또는 204, 이후 GET → 404 재확인.

    Note:
      이 테스트가 챗방을 먼저 삭제하면 created_chatroom fixture 의 teardown 이
      같은 id 로 DELETE 를 재시도한다. 404 가 오지만 raise_for_status() 가 없으므로 무시된다.
    """
    chatroom_id = created_chatroom["id"]

    with allure.step(f"DELETE /chatroom/{chatroom_id} 요청"):
        response = chatroom_api.delete_chatroom(chatroom_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code in (200, 204)  # TODO: 실제 API로 확인

    with allure.step("삭제 후 GET → 404 확인"):
        get_response = chatroom_api.get_chatroom(chatroom_id)
        assert get_response.status_code == 404


@allure.epic("Helpychat API")
@allure.feature("Chatroom 관리")
@allure.story("챗방 삭제 - 존재하지 않음")
@pytest.mark.regression
def test_delete_chatroom_not_found(chatroom_api):
    """존재하지 않는 ID 로 DELETE /chatroom/{id} → 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"  # TODO: ID 형식 확인

    with allure.step(f"존재하지 않는 ID 로 DELETE /chatroom/{fake_id} 요청"):
        response = chatroom_api.delete_chatroom(fake_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == 409  # 실제 API: 없는 ID → 409
