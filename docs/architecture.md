# 统一模型编译框架 - 架构图

## 系统整体架构

```mermaid
flowchart TB
    subgraph Users["用户层"]
        CLI[命令行工具<br/>unified-compile]
        Python[Python API]
        Config[配置文件]
        Web[Web UI]
    end

    subgraph API["API 服务层"]
        FastAPI[FastAPI 服务器]
        CompileAPI[编译 API 端点]
        DeviceAPI[设备管理 API]
        PushAPI[推送服务 API]
    end

    subgraph Core["核心层"]
        Engine[ModelCompileEngine<br/>编译引擎]
        Registry[CompilerRegistry<br/>编译器注册表]
        BaseCompiler[BaseCompiler<br/>基础编译器类]
    end

    subgraph Platforms["平台层"]
        Ascend[AscendCompiler<br/>昇腾编译器]
        Iluvatar[IluvatarCompiler<br/>天数智芯编译器]
        Rockchip[RockchipCompiler<br/>瑞芯微编译器]
    end

    subgraph Services["服务层"]
        DeviceMgr[DeviceManager<br/>设备管理器]
        PushSvc[PushService<br/>推送服务]
    end

    subgraph Utils["工具层"]
        ConfigLoader[ConfigLoader<br/>配置加载器]
        Logger[Logger<br/>日志工具]
    end

    Users --> API
    CLI --> Engine
    Python --> Engine
    Config --> ConfigLoader
    ConfigLoader --> Engine

    API --> CompileAPI
    API --> DeviceAPI
    API --> PushAPI

    CompileAPI --> Engine
    DeviceAPI --> DeviceMgr
    PushAPI --> PushSvc

    Engine --> Registry
    Registry --> BaseCompiler
    BaseCompiler --> Ascend
    BaseCompiler --> Iluvatar
    BaseCompiler --> Rockchip

    PushSvc --> DeviceMgr

    Engine --> ConfigLoader
    Engine --> Logger
```

## 编译请求处理流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant CLI as 命令行/API
    participant Engine as ModelCompileEngine
    participant Registry as CompilerRegistry
    participant Compiler as 平台编译器
    participant SDK as 平台 SDK

    User->>CLI: 编译请求
    CLI->>Engine: compile(platform, model_path, ...)
    Engine->>Engine: 构建 CompileConfig
    Engine->>Registry: get_compiler(platform, config)
    Registry-->>Engine: 返回对应平台编译器

    Engine->>Compiler: compile()
    activate Compiler

    Compiler->>Compiler: _pre_compile_check()
    Compiler->>Compiler: _do_compile()

    alt Ascend 平台
        Compiler->>SDK: ATC 工具编译
        SDK-->>Compiler: 生成.om 文件
    else Iluvatar 平台
        Compiler->>SDK: IXRT 编译
        SDK-->>Compiler: 生成.engine 文件
    else Rockchip 平台
        Compiler->>SDK: RKNN 编译
        SDK-->>Compiler: 生成.rknn 文件
    end

    Compiler->>Compiler: _post_compile_process()
    Compiler-->>Engine: CompileResult

    deactivate Compiler

    Engine->>Engine: 记录编译历史
    Engine-->>CLI: 返回编译结果
    CLI-->>User: 显示结果
