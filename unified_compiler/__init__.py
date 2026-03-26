"""
统一模型编译框架

支持多硬件平台的模型编译：
- 华为昇腾 (Ascend)
- 天数智芯 MR100
- 瑞芯微 RKNN
"""

from .core.base_compiler import BaseCompiler, CompileConfig, CompileResult, CompileStatus, PlatformType
from .core.compiler_registry import CompilerRegistry
from .compiler_engine import ModelCompileEngine
from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger

from . import platforms

__version__ = "1.0.0"

__all__ = [
    # 核心类
    'ModelCompileEngine',
    
    # 基础类型
    'BaseCompiler',
    'CompileConfig',
    'CompileResult',
    'CompileStatus',
    'PlatformType',
    
    # 工具类
    'CompilerRegistry',
    'ConfigLoader',
    'setup_logger',
]
