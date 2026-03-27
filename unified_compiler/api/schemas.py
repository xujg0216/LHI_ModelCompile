"""
@Descripttion: API 数据模型定义
@File: schemas.py
@Author: Software R&D Department 3
@Version: 0.1
@Date: 2026-03-27
@Company: 北京鲲鹏凌昊智能技术有限公司
@Copyright:
    © 2026 北京鲲鹏凌昊智能技术有限公司 版权所有
@Notice:
    注意: 以下内容均为北京鲲鹏凌昊智能技术有限公司原创，
    未经本公司允许，不得转载，否则视为侵权;
    对于不遵守此声明或其他违法使用以下内容者，
    本公司依法保留追究权。
@NoticeEn:
    © 2026 LinkedHope Intelligent Technologies Co., Ltd. All rights reserved.
    NOTICE: All information contained here is, and remains the property of LinkedHope.
    This file cannot be copied or distributed without permission.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


class PlatformEnum(str, Enum):
    """支持的平台枚举"""
    ASCEND = "ascend"
    ILUVATAR = "iluvatar"
    ROCKCHIP = "rockchip"


class DeviceModelEnum(str, Enum):
    """设备型号枚举"""
    # Ascend 设备
    ASCEND_310P = "Ascend_310P"
    ASCEND_310B = "Ascend_310B"
    # Iluvatar 设备
    ILUVATAR_MR50 = "Iluvatar_MR50"
    ILUVATAR_MR100 = "Iluvatar_MR100"
    # Rockchip 设备
    ROCKCHIP_RK3588 = "Rockchip_RK3588"
    ROCKCHIP_RK3568 = "Rockchip_RK3568"


class CompileStatusEnum(str, Enum):
    """编译状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class CompileRequest(BaseModel):
    """编译请求模型"""

    platform: PlatformEnum = Field(..., description="目标平台")
    model_path: str = Field(..., description="输入模型路径", min_length=1)
    output_path: str = Field(..., description="输出模型路径", min_length=1)

    # 模型配置
    framework: str = Field(default="onnx", description="模型框架")
    input_shape: Optional[Dict[str, List[int]]] = Field(
        default=None,
        description="输入形状，如 {'input': [1, 3, 640, 640]}"
    )
    input_format: str = Field(default="NCHW", description="输入格式")
    precision: str = Field(default="fp16", description="精度模式")

    # 平台特定配置
    platform_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="平台特定配置"
    )

    # 量化配置
    do_quantization: bool = Field(default=False, description="是否量化")
    dataset_path: Optional[str] = Field(default=None, description="量化数据集路径")
    mean_values: Optional[List[float]] = Field(default=None, description="均值")
    std_values: Optional[List[float]] = Field(default=None, description="标准差")

    # 任务配置
    callback_url: Optional[str] = Field(default=None, description="回调 URL")

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "ascend",
                "model_path": "/path/to/model.onnx",
                "output_path": "/path/to/output.om",
                "input_shape": {"input": [1, 3, 640, 640]},
                "input_format": "NCHW",
                "precision": "fp16",
                "platform_config": {"soc_version": "Ascend310P1"},
                "do_quantization": False
            }
        }


class CompileResponse(BaseModel):
    """编译响应模型"""

    task_id: str = Field(..., description="任务 ID")
    status: CompileStatusEnum = Field(..., description="编译状态")
    message: str = Field(default="", description="消息")

    # 编译结果（仅当完成时）
    output_path: Optional[str] = Field(default=None, description="输出路径")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    compile_time: Optional[float] = Field(default=None, description="编译时间（秒）")
    model_info: Optional[Dict[str, Any]] = Field(default=None, description="模型信息")
    warnings: Optional[List[str]] = Field(default=None, description="警告信息")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123456",
                "status": "success",
                "message": "编译成功",
                "output_path": "/path/to/output.om",
                "compile_time": 12.5,
                "model_info": {"platform": "ascend", "format": "om"},
                "warnings": [],
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:12"
            }
        }


