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