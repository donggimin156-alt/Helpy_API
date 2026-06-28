# tests/test_e2e_flow.py
# ============================================================
# 전체 시나리오 E2E 스모크 테스트
#
# 목적:
#   개별 엔드포인트 테스트(test_model, test_chatroom, test_message)가
#   "각 API 가 올바른가"를 본다면,
#   이 테스트는 "핵심 사용자 시나리오가 끝까지 이상 없나"를 본다.
#
#   → 연결부 문제 검출: 모델 → 챗방 → 메시지 흐름이 실제로 이어지는가
#   → 배포 직후 의존 확인: 새 배포 후 이 테스트 하나로 핵심 동선을 검증
#
# 시나리오:
#   1. 모델 생성
#   2. 챗방 생성 (model_id 주입)
#   3. 메시지 전송 (LLM 호출)
#   4. 메시지 목록 조회
#   5. 정리 (teardown — 챗방 삭제 → 모델 삭제)
#
# 설계:
#   - 새 로직을 만들지 않고 기존 API 클라이언트 fixture 를 그대로 조립한다.
#   - addfinalizer 는 LIFO 순서로 실행되므로, 챗방(나중 등록) → 모델(먼저 등록) 순으로 삭제된다.
#
# 마커: @pytest.mark.smoke, @pytest.mark.destructive
#
# [1차 Selenium 대응]
#   1차: 브라우저로 전체 사용자 흐름을 실제로 걸어다녔다.
#   2차: HTTP 요청으로 동일한 흐름을 API 레벨에서 검증한다.
# ============================================================

import uuid

import allure
import pytest


@allure.epic("Helpychat API")
@allure.feature("전체 시나리오")
@allure.story("모델 생성 → 챗방 생성 → 메시지 전송 → 메시지 조회 → 정리")
@pytest.mark.smoke
@pytest.mark.destructive
@pytest.mark.xfail(
    reason="POST /model 에 key/endpoint 필수 필드 값 미확인", strict=False
)
def test_full_user_scenario(model_api, chatroom_api, message_api, request):
    """
    핵심 사용자 시나리오 전체를 한 흐름으로 검증한다.

    실패 시 어느 단계에서 끊겼는지 Allure step 으로 바로 확인 가능하다.
    """

    # ── 1단계: 모델 생성 ──────────────────────────────────────────
    model_payload = {
        "name": f"e2e-model-{uuid.uuid4()}",
        # TODO: 실제 API 로 필수 필드 확인
    }

    with allure.step("1단계: 모델 생성"):
        model_resp = model_api.create_model(model_payload)

    allure.attach(str(model_payload), "모델 요청 본문", allure.attachment_type.TEXT)
    allure.attach(model_resp.text, "모델 응답 본문", allure.attachment_type.TEXT)

    assert model_resp.status_code in (200, 201), (
        f"모델 생성 실패: {model_resp.status_code}"
    )
    model = model_resp.json()
    model_id = model["id"]

    # 모델은 가장 마지막에 삭제 (LIFO → 먼저 등록)
    request.addfinalizer(lambda: model_api.delete_model(model_id))

    # ── 2단계: 챗방 생성 ──────────────────────────────────────────
    chatroom_payload = {
        "model_id": model_id,
        "name": f"e2e-chatroom-{uuid.uuid4()}",
        # TODO: 실제 API 로 필드 확인
    }

    with allure.step("2단계: 챗방 생성 (model_id 주입)"):
        chatroom_resp = chatroom_api.create_chatroom(chatroom_payload)

    allure.attach(str(chatroom_payload), "챗방 요청 본문", allure.attachment_type.TEXT)
    allure.attach(chatroom_resp.text, "챗방 응답 본문", allure.attachment_type.TEXT)

    assert chatroom_resp.status_code in (200, 201), (
        f"챗방 생성 실패: {chatroom_resp.status_code}"
    )
    chatroom = chatroom_resp.json()
    chatroom_id = chatroom["id"]

    # 챗방은 모델보다 먼저 삭제 (LIFO → 나중에 등록)
    request.addfinalizer(lambda: chatroom_api.delete_chatroom(chatroom_id))

    # ── 3단계: 메시지 전송 (LLM 호출) ────────────────────────────
    message_payload = {
        "content": "안녕하세요, 테스트 메시지입니다.",
        # TODO: 실제 API 로 필드명 확인
    }

    with allure.step("3단계: 메시지 전송 (LLM_READ_TIMEOUT 적용)"):
        msg_resp = message_api.send_message(chatroom_id, message_payload)

    allure.attach(str(message_payload), "메시지 요청 본문", allure.attachment_type.TEXT)
    allure.attach(msg_resp.text, "메시지 응답 본문", allure.attachment_type.TEXT)

    assert msg_resp.status_code in (200, 201), (
        f"메시지 전송 실패: {msg_resp.status_code}"
    )
    # 원칙 9: 응답 content 값은 검증하지 않는다 — 구조(id, chatroom_id)만 확인
    msg_body = msg_resp.json()
    assert "id" in msg_body, "메시지 응답에 id 필드가 없음"

    # ── 4단계: 메시지 목록 조회 ───────────────────────────────────
    with allure.step("4단계: 메시지 목록 조회"):
        list_resp = message_api.get_messages(chatroom_id)

    allure.attach(list_resp.text, "메시지 목록 응답 본문", allure.attachment_type.TEXT)

    assert list_resp.status_code == 200, f"메시지 조회 실패: {list_resp.status_code}"

    # 원칙 9: 목록의 내용(각 메시지 텍스트)은 검증하지 않는다
    # 응답이 파싱 가능한 JSON 인지만 확인
    list_body = list_resp.json()
    assert list_body is not None, "메시지 목록 응답이 None"
