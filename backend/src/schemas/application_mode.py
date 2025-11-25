"""应用模式相关的 Pydantic Schema 定义"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ApplicationModeBase(BaseModel):
    """应用模式基础Schema"""
    mode_name: str = Field(..., max_length=64, description="模式名称（如：5分钟、10分钟）")
    price: Decimal = Field(..., gt=0, description="模式价格")
    description: Optional[str] = Field(None, description="模式描述")
    sort_order: int = Field(0, description="排序顺序")
    is_active: bool = Field(True, description="是否启用")

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """验证价格范围"""
        if v <= 0:
            raise ValueError('价格必须大于0')
        if v > 9999.99:
            raise ValueError('价格不能超过9999.99')
        return v


class ApplicationModeCreate(ApplicationModeBase):
    """创建应用模式Schema"""
    pass


class ApplicationModeUpdate(BaseModel):
    """更新应用模式Schema"""
    mode_name: Optional[str] = Field(None, max_length=64)
    price: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """验证价格范围"""
        if v is not None:
            if v <= 0:
                raise ValueError('价格必须大于0')
            if v > 9999.99:
                raise ValueError('价格不能超过9999.99')
        return v


class ApplicationModeResponse(ApplicationModeBase):
    """应用模式响应Schema"""
    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
