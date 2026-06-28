# schemas/model_schema.py
# ============================================================
# /model 엔드포인트 응답 본문 검증용 Pydantic 모델
#
# GET /model/{model_id} 응답 필드 (스펙 확인):
#   id, name, endpoint, key, description, logo_resource_id,
#   sort_order, auto_active, enable_file_upload, tools, enable_reasoning_effort
# ============================================================

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ModelResponse(BaseModel):
    """GET /model/{model_id} 단건 응답 스키마."""

    id: str
    name: str
    endpoint: Optional[str] = None
    key: Optional[str] = None
    description: Optional[dict[str, Any]] = None
    logo_resource_id: Optional[str] = None
    sort_order: Optional[int] = None
    auto_active: Optional[bool] = None
    enable_file_upload: Optional[bool] = None
    tools: Optional[list[str]] = None
    enable_reasoning_effort: Optional[list[str]] = None

    class Config:
        extra = "ignore"


class ModelListItem(BaseModel):
    """GET /model 목록의 개별 항목 스키마."""

    id: str
    name: str

    class Config:
        extra = "ignore"
