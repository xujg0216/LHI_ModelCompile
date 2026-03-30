"""
@Descripttion: 配置文件加载器
@File: config_loader.py
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
import yaml
from typing import Dict, Any, Optional

from ..core.base_compiler import CompileConfig, PlatformType


class ConfigLoader:
    """配置文件加载器"""
    
    @staticmethod
    def load_yaml(config_path: str) -> Dict[str, Any]:
        """
        加载 YAML 配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在：{config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def parse_compile_config(config_dict: Dict[str, Any]) -> CompileConfig:
        """
        从字典解析编译配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            CompileConfig: 编译配置对象
        """
        # 解析平台类型
        platform_str = config_dict.get("platform", "").lower()
        platform_map = {
            "ASCEND": PlatformType.ASCEND,
            "ILUVATAR": PlatformType.ILUVATAR,
            "ROCKCHIP": PlatformType.ROCKCHIP
        }
        platform = platform_map.get(platform_str)
        if platform is None:
            raise ValueError(f"不支持的平台：{platform_str}")
        
        # 解析输入形状
        input_shape = config_dict.get("input_shape")
        if isinstance(input_shape, dict):
            # 已经是正确的格式
            pass
        elif isinstance(input_shape, str):
            # 解析字符串格式 "input1:1,3,640,640"
            input_shape = ConfigLoader._parse_input_shape(input_shape)
        
        return CompileConfig(
            platform=platform,
            model_path=config_dict.get("model_path", ""),
            output_path=config_dict.get("output_path", ""),
            framework=config_dict.get("framework", "onnx"),
            input_shape=input_shape,
            input_format=config_dict.get("input_format", "NCHW"),
            precision=config_dict.get("precision", "fp16"),
            platform_config=config_dict.get("platform_config", {}),
            do_quantization=config_dict.get("do_quantization", False),
            dataset_path=config_dict.get("dataset_path"),
            mean_values=config_dict.get("mean_values"),
            std_values=config_dict.get("std_values"),
            verbose=config_dict.get("verbose", True),
            log_dir=config_dict.get("log_dir")
        )
    
    @staticmethod
    def _parse_input_shape(shape_str: str) -> Dict[str, list]:
        """
        解析输入形状字符串
        
        Args:
            shape_str: 格式如 "input1:1,3,640,640;input2:1,3,320,320"
            
        Returns:
            Dict[str, list]: 如 {"input1": [1,3,640,640], "input2": [1,3,320,320]}
        """
        result = {}
        parts = shape_str.split(";")
        for part in parts:
            if ":" in part:
                name, values = part.split(":")
                result[name.strip()] = [int(v.strip()) for v in values.split(",")]
        return result
    
    @staticmethod
    def save_config(config: CompileConfig, output_path: str):
        """
        保存配置到文件
        
        Args:
            config: 编译配置
            output_path: 输出路径
        """
        config_dict = {
            "platform": config.platform.value,
            "model_path": config.model_path,
            "output_path": config.output_path,
            "framework": config.framework,
            "input_shape": config.input_shape,
            "input_format": config.input_format,
            "precision": config.precision,
            "platform_config": config.platform_config,
            "do_quantization": config.do_quantization,
            "dataset_path": config.dataset_path,
            "mean_values": config.mean_values,
            "std_values": config.std_values,
            "verbose": config.verbose
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
