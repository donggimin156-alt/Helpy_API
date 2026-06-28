# tests/test_model_activation.py
# ============================================================
# /model_activation 엔드포인트 기능 테스트
#
# 커버리지:
#   ACTIVATE   (POST /model_activation)   — 성공 / 인증 실패
#   DEACTIVATE (DELETE /model_activation) — 성공 / 인증 실패
#
# 시나리오:
#   비활성화된 모델을 하나 찾아 → 활성화 → 목록에서 확인 → 비활성화(teardown)
#
# 설계:
#   - UI에서 사람이 토글을 ON/OFF 하는 동작을 API로 자동화한다.
#   - 테스트 전후 상태를 동일하게 유지한다 (teardown에서 원상복구).
#   - 비활성 모델이 없으면 pytest.skip 으로 안전하게 건너뛴다.
#
# [1차 Selenium 대응]
#   1차: 모델 설정 화면 → 토글 클릭 → 상태 변화 UI 확인
#   2차: POST/DELETE /model_activation → 상태코드 + 목록 재조회로 확인
# ============================================================

import allure
import pytest


def _no_auth_activation_api():
    from api.model_activation_api import ModelActivationApi
    from config.settings import BASE_API_URL

    return ModelActivationApi(BASE_API_URL)


def _find_inactive_model(model_api):
    """
    비활성화된 모델 ID 를 반환한다.

    전체 목록과 활성 목록의 차집합으로 비활성 모델을 찾는다.
    없으면 None 을 반환한다.
    """
    all_resp = model_api.list_all_models()
    active_resp = model_api.list_models()

    if all_resp.status_code != 200 or active_resp.status_code != 200:
        return None

    all_ids = {m["id"] for m in all_resp.json()}
    active_ids = {m["id"] for m in active_resp.json()}
    inactive_ids = all_ids - active_ids

    return next(iter(inactive_ids), None)


# ════════════════════════════════════════════════════════════
# ACTIVATE — POST /model_activation
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model Activation 관리")
@allure.story("모델 활성화 - 성공")
@pytest.mark.regression
@pytest.mark.destructive
def test_activate_model_success(model_api, model_activation_api):
    """
    비활성 모델을 POST /model_activation 으로 활성화 → 활성 목록에서 확인.

    teardown: 테스트 종료 후 원래 상태(비활성)로 되돌린다.
    """
    inactive_id = _find_inactive_model(model_api)

    if inactive_id is None:
        pytest.skip("비활성 모델이 없어 활성화 테스트를 건너뜁니다")

    with allure.step(f"POST /model_activation (model_id={inactive_id})"):
        response = model_activation_api.activate_model(inactive_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code in (200, 201)

    with allure.step("활성 목록에서 해당 모델 확인"):
        active_resp = model_api.list_models()
        active_ids = {m["id"] for m in active_resp.json()}
        assert inactive_id in active_ids, "활성화 후에도 목록에 없음"

    # teardown: 원래 비활성 상태로 되돌림
    model_activation_api.deactivate_model(inactive_id)


@allure.epic("Helpychat API")
@allure.feature("Model Activation 관리")
@allure.story("모델 활성화 - 인증 실패")
@pytest.mark.regression
def test_activate_model_unauthorized(created_model):
    """토큰 없이 POST /model_activation → 401 또는 403."""
    no_auth = _no_auth_activation_api()

    with allure.step("인증 없이 POST /model_activation 요청"):
        response = no_auth.activate_model(created_model["id"])

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)


# ════════════════════════════════════════════════════════════
# DEACTIVATE — DELETE /model_activation
# ════════════════════════════════════════════════════════════


@allure.epic("Helpychat API")
@allure.feature("Model Activation 관리")
@allure.story("모델 비활성화 - 성공")
@pytest.mark.regression
@pytest.mark.destructive
def test_deactivate_model_success(model_api, model_activation_api):
    """
    활성 모델을 DELETE /model_activation 으로 비활성화 → 활성 목록에서 제거 확인.

    teardown: 테스트 종료 후 원래 상태(활성)로 되돌린다.
    """
    # 활성화된 모델 중 마지막 것을 사용 (Helpy Pro Agent 등 필수 모델 건드리지 않도록 마지막 선택)
    active_resp = model_api.list_models()
    assert active_resp.status_code == 200
    active_models = active_resp.json()

    if len(active_models) < 2:
        pytest.skip(
            "활성 모델이 1개 이하라 비활성화 테스트를 건너뜁니다 (서비스 영향 방지)"
        )

    # 목록 마지막 모델을 선택 (앞쪽 핵심 모델 보호)
    target = active_models[-1]
    target_id = target["id"]

    with allure.step(f"DELETE /model_activation (model_id={target_id})"):
        response = model_activation_api.deactivate_model(target_id)

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    with allure.step("상태코드 확인"):
        assert response.status_code in (200, 204)

    with allure.step("활성 목록에서 해당 모델 제거 확인"):
        active_resp2 = model_api.list_models()
        active_ids = {m["id"] for m in active_resp2.json()}
        assert target_id not in active_ids, "비활성화 후에도 목록에 남아있음"

    # teardown: 원래 활성 상태로 되돌림
    model_activation_api.activate_model(target_id)


@allure.epic("Helpychat API")
@allure.feature("Model Activation 관리")
@allure.story("모델 비활성화 - 인증 실패")
@pytest.mark.regression
def test_deactivate_model_unauthorized(created_model):
    """토큰 없이 DELETE /model_activation → 401 또는 403."""
    no_auth = _no_auth_activation_api()

    with allure.step("인증 없이 DELETE /model_activation 요청"):
        response = no_auth.deactivate_model(created_model["id"])

    no_auth.close()

    allure.attach(response.text, "응답 본문", allure.attachment_type.TEXT)

    assert response.status_code in (401, 403)
