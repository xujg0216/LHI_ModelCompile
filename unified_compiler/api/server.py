#!/usr/bin/env python3
"""
@Descripttion: API 服务启动脚本
@File: server.py
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

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unified_compiler.api.compiler_api import start_server


def main():
    parser = argparse.ArgumentParser(
        description="统一模型编译 API 服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动服务（默认端口 8000）
  python -m unified_compiler.api.server

  # 指定端口
  python -m unified_compiler.api.server --port 8080

  # 开发模式（自动重载）
  python -m unified_compiler.api.server --reload

  # 指定监听地址
  python -m unified_compiler.api.server --host 0.0.0.0 --port 8000
        """
    )
    
    parser.add_argument("--host", "-H", default="0.0.0.0",
                        help="监听地址 (默认：0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=8000,
                        help="端口号 (默认：8000)")
    parser.add_argument("--reload", "-r", action="store_true",
                        help="开发模式，自动重载")
    parser.add_argument("--workers", "-w", type=int, default=1,
                        help="工作进程数 (默认：1)")
    
    args = parser.parse_args()
    
    print(f"启动 API 服务：http://{args.host}:{args.port}")
    print(f"API 文档：http://{args.host}:{args.port}/docs")
    
    start_server(
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