```

## Web UI 编译 + 推送流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Web as Web UI
    participant API as API 服务器
    participant Engine as 编译引擎
    participant DeviceMgr as 设备管理器
    participant PushSvc as 推送服务
    participant SSH as 目标设备

    User->>Web: 上传模型文件 + 配置
    Web->>API: POST /upload (含 push_device_ids)

    API->>API: 创建任务记录
    API->>Engine: 异步执行编译

    loop 编译过程
        Engine->>Engine: 执行平台编译
        Engine-->>API: 更新进度状态
    end

    alt 编译成功
        API->>API: 检查 push_device_ids
        API->>DeviceMgr: 获取目标设备列表

        loop 每个设备
            DeviceMgr-->>API: 返回设备配置
        end

        API->>PushSvc: create_push_task()
        API->>PushSvc: execute_push()

        par 并行推送到所有设备
            loop 每个设备
                PushSvc->>SSH: SSH 连接
                PushSvc->>SSH: 创建远程目录
                PushSvc->>SSH: SFTP 上传文件
                PushSvc->>SSH: 验证文件
                SSH-->>PushSvc: 推送结果
            end
        end

        PushSvc-->>API: 推送任务完成
        API-->>Web: 推送状态更新
        Web-->>User: 显示最终结果
    else 编译失败
        API-->>Web: 编译失败
        Web-->>User: 显示错误信息
    end
```

## 设备管理数据流

```mermaid
flowchart LR
    subgraph DeviceOps["设备操作"]
        Create[创建设备]
        Read[查询设备]
        Update[更新设备]
        Delete[删除设备]
        Test[测试连接]
    end

    subgraph DeviceMgr["DeviceManager"]
        DM[设备管理逻辑]
        Cache[内存缓存<br/>devices dict]
    end

    subgraph Storage["持久化存储"]
        JSON[devices.json<br/>~/.unified_compiler/]
    end

    subgraph API["API 端点"]
        GetDev[GET /push-devices]
        PostDev[POST /push-devices]
        PutDev[PUT /push-devices/{id}]
        DelDev[DELETE /push-devices/{id}]
        TestDev[POST /push-devices/{id}/test]
    end

    Create --> DM
    Read --> DM
    Update --> DM
    Delete --> DM
    Test --> DM

    GetDev --> DM
    PostDev --> DM
    PutDev --> DM
    DelDev --> DM
    TestDev --> DM

    DM <--> Cache
    Cache <--> JSON
```

## 推送服务架构

```mermaid
flowchart TB
    subgraph PushAPI["推送 API"]
        CreateTask[创建推送任务]
        QueryStatus[查询推送状态]
    end

    subgraph PushService["PushService"]
        Tasks[任务队列<br/>tasks dict]
        ExecPush[execute_push]
        PushDevice[_push_to_device]
        Mkdir[_mkdir_recursive]
    end

    subgraph TaskItems["任务项"]
        Item1["PushTaskItem 1<br/>设备 A"]
        Item2["PushTaskItem 2<br/>设备 B"]
        Item3["PushTaskItem 3<br/>设备 C"]
    end

    subgraph AsyncSSH["asyncssh"]
        Connect[SSH 连接]
        SFTP[SFTP 客户端]
        Upload[文件上传]
        Verify[文件验证]
    end

    subgraph Targets["目标设备"]
        DevA["设备 A<br/>192.168.1.100"]
        DevB["设备 B<br/>192.168.1.101"]
        DevC["设备 C<br/>192.168.1.102"]
    end

    CreateTask --> PushService
    QueryStatus --> Tasks

    ExecPush --> Item1
    ExecPush --> Item2
    ExecPush --> Item3

    Item1 --> PushDevice
    Item2 --> PushDevice
    Item3 --> PushDevice

    PushDevice --> Connect
    Connect --> SFTP
    SFTP --> Mkdir
    Mkdir --> Upload
    Upload --> Verify

    PushDevice --> DevA
    PushDevice --> DevB
    PushDevice --> DevC
```

## 核心类关系图

