# schemas/chatroom_schema.py
# ============================================================
# /chatroom 엔드포인트 응답 본문 검증용 Pydantic 모델
#
# GET /chatroom      → list[ChatroomListItem]  (단순 배열)
# GET /chatroom/{id} → ChatroomResponse
# POST /chatroom     → ChatroomResponse
# ============================================================

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgentRef(BaseModel):
    """ChatroomListItem 안에 중첩된 agent 객체."""

    id: str
    name: Optional[str] = None
    logo_resource_id: Optional[str] = None

    class Config:
        extra = "ignore"


class ModelRef(BaseModel):
    """ChatroomListItem 안에 중첩된 model 객체."""

    id: str
    name: Optional[str] = None
    logo_resource_id: Optional[str] = None

    class Config:
        extra = "ignore"


class LxpConfig(BaseModel):
    """GET /chatroom/{id} 응답의 lxp_config 객체 (LXP 강의 연동 설정)."""

    lecture_page_id: Optional[int] = None
    lecture_page_name: Optional[str] = None
    lecture_page_type: Optional[str] = None
    lecture_id: Optional[int] = None
    lecture_name: Optional[str] = None
    course_id: Optional[int] = None
    course_name: Optional[str] = None

    class Config:
        extra = "ignore"


class ChatroomListItem(BaseModel):
    """
    GET /chatroom 목록 응답의 개별 항목 스키마.

    응답이 단순 배열([...])임을 확인 — 래퍼 객체 없음.
    """

    id: str
    chatroom_type: Optional[str] = None  # 예: "community"
    agent_id: Optional[str] = None
    model_id: Optional[str] = None
    agent: Optional[AgentRef] = None
    model: Optional[ModelRef] = None
    name: Optional[str] = None
    created: Optional[datetime] = None

    class Config:
        extra = "ignore"


class ChatroomResponse(BaseModel):
    """
    POST /chatroom, GET /chatroom/{chatroom_id} 단건 응답 스키마.

    주의: 날짜 필드명은 created_at 이 아닌 created 임.
    """

    id: str
    agent_id: Optional[str] = None
    model_id: Optional[str] = None
    name: Optional[str] = None
    last_message_created_at: Optional[str] = None
    created: Optional[datetime] = None
    lxp_config: Optional[LxpConfig] = None

    class Config:
        extra = "ignore"
