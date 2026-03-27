"""
@Descripttion: 
@File: iluvatar_test.py
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
from unified_compiler import ModelCompileEngine

# 创建编译引擎
engine = ModelCompileEngine(verbose=True)

# 编译到昇腾平台
result = engine.compile(
    platform="iluvatar",
    model_path="yolo11s.onnx",
    output_path="yolo11s.engine",
    input_shape={"images": [1, 3, 640, 640]},
)

# 检查结果
if result.success:
    print(f"✓ 编译成功！")
    print(f"  输出路径：{result.output_path}")
    print(f"  编译时间：{result.compile_time:.2f}秒")
    print(f"  模型信息：{result.model_info}")
else:
    print(f"✗ 编译失败：{result.error_message}")