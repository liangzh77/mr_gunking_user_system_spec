"""数据导出相关的Pydantic Schemas (T109)

此模块定义数据导出的请求和响应模型。
用于API响应和数据序列化。
"""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ========== 导出格式枚举 ==========

ExportFormat = Literal["excel", "csv"]


# ========== 导出请求参数 ==========

class ExportUsageRecordsRequest(BaseModel):
    """导出使用记录请求参数 (T116)

    支持时间范围筛选和格式选择
    """

    format: ExportFormat = Field("excel", description="导出格式: excel或csv")
    start_time: Optional[datetime] = Field(None, description="开始时间(ISO 8601格式)")
    end_time: Optional[datetime] = Field(None, description="结束时间(ISO 8601格式)")
    site_id: Optional[str] = Field(None, description="运营点ID筛选(可选)")
    app_id: Optional[str] = Field(None, description="应用ID筛选(可选)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "format": "excel",
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-31T23:59:59Z",
                "site_id": "site_xxx",
                "app_id": "app_yyy"
            }
        }


class ExportStatisticsRequest(BaseModel):
    """导出统计报表请求参数 (T117)

    支持多维度统计数据的导出
    """

    format: ExportFormat = Field("excel", description="导出格式: excel或csv")
    report_type: Literal["site", "application", "consumption", "player_distribution"] = Field(
        ...,
        description="报表类型: site(按运营点)/application(按应用)/consumption(按时间)/player_distribution(玩家分布)"
    )
    start_time: Optional[datetime] = Field(None, description="开始时间(ISO 8601格式)")
    end_time: Optional[datetime] = Field(None, description="结束时间(ISO 8601格式)")
    dimension: Optional[Literal["day", "week", "month"]] = Field(
        None,
        description="时间维度(仅report_type=consumption时有效): day/week/month"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "format": "excel",
                "report_type": "consumption",
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-31T23:59:59Z",
                "dimension": "day"
            }
        }


# ========== 导出响应 ==========

class ExportResponse(BaseModel):
    """导出数据响应

    返回文件下载链接或直接返回文件内容
    """

    export_id: str = Field(..., description="导出任务ID", examples=["export_xxx"])
    filename: str = Field(..., description="文件名", examples=["usage_records_20250115.xlsx"])
    format: ExportFormat = Field(..., description="文件格式")
    download_url: str = Field(..., description="下载链接(临时URL,有效期30分钟)", examples=["https://storage.example.com/exports/xxx.xlsx"])
    file_size: int = Field(..., description="文件大小(字节)", examples=[102400], ge=0)
    expires_at: datetime = Field(..., description="下载链接过期时间")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "export_id": "export_123e4567",
                "filename": "usage_records_20250115.xlsx",
                "format": "excel",
                "download_url": "https://storage.example.com/exports/usage_records_20250115.xlsx",
                "file_size": 102400,
                "expires_at": "2025-01-15T12:30:00Z",
                "created_at": "2025-01-15T12:00:00Z"
            }
        }


# ========== 导出状态查询 ==========

class ExportStatusResponse(BaseModel):
    """导出任务状态响应

    用于查询异步导出任务的进度
    """

    export_id: str = Field(..., description="导出任务ID")
    status: Literal["pending", "processing", "completed", "failed"] = Field(..., description="任务状态")
    progress: int = Field(..., description="进度百分比(0-100)", ge=0, le=100)
    filename: Optional[str] = Field(None, description="文件名(completed状态时有值)")
    download_url: Optional[str] = Field(None, description="下载链接(completed状态时有值)")
    error_message: Optional[str] = Field(None, description="错误信息(failed状态时有值)")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "export_id": "export_123e4567",
                "status": "completed",
                "progress": 100,
                "filename": "usage_records_20250115.xlsx",
                "download_url": "https://storage.example.com/exports/usage_records_20250115.xlsx",
                "error_message": None,
                "created_at": "2025-01-15T12:00:00Z",
                "completed_at": "2025-01-15T12:01:30Z"
            }
        }
