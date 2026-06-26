# schemas/model_schema.py
# ============================================================
# /model 엔드포인트 응답 본문 검증용 Pydantic 모델
#
# 사용 목적:
#   테스트에서 response.json() 을 이 스키마로 파싱하면
#   pydantic 이 필드 존재 여부·타입을 자동으로 검증한다.
#   → "상태코드만 보는 테스트"가 아닌 "응답 계약(contract) 테스트" 가능
#
# TODO 가이드:
#   실제 API Swagger(/docs 또는 /openapi.json)에서 응답 스키마를 확인한 뒤
#   # TODO 주석이 달린 필드의 타입·이름·필수 여부를 수정한다.
# ============================================================

from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class ModelResponse(BaseModel):
    """
    POST /model, GET /model/{model_id} 단건 응답 스키마.

    TODO: Swagger 에서 실제 필드명·타입 확인 후 수정
    """

    id: str                            # TODO: str vs int vs UUID 확인
    name: str
    instructions: Optional[str] = None  # TODO: 필드명 확인 (system_prompt 등)
    created_at: Optional[datetime] = None  # TODO: 존재 여부 확인

    class Config:
        # 정의되지 않은 추가 필드를 무시 → API 응답에 예상 외 필드가 있어도 통과
        extra = "ignore"


class ModelListItem(BaseModel):
    """GET /model 목록의 개별 항목 스키마."""

    id: str   # TODO: 타입 확인
    name: str

    class Config:
        extra = "ignore"


class ModelListResponse(BaseModel):
    """
    GET /model 목록 응답 스키마.

    TODO: 실제 응답 구조 확인 필요
      - {"items": [...], "total": N}  형태인지
      - 단순 배열([...])인지
    현재는 래퍼 객체 가정. 단순 배열이면 테스트에서 직접 list[ModelListItem] 로 파싱할 것.
    """

    items: list[ModelListItem]
    total: Optional[int] = None  # TODO: total 필드 존재 여부 확인

    class Config:
        extra = "ignore"
