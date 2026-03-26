# 统一模型编译框架 (Unified Model Compiler)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

一个统一的多硬件平台深度学习模型编译框架，提供一套 API 支持将 ONNX 等深度学习模型编译到不同的 AI 加速芯片平台（昇腾、天数智芯、瑞芯微等）。

---

## 目录

- [特性](#特性)
- [支持的平台](#支持的平台)
- [快速开始](#快速开始)
- [安装指南](#安装指南)
- [使用文档](#使用文档)
  - [命令行工具](#命令行工具)
  - [Python API](#python-api)
  - [配置文件方式](#配置文件方式)
  - [REST API 服务](#rest-api-服务)
- [配置选项详解](#配置选项详解)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系方式](#联系方式)

---

## 特性

### 核心特性

- **统一 API 设计** - 一套简洁的接口支持多平台编译，无需学习各平台专属工具
- **多编译模式** - 支持命令行、Python API、配置文件、REST API 四种使用方式
- **类型安全** - 完整的类型注解和 Pydantic 数据验证
- **详细日志** - 可调节的日志级别，便于问题排查

### 编译特性

- **多精度支持** - FP32、FP16、INT8 量化
- **输入格式灵活** - 支持 NCHW/NHWC 格式转换
- **量化优化** - 支持 INT8 量化与校准数据集配置
- **预处理配置** - 支持 mean_values/std_values 归一化参数

### 服务特性

- **REST API** - 完整的 HTTP API 服务，支持远程编译
- **交互式文档** - 自动生成的 Swagger/OpenAPI 文档
- **Web 上传界面** - 友好的 Web UI 进行模型上传和编译

---

## 支持的平台

| 平台 | 厂商 | 类型 | 输出格式 | 主要芯片/版本 |
|------|------|------|----------|---------------|
| **Ascend** | 华为昇腾 | NPU | `.om` | Ascend310P1, Ascend910, Ascend310 |
| **Iluvatar** | 天数智芯 | GPU | `.engine` | MR 系列 (MR100, MR110) |
| **Rockchip** | 瑞芯微 | NPU | `.rknn` | RK3588, RK3568, RV1126 |

---

## 快速开始

### 30 秒快速体验

```bash
# 1. 安装
pip install -e .

# 2. 查看支持的平台
unified-compile list-platforms

# 3. 生成配置模板
unified-compile gen-template -p ascend -o config.yaml

# 4. 编译模型（以昇腾为例）
unified-compile compile \
  -p ascend \
  -m model.onnx \
  -o model.om \
  --soc-version Ascend310P1
```

---

## 安装指南

### 基础安装

```bash
# 克隆项目
git clone <repository-url>
cd LHI_ModelCompile

# 基础安装（包含核心依赖）
pip install -e .

# 完整安装（包含 API 服务依赖）
pip install -e ".[api]"
```

### 平台特定安装

根据不同目标平台，需要安装相应的 SDK：

#### 昇腾平台 (Ascend)

```bash
# 1. 安装 CANN Toolkit (需从华为官网下载)
# 下载地址：https://www.hiascend.com/developer/download/community/result?module=cann

# 2. 安装 Python 包
pip install -e ".[ascend]"

# 3. 验证安装
python -c "import ascendl; print('Ascend CANN OK')"
```

#### 天数智芯平台 (Iluvatar)

```bash
# 1. 安装 IXRT (需从天数智芯获取)

# 2. 安装 Python 包
pip install -e ".[iluvatar]"

# 3. 验证安装
python -c "import ixrt; print('Iluvatar IXRT OK')"
```

#### 瑞芯微平台 (Rockchip)

```bash
# 1. 安装 RKNN-Toolkit (需从瑞芯微获取)
# 下载地址：https://github.com/airockchip

# 2. 安装 Python 包
pip install -e ".[rockchip]"

# 3. 验证安装
python -c "from rknn.api import RKNN; print('RKNN OK')"
```

### 依赖要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.8 | 推荐 3.9+ |
| PyYAML | >= 6.0 | 配置文件解析 |
| FastAPI | >= 0.104.0 | API 服务（可选） |
| Uvicorn | >= 0.24.0 | API 服务器（可选） |
| Pydantic | >= 2.0.0 | 数据验证 |

---

## 使用文档

### 命令行工具

命令行工具提供 `unified-compile` 命令（安装后可直接使用）。

#### 查看帮助

```bash
unified-compile --help
```

#### 编译命令

**昇腾平台编译：**

```bash
unified-compile compile \
  --platform ascend \
  --model model.onnx \
  --output model.om \
  --input-shape "input:1,3,640,640" \
  --input-format NCHW \
  --precision fp16 \
  --soc-version Ascend310P1
```

**天数智芯平台编译：**

```bash
unified-compile compile \
  --platform iluvatar \
  --model model.onnx \
  --output model.engine \
  --input-shape "data:1,3,224,224" \
  --input-format NCHW \
  --precision fp32
```

**瑞芯微平台编译（带量化）：**

```bash
unified-compile compile \
  --platform rockchip \
  --model model.onnx \
  --output model.rknn \
  --input-shape "input:1,3,640,640" \
  --quantize \
  --dataset ./calib_dataset \
  --target-platform rk3588 \
  --mean-values "0.485,0.456,0.406" \
  --std-values "0.229,0.224,0.225"
```

#### 配置文件编译

```bash
# 从 YAML 配置文件编译
unified-compile compile-from-config config.yaml
```

#### 列出支持的平台

```bash
unified-compile list-platforms
```

输出示例：
```
支持的平台:
  - ascend
  - iluvatar
  - rockchip
```

#### 生成配置模板

```bash
# 生成昇腾配置模板
unified-compile gen-template --platform ascend --output ascend_config.yaml

# 生成瑞芯微配置模板
unified-compile gen-template --platform rockchip --output rknn_config.yaml
```

---

### Python API

#### 基础使用

```python
from unified_compiler import ModelCompileEngine

# 创建编译引擎
engine = ModelCompileEngine(verbose=True)

# 编译到昇腾平台
result = engine.compile(
    platform="ascend",
    model_path="model.onnx",
    output_path="model.om",
    input_shape={"input": [1, 3, 640, 640]},
    input_format="NCHW",
    precision="fp16",
    soc_version="Ascend310P1"
)

# 检查结果
if result.success:
    print(f"编译成功：{result.output_path}")
    print(f"编译耗时：{result.compile_time:.2f}秒")
else:
    print(f"编译失败：{result.error_message}")
```

#### 批量编译

```python
from unified_compiler import ModelCompileEngine, PlatformType

engine = ModelCompileEngine()

# 编译到多个平台
platforms = ["ascend", "iluvatar", "rockchip"]
results = {}

for platform in platforms:
    output_path = f"model_{platform}"
    results[platform] = engine.compile(
        platform=platform,
        model_path="model.onnx",
        output_path=output_path,
        input_shape={"input": [1, 3, 640, 640]}
    )

# 查看各平台编译结果
for platform, result in results.items():
    status = "成功" if result.success else "失败"
    print(f"{platform}: {status}")
```

#### 从配置文件编译

```python
from unified_compiler import ModelCompileEngine

engine = ModelCompileEngine()
result = engine.compile_from_config("config.yaml")

if result.success:
    print(f"输出：{result.output_path}")
```

#### 获取支持的平台

```python
from unified_compiler import ModelCompileEngine

engine = ModelCompileEngine()
platforms = engine.get_supported_platforms()
print(f"支持的平台：{platforms}")
```

---

### 配置文件方式

#### 配置文件结构

```yaml
# 基础配置
platform: ascend              # 目标平台
model_path: model.onnx        # 输入模型路径
output_path: model.om         # 输出模型路径

# 模型配置
framework: onnx               # 模型框架 (onnx/tensorflow/pytorch)
input_shape:                  # 输入形状
  input: [1, 3, 640, 640]     # 格式：name: [N, C, H, W]
input_format: NCHW            # 输入格式 (NCHW/NHWC)
precision: fp16               # 精度 (fp32/fp16/int8)

# 平台特定配置
platform_config:
  soc_version: Ascend310P1    # SoC 版本 (昇腾专用)
  framework: 5                # 框架类型 ID (昇腾专用)

# 量化配置 (可选)
do_quantization: false
dataset_path: ./calib_data

# 归一化参数 (可选，RKNN 常用)
mean_values: [0.485, 0.456, 0.406]
std_values: [0.229, 0.224, 0.225]

# 日志配置
verbose: true
log_dir: ./logs
```

#### 平台特定配置示例

**昇腾平台配置：**

```yaml
platform: ascend
model_path: yolov5.onnx
output_path: yolov5.om
input_shape:
  images: [1, 3, 640, 640]
precision: fp16
platform_config:
  soc_version: Ascend310P1
  framework: 5
```

**天数智芯配置：**

```yaml
platform: iluvatar
model_path: resnet50.onnx
output_path: resnet50.engine
input_shape:
  data: [1, 3, 224, 224]
precision: fp32
platform_config:
  model: MR
  libs: cudnn,cublas,ixinfer
```

**瑞芯微配置：**

```yaml
platform: rockchip
model_path: yolov8.onnx
output_path: yolov8.rknn
input_shape:
  input: [1, 3, 640, 640]
precision: fp16
platform_config:
  target_platform: rk3588
do_quantization: true
dataset_path: ./calib_dataset
mean_values: [0.0, 0.0, 0.0]
std_values: [1.0, 1.0, 1.0]
```

---

### REST API 服务

#### 启动服务

```bash
# 使用模块方式启动（推荐）
python -m unified_compiler.api.server --port 8080

# 指定监听地址
python -m unified_compiler.api.server --host 0.0.0.0 --port 8000

# 开发模式（自动重载）
python -m unified_compiler.api.server --reload
```

#### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/platforms` | GET | 获取支持的平台列表 |
| `/api/compile` | POST | 编译模型 |
| `/api/upload` | POST | 上传模型文件 |

#### API 文档

启动服务后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### 调用示例

```bash
# 健康检查
curl http://localhost:8000/api/health

# 获取支持的平台
curl http://localhost:8000/api/platforms

# 编译模型
curl -X POST http://localhost:8000/api/compile \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "ascend",
    "model_path": "model.onnx",
    "output_path": "model.om",
    "input_shape": {"input": [1, 3, 640, 640]},
    "platform_config": {"soc_version": "Ascend310P1"}
  }'
```

---

## 配置选项详解

### 通用配置参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `platform` | string | 是 | - | 目标平台：`ascend`, `iluvatar`, `rockchip` |
| `model_path` | string | 是 | - | 输入模型文件路径 |
| `output_path` | string | 是 | - | 输出模型文件路径 |
| `framework` | string | 否 | `onnx` | 模型框架类型 |
| `input_shape` | object | 否 | - | 输入张量形状 `{"name": [N,C,H,W]}` |
| `input_format` | string | 否 | `NCHW` | 输入数据格式：`NCHW` 或 `NHWC` |
| `precision` | string | 否 | `fp16` | 计算精度：`fp32`, `fp16`, `int8` |
| `verbose` | boolean | 否 | `true` | 是否输出详细日志 |

### 昇腾平台特有参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `soc_version` | string | SoC 版本 | `Ascend310P1`, `Ascend910`, `Ascend310` |
| `framework` | int | 框架类型 ID | `5` (ONNX) |

### 天数智芯平台特有参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `model` | string | GPU 型号 | `MR`, `MR100` |
| `libs` | string | 依赖库列表 | `cudnn,cublas,ixinfer` |

### 瑞芯微平台特有参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `target_platform` | string | 目标芯片型号 | `rk3588`, `rk3568`, `rv1126` |
| `mean_values` | array | 归一化均值 | `[0.485, 0.456, 0.406]` |
| `std_values` | array | 归一化标准差 | `[0.229, 0.224, 0.225]` |
| `do_quantization` | boolean | 是否启用量化 | `true`/`false` |
| `dataset_path` | string | 量化校准数据集路径 | `./calib_data` |

---

## 项目结构

```
LHI_ModelCompile/
├── unified_compiler/           # 包目录
│   ├── __init__.py            # 包入口，导出公共 API
│   ├── compiler_engine.py     # 编译引擎主类
│   ├── cli.py                 # 命令行工具入口
│   │
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   ├── base_compiler.py   # 基础编译器抽象类
│   │   └── compiler_registry.py # 编译器注册表
│   │
│   ├── platforms/             # 平台实现
│   │   ├── __init__.py
│   │   ├── ascend_compiler.py    # 昇腾编译器
│   │   ├── iluvatar_compiler.py  # 天数智芯编译器
│   │   └── rockchip_compiler.py  # 瑞芯微编译器
│   │
│   ├── utils/               # 工具模块
│   │   ├── __init__.py
│   │   ├── config_loader.py # 配置加载器
│   │   └── logger.py        # 日志工具
│   │
│   └── api/                 # REST API 服务
│       ├── __init__.py
│       ├── server.py        # 服务器启动脚本
│       ├── compiler_api.py  # 编译 API 端点
│       ├── schemas.py       # Pydantic 数据模型
│       └── device_manager.py # 设备管理
│
├── setup.py                 # setuptools 配置
├── ascend_test.py           # 昇腾平台测试
├── iluvatar_test.py         # 天数智芯平台测试
└── README.md                # 项目文档
```

---

## 开发指南

### 添加新平台支持

1. 在 `unified_compiler/platforms/` 创建新平台文件

```python
# new_platform_compiler.py
from unified_compiler.core.base_compiler import BaseCompiler, CompileResult

class NewPlatformCompiler(BaseCompiler):
    @property
    def platform_name(self) -> str:
        return "new_platform"

    def _do_compile(self) -> CompileResult:
        # 实现编译逻辑
        pass
```

2. 在 `compiler_registry.py` 注册新平台

```python
CompilerRegistry.register_compiler(
    PlatformType.NEW_PLATFORM,
    NewPlatformCompiler
)
```

### 本地开发安装

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

---

## 常见问题

### Q: 编译时提示找不到 SDK

**A:** 请确保已正确安装对应平台的 SDK：
- 昇腾：安装 CANN Toolkit
- 天数智芯：安装 IXRT
- 瑞芯微：安装 RKNN-Toolkit

### Q: 如何设置输入形状？

**A:** 使用 `--input-shape` 参数，格式为 `name:d1,d2,d3,d4`，例如：
```bash
--input-shape "input:1,3,640,640"
```

### Q: 量化校准数据集如何准备？

**A:** 校准数据集应包含代表实际输入的样本，通常为 `.npy` 格式或图像文件夹。

### Q: API 服务无法启动？

**A:** 检查端口是否被占用，或尝试使用其他端口：
```bash
python -m unified_compiler.api.server --port 8080
```

---

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 联系方式

- **Author**: Nick Xu
- **Email**: [your-email@example.com]
- **Project Link**: [https://github.com/yourusername/LHI_ModelCompile](https://github.com/yourusername/LHI_ModelCompile)

---

## 更新日志

### v1.0.0 (2026-03)
- 初始发布
- 支持昇腾、天数智芯、瑞芯微三个平台
- 提供命令行、Python API、配置文件、REST API 四种使用方式
- 支持 INT8 量化
- 添加完整的 API 文档
