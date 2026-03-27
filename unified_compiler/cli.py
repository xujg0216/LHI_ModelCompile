#!/usr/bin/env python3
"""
@Descripttion: 统一模型编译命令行工具
@File: cli.py
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

import argparse
import sys
import os

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_compiler import ModelCompileEngine, PlatformType, ConfigLoader
from unified_compiler.utils.logger import setup_logger


def main():
    parser = argparse.ArgumentParser(
        description="统一模型编译工具 - 支持 Ascend, Iluvatar, Rockchip 平台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 编译到昇腾平台
  python -m unified_compiler.cli compile \\
    --platform ascend \\
    --model model.onnx \\
    --output model.om \\
    --input-shape "input:1,3,640,640" \\
    --soc-version Ascend310P1

  # 从配置文件编译
  python -m unified_compiler.cli compile-from-config config.yaml

  # 列出支持的平台
  python -m unified_compiler.cli list-platforms

  # 生成配置模板
  python -m unified_compiler.cli gen-template --platform ascend --output ascend_config.yaml
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # compile 命令
    compile_parser = subparsers.add_parser("compile", help="编译模型到指定平台")
    compile_parser.add_argument("--platform", "-p", required=True,
                                choices=["ascend", "iluvatar", "rockchip"],
                                help="目标平台")
    compile_parser.add_argument("--model", "-m", required=True,
                                help="输入模型路径")
    compile_parser.add_argument("--output", "-o", required=True,
                                help="输出模型路径")
    compile_parser.add_argument("--input-shape", "-s",
                                help="输入形状，格式：name:d1,d2,d3,d4")
    compile_parser.add_argument("--input-format", default="NCHW",
                                choices=["NCHW", "NHWC"],
                                help="输入格式")
    compile_parser.add_argument("--precision", default="fp16",
                                choices=["fp32", "fp16", "int8"],
                                help="精度模式")
    compile_parser.add_argument("--soc-version",
                                help="SoC 版本 (Ascend 专用)")
    compile_parser.add_argument("--target-platform",
                                help="目标平台 (RKNN 专用)")
    compile_parser.add_argument("--quantize", action="store_true",
                                help="启用量化")
    compile_parser.add_argument("--dataset",
                                help="量化数据集路径")
    compile_parser.add_argument("--verbose", "-v", action="store_true",
                                help="详细输出")
    
    # compile-from-config 命令
    config_parser = subparsers.add_parser("compile-from-config",
                                          help="从配置文件编译")
    config_parser.add_argument("config", help="配置文件路径")
    config_parser.add_argument("--verbose", "-v", action="store_true",
                               help="详细输出")
    
    # list-platforms 命令
    subparsers.add_parser("list-platforms", help="列出支持的平台")
    
    # gen-template 命令
    template_parser = subparsers.add_parser("gen-template",
                                            help="生成配置模板")
    template_parser.add_argument("--platform", "-p", required=True,
                                 choices=["ascend", "iluvatar", "rockchip"],
                                 help="目标平台")
    template_parser.add_argument("--output", "-o", required=True,
                                 help="输出文件路径")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    engine = ModelCompileEngine(verbose=getattr(args, 'verbose', True))
    
    if args.command == "compile":
        # 构建平台特定配置
        platform_config = {}
        if args.soc_version:
            platform_config["soc_version"] = args.soc_version
        if args.target_platform:
            platform_config["target_platform"] = args.target_platform
        
        # 解析输入形状
        input_shape = None
        if args.input_shape:
            input_shape = ConfigLoader._parse_input_shape(args.input_shape)
        
        result = engine.compile(
            platform=args.platform,
            model_path=args.model,
            output_path=args.output,
            input_shape=input_shape,
            input_format=args.input_format,
            precision=args.precision,
            platform_config=platform_config,
            do_quantization=args.quantize,
            dataset_path=args.dataset
        )
        
        if result.success:
            print(f"\n✓ 编译成功！输出：{result.output_path}")
            sys.exit(0)
        else:
            print(f"\n✗ 编译失败：{result.error_message}")
            sys.exit(1)
    
    elif args.command == "compile-from-config":
        result = engine.compile_from_config(args.config)
        
        if result.success:
            print(f"\n✓ 编译成功！输出：{result.output_path}")
            sys.exit(0)
        else:
            print(f"\n✗ 编译失败：{result.error_message}")
            sys.exit(1)
    
    elif args.command == "list-platforms":
        platforms = engine.get_supported_platforms()
        print("支持的平台:")
        for p in platforms:
            print(f"  - {p}")
        sys.exit(0)
    
    elif args.command == "gen-template":
        engine.save_config_template(args.platform, args.output)
        print(f"配置模板已保存到：{args.output}")
        sys.exit(0)


if __name__ == "__main__":
    main()
