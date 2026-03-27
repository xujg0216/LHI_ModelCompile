"""
@Descripttion: 统一模型编译框架
@File: setup.py
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

from setuptools import setup, find_packages

# with open("unified_compiler/README.md", "r", encoding="utf-8") as fh:
#     long_description = fh.read()

setup(
    name="unified-compiler",
    version="1.0.0",
    author="Nick xu",
    description="统一的多硬件平台模型编译框架",
    # long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=6.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "ascend": [],  # 需要安装昇腾 CANN
        "iluvatar": ["ixrt"],  # ixrt for Iluvatar
        "rockchip": ["rknn-toolkit"],  # RKNN toolkit
        "api": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "unified-compile=unified_compiler.cli:main",
        ],
    },
)
