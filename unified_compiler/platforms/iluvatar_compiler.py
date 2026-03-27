"""
@Descripttion: 天数智芯 Iluvatar 编译器实现 - 使用 ixrt API
@File: iluvatar_compiler.py
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
from typing import Dict, Any, List, Optional

from ..core.base_compiler import BaseCompiler, CompileConfig, CompileResult, CompileStatus
from ..core.compiler_registry import CompilerRegistry
from ..core.base_compiler import PlatformType


@CompilerRegistry.register(PlatformType.ILUVATAR)
class IluvatarCompiler(BaseCompiler):
    """天数智芯 Iluvatar ixrt 编译器封装"""

    @property
    def platform_name(self) -> str:
        return "Iluvatar"

    def _pre_compile_check(self):
        """Iluvatar 平台特有的检查"""
        super()._pre_compile_check()

        # 检查 ixrt 是否可用
        try:
            import ixrt
        except ImportError as e:
            raise RuntimeError(f"ixrt 未安装或导入失败：{e}")

    def _do_compile(self) -> CompileResult:
        """执行 ixrt 编译"""
        try:
            import ixrt

            pcfg = self.config.platform_config

            # 获取配置参数
            use_int8 = pcfg.get("use_int8", False)
            input_shapes = pcfg.get("input_shapes", {})
            log_level = pcfg.get("log_level", "WARNING")

            self._log(f"导入模型：{self.config.model_path}")

            # 1. 创建 Builder
            IXRT_LOGGER = ixrt.Logger(ixrt.Logger.WARNING)
            builder = ixrt.Builder(IXRT_LOGGER)
            EXPLICIT_BATCH = 1 << (int)(ixrt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            network = builder.create_network(EXPLICIT_BATCH)
            build_config = builder.create_builder_config()
            parser = ixrt.OnnxParser(network, IXRT_LOGGER)

            # 2. 解析 ONNX
            if not os.path.exists(self.config.model_path):
                raise FileNotFoundError(f"ONNX 文件不存在：{self.config.model_path}")
            parser.parse_from_file(self.config.model_path)

            # 3. 设置优化配置 - FP16 或 INT8
            if use_int8:
                self._log("使用 INT8 精度编译")
                build_config.set_flag(ixrt.BuilderFlag.INT8)
            else:
                self._log("使用 FP16 精度编译")
                build_config.set_flag(ixrt.BuilderFlag.FP16)

            # 4. 固定输入尺寸
            if input_shapes:
                self._log(f"设置输入尺寸：{input_shapes}")
                for input_name, shape in input_shapes.items():
                    try:
                        input_tensor = network.get_input(input_name)
                        if input_tensor is not None:
                            input_tensor.shape = shape
                            self._log(f"  {input_name}: {shape}")
                        else:
                            self._log(f"  警告：找不到输入 '{input_name}'，跳过")
                    except Exception as e:
                        self._log(f"  设置输入 '{input_name}' 失败：{e}")
            else:
                # 如果没有指定输入形状，尝试使用第一个输入
                if network.num_inputs > 0:
                    first_input = network.get_input(0)
                    if first_input is not None:
                        # 使用默认形状或从配置中获取
                        default_shape = pcfg.get("default_input_shape", None)
                        if default_shape:
                            first_input.shape = default_shape
                            self._log(f"设置默认输入形状：{default_shape}")

            # 5. 构建 engine
            self._log("开始构建 engine...")
            plan = builder.build_serialized_network(network, build_config)
            if plan is None:
                raise RuntimeError("Engine 构建失败，请检查 ONNX 输入形状和 profile")

            # 6. 导出引擎文件
            output_path = self.config.output_path
            if not output_path.endswith(".engine"):
                output_path = f"{output_path}.engine"

            self._log(f"导出引擎文件：{output_path}")
            with open(output_path, "wb") as f:
                f.write(plan)

            self._log(f"Build engine done! Saved to {output_path}")

            return CompileResult(
                status=CompileStatus.SUCCESS,
                output_path=output_path,
                model_info={
                    "platform": "Iluvatar",
                    "format": "engine",
                    "precision": "int8" if use_int8 else "fp16",
                }
            )

        except ImportError as e:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message=f"ixrt 导入失败：{e}"
            )
        except FileNotFoundError as e:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message=str(e)
            )
        except Exception as e:
            return CompileResult(
                status=CompileStatus.FAILED,
                error_message=f"编译失败：{e}"
            )

    def _log(self, message: str):
        """日志输出"""
        if self.config.verbose:
            print(f"[Iluvatar] {message}")
