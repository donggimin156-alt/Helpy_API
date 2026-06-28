# tests/test_model.py
# ============================================================
# /model 엔드포인트 기능 테스트
#
# 커버리지:
#   CREATE (POST /model)  — 성공 / 검증 실패(parametrize) / 인증 실패
#   LIST   (GET  /model)  — 성공 / 인증 실패
#   GET    (GET  /model/{id}) — 성공 / 404 / 인증 실패
#   UPDATE (PATCH /model/{id}) — 성공 / 404 / 인증 실패
#   DELETE (DELETE /model/{id}) — 성공(삭제 후 404 재확인) / 404 / 인증 실패
#
# 마커:
#   smoke       : 핵심 경로만 빠르게 (CREATE 성공, LIST 성공, GET 성공)
#   regression  : 전체 케이스
#   destructive : 데이터를 생성·수정·삭제하는 테스트 (운영 환경 자동 차단)
#
# [1차 Selenium 대응]
#   1차: 브라우저에서 UI 를 직접 조작하며 화면 변화로 결과를 확인했다.
#   2차: HTTP 요청 → 상태코드 + 응답 본문(스키마)으로 결과를 확인한다.
# ============================================================

import uuid

import allure
import pytest

from schemas.model_schema import ModelListItem, ModelResponse

# ── 헬퍼: 인증 없는 클라이언트 생성 ────────────────────────────────
#
# 인증 실패 테스트에서 공통으로 사용한다.
# fixture 로 빼지 않고 테스트 내부에서 직접 생성해 각 테스트를 독립적으로 유지.


def _no_auth_model_api():
    """토큰을 주입하지 않은 ModelApi 인스턴스를 반환한다."""
    from api.model_api import ModelApi
    from config.settings import BASE_API_URL

    return ModelApi(BASE_API_URL)


