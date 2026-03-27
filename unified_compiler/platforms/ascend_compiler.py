"""
@Descripttion: 华为昇腾 (Ascend) 编译器实现
@File: ascend_compiler.py
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
import subprocess
import shutil
from typing import Dict, Any, List

from ..core.base_compiler import BaseCompiler, CompileConfig, CompileResult, CompileStatus
from ..core.compiler_registry import CompilerRegistry
from ..core.base_compiler import PlatformType


@CompilerRegistry.register(PlatformType.ASCEND)
class AscendCompiler(BaseCompiler):
    """华为昇腾 ATC 编译工具封装"""
    
    @property
    def platform_name(self) -> str:
        return "Ascend"
    
    def _pre_compile_check(self):
        """昇腾平台特有的检查"""
        super()._pre_compile_check()
        
        # 检查 ATC 工具是否可用
        if not shutil.which("atc"):
            raise RuntimeError("ATC 工具未找到，请确保已安装昇腾 CANN  toolkit")
    
    def _do_compile(self) -> CompileResult:
        """执行 ATC 编译"""
        pcfg = self.config.platform_config
        
        # 构建 ATC 命令
        cmd = [
            "atc",
            "--framework", str(pcfg.get("framework", 5)),  # 5 = ONNX
            "--model", self.config.model_path,
            "--output", self.config.output_path.replace(".om", ""),
            "--input_shape", self._format_input_shape(),
            "--soc_version", pcfg.get("soc_version", "Ascend310P1"),
            "--input_format", self.config.input_format,
            "--precision_mode", self._get_precision_mode()
        ]
        
        # 添加可选参数
        if pcfg.get("op_select_implmode"):
            cmd.extend(["--op_select_implmode", pcfg.get("op_select_implmode")])
        
        if pcfg.get("fusion_switch_file"):
            cmd.extend(["--fusion_switch_file", pcfg.get("fusion_switch_file")])
        
        self._log(f"执行 ATC 编译：{' '.join(cmd)}")
        
        try:
            # 执行编译命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=pcfg.get("timeout", 3600)
            )
            
            if result.returncode == 0:
                output_file = self.config.output_path if self.config.output_path.endswith(".om") else f"{self.config.output_path}.om"
                return CompileResult(
                    status=CompileStatus.SUCCESS,
                    output_path=output_file,
                    model_info={
                        "platform": "Ascend",
                        "soc_version": pcfg.get("soc_version", "Ascend310P1"),
                        "format": "om"
                    }
                )
            else:
                return CompileResult(
                    status=CompileStatus.FAILED,
                    error_message=f"ATC 编译失败：{result.stderr}",
                    warnings=self._parse_warnings(result.stdout)
                )
                
        except subprocess.TimeoutExpired:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message="编译超时"
            )
        except Exception as e:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message=str(e)
            )
    
    def _format_input_shape(self) -> str:
        """格式化输入形状为 ATC 所需格式"""
        if not self.config.input_shape:
            return ""
        
        shapes = []
        for name, shape in self.config.input_shape.items():
            shape_str = ",".join(map(str, shape))
            shapes.append(f"{name}:{shape_str}")
        return ";".join(shapes)
    
    def _get_precision_mode(self) -> str:
        """获取精度模式"""
        precision_map = {
            "fp32": "force_fp32",
            "fp16": "allow_fp32_to_fp16",
            "int8": "allow_fp32_to_fp16"  # ATC 不直接支持 int8
        }
        return precision_map.get(self.config.precision, "allow_fp32_to_fp16")
    
    def _parse_warnings(self, output: str) -> List[str]:
        """解析 ATC 输出中的警告信息"""
        warnings = []
        for line in output.split("\n"):
            if "WARNING" in line.upper():
                warnings.append(line.strip())
        return warnings
    
    def _log(self, message: str):
        """日志输出"""
        if self.config.verbose:
            print(f"[Ascend] {message}")
