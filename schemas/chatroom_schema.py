# schemas/chatroom_schema.py
# ============================================================
# /chatroom 엔드포인트 응답 본문 검증용 Pydantic 모델
#
# TODO 가이드:
#   실제 API Swagger에서 응답 스키마를 확인한 뒤
#   # TODO 주석이 달린 필드의 타입·이름·필수 여부를 수정한다.
# ============================================================

from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class ChatroomResponse(BaseModel):
    """
    POST /chatroom, GET /chatroom/{chatroom_id} 단건 응답 스키마.

    TODO: Swagger 에서 실제 필드명·타입 확인 후 수정
    """

    id: str                              # TODO: 타입 확인
    model_id: str                        # TODO: 필드명 확인
    name: Optional[str] = None           # TODO: name 필드 존재 여부 확인
    created_at: Optional[datetime] = None  # TODO: 존재 여부 확인

    class Config:
        extra = "ignore"


class ChatroomListItem(BaseModel):
    """GET /chatroom 목록의 개별 항목 스키마."""

    id: str       # TODO: 타입 확인
    model_id: str  # TODO: 필드명 확인
    name: Optional[str] = None

    class Config:
        extra = "ignore"


class ChatroomListResponse(BaseModel):
    """
    GET /chatroom 목록 응답 스키마.

    TODO: 실제 응답 구조 확인 필요 (래퍼 객체 vs 단순 배열)
    """

    items: list[ChatroomListItem]
    total: Optional[int] = None  # TODO: total 필드 존재 여부 확인

    class Config:
        extra = "ignore"
