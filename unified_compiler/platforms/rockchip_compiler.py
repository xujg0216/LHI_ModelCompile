"""
瑞芯微 Rockchip 编译器实现
"""

import os
import shutil
from typing import Dict, Any, List

from ..core.base_compiler import BaseCompiler, CompileConfig, CompileResult, CompileStatus
from ..core.compiler_registry import CompilerRegistry
from ..core.base_compiler import PlatformType


@CompilerRegistry.register(PlatformType.ROCKCHIP)
class RockchipCompiler(BaseCompiler):
    """瑞芯微 Rockchip RKNN 编译器封装"""

    @property
    def platform_name(self) -> str:
        return "Rockchip"

    def _pre_compile_check(self):
        """Rockchip 平台特有的检查"""
        super()._pre_compile_check()

        # 检查 RKNN API 是否可用
        try:
            from rknn.api import RKNN
        except ImportError as e:
            raise RuntimeError(f"RKNN API 未安装：{e}")

    def _do_compile(self) -> CompileResult:
        """执行 RKNN 编译"""
        try:
            from rknn.api import RKNN

            pcfg = self.config.platform_config

            # 创建 RKNN 对象
            rknn = RKNN(verbose=self.config.verbose)

            self._log("配置模型...")

            # 配置模型
            config_kwargs = {
                "target_platform": pcfg.get("target_platform", "rk3588")
            }

            # 预处理配置
            if self.config.mean_values:
                config_kwargs["mean_values"] = [[m * 255 for m in self.config.mean_values]]
            if self.config.std_values:
                config_kwargs["std_values"] = [[s * 255 for s in self.config.std_values]]

            rknn.config(**config_kwargs)

            self._log(f"加载模型：{self.config.model_path}")

            # 加载模型
            ret = rknn.load_onnx(model=self.config.model_path)
            if ret != 0:
                return CompileResult(
                    status=CompileStatus.FAILED,
                    error_message="加载模型失败"
                )

            self._log("构建模型...")

            # 构建模型
            dataset = self.config.dataset_path if self.config.do_quantization else None
            ret = rknn.build(
                do_quantization=self.config.do_quantization,
                dataset=dataset
            )
            if ret != 0:
                return CompileResult(
                    status=CompileStatus.FAILED,
                    error_message="构建模型失败"
                )

            # 导出 RKNN 模型
            output_path = self.config.output_path
            if not output_path.endswith(".rknn"):
                output_path = f"{output_path}.rknn"

            self._log(f"导出模型：{output_path}")
            ret = rknn.export_rknn(output_path)
            if ret != 0:
                return CompileResult(
                    status=CompileStatus.FAILED,
                    error_message="导出模型失败"
                )

            # 可选：精度分析
            if pcfg.get("accuracy_analysis", {}).get("enable", False):
                self._log("执行精度分析...")
                acc_cfg = pcfg["accuracy_analysis"]
                rknn.accuracy_analysis(
                    inputs=acc_cfg.get("input_img_path"),
                    output_dir=acc_cfg.get("output_dir"),
                    target=acc_cfg.get("target")
                )

            # 释放资源
            rknn.release()

            return CompileResult(
                status=CompileStatus.SUCCESS,
                output_path=output_path,
                model_info={
                    "platform": "Rockchip",
                    "target_platform": pcfg.get("target_platform", "rk3588"),
                    "quantization": self.config.do_quantization,
                    "format": "rknn"
                }
            )

        except ImportError as e:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message=f"RKNN API 导入失败：{e}"
            )
        except Exception as e:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message=f"编译失败：{e}"
            )

    def _post_compile_process(self, result: CompileResult):
        """编译后处理 - 复制配置文件到输出目录"""
        if result.success:
            # 可选：保存配置文件到输出目录
            pass

    def _log(self, message: str):
        """日志输出"""
        if self.config.verbose:
            print(f"[Rockchip] {message}")
