# 统一模型编译框架 (Unified Model Compiler)

一个统一的多硬件平台模型编译框架，支持将深度学习模型编译到不同的 AI 加速芯片平台。

## 特性

- 🚀 **统一 API** - 一套接口支持多平台编译
- 🔧 **多平台支持** - 昇腾、天数智芯、瑞芯微
- 📦 **灵活配置** - 支持命令行、配置文件、Python API 三种使用方式
- 🌐 **REST API** - 提供完整的 HTTP API 服务
- 📊 **量化支持** - 支持 INT8 量化优化

## 支持的平台

| 平台 | 类型 | 输出格式 |
|------|------|----------|
| Ascend (华为昇腾) | NPU | .om |
| Iluvatar (天数智芯) | GPU | .engine |
| Rockchip (瑞芯微) | NPU | .rknn |

## 安装

```bash
# 安装基础包
pip install -e .

# 安装 API 服务依赖
pip install -e ".[api]"

# 平台特定依赖
pip install -e ".[ascend]"    # 昇腾 (需要 CANN)
pip install -e ".[iluvatar]"  # 天数智芯 (需要 IXRT)
pip install -e ".[rockchip]"  # 瑞芯微 (需要 RKNN-Toolkit)
```

## 快速开始

### 1. 命令行使用

```bash
# 编译到昇腾平台
unified-compile compile \
  --platform ascend \
  --model model.onnx \
  --output model.om \
  --input-shape "input:1,3,640,640" \
  --soc-version Ascend310P1

# 编译到天数智芯平台
unified-compile compile \
  --platform iluvatar \
  --model model.onnx \
  --output model.engine \
  --input-shape "data:1,3,224,224"

# 编译到瑞芯微平台
unified-compile compile \
  --platform rockchip \
  --model model.onnx \
  --output model.rknn \
  --quantize \
  --dataset ./calib_dataset
```

### 2. Python API

```python
from unified_compiler import ModelCompileEngine, PlatformType

# 创建编译引擎
engine = ModelCompileEngine(verbose=True)

# 编译到昇腾平台
result = engine.compile(
    platform="ascend",
    model_path="model.onnx",
    output_path="model.om",
    input_shape={"input": [1, 3, 640, 640]},
    soc_version="Ascend310P1"
)

if result.success:
    print(f"编译成功：{result.output_path}")
else:
    print(f"编译失败：{result.error_message}")
```

### 3. 配置文件方式

```yaml
# config.yaml
platform: ascend
model_path: model.onnx
output_path: model.om
framework: onnx
input_shape:
  input: [1, 3, 640, 640]
input_format: NCHW
precision: fp16
platform_config:
  soc_version: Ascend310P1
  framework: 5
```

```bash
unified-compile compile-from-config config.yaml
```

### 4. 启动 API 服务

```bash
cd unified_compiler/api
python server.py
```

API 端点：
- `POST /api/compile` - 编译模型
- `GET /api/platforms` - 获取支持的平台
- `POST /api/upload` - 上传模型文件
- `GET /api/health` - 健康检查

## 项目结构

```
unified_compiler/
├── api/                    # REST API 服务
│   ├── server.py          # FastAPI 服务器
│   ├── compiler_api.py    # 编译 API 端点
│   ├── device_manager.py  # 设备管理
│   ├── schemas.py         # Pydantic 数据模型
│   └── upload_v4.html     # Web 上传界面
├── core/                   # 核心编译逻辑
│   ├── base_compiler.py   # 基础编译器类
│   ├── compiler_registry.py # 编译器注册表
│   └── ...
├── platforms/              # 平台特定实现
│   ├── ascend_compiler.py    # 昇腾编译器
│   ├── iluvatar_compiler.py  # 天数智芯编译器
│   └── rockchip_compiler.py  # 瑞芯微编译器
├── utils/                  # 工具模块
│   ├── config_loader.py   # 配置加载器
│   └── logger.py          # 日志工具
├── cli.py                  # 命令行工具
└── compiler_engine.py      # 编译引擎入口
```

## 命令行工具

```bash
# 查看帮助
unified-compile --help

# 列出支持的平台
unified-compile list-platforms

# 生成配置模板
unified-compile gen-template --platform ascend --output ascend_config.yaml
```

## 配置选项

### 通用配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `platform` | 目标平台 | 必填 |
| `model_path` | 输入模型路径 | 必填 |
| `output_path` | 输出模型路径 | 必填 |
| `framework` | 模型框架 | onnx |
| `input_shape` | 输入形状 | - |
| `input_format` | 输入格式 (NCHW/NHWC) | NCHW |
| `precision` | 精度 (fp32/fp16/int8) | fp16 |

### 昇腾平台特有配置

| 参数 | 说明 |
|------|------|
| `soc_version` | SoC 版本 (如 Ascend310P1, Ascend910) |
| `framework` | 框架类型 ID (ONNX=5) |

### 瑞芯微平台特有配置

| 参数 | 说明 |
|------|------|
| `target_platform` | 目标芯片 (如 rk3588, rk3568) |
| `mean_values` | 归一化均值 |
| `std_values` | 归一化标准差 |
| `do_quantization` | 是否量化 |
| `dataset_path` | 量化数据集路径 |

## 开发

```bash
# 克隆仓库
git clone <repository-url>
cd LHI_ModelCompile

# 开发模式安装
pip install -e .

# 运行测试
python ascend_test.py
python iluvatar_test.py
```

## 许可证

MIT License

## 联系方式

Author: Nick Xu
