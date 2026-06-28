# api/chatroom_api.py
# ============================================================
# Chatroom 리소스 API 클라이언트
#
# [1차 Selenium 대응]
#   pages/ChatroomPage.py → api/chatroom_api.py
#
# 설계 원칙:
#   - BaseClient 상속 → 공통 세션·헤더·타임아웃 자동 적용
#   - 챗방은 model_id 에 종속 → create_chatroom 의 payload 에 model_id 필수
#   - 모든 메서드는 requests.Response 를 그대로 반환 (raise_for_status 금지)
# ============================================================

from api.base_client import BaseClient

# TODO: 실제 API로 경로 확인 필요
_PATH = "/chatroom"


class ChatroomApi(BaseClient):
    """
    /chatroom 엔드포인트 래퍼.

    [1차 Selenium 대응]
      Selenium 의 ChatroomPage 가 UI 에서 챗방 목록·생성·삭제를 담당했다면,
      ChatroomApi 는 동일한 동작을 HTTP 요청으로 수행한다.
    """

    def create_chatroom(self, payload: dict):
        """
        POST /chatroom — 챗방 생성.

        Parameters
        ----------
        payload : dict
            예) {"model_id": "...", "name": "..."}
            TODO: 실제 API로 필수/선택 필드 확인 필요
        """
        return self.post(_PATH, json=payload)

    def list_chatrooms(self):
        """GET /chatroom — 챗방 목록 조회."""
        return self.get(_PATH, params={"count": 20})

    def get_chatroom(self, chatroom_id: str):
        """GET /chatroom/{chatroom_id} — 챗방 단건 조회."""
        return self.get(f"{_PATH}/{chatroom_id}")

    def delete_chatroom(self, chatroom_id: str):
        """DELETE /chatroom/{chatroom_id} — 챗방 삭제."""
        return self.delete(f"{_PATH}/{chatroom_id}")
