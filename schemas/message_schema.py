# schemas/message_schema.py
# ============================================================
# /chatroom/{chatroom_id}/message 엔드포인트 응답 본문 검증용 Pydantic 모델
#
# 설계 원칙 9 반영:
#   메시지 응답은 LLM 이 생성하므로 내용(content)이 비결정적.
#   → 응답 *내용*은 assert 하지 않고, 구조(필드 존재·타입)만 검증한다.
#
# TODO 가이드:
#   실제 API Swagger에서 응답 스키마를 확인한 뒤
#   # TODO 주석이 달린 필드의 타입·이름·필수 여부를 수정한다.
# ============================================================

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """
    POST /chatroom/{id}/message/response 단건 응답 스키마.

    테스트에서 검증하는 것:
      - id, chatroom_id, role, content 필드가 존재하는가  ← 구조 검증
      - content 의 실제 값                               ← 검증 안 함 (원칙 9)

    TODO: Swagger 에서 실제 필드명·타입 확인 후 수정
    """

    id: str  # TODO: 타입 확인
    chatroom_id: str  # TODO: 필드명 확인
    # TODO: role 값 확인 ("user"/"assistant" vs "human"/"ai" 등)
    role: Optional[str] = None
    content: str  # LLM 생성 내용 — 구조만 확인, 값은 assert 안 함
    created_at: Optional[datetime] = None  # TODO: 존재 여부 확인

    class Config:
        extra = "ignore"


class MessageListItem(BaseModel):
    """GET /chatroom/{id}/message 목록의 개별 항목 스키마."""

    id: str
    chatroom_id: str  # TODO: 필드명 확인
    role: Optional[str] = None
    content: str

    class Config:
        extra = "ignore"


class MessageListResponse(BaseModel):
    """
    GET /chatroom/{id}/message 목록 응답 스키마.

    TODO: 실제 응답 구조 확인 필요 (래퍼 객체 vs 단순 배열)
    """

    items: list[MessageListItem]
    total: Optional[int] = None  # TODO: total 필드 존재 여부 확인

    class Config:
        extra = "ignore"
