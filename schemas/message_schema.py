# schemas/message_schema.py
# ============================================================
# /chatroom/{chatroom_id}/message 엔드포인트 응답 본문 검증용 Pydantic 모델
#
# POST /chatroom/{id}/message/responses 응답 (스펙 확인):
#   → "string" — JSON 객체가 아닌 문자열 그 자체 (LLM 출력 텍스트)
#   → stream: true 기본값이면 SSE 스트리밍일 수 있음
#
# GET /chatroom/{id}/message 응답:
#   → 스펙 미확인, 배열로 추정
# ============================================================

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageListItem(BaseModel):
    """GET /chatroom/{id}/message 목록의 개별 항목 스키마."""

    id: str
    role: Optional[str] = None  # "user" | "assistant"
    content: Optional[str] = None  # 저장된 메시지 텍스트
    content_raw: Optional[list] = None
    raw: Optional[list] = None
    created: Optional[datetime] = None

    class Config:
        extra = "ignore"
