# tests/test_message.py
# ============================================================
# /chatroom/{id}/message 엔드포인트 기능 테스트
#
# 커버리지:
#   SEND (POST /chatroom/{id}/message/response) — 성공 / 검증 실패 / 인증 실패
#   GET  (GET  /chatroom/{id}/message)          — 성공
#
# 설계 원칙 9 반영:
#   메시지 응답은 LLM 이 생성하므로 내용(content)이 비결정적이다.
#   → 응답 *내용*은 assert 하지 않는다.
#   → 상태코드 + 응답 구조(필드 존재·타입)만 검증한다.
#
# 의존성:
#   메시지는 chatroom_id 가 필수 → created_chatroom fixture 에 의존.
#   created_chatroom 은 내부적으로 created_model 에 의존.
#
# [1차 Selenium 대응]
#   1차: 입력창 클릭 → 텍스트 입력 → 전송 버튼 클릭 → 응답 버블 로드 대기
#   2차: POST /message/response 단일 요청 + LLM_READ_TIMEOUT(60s)
# ============================================================

import allure
import pytest

from schemas.message_schema import MessageListResponse, MessageResponse


def _no_auth_message_api():
    """토큰을 주입하지 않은 MessageApi 인스턴스를 반환한다."""
    from api.message_api import MessageApi
    from config.settings import BASE_API_URL

    return MessageApi(BASE_API_URL)


# ════════════════════════════════════════════════════════════
# SEND — POST /chatroom/{id}/message/response
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Message 관리")
@allure.story("메시지 전송 - 성공")
@pytest.mark.smoke
@pytest.mark.destructive
def test_send_message_success(message_api, created_chatroom):
    """
    POST /chatroom/{id}/message/response → 200 또는 201 + 응답 구조 검증.

    원칙 9: 응답 content 의 *값*은 검증하지 않는다. 구조(필드 존재)만 확인한다.
    LLM 응답 지연을 위해 MessageApi.send_message() 가 LLM_READ_TIMEOUT(60s) 을 적용한다.
    """
    chatroom_id = created_chatroom["id"]
    payload = {
        "content": "안녕하세요",  # TODO: 실제 API로 필드명 확인
    }

    with allure.step(f"POST /chatroom/{chatroom_id}/message/response 요청 (LLM 호출)"):
        response = message_api.send_message(chatroom_id, payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code in (200, 201)  # TODO: 실제 API로 확인

    with allure.step("응답 구조 검증 (content 값은 검증하지 않음)"):
        body = response.json()
        # pydantic 이 필드 존재·타입을 검증. content 의 실제 값은 보지 않는다.
        MessageResponse(**body)


@allure.epic("Helpychat API")
@allure.feature("Message 관리")
@allure.story("메시지 전송 - 검증 실패")
@pytest.mark.regression
@pytest.mark.parametrize(
    "payload,expected_status",
    [
        ({}, 422),  # 빈 페이로드 → content 없음
        ({"content": ""}, 422),  # 빈 문자열 content  TODO: 400 vs 422 확인
    ],
)
def test_send_message_validation_error(
    message_api, created_chatroom, payload, expected_status
):
    """필수 필드(content) 누락 → 422."""
    chatroom_id = created_chatroom["id"]

    with allure.step(f"잘못된 payload 로 메시지 전송: {payload}"):
        response = message_api.send_message(chatroom_id, payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == expected_status  # TODO: 실제 API로 확인


@allure.epic("Helpychat API")
@allure.feature("Message 관리")
@allure.story("메시지 전송 - 인증 실패")
@pytest.mark.regression
def test_send_message_unauthorized(created_chatroom):
    """토큰 없이 POST /chatroom/{id}/message/response → 401 또는 403."""
    no_auth = _no_auth_message_api()
    chatroom_id = created_chatroom["id"]

    with allure.step("인증 없이 메시지 전송 요청"):
        response = no_auth.send_message(chatroom_id, {"content": "test"})

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO: 실제 API로 확인


# ════════════════════════════════════════════════════════════
# GET messages — GET /chatroom/{id}/message
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Message 관리")
@allure.story("메시지 목록 조회 - 성공")
@pytest.mark.smoke
@pytest.mark.destructive
def test_get_messages_success(message_api, created_chatroom):
    """
    GET /chatroom/{id}/message → 200 + 목록 스키마 검증.

    원칙 9: 메시지 개수·내용은 검증하지 않는다. 응답 구조만 확인한다.
    (LLM 이 생성한 메시지가 있을 수도, 없을 수도 있다.)
    """
    chatroom_id = created_chatroom["id"]

    with allure.step(f"GET /chatroom/{chatroom_id}/message 요청"):
        response = message_api.get_messages(chatroom_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200

    with allure.step("응답 스키마 검증 (내용은 검증하지 않음)"):
        body = response.json()
        # TODO: 단순 배열([...])이면 MessageListItem 으로 교체
        MessageListResponse(**body)