```mermaid
classDiagram
    class ModelCompileEngine {
        -verbose: bool
        -logger: Logger
        -history: list
        +compile() CompileResult
        +compile_from_config() CompileResult
        +get_supported_platforms() list
        +save_config_template()
    }

    class CompileConfig {
        +platform: PlatformType
        +model_path: str
        +output_path: str
        +framework: str
        +input_shape: dict
        +input_format: str
        +precision: str
        +platform_config: dict
        +do_quantization: bool
    }

    class CompileResult {
        +status: CompileStatus
        +output_path: str
        +error_message: str
        +compile_time: float
        +success: bool
        +to_dict() dict
    }

    class BaseCompiler {
        <<abstract>>
        #config: CompileConfig
        #_result: CompileResult
        +compile() CompileResult
        #_do_compile() CompileResult*
        #_pre_compile_check()
        #_post_compile_process()
    }

    class AscendCompiler {
        +platform_name: str
        -_do_compile() CompileResult
    }

    class IluvatarCompiler {
        +platform_name: str
        -_do_compile() CompileResult
    }

    class RockchipCompiler {
        +platform_name: str
        -_do_compile() CompileResult
    }

    class CompilerRegistry {
        +register_compiler()
        +get_compiler()
        +get_all_platforms()
    }

    class DeviceManager {
        -config_path: Path
        -devices: dict
        +list_devices() list
        +get_device() TargetDevice
        +create_device() TargetDevice
        +update_device() TargetDevice
        +delete_device() bool
        +test_connection() dict
    }

    class TargetDevice {
        +id: str
        +name: str
        +ip_address: str
        +port: int
        +username: str
        +password: str
        +target_path: str
        +enabled: bool
    }

    class PushService {
        -tasks: dict
        +create_push_task() PushTask
        +execute_push() PushTask
        -_push_to_device()
        -_mkdir_recursive()
    }

    ModelCompileEngine --> CompileConfig
    ModelCompileEngine --> CompileResult
    ModelCompileEngine --> CompilerRegistry
    BaseCompiler <|-- AscendCompiler
    BaseCompiler <|-- IluvatarCompiler
    BaseCompiler <|-- RockchipCompiler
    CompilerRegistry --> BaseCompiler
    ModelCompileEngine --> CompilerRegistry
    DeviceManager --> TargetDevice
    PushService --> TargetDevice
```

## 配置文件结构

```mermaid
flowchart LR
    subgraph ConfigFile["config.yaml"]
        Platform[platform: ascend]
        ModelPath[model_path: model.onnx]
        OutputPath[output_path: model.om]
        Framework[framework: onnx]
        InputShape[input_shape]
        Precision[precision: fp16]
        PlatformConfig[platform_config]
        Quantize[do_quantization: false]
        MeanStd[mean_values/std_values]
    end

    subgraph Loader["ConfigLoader"]
        LoadYAML[load_yaml]
        ParseConfig[parse_compile_config]
        BuildConfig[build CompileConfig]
    end

    subgraph Engine["编译引擎"]
        Validate[验证配置]
        Compile[执行编译]
    end

    ConfigFile --> LoadYAML
    LoadYAML --> ParseConfig
    ParseConfig --> BuildConfig
    BuildConfig --> Validate
    Validate --> Compile
```

## 数据模型枚举

```mermaid
flowchart LR
    subgraph PlatformType["PlatformType 枚举"]
        ASCEND["ASCEND<br/>'ascend'"]
        ILUVATAR["ILUVATAR<br/>'iluvatar'"]
        ROCKCHIP["ROCKCHIP<br/>'rockchip'"]
        CUSTOM["CUSTOM<br/>'custom'"]
    end

    subgraph CompileStatus["CompileStatus 枚举"]
        PENDING["PENDING<br/>等待中"]
        RUNNING["RUNNING<br/>运行中"]
        SUCCESS["SUCCESS<br/>成功"]
        FAILED["FAILED<br/>失败"]
    end

    subgraph PushStatus["PushStatusEnum 枚举"]
        PUSH_PENDING["pending<br/>等待推送"]
        PUSH_RUNNING["running<br/>推送中"]
        PUSH_SUCCESS["success<br/>推送成功"]
        PUSH_FAILED["failed<br/>推送失败"]
    end

    subgraph DeviceModel["设备型号"]
        Ascend310P["Ascend_310P"]
        Ascend310B["Ascend_310B"]
        IluvatarMR50["Iluvatar_MR50"]
        IluvatarMR100["Iluvatar_MR100"]
        RK3588["Rockchip_RK3588"]
        RK3568["Rockchip_RK3568"]
    end
```

