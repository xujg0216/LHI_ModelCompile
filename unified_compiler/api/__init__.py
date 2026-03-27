"""
@Descripttion: REST API 服务模块
@File: __init__.py
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

from .schemas import (
    CompileRequest,
    CompileResponse,
    PlatformInfo,
    HealthResponse,
    TaskStatus,
)
from .compiler_api import create_app, app

__all__ = [
    'CompileRequest',
    'CompileResponse',
    'PlatformInfo',
    'HealthResponse',
    'TaskStatus',
    'create_app',
    'app',
]
