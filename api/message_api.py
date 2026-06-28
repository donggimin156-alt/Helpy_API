# api/message_api.py
# ============================================================
# Message 리소스 API 클라이언트
#
# [1차 Selenium 대응]
#   pages/MessagePage.py → api/message_api.py
#
# 특별 취급 (설계 원칙 9):
#   send_message 는 실제 LLM 을 호출하므로
#   (a) 응답이 느리고 (b) 내용이 비결정적 → timeout 을 넉넉하게 줘야 한다.
#   일반 READ_TIMEOUT(15s) 대신 LLM_READ_TIMEOUT(60s) 을 적용한다.
#
# 모든 메서드는 requests.Response 를 그대로 반환 (raise_for_status 금지)
# ============================================================

from api.base_client import BaseClient
from config.settings import CONNECT_TIMEOUT, LLM_READ_TIMEOUT

# TODO: 실제 API로 경로 확인 필요
_MSG_RESPONSE_PATH = "/chatroom/{chatroom_id}/message/responses"
_MSG_LIST_PATH = "/chatroom/{chatroom_id}/message"


class MessageApi(BaseClient):
    """
    /chatroom/{chatroom_id}/message 엔드포인트 래퍼.

    [1차 Selenium 대응]
      Selenium 에서 메시지 입력창 클릭 → 텍스트 입력 → 전송 버튼 클릭 →
      응답 버블 로드 대기(LONG_WAIT) 하던 패턴을,
      POST /message/response 단일 요청 + LLM 전용 타임아웃으로 대체한다.
    """

    def send_message(self, chatroom_id: str, payload: dict):
        """
        POST /chatroom/{chatroom_id}/message/response — 메시지 전송 (LLM 호출).

        일반 타임아웃(READ_TIMEOUT=15s) 대신 LLM_READ_TIMEOUT(60s) 을 적용한다.

        Parameters
        ----------
        chatroom_id : str
            대상 챗방 ID
        payload : dict
            예) {"content": "안녕하세요"}
            TODO: 실제 API로 필수/선택 필드 확인 필요
        """
        path = _MSG_RESPONSE_PATH.format(chatroom_id=chatroom_id)
        # LLM 응답 지연을 위해 _request() 로 직접 호출하여 timeout 을 개별 지정
        return self._request(
            "POST",
            path,
            json=payload,
            timeout=(CONNECT_TIMEOUT, LLM_READ_TIMEOUT),
        )

    def get_messages(self, chatroom_id: str, count: int = 20):
        """GET /chatroom/{chatroom_id}/message — 챗방 메시지 목록 조회.

        count 는 필수 파라미터 (스펙: 1~50).
        """
        path = _MSG_LIST_PATH.format(chatroom_id=chatroom_id)
        return self.get(path, params={"count": count})
