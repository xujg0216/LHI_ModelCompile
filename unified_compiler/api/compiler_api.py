"""
@Descripttion: 模型编译 API 实现 - 支持文件上传模式
@File: compiler_api.py
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
import re
import uuid
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .. import ModelCompileEngine, PlatformType
from ..core.base_compiler import CompileResult, CompileStatus
from .schemas import (
    CompileRequest,
    CompileResponse,
    TaskStatus,
    PlatformInfo,
    DeviceInfo,
    HealthResponse,
    ListTasksResponse,
    CompileStatusEnum,
    UploadResponse,
    ProgressResponse,
    PlatformEnum,
    DeviceModelEnum,
    # 推送相关
    TargetDeviceResponse,
    TargetDeviceCreate,
    TargetDeviceUpdate,
    PushTaskResponse,
    PushTaskItemResponse,
    PushStatusEnum,
)


# 缓存目录配置
CACHE_DIR = Path("model_compile_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存保留时间（秒），默认 24 小时
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))

# 简单的任务存储（用于历史记录）
task_store: Dict[str, dict] = {}

# 推送任务存储
push_task_store: Dict[str, dict] = {}


def get_next_version(output_dir: Path, model_name: str, device_model: str) -> str:
    """
    获取下一个版本号
    
    扫描目录下已有文件，找到最大版本号并返回下一个版本
    文件名格式：{model_name}_v{version}.{ext}
    """
    if not output_dir.exists():
        return "v1"
    
    # 获取输出文件的扩展名（根据平台）
    ext_map = {
        "ASCEND_310P": ".om",
        "ASCEND_310B": ".om",
        "ILUVATAR_MR50": ".engine",
        "ILUVATAR_MR100": ".engine",
        "ROCKCHIP_RK3588": ".rknn",
        "ROCKCHIP_RK3568": ".rknn",
    }
    ext = ext_map.get(device_model, ".om")
    
    # 匹配版本号的正则表达式
    pattern = re.compile(rf"^{re.escape(model_name)}_v(\d+){re.escape(ext)}$")
    
    max_version = 0
    for file_path in output_dir.iterdir():
        if file_path.is_file():
            match = pattern.match(file_path.name)
            if match:
                version = int(match.group(1))
                if version > max_version:
                    max_version = version
    
    return f"v{max_version + 1}"


def build_output_path(output_root: str, task_name: str, device_model: str, 
                      model_name: str, version: str) -> str:
    """
    构建输出路径
    
    格式：{output_root}/{task_name}/{device_model}/{model_name}_{version}.{ext}
    例如：/runtime/task_A/Ascend_310P/yolo11s_v1.om
    """
    # 根据设备型号确定扩展名
    ext_map = {
        "ASCEND_310P": ".om",
        "ASCEND_310B": ".om",
        "ILUVATAR_MR50": ".engine",
        "ILUVATAR_MR100": ".engine",
        "ROCKCHIP_RK3588": ".rknn",
        "ROCKCHIP_RK3568": ".rknn",
    }
    ext = ext_map.get(device_model, ".om")
    
    # 构建完整路径
    output_dir = Path(output_root) / task_name / device_model
    output_filename = f"{model_name}_{version}{ext}"
    output_path = output_dir / output_filename
    
    return str(output_path)


def cleanup_expired_cache():
    """清理过期的缓存文件"""
    if not CACHE_DIR.exists():
        return

    current_time = datetime.now()
    cleaned_count = 0

    for task_dir in CACHE_DIR.iterdir():
        if not task_dir.is_dir():
            continue

        task_id = task_dir.name
        task = task_store.get(task_id)

        # 如果任务不存在或已完成超过 TTL 时间，则删除
        should_delete = False
        if task:
            created_at = task.get("created_at")
            if created_at:
                age = (current_time - created_at).total_seconds()
                if age > CACHE_TTL:
                    should_delete = True
        else:
            # 任务不在内存中，检查目录修改时间
            try:
                mtime = datetime.fromtimestamp(task_dir.stat().st_mtime)
                age = (current_time - mtime).total_seconds()
                if age > CACHE_TTL:
                    should_delete = True
            except Exception:
                should_delete = True

        if should_delete:
            try:
                shutil.rmtree(task_dir)
                cleaned_count += 1
                # 从任务存储中删除
                if task_id in task_store:
                    del task_store[task_id]
            except Exception as e:
                print(f"清理缓存失败 {task_id}: {e}")

    if cleaned_count > 0:
        print(f"清理了 {cleaned_count} 个过期缓存目录")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("模型编译 API 服务启动...")
    print(f"缓存目录：{CACHE_DIR}")
    print(f"缓存保留时间：{CACHE_TTL}秒")

    # 启动定时清理任务
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # 每小时清理一次
            try:
                cleanup_expired_cache()
            except Exception as e:
                print(f"定时清理失败：{e}")

    cleanup_task = asyncio.create_task(cleanup_loop())

    yield

    # 关闭时取消清理任务
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    print("模型编译 API 服务关闭...")


async def execute_compile_task(
    task_id: str,
    task_info: dict,
    compile_engine: ModelCompileEngine,
    platform: PlatformType,
    model_path: str,
    output_path: str,
    framework: str,
    input_shape: Optional[Dict[str, List[int]]],
    input_format: str,
    precision: str,
    platform_config: dict,
    do_quantization: bool,
    mean_values: Optional[List[float]],
    std_values: Optional[List[float]],
    # 推送相关参数
    push_device_ids: Optional[List[str]] = None,
    output_root: Optional[str] = None,
):
    """后台执行编译任务"""
    try:
        # 更新状态 - 开始编译
        task_info["status"] = CompileStatusEnum.RUNNING
        task_info["progress"] = 10
        task_info["message"] = "开始编译..."

        # 确保输出目录存在
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # 执行编译
        result = compile_engine.compile(
            platform=platform.value,
            model_path=model_path,
            output_path=output_path,
            framework=framework,
            input_shape=input_shape,
            input_format=input_format,
            precision=precision,
            platform_config=platform_config,
            do_quantization=do_quantization,
            mean_values=mean_values,
            std_values=std_values,
            verbose=False
        )

        # 更新进度和状态
        if result.success:
            task_info["progress"] = 100
            task_info["status"] = CompileStatusEnum.SUCCESS
            task_info["message"] = "编译成功"
            task_info["result"] = result
            task_info["output_path"] = result.output_path

            # ========== 编译成功后自动推送 ==========
            if push_device_ids and output_root:
                from .device_manager import get_device_manager
                from .push_service import get_push_service, PushTask

                device_manager = get_device_manager()
                push_service = get_push_service()

                # 获取设备列表
                devices = []
                for dev_id in push_device_ids:
                    device = device_manager.get_device(dev_id)
                    if device and device.enabled:
                        devices.append(device)
                    else:
                        print(f"设备 {dev_id} 未找到或未启用")

                if devices:
                    task_info["message"] = "编译成功，开始推送..."
                    task_info["push_status"] = "running"
                    print(f"开始推送到 {len(devices)} 台设备：{[d.name for d in devices]}")

                    # 创建并执行推送任务
                    push_task = push_service.create_push_task(
                        source_task_id=task_id,
                        devices=devices,
                        local_file=result.output_path,
                        output_path=output_path,
                        output_root=output_root
                    )

                    # 后台执行推送
                    asyncio.create_task(execute_push_task(push_task, task_info))
                else:
                    print(f"警告：没有可用的设备可推送，push_device_ids={push_device_ids}")
        else:
            task_info["progress"] = 0
            task_info["status"] = CompileStatusEnum.FAILED
            task_info["message"] = "编译失败"
            task_info["error_message"] = result.error_message or "未知错误"

    except Exception as e:
        task_info["progress"] = 0
        task_info["status"] = CompileStatusEnum.FAILED
        task_info["message"] = f"编译异常：{str(e)}"
        task_info["error_message"] = str(e)


async def execute_push_task(push_task, task_info: dict):
    """后台执行推送任务"""
    try:
        from .push_service import get_push_service
        push_service = get_push_service()

        # 执行推送
        await push_service.execute_push(push_task)

        # 更新任务信息
        task_info["push_status"] = push_task.status.value
        task_info["push_result"] = push_task.model_dump()

        if push_task.status == PushStatusEnum.SUCCESS and push_task.failed_count == 0:
            task_info["message"] = f"编译并推送成功（{push_task.success_count} 台设备）"
        elif push_task.success_count > 0:
            task_info["message"] = f"编译成功，部分推送成功（{push_task.success_count}/{push_task.total}）"
        else:
            task_info["message"] = f"编译成功，但推送失败（{push_task.failed_count} 台设备失败）"

    except Exception as e:
        task_info["push_status"] = "failed"
        task_info["message"] = f"编译成功，但推送异常：{str(e)}"


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    app = FastAPI(
        title="统一模型编译 API",
        description="支持多硬件平台（Ascend, MR100, RKNN）的统一模型编译服务",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 获取当前文件所在目录
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 挂载静态文件目录（提供 test_upload.html 等文件）
    app.mount("/static", StaticFiles(directory=current_dir), name="static")

    # 创建编译引擎实例
    compile_engine = ModelCompileEngine(verbose=False)

    @app.get("/", tags=["Root"])
    async def root():
        """根路径 - 返回上传页面"""
        return FileResponse(os.path.join(current_dir, "upload_v4.html"))

    @app.get("/upload_v4.html", tags=["Root"])
    async def get_test_page():
        """获取测试页面"""
        return FileResponse(os.path.join(current_dir, "upload_v4.html"))

    @app.get("/upload_v4.html", tags=["Root"])
    async def get_upload_v4_page():
        """获取上传页面 v4"""
        return FileResponse(os.path.join(current_dir, "upload_v4.html"))

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """健康检查"""
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            platforms=compile_engine.get_supported_platforms(),
            timestamp=datetime.now()
        )

    @app.get("/platforms", response_model=List[PlatformInfo], tags=["Platforms"])
    async def list_platforms():
        """获取支持的平台列表"""
        platforms = {
            "ASCEND": {
                "name": "华为昇腾",
                "value": "ASCEND",
                "supported": True,
                "description": "华为昇腾 NPU，支持 ATC 编译工具"
            },
            "ILUVATAR": {
                "name": "天数智芯 ILUVATAR",
                "value": "ILUVATAR",
                "supported": True,
                "description": "天数智芯 ILUVATAR NPU"
            },
            "ROCKCHIP": {
                "name": "瑞芯微 ROCKCHIP",
                "value": "ROCKCHIP",
                "supported": True,
                "description": "瑞芯微 NPU"
            }
        }

        supported = compile_engine.get_supported_platforms()
        result = []
        for name, info in platforms.items():
            info["supported"] = name in supported
            result.append(PlatformInfo(**info))
        return result

    @app.get("/devices", response_model=List[DeviceInfo], tags=["Devices"])
    async def list_devices():
        """获取支持的设备型号列表"""
        devices = [
            {"name": "昇腾 310P", "value": "ASCEND_310P", "platform": "ASCEND", "description": "华为昇腾 310P 推理卡"},
            {"name": "昇腾 310B", "value": "ASCEND_310B", "platform": "ASCEND", "description": "华为昇腾 310B 推理卡"},
            {"name": "MR50", "value": "ILUVATAR_MR50", "platform": "ILUVATAR", "description": "天数智芯 MR50 推理卡"},
            {"name": "MR100", "value": "ILUVATAR_MR100", "platform": "ILUVATAR", "description": "天数智芯 MR100 推理卡"},
            {"name": "RK3588", "value": "ROCKCHIP_RK3588", "platform": "ROCKCHIP", "description": "瑞芯微 RK3588 SoC"},
            {"name": "RK3568", "value": "ROCKCHIP_RK3568", "platform": "ROCKCHIP", "description": "瑞芯微 RK3568 SoC"},
        ]
        return [DeviceInfo(**d) for d in devices]

    @app.post("/upload", response_model=UploadResponse, tags=["Upload"])
    async def upload_and_compile(
        model_file: UploadFile = File(..., description="上传的模型文件 (.onnx)"),
        task_name: str = Form(..., description="任务名称，如 task_A"),
        model_name: str = Form(..., description="模型名称（不含后缀），如 yolo11s"),
        output_root: str = Form(..., description="输出根目录，如 /runtime"),
        platform: PlatformEnum = Form(..., description="目标平台"),
        device_model: DeviceModelEnum = Form(..., description="设备型号"),
        framework: str = Form(default="onnx", description="模型框架"),
        input_shape: Optional[str] = Form(default=None, description="输入形状 JSON 字符串"),
        input_format: str = Form(default="NCHW", description="输入格式"),
        precision: str = Form(default="fp16", description="精度模式"),
        platform_config: Optional[str] = Form(default=None, description="平台配置 JSON 字符串"),
        do_quantization: bool = Form(default=False, description="是否量化"),
        mean_values: Optional[str] = Form(default=None, description="均值"),
        std_values: Optional[str] = Form(default=None, description="标准差"),
        # 推送相关参数
        push_device_ids: Optional[str] = Form(default=None, description="推送目标设备 ID 列表（JSON 数组）"),
    ):
        """
        上传模型文件并启动编译任务

        支持手动指定：
        - task_name: 任务名称（如 task_A）
        - model_name: 模型名称不含后缀（如 yolo11s）
        - output_root: 输出根目录（如 /runtime）
        - device_model: 设备型号（如 Ascend_310P）
        - push_device_ids: 推送目标设备 ID 列表（如 ['dev_001', 'dev_002']）

        输出路径格式：{output_root}/{task_name}/{device_model}/{model_name}_v{version}.{ext}
        例如：/runtime/task_A/Ascend_310P/yolo11s_v1.om
        """
        import json

        # 1. 生成任务 ID
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now()

        # 2. 创建任务目录（用于保存上传的原始文件）
        task_dir = CACHE_DIR / task_id
        input_dir = task_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        # 3. 保存上传文件
        model_filename = model_file.filename or "model.onnx"
        input_path = input_dir / model_filename

        try:
            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(model_file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件保存失败：{str(e)}"
            )

        # 4. 解析 JSON 参数
        try:
            input_shape_dict = json.loads(input_shape) if input_shape else None
        except json.JSONDecodeError:
            input_shape_dict = None

        try:
            platform_config_dict = json.loads(platform_config) if platform_config else {}
        except json.JSONDecodeError:
            platform_config_dict = {}

        try:
            mean_values_list = json.loads(mean_values) if mean_values else None
        except json.JSONDecodeError:
            mean_values_list = None

        try:
            std_values_list = json.loads(std_values) if std_values else None
        except json.JSONDecodeError:
            std_values_list = None

        # 5. 解析推送设备 ID 列表
        push_device_id_list = None
        if push_device_ids:
            try:
                push_device_id_list = json.loads(push_device_ids)
            except json.JSONDecodeError:
                push_device_id_list = None

        # 6. 构建输出路径（带版本迭代）
        output_dir = Path(output_root) / task_name / device_model.value
        version = get_next_version(output_dir, model_name, device_model.value)
        output_path = build_output_path(output_root, task_name, device_model.value,
                                        model_name, version)

        # 7. 创建任务记录（保存推送配置）
        task_store[task_id] = {
            "task_id": task_id,
            "task_name": task_name,
            "model_name": model_name,
            "device_model": device_model.value,
            "status": CompileStatusEnum.PENDING,
            "progress": 0,
            "message": "文件上传成功，准备编译",
            "input_path": str(input_path),
            "output_path": output_path,
            "output_root": output_root,
            "platform": platform.value,
            "push_device_ids": push_device_id_list,
            "push_status": None,
            "push_result": None,
            "created_at": created_at,
            "result": None,
            "error_message": None
        }

        # 8. 后台执行编译
        asyncio.create_task(
            execute_compile_task(
                task_id=task_id,
                task_info=task_store[task_id],
                compile_engine=compile_engine,
                platform=platform,
                model_path=str(input_path),
                output_path=output_path,
                framework=framework,
                input_shape=input_shape_dict,
                input_format=input_format,
                precision=precision,
                platform_config=platform_config_dict,
                do_quantization=do_quantization,
                mean_values=mean_values_list,
                std_values=std_values_list,
                # 推送相关参数
                push_device_ids=push_device_id_list,
                output_root=output_root,
            )
        )

        return UploadResponse(
            task_id=task_id,
            task_name=task_name,
            model_name=model_name,
            device_model=device_model.value,
            output_path=output_path,
            status="pending",
            message="文件上传成功，开始编译",
            created_at=created_at
        )

    @app.get("/tasks/{task_id}/progress", response_model=ProgressResponse, tags=["Tasks"])
    async def get_task_progress(task_id: str):
        """
        获取任务进度

        返回当前编译进度和状态，可用于轮询查询。
        """
        task = task_store.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在：{task_id}"
            )

        return ProgressResponse(
            task_id=task_id,
            status=task["status"],
            progress=task["progress"],
            message=task.get("message", ""),
            output_path=task.get("output_path") if task["status"] == CompileStatusEnum.SUCCESS else None,
            error_message=task.get("error_message")
        )

    @app.get("/download/{task_id}", tags=["Download"])
    async def download_compiled_model(task_id: str):
        """
        下载编译后的模型文件

        仅在编译成功后可用。
        """
        task = task_store.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在：{task_id}"
            )

        if task["status"] != CompileStatusEnum.SUCCESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"任务未完成，当前状态：{task['status'].value}"
            )

        # 获取输出文件路径
        output_path = task.get("output_path")
        if not output_path or not Path(output_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="编译文件不存在"
            )

        # 返回文件
        filename = Path(output_path).name
        return FileResponse(
            path=output_path,
            filename=filename,
            media_type="application/octet-stream"
        )

    @app.post("/compile", response_model=CompileResponse, tags=["Compile"])
    async def compile_model(request: CompileRequest):
        """
        编译模型到指定平台（同步等待模式）

        请求会等待编译完成后返回结果。
        适用于编译时间较短的场景。
        """
        # 验证模型文件存在
        if not os.path.exists(request.model_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"模型文件不存在：{request.model_path}"
            )

        # 检查平台是否支持
        if not compile_engine.is_platform_supported(request.platform.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的平台：{request.platform.value}"
            )

        # 生成任务 ID
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now()

        try:
            # 执行编译（同步等待）
            result = compile_engine.compile(
                platform=request.platform.value,
                model_path=request.model_path,
                output_path=request.output_path,
                framework=request.framework,
                input_shape=request.input_shape,
                input_format=request.input_format,
                precision=request.precision,
                platform_config=request.platform_config,
                do_quantization=request.do_quantization,
                dataset_path=request.dataset_path,
                mean_values=request.mean_values,
                std_values=request.std_values,
                verbose=False
            )

            updated_at = datetime.now()

            # 构建响应
            if result.success:
                response = CompileResponse(
                    task_id=task_id,
                    status=CompileStatusEnum.SUCCESS,
                    message="编译成功",
                    output_path=result.output_path,
                    compile_time=result.compile_time,
                    model_info=result.model_info,
                    warnings=result.warnings or [],
                    created_at=created_at,
                    updated_at=updated_at
                )
            else:
                response = CompileResponse(
                    task_id=task_id,
                    status=CompileStatusEnum.FAILED,
                    message=result.error_message or "编译失败",
                    error_message=result.error_message,
                    created_at=created_at,
                    updated_at=updated_at
                )

            # 保存到历史记录
            task_store[task_id] = {
                "task_id": task_id,
                "request": request.model_dump(),
                "result": response,
                "created_at": created_at
            }

            return response

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"编译异常：{str(e)}"
            )

    @app.get("/tasks", response_model=ListTasksResponse, tags=["Tasks"])
    async def list_tasks(
        limit: int = 50,
        offset: int = 0
    ):
        """获取历史任务列表"""
        all_tasks = list(task_store.values())
        all_tasks = sorted(all_tasks, key=lambda x: x["created_at"], reverse=True)

        # 分页
        total = len(all_tasks)
        tasks = all_tasks[offset:offset + limit]

        return ListTasksResponse(
            total=total,
            tasks=[
                TaskStatus(
                    task_id=t["task_id"],
                    status=t["result"].status if t.get("result") else CompileStatusEnum.PENDING,
                    progress=100 if t.get("result") and t["result"].status != CompileStatusEnum.FAILED else 100,
                    message=t.get("message", ""),
                    created_at=t["created_at"],
                    updated_at=t["result"].updated_at if t.get("result") else t["created_at"],
                    result=t.get("result")
                )
                for t in tasks
            ]
        )

    @app.get("/tasks/{task_id}", response_model=CompileResponse, tags=["Tasks"])
    async def get_task_result(task_id: str):
        """获取历史任务结果"""
        task = task_store.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在：{task_id}"
            )
        return task.get("result")

    @app.delete("/tasks/{task_id}", tags=["Tasks"])
    async def delete_task(task_id: str):
        """删除历史任务记录"""
        if task_id not in task_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在：{task_id}"
            )

        del task_store[task_id]
        return {"message": f"任务 {task_id} 已删除"}

    @app.post("/cache/cleanup", tags=["Cache"])
    async def cleanup_cache():
        """
        手动清理过期缓存

        清理超过保留时间（默认 24 小时）的缓存文件。
        """
        cleanup_expired_cache()
        return {"message": "缓存清理完成"}

    @app.get("/cache/stats", tags=["Cache"])
    async def get_cache_stats():
        """
        获取缓存统计信息
        """
        if not CACHE_DIR.exists():
            return {"cache_dir": str(CACHE_DIR), "task_count": 0, "total_size_bytes": 0}

        task_count = 0
        total_size = 0

        for task_dir in CACHE_DIR.iterdir():
            if task_dir.is_dir():
                task_count += 1
                try:
                    for root, dirs, files in os.walk(task_dir):
                        for f in files:
                            fp = Path(root) / f
                            if fp.exists():
                                total_size += fp.stat().st_size
                except Exception:
                    pass

        return {
            "cache_dir": str(CACHE_DIR),
            "task_count": task_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2)
        }

    @app.delete("/cache/{task_id}", tags=["Cache"])
    async def delete_task_cache(task_id: str):
        """
        删除指定任务的缓存文件
        """
        task_dir = CACHE_DIR / task_id
        if not task_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"缓存目录不存在：{task_id}"
            )

        try:
            shutil.rmtree(task_dir)
            # 同时从任务存储中删除
            if task_id in task_store:
                del task_store[task_id]
            return {"message": f"任务 {task_id} 的缓存已删除"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除失败：{str(e)}"
            )

    # ========== 推送功能相关 API ==========

    @app.get("/push-devices", response_model=List[TargetDeviceResponse], tags=["Push"])
    async def list_push_devices(enabled_only: bool = False):
        """获取可推送的目标设备列表"""
        from .device_manager import get_device_manager
        device_manager = get_device_manager()
        devices = device_manager.list_devices(enabled_only=enabled_only)
        return devices

    @app.post("/push-devices", response_model=TargetDeviceResponse, tags=["Push"])
    async def create_push_device(device: TargetDeviceCreate):
        """添加推送目标设备"""
        from .device_manager import get_device_manager
        device_manager = get_device_manager()

        created_device = device_manager.create_device(
            name=device.name,
            ip_address=device.ip_address,
            port=device.port,
            username=device.username,
            password=device.password,
            target_path=device.target_path,
            description=device.description,
            enabled=device.enabled
        )
        return created_device

    @app.put("/push-devices/{device_id}", response_model=TargetDeviceResponse, tags=["Push"])
    async def update_push_device(device_id: str, device_update: TargetDeviceUpdate):
        """更新推送目标设备"""
        from .device_manager import get_device_manager
        device_manager = get_device_manager()

        update_data = device_update.model_dump(exclude_unset=True)
        updated_device = device_manager.update_device(device_id, **update_data)

        if not updated_device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"设备不存在：{device_id}"
            )
        return updated_device

    @app.delete("/push-devices/{device_id}", tags=["Push"])
    async def delete_push_device(device_id: str):
        """删除推送目标设备"""
        from .device_manager import get_device_manager
        device_manager = get_device_manager()

        if not device_manager.delete_device(device_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"设备不存在：{device_id}"
            )
        return {"message": f"设备 {device_id} 已删除"}

    @app.post("/push-devices/{device_id}/test", tags=["Push"])
    async def test_push_device(device_id: str):
        """测试设备连接"""
        from .device_manager import get_device_manager
        device_manager = get_device_manager()

        result = device_manager.test_connection(device_id)
        if result["success"]:
            return {"message": "连接成功", "detail": result}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )

    @app.get("/tasks/{task_id}/push-status", response_model=PushTaskResponse, tags=["Push"])
    async def get_task_push_status(task_id: str):
        """获取任务的推送状态"""
        from datetime import datetime

        task = task_store.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在：{task_id}"
            )

        push_result = task.get("push_result")
        if not push_result:
            # 返回空响应
            return PushTaskResponse(
                push_task_id="",
                source_task_id=task_id,
                status=PushStatusEnum.PENDING,
                total=0,
                success_count=0,
                failed_count=0,
                items=[],
                created_at=datetime.now().isoformat(),
                updated_at=None,
                completed_at=None
            )

        return PushTaskResponse(**push_result)

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """全局异常处理"""
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc)
            }
        )

    return app


# 创建 app 实例
app = create_app()


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """启动 API 服务器"""
    uvicorn.run(
        "unified_compiler.api.compiler_api:app",
        host=host,
        port=port,
        reload=reload
    )


if __name__ == "__main__":
    start_server()
