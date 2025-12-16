"""应用版本相关Schema"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationVersionResponse(BaseModel):
    """应用版本响应Schema"""

    id: UUID = Field(description="版本ID")
    application_id: UUID = Field(description="所属应用ID")
    version: str = Field(description="版本号")
    filename: str = Field(description="原始文件名")
    file_path: str = Field(description="存储路径")
    apk_url: str = Field(description="下载链接")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    description: Optional[str] = Field(default=None, description="版本说明")
    created_at: datetime = Field(description="上传时间")
    uploaded_by: Optional[UUID] = Field(default=None, description="上传者ID")

    class Config:
        from_attributes = True


class ApplicationVersionListResponse(BaseModel):
    """应用版本列表响应Schema"""

    items: list[ApplicationVersionResponse] = Field(description="版本列表")
    total: int = Field(description="总数")
    app_name: str = Field(description="应用名称")
    app_code: str = Field(description="应用代码")


class LatestVersionResponse(BaseModel):
    """最新版本响应Schema"""

    app_code: str = Field(description="应用代码")
    app_name: str = Field(description="应用名称")
    latest_version: Optional[str] = Field(default=None, description="最新版本号")
    apk_url: Optional[str] = Field(default=None, description="APK下载链接")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