class TaskStatus(BaseModel):
    """任务状态响应"""

    task_id: str = Field(..., description="任务 ID")
    status: CompileStatusEnum = Field(..., description="编译状态")
    progress: int = Field(default=0, description="进度百分比 0-100")
    message: str = Field(default="", description="状态消息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

    # 完成后的结果
    result: Optional[CompileResponse] = Field(default=None, description="编译结果")


class PlatformInfo(BaseModel):
    """平台信息"""

    name: str = Field(..., description="平台名称")
    value: str = Field(..., description="平台值")
    supported: bool = Field(default=True, description="是否支持")
    description: str = Field(default="", description="平台描述")


class DeviceInfo(BaseModel):
    """设备型号信息"""
    
    name: str = Field(..., description="设备名称")
    value: str = Field(..., description="设备值")
    platform: str = Field(..., description="所属平台")
    description: str = Field(default="", description="设备描述")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(default="healthy", description="服务状态")
    version: str = Field(default="1.0.0", description="API 版本")
    platforms: List[str] = Field(default_factory=list, description="支持的平台")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ListTasksResponse(BaseModel):
    """任务列表响应"""

    total: int = Field(..., description="总任务数")
    tasks: List[TaskStatus] = Field(..., description="任务列表")


class UploadCompileRequest(BaseModel):
    """上传编译请求模型 - 支持手动指定任务名、设备型号、输出目录等"""
    
    # 任务标识
    task_name: str = Field(..., description="任务名称，如 task_A", min_length=1)
    model_name: str = Field(..., description="模型名称（不含后缀），如 yolo11s", min_length=1)
    output_root: str = Field(..., description="输出根目录，如 /runtime", min_length=1)
    
    # 平台和设备
    platform: PlatformEnum = Field(..., description="目标平台")
    device_model: DeviceModelEnum = Field(..., description="设备型号")
    
    # 模型配置
    framework: str = Field(default="onnx", description="模型框架")
    input_shape: Optional[Dict[str, List[int]]] = Field(
        default=None,
        description="输入形状，如 {'input': [1, 3, 640, 640]}"
    )
    input_format: str = Field(default="NCHW", description="输入格式")
    precision: str = Field(default="fp16", description="精度模式")
    
    # 平台特定配置
    platform_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="平台特定配置"
    )
    
    # 量化配置
    do_quantization: bool = Field(default=False, description="是否量化")
    mean_values: Optional[List[float]] = Field(default=None, description="均值")
    std_values: Optional[List[float]] = Field(default=None, description="标准差")


class UploadResponse(BaseModel):
    """文件上传响应"""
    task_id: str = Field(..., description="任务 ID")
    task_name: str = Field(..., description="任务名称")
    model_name: str = Field(..., description="模型名称")
    device_model: str = Field(..., description="设备型号")
    output_path: str = Field(..., description="输出路径")
    status: str = Field(default="pending", description="初始状态")
    message: str = Field(default="文件上传成功，开始编译", description="消息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class ProgressResponse(BaseModel):
    """进度响应"""
    task_id: str = Field(..., description="任务 ID")
    status: CompileStatusEnum = Field(..., description="编译状态")
    progress: int = Field(0, ge=0, le=100, description="进度百分比")
    message: str = Field(default="", description="状态消息")
    output_path: Optional[str] = Field(default=None, description="输出文件路径（编译成功后）")
    error_message: Optional[str] = Field(default=None, description="错误信息（编译失败时）")


# ========== 推送功能相关模型 ==========

class PushStatusEnum(str, Enum):
    """推送状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TargetDeviceResponse(BaseModel):
    """目标设备响应"""
    id: str = Field(..., description="设备 ID")
    name: str = Field(..., description="设备名称")
    ip_address: str = Field(..., description="IP 地址")
    port: int = Field(default=22, description="SSH 端口")
    username: str = Field(..., description="用户名")
    target_path: str = Field(..., description="目标根路径")
    description: str = Field(default="", description="设备描述")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: str = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class TargetDeviceCreate(BaseModel):
    """创建目标设备请求"""
    name: str = Field(..., description="设备名称")
    ip_address: str = Field(..., description="IP 地址")
    port: int = Field(default=22, description="SSH 端口")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码（明文存储）")
    target_path: str = Field(..., description="目标根路径")
    description: str = Field(default="", description="设备描述")
    enabled: bool = Field(default=True, description="是否启用")


class TargetDeviceUpdate(BaseModel):
    """更新目标设备请求"""
    name: Optional[str] = Field(default=None, description="设备名称")
    ip_address: Optional[str] = Field(default=None, description="IP 地址")
    port: Optional[int] = Field(default=None, description="SSH 端口")
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    target_path: Optional[str] = Field(default=None, description="目标根路径")
    description: Optional[str] = Field(default="", description="设备描述")
    enabled: Optional[bool] = Field(default=None, description="是否启用")


class PushTaskItemResponse(BaseModel):
    """推送任务项响应"""
    device_id: str = Field(..., description="设备 ID")
    device_name: str = Field(..., description="设备名称")
    device_ip: str = Field(..., description="设备 IP")
    status: PushStatusEnum = Field(..., description="推送状态")
    progress: int = Field(default=0, description="推送进度")
    message: str = Field(default="", description="状态消息")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    local_file: str = Field(..., description="本地文件路径")
    remote_file: str = Field(..., description="远程文件路径")
    pushed_at: Optional[str] = Field(default=None, description="推送完成时间")


class PushTaskResponse(BaseModel):
    """推送任务响应"""
    push_task_id: str = Field(..., description="推送任务 ID")
    source_task_id: str = Field(..., description="源编译任务 ID")
    status: PushStatusEnum = Field(..., description="整体推送状态")
    total: int = Field(..., description="总设备数")
    success_count: int = Field(default=0, description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    items: List[PushTaskItemResponse] = Field(default_factory=list, description="推送详情")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
