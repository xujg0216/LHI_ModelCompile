"""
@Descripttion: 瑞芯微 ROCKCHIP 编译器实现
@File: rockchip_compiler.py
@Author: Software R&D Department 3
@Version: 0.1
@Date: 2026-03-27
@Company: 北京鲲鹏凌昊智能技术有限公司
@Copyright:
    © 2026 北京鲲鹏凌昊智能技术有限公司 版权所有
@Notice:
    注意：以下内容均为北京鲲鹏凌昊智能技术有限公司原创，
    未经本公司允许，不得转载，否则视为侵权;
    对于不遵守此声明或其他违法使用以下内容者，
    本公司依法保留追究权。
@NoticeEn:
    © 2026 LinkedHope Intelligent Technologies Co., Ltd. All rights reserved.
    NOTICE: All information contained here is, and remains the property of LinkedHope.
    This file cannot be copied or distributed without permission.
"""
import shutil
from typing import Dict, Any, List

from ..core.base_compiler import BaseCompiler, CompileConfig, CompileResult, CompileStatus
from ..core.compiler_registry import CompilerRegistry
from ..core.base_compiler import PlatformType


@CompilerRegistry.register(PlatformType.ROCKCHIP)
class RockchipCompiler(BaseCompiler):
    """瑞芯微 ROCKCHIP RKNN 编译器封装"""

    @property
    def platform_name(self) -> str:
        return "ROCKCHIP"

    def _pre_compile_check(self):
        """ROCKCHIP 平台特有的检查"""
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
                    "platform": "ROCKCHIP",
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
            print(f"[ROCKCHIP] {message}")