# ════════════════════════════════════════════════════════════
# CREATE — POST /model
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 생성 - 성공")
@pytest.mark.smoke
@pytest.mark.destructive
@pytest.mark.xfail(
    reason="POST /model: key/endpoint 실제 값 미확인 또는 계정 권한 부족(403)",
    strict=False,
)
def test_create_model_success(model_api, request):
    """
    올바른 데이터로 POST /model → 200 또는 201.

    API 스펙: 응답 본문은 {"model_id": "..."} 만 반환.
    에러코드: has_no_permission(403) — 계정 권한 없을 시 실패 가능.

    [1차 Selenium 대응]
      1차: 모델 생성 버튼 클릭 → 폼 입력 → 저장 → 목록에서 생성 확인
      2차: POST /model 단일 요청 → 상태코드 + 응답 본문으로 확인
    """
    payload = {
        "name": f"test-model-{uuid.uuid4()}",
        "key": "test-api-key",
        "endpoint": "https://api.openai.com/v1",
    }

    with allure.step("POST /model 요청"):
        response = model_api.create_model(payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code in (200, 201)

    body = response.json()

    # POST /model 응답: {"model_id": "..."} — id 가 아닌 model_id
    created_id = body.get("model_id")
    if created_id:
        request.addfinalizer(lambda: model_api.delete_model(created_id))

    with allure.step("응답 구조 검증 (model_id 필드 존재 확인)"):
        assert "model_id" in body, "POST /model 응답에 model_id 필드가 없음"


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 생성 - 검증 실패")
@pytest.mark.regression
@pytest.mark.parametrize(
    "payload,expected_status",
    [
        ({}, 422),  # 빈 페이로드 → 필수 필드 없음
        ({"name": ""}, 422),  # 빈 문자열 name  TODO: 400 vs 422 확인
        ({"wrong_field": "value"}, 422),  # 잘못된 필드명 → 필수 필드 누락
    ],
)
def test_create_model_validation_error(model_api, payload, expected_status):
    """
    필수 필드 누락·잘못된 입력으로 POST /model → 422.

    [1차 Selenium 대응]
      1차: 폼 제출 후 에러 메시지 UI 확인
      2차: 상태코드 422 확인 (Pydantic validation error)
    """
    with allure.step(f"잘못된 payload 로 POST /model: {payload}"):
        response = model_api.create_model(payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == expected_status  # TODO: 실제 API로 확인


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 생성 - 인증 실패")
@pytest.mark.regression
def test_create_model_unauthorized():
    """토큰 없이 POST /model → 401 또는 403."""
    no_auth = _no_auth_model_api()

    with allure.step("인증 없이 POST /model 요청"):
        response = no_auth.create_model({"name": "unauthorized-test"})

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO: 실제 API로 확인


# ════════════════════════════════════════════════════════════
# LIST — GET /model
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 목록 조회 - 성공")
@pytest.mark.smoke
def test_list_models_success(model_api):
    """GET /model → 200 + 목록 스키마 검증."""
    with allure.step("GET /model 요청"):
        response = model_api.list_models()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200

    with allure.step("응답 스키마 검증"):
        body = response.json()
        [ModelListItem(**item) for item in body]


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 목록 조회 - 인증 실패")
@pytest.mark.regression
def test_list_models_unauthorized():
    """토큰 없이 GET /model → 401 또는 403."""
    no_auth = _no_auth_model_api()

    with allure.step("인증 없이 GET /model 요청"):
        response = no_auth.list_models()

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO


# ════════════════════════════════════════════════════════════
# GET single — GET /model/{id}
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 단건 조회 - 성공")
@pytest.mark.smoke
@pytest.mark.destructive
def test_get_model_success(model_api, created_model):
    """GET /model/{id} → 200 + 스키마 검증 + id 일치 확인."""
    model_id = created_model["id"]

    with allure.step(f"GET /model/{model_id} 요청"):
        response = model_api.get_model(model_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200

    with allure.step("응답 스키마 + id 검증"):
        body = response.json()
        validated = ModelResponse(**body)
        assert validated.id == model_id


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 단건 조회 - 존재하지 않음")
@pytest.mark.regression
def test_get_model_not_found(model_api):
    """존재하지 않는 ID 로 GET /model/{id} → 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"  # TODO: ID 형식 확인

    with allure.step(f"존재하지 않는 ID 로 GET /model/{fake_id} 요청"):
        response = model_api.get_model(fake_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == 409  # 실제 API: 없는 ID → 409


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 단건 조회 - 인증 실패")
@pytest.mark.regression
@pytest.mark.destructive
def test_get_model_unauthorized(created_model):
    """토큰 없이 GET /model/{id} → 401 또는 403."""
    no_auth = _no_auth_model_api()

    with allure.step("인증 없이 GET /model/{id} 요청"):
        response = no_auth.get_model(created_model["id"])

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO


# ════════════════════════════════════════════════════════════
# UPDATE — PATCH /model/{id}
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 수정 - 성공")
@pytest.mark.regression
@pytest.mark.destructive
def test_update_model_success(model_api, created_model):
    """PATCH /model/{id} → 200 + 수정 내용 응답 본문 반영 확인."""
    model_id = created_model["id"]
    new_name = f"updated-{uuid.uuid4()}"
    payload = {"name": new_name}  # TODO: 수정 가능한 필드 목록 확인

    with allure.step(f"PATCH /model/{model_id} 요청"):
        response = model_api.update_model(model_id, payload)

    allure.attach(str(payload), "요청 본문", allure.attachment_type.TEXT)
    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200  # TODO: 204(본문 없음)인지 확인

    with allure.step("수정된 name 값 확인"):
        body = response.json()
        assert body.get("name") == new_name


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 수정 - 존재하지 않음")
@pytest.mark.regression
def test_update_model_not_found(model_api):
    """존재하지 않는 ID 로 PATCH /model/{id} → 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"  # TODO: ID 형식 확인

    with allure.step(f"존재하지 않는 ID 로 PATCH /model/{fake_id} 요청"):
        response = model_api.update_model(fake_id, {"name": "ghost"})

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == 409  # 실제 API: 없는 ID → 409


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 수정 - 인증 실패")
@pytest.mark.regression
@pytest.mark.destructive
def test_update_model_unauthorized(created_model):
    """토큰 없이 PATCH /model/{id} → 401 또는 403."""
    no_auth = _no_auth_model_api()

    with allure.step("인증 없이 PATCH /model/{id} 요청"):
        response = no_auth.update_model(created_model["id"], {"name": "hack"})

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO


# ════════════════════════════════════════════════════════════
# DELETE — DELETE /model/{id}
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 삭제 - 성공")
@pytest.mark.regression
@pytest.mark.destructive
def test_delete_model_success(model_api, created_model):
    """
    DELETE /model/{id} → 200 또는 204, 이후 GET → 404 재확인.

    Note:
      이 테스트가 모델을 먼저 삭제하면,
      created_model fixture 의 teardown 이 같은 id 로 DELETE 를 재시도한다.
      서버에서 404 가 오지만 raise_for_status() 가 없으므로 teardown 은 정상 완료된다.
    """
    model_id = created_model["id"]

    with allure.step(f"DELETE /model/{model_id} 요청"):
        response = model_api.delete_model(model_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code == 200  # 스펙: DELETE 성공 → 200, 응답 본문 {}

    with allure.step("삭제 후 GET → 409 확인"):
        get_response = model_api.get_model(model_id)
        assert get_response.status_code == 409  # 실제 API: 없는 리소스 → 409


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 삭제 - 존재하지 않음")
@pytest.mark.regression
def test_delete_model_not_found(model_api):
    """존재하지 않는 ID 로 DELETE /model/{id} → 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"  # TODO: ID 형식 확인

    with allure.step(f"존재하지 않는 ID 로 DELETE /model/{fake_id} 요청"):
        response = model_api.delete_model(fake_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code == 409  # 실제 API: 없는 ID → 409


@allure.epic("Helpychat API")
@allure.feature("Model 관리")
@allure.story("모델 삭제 - 인증 실패")
@pytest.mark.regression
@pytest.mark.destructive
def test_delete_model_unauthorized(created_model):
    """토큰 없이 DELETE /model/{id} → 401 또는 403."""
    no_auth = _no_auth_model_api()

    with allure.step("인증 없이 DELETE /model/{id} 요청"):
        response = no_auth.delete_model(created_model["id"])

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)  # TODO
