# api/model_api.py
# ============================================================
# Model 리소스 API 클라이언트
#
# [1차 Selenium 대응]
#   pages/ModelPage.py → api/model_api.py
#   UI 클릭·입력·확인 → HTTP GET/POST/PATCH/DELETE
#
# 설계 원칙:
#   - BaseClient 상속 → 공통 세션·헤더·타임아웃 자동 적용
#   - 메서드명: 동사 + 리소스 형태 (create_model, get_model …)
#     ※ BaseClient.delete() 와 이름 충돌을 피하기 위해 delete_model() 사용
#   - 모든 메서드는 requests.Response 를 그대로 반환 (raise_for_status 금지)
# ============================================================

from api.base_client import BaseClient

# TODO: 실제 API로 경로 확인 필요 (버전 접두사 여부: /model vs /api/v1/model 등)
_PATH = "/model"


class ModelApi(BaseClient):
    """
    /model 엔드포인트 래퍼.

    [1차 Selenium 대응]
      Selenium 의 ModelPage 가 UI 조작(클릭·입력·확인)을 담당했다면,
      ModelApi 는 동일한 비즈니스 동작을 HTTP 요청으로 수행한다.
      BasePage(driver, wait) → BaseClient(session, timeout) 상속 구조도 동일.
    """

    def create_model(self, payload: dict):
        """
        POST /model — 모델 생성.

        Parameters
        ----------
        payload : dict
            예) {"name": "...", "instructions": "..."}
            TODO: 실제 API로 필수/선택 필드 확인 필요
        """
        return self.post(_PATH, json=payload)

    def list_models(self):
        """GET /model — 활성화된 모델 목록 조회."""
        return self.get(
            _PATH, params={"filter_is_active": "true", "skip": 0, "count": 40}
        )

    def list_all_models(self):
        """GET /model — 활성/비활성 포함 전체 모델 목록 조회."""
        return self.get(_PATH, params={"skip": 0, "count": 100})

    def get_model(self, model_id: str):
        """GET /model/{model_id} — 모델 단건 조회."""
        return self.get(f"{_PATH}/{model_id}")

    def update_model(self, model_id: str, payload: dict):
        """
        PATCH /model/{model_id} — 모델 일부 수정.

        Parameters
        ----------
        payload : dict
            수정할 필드만 포함. 예) {"name": "새 이름"}
        """
        return self.patch(f"{_PATH}/{model_id}", json=payload)

    def delete_model(self, model_id: str):
        """DELETE /model/{model_id} — 모델 삭제."""
        return self.delete(f"{_PATH}/{model_id}")
