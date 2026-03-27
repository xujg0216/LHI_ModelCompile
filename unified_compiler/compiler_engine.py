"""
@Descripttion: 统一模型编译工厂 - 提供统一的编译入口
@File: compiler_engine.py
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

import os
from typing import Dict, Any, Optional, Union
from datetime import datetime

from .core.base_compiler import BaseCompiler, CompileConfig, CompileResult, PlatformType
from .core.compiler_registry import CompilerRegistry
from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger


class ModelCompileEngine:
    """
    统一模型编译引擎
    
    提供统一的 API 接口来编译模型到不同的硬件平台
    """
    
    def __init__(self, verbose: bool = True):
        """
        初始化编译引擎
        
        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        self.logger = setup_logger(verbose=verbose)
        self._history: list = []
    
    def compile(
        self,
        platform: Union[str, PlatformType],
        model_path: str,
        output_path: str,
        **kwargs
    ) -> CompileResult:
        """
        编译模型到指定平台

        Args:
            platform: 目标平台 ("ascend", "iluvatar", "rockchip")
            model_path: 输入模型路径
            output_path: 输出模型路径
            **kwargs: 其他配置参数

        Returns:
            CompileResult: 编译结果

        Examples:
            >>> engine = ModelCompileEngine()
            >>> result = engine.compile(
            ...     platform="ascend",
            ...     model_path="model.onnx",
            ...     output_path="model.om",
            ...     input_shape={"input": [1, 3, 640, 640]},
            ...     soc_version="Ascend310P1"
            ... )
        """
        # 解析平台类型
        if isinstance(platform, str):
            platform = PlatformType(platform.lower())
        
        # 构建配置
        config = CompileConfig(
            platform=platform,
            model_path=model_path,
            output_path=output_path,
            **kwargs
        )
        
        self.logger.info(f"开始编译模型到平台：{platform.value}")
        self.logger.info(f"输入模型：{model_path}")
        self.logger.info(f"输出路径：{output_path}")
        
        # 获取编译器
        compiler = CompilerRegistry.get_compiler(platform, config)
        if compiler is None:
            result = CompileResult(
                status=CompileStatus.FAILED,
                error_message=f"不支持的平台：{platform.value}"
            )
            self._record_result(result)
            return result
        
        # 执行编译
        result = compiler.compile()
        
        # 记录结果
        self._record_result(result)
        
        if result.success:
            self.logger.info(f"编译成功！输出：{result.output_path}")
        else:
            self.logger.error(f"编译失败：{result.error_message}")
        
        return result
    
    def compile_from_config(self, config_path: str) -> CompileResult:
        """
        从配置文件编译
        
        Args:
            config_path: 配置文件路径 (YAML 格式)
            
        Returns:
            CompileResult: 编译结果
        """
        self.logger.info(f"从配置文件加载：{config_path}")
        
        config_dict = ConfigLoader.load_yaml(config_path)
        config = ConfigLoader.parse_compile_config(config_dict)
        
        return self.compile(
            platform=config.platform,
            model_path=config.model_path,
            output_path=config.output_path,
            framework=config.framework,
            input_shape=config.input_shape,
            input_format=config.input_format,
            precision=config.precision,
            platform_config=config.platform_config,
            do_quantization=config.do_quantization,
            dataset_path=config.dataset_path,
            mean_values=config.mean_values,
            std_values=config.std_values,
            verbose=config.verbose
        )
    
    def get_supported_platforms(self) -> list:
        """
        获取支持的平台列表
        
        Returns:
            list: 支持的平台名称列表
        """
        return CompilerRegistry.get_all_platforms()
    
    def is_platform_supported(self, platform: str) -> bool:
        """
        检查平台是否被支持
        
        Args:
            platform: 平台名称
            
        Returns:
            bool: 是否支持
        """
        return CompilerRegistry.is_platform_supported(PlatformType(platform.lower()))
    
    def get_compile_history(self) -> list:
        """
        获取编译历史记录
        
        Returns:
            list: 历史记录列表
        """
        return self._history.copy()
    
    def _record_result(self, result: CompileResult):
        """记录编译结果"""
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "result": result.to_dict()
        })
    
    def save_config_template(self, platform: str, output_path: str):
        """
        保存配置模板
        
        Args:
            platform: 平台名称
            output_path: 输出路径
        """
        platform_type = PlatformType(platform.lower())
        
        templates = {
            "ascend": {
                "platform": "ascend",
                "model_path": "model.onnx",
                "output_path": "model.om",
                "framework": "onnx",
                "input_shape": {"input": [1, 3, 640, 640]},
                "input_format": "NCHW",
                "precision": "fp16",
                "platform_config": {
                    "soc_version": "Ascend310P1",
                    "framework": 5
                }
            },
            "iluvatar": {
                "platform": "iluvatar",
                "model_path": "model.onnx",
                "output_path": "model.engine",
                "framework": "onnx",
                "input_shape": {"data": [1, 3, 224, 224]},
                "input_format": "NCHW",
                "precision": "fp32",
                "platform_config": {
                    "model": "MR",
                    "libs": "cudnn,cublas,ixinfer"
                }
            },
            "rockchip": {
                "platform": "rockchip",
                "model_path": "model.onnx",
                "output_path": "model.rknn",
                "framework": "onnx",
                "input_format": "NCHW",
                "precision": "fp16",
                "do_quantization": False,
                "platform_config": {
                    "target_platform": "rk3588"
                },
                "mean_values": [0.485, 0.456, 0.406],
                "std_values": [0.229, 0.224, 0.225]
            }
        }
        
        template = templates.get(platform_type.value, {})
        ConfigLoader.save_config(
            CompileConfig(
                platform=platform_type,
                model_path=template.get("model_path", ""),
                output_path=template.get("output_path", "")
            ),
            output_path
        )
        self.logger.info(f"配置模板已保存到：{output_path}")


# 导入需要的类型
from .core.base_compiler import CompileStatus
