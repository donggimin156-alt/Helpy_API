# api/model_activation_api.py
# ============================================================
# Model Activation 리소스 API 클라이언트
#
# /model_activation 엔드포인트 래퍼.
# 기관 관리자가 AI 모델 설정 화면에서 모델별 ON/OFF 토글을 조작하는 것을
# HTTP 요청으로 수행한다.
#
# POST /model_activation   → 모델 활성화 (토글 ON)
# DELETE /model_activation → 모델 비활성화 (토글 OFF)
# ============================================================

from api.base_client import BaseClient

_PATH = "/model_activation"


class ModelActivationApi(BaseClient):
    """
    /model_activation 엔드포인트 래퍼.

    기관 구성원에게 노출할 모델을 활성화/비활성화한다.
    """

    def activate_model(self, model_id: str):
        """POST /model_activation — 모델 활성화 (토글 ON)."""
        return self.post(_PATH, json={"model_id": model_id})

    def deactivate_model(self, model_id: str):
        """DELETE /model_activation — 모델 비활성화 (토글 OFF)."""
        return self.delete(_PATH, json={"model_id": model_id})
