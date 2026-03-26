"""
基础编译器抽象类 - 定义统一的编译接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import time
from datetime import datetime


class PlatformType(Enum):
    """支持的硬件平台类型"""
    ASCEND = "ascend"           # 华为昇腾
    ILUVATAR = "iluvatar"       # 天数智芯 Iluvatar (MR 系列)
    ROCKCHIP = "rockchip"       # 瑞芯微 Rockchip (RKNN)
    CUSTOM = "custom"           # 自定义平台


class CompileStatus(Enum):
    """编译状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class CompileConfig:
    """编译配置"""
    # 基础配置
    platform: PlatformType
    model_path: str
    output_path: str
    
    # 模型配置
    framework: str = "onnx"     # onnx, tensorflow, pytorch, etc.
    input_shape: Optional[Dict[str, List[int]]] = None
    input_format: str = "NCHW"  # NCHW or NHWC
    precision: str = "fp16"     # fp32, fp16, int8
    
    # 平台特定配置
    platform_config: Dict[str, Any] = field(default_factory=dict)
    
    # 量化配置
    do_quantization: bool = False
    dataset_path: Optional[str] = None
    mean_values: Optional[List[float]] = None
    std_values: Optional[List[float]] = None
    
    # 日志配置
    verbose: bool = True
    log_dir: Optional[str] = None
    
    def __post_init__(self):
        """验证配置"""
        if self.platform_config is None:
            self.platform_config = {}


@dataclass
class CompileResult:
    """编译结果"""
    status: CompileStatus
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    compile_time: float = 0.0
    model_info: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success(self) -> bool:
        return self.status == CompileStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于 API 响应"""
        return {
            "status": self.status.value,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "compile_time": self.compile_time,
            "model_info": self.model_info,
            "warnings": self.warnings,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "success": self.success
        }


class BaseCompiler(ABC):
    """编译器基类 - 所有平台编译器必须继承此类"""
    
    def __init__(self, config: CompileConfig):
        """
        初始化编译器
        
        Args:
            config: 编译配置
        """
        self.config = config
        self._result: Optional[CompileResult] = None
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """返回平台名称"""
        pass
    
    @abstractmethod
    def _do_compile(self) -> CompileResult:
        """
        执行实际编译操作（子类实现）
        
        Returns:
            CompileResult: 编译结果
        """
        pass
    
    def compile(self) -> CompileResult:
        """
        编译入口方法（模板方法模式）
        
        Returns:
            CompileResult: 编译结果
        """
        start_time = datetime.now()
        
        try:
            # 编译前检查
            self._pre_compile_check()
            
            # 执行编译
            result = self._do_compile()
            
            # 编译后处理
            self._post_compile_process(result)
            
        except Exception as e:
            result = CompileResult(
                status=CompileStatus.FAILED,
                error_message=str(e),
                start_time=start_time,
                end_time=datetime.now()
            )
        
        result.start_time = start_time
        result.end_time = datetime.now()
        result.compile_time = (result.end_time - result.start_time).total_seconds()
        
        self._result = result
        return result
    
    def _pre_compile_check(self):
        """编译前检查（可被子类重写）"""
        import os
        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(f"模型文件不存在：{self.config.model_path}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(self.config.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    
    def _post_compile_process(self, result: CompileResult):
        """编译后处理（可被子类重写）"""
        pass
    
    def get_result(self) -> Optional[CompileResult]:
        """获取最近的编译结果"""
        return self._result
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        if not self.config.model_path:
            raise ValueError("模型路径不能为空")
        if not self.config.output_path:
            raise ValueError("输出路径不能为空")
        return True