## API 端点总览

```mermaid
flowchart TB
    subgraph Root["根路径"]
        RootPath["/ → 上传页面"]
        UploadHTML["/upload_v4.html → 上传页面"]
    end

    subgraph Health["健康检查"]
        HealthEP["/health"]
    end

    subgraph Platforms["平台信息"]
        PlatformsEP["/platforms"]
        DevicesEP["/devices"]
    end

    subgraph Compile["编译相关"]
        UploadEP["/upload POST"]
        CompileEP["/compile POST"]
        TasksEP["/tasks GET"]
        TaskEP["/tasks/{id} GET"]
        TaskDel["/tasks/{id} DELETE"]
        ProgressEP["/tasks/{id}/progress GET"]
        DownloadEP["/download/{id} GET"]
    end

    subgraph Push["推送相关"]
        PushDevGet["/push-devices GET"]
        PushDevPost["/push-devices POST"]
        PushDevPut["/push-devices/{id} PUT"]
        PushDevDel["/push-devices/{id} DELETE"]
        PushDevTest["/push-devices/{id}/test POST"]
        PushStatus["/tasks/{id}/push-status GET"]
    end

    subgraph Cache["缓存管理"]
        CacheCleanup["/cache/cleanup POST"]
        CacheStats["/cache/stats GET"]
        CacheDel["/cache/{id} DELETE"]
    end

    Root --> RootPath
    Root --> UploadHTML
    Root --> HealthEP
    Root --> PlatformsEP
    Root --> DevicesEP
    Root --> Compile
    Root --> Push
    Root --> Cache
```

## 目录结构

```mermaid
flowchart TB
    subgraph Root["LHI_ModelCompile"]
        subgraph Pkg["unified_compiler/"]
            subgraph API["api/"]
                A1[__init__.py]
                A2[server.py]
                A3[compiler_api.py]
                A4[device_manager.py]
                A5[push_service.py]
                A6[schemas.py]
                A7[upload_v4.html]
            end

            subgraph Core["core/"]
                C1[base_compiler.py]
                C2[compiler_registry.py]
            end

            subgraph Platforms["platforms/"]
                P1[ascend_compiler.py]
                P2[iluvatar_compiler.py]
                P3[rockchip_compiler.py]
            end

            subgraph Utils["utils/"]
                U1[config_loader.py]
                U2[logger.py]
            end

            E1[__init__.py]
            E2[compiler_engine.py]
            E3[cli.py]
        end

        S1[setup.py]
        T1[ascend_test.py]
        T2[iluvatar_test.py]
        R1[README.md]
    end

    Pkg --> API
    Pkg --> Core
    Pkg --> Platforms
    Pkg --> Utils
```

## 依赖关系图

```mermaid
graph LR
    subgraph Core["核心依赖"]
        PyYAML[PyYAML>=6.0]
        FastAPI[FastAPI>=0.104.0]
        Uvicorn[Uvicorn>=0.24.0]
        Pydantic[Pydantic>=2.0.0]
    end

    subgraph Optional["可选依赖"]
        AscendDep[昇腾 CANN SDK]
        IluvatarDep[ixrt]
        RockchipDep[rknn-toolkit]
        AsyncSSH[asyncssh]
    end

    subgraph Features["功能模块"]
        CLI[命令行工具]
        API[REST API]
        WebUI[Web UI]
        Push[SFTP 推送]
    end

    Core --> CLI
    Core --> API
    API --> WebUI
    API --> Push

    AscendDep -.-> CLI
    IluvatarDep -.-> CLI
    RockchipDep -.-> CLI
    AsyncSSH -.-> Push
```
