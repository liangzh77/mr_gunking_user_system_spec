"""运营点相关Schema定义"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SiteCreateRequest(BaseModel):
    """创建运营点请求"""
    name: str = Field(..., min_length=2, max_length=100, description="运营点名称")
    address: str = Field(..., min_length=5, max_length=200, description="运营点地址")
    description: Optional[str] = Field(None, max_length=500, description="运营点描述")
    operator_id: UUID = Field(..., description="所属运营商ID")
    contact_person: Optional[str] = Field(None, max_length=64, description="现场负责人")
    contact_phone: Optional[str] = Field(None, max_length=32, description="现场联系电话")
    server_identifier: Optional[str] = Field(None, max_length=128, description="头显Server设备标识符")


class SiteUpdateRequest(BaseModel):
    """更新运营点请求"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="运营点名称")
    address: Optional[str] = Field(None, min_length=5, max_length=200, description="运营点地址")
    description: Optional[str] = Field(None, max_length=500, description="运营点描述")
    operator_id: Optional[UUID] = Field(None, description="所属运营商ID")
    contact_person: Optional[str] = Field(None, max_length=64, description="现场负责人")
    contact_phone: Optional[str] = Field(None, max_length=32, description="现场联系电话")
    server_identifier: Optional[str] = Field(None, max_length=128, description="头显Server设备标识符")
    is_active: Optional[bool] = Field(None, description="运营点状态")


class SiteItem(BaseModel):
    """运营点项"""
    site_id: UUID = Field(..., description="运营点ID")
    name: str = Field(..., description="运营点名称")
    address: str = Field(..., description="运营点地址")
    description: Optional[str] = Field(None, description="运营点描述")
    operator_id: UUID = Field(..., description="所属运营商ID")
    operator_name: str = Field(..., description="运营商名称")
    contact_person: Optional[str] = Field(None, description="现场负责人")
    contact_phone: Optional[str] = Field(None, description="现场联系电话")
    server_identifier: Optional[str] = Field(None, description="头显Server设备标识符")
    is_active: bool = Field(..., description="运营点状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class SiteListResponse(BaseModel):
    """运营点列表响应"""
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total: int = Field(..., description="总记录数")
    items: list[SiteItem] = Field(..., description="运营点列表")