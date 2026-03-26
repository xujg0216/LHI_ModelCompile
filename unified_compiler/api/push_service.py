"""
SFTP 推送服务
将编译后的模型文件推送到局域网目标设备
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from .device_manager import TargetDevice


class PushStatusEnum(str, Enum):
    """推送状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class PushTaskItem:
    """单个设备的推送任务"""

    def __init__(
        self,
        device: TargetDevice,
        local_file: str,
        remote_file: str
    ):
        self.device = device
        self.local_file = local_file
        self.remote_file = remote_file
        self.status = PushStatusEnum.PENDING
        self.progress = 0
        self.message = "等待中..."
        self.error_message: Optional[str] = None
        self.pushed_at: Optional[datetime] = None
        self.transfer_time: Optional[float] = None
        self.file_size: Optional[int] = None

    def model_dump(self) -> Dict:
        """转换为字典"""
        return {
            "device_id": self.device.id,
            "device_name": self.device.name,
            "device_ip": self.device.ip_address,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "error_message": self.error_message,
            "local_file": self.local_file,
            "remote_file": self.remote_file,
            "pushed_at": self.pushed_at.isoformat() if self.pushed_at else None,
            "transfer_time": self.transfer_time,
            "file_size": self.file_size
        }


class PushTask:
    """推送任务"""

    def __init__(self, push_task_id: str, source_task_id: str):
        self.push_task_id = push_task_id
        self.source_task_id = source_task_id
        self.status = PushStatusEnum.PENDING
        self.items: List[PushTaskItem] = []
        self.created_at = datetime.now()
        self.updated_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def success_count(self) -> int:
        return sum(1 for item in self.items if item.status == PushStatusEnum.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == PushStatusEnum.FAILED)

    def model_dump(self) -> Dict:
        """转换为字典"""
        return {
            "push_task_id": self.push_task_id,
            "source_task_id": self.source_task_id,
            "status": self.status.value,
            "total": self.total,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "items": [item.model_dump() for item in self.items],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PushService:
    """推送服务"""

    def __init__(self):
        self.tasks: Dict[str, PushTask] = {}

    def create_push_task(
        self,
        source_task_id: str,
        devices: List[TargetDevice],
        local_file: str,
        output_path: str,
        output_root: str
    ) -> PushTask:
        """
        创建推送任务

        Args:
            source_task_id: 源编译任务 ID
            devices: 目标设备列表
            local_file: 本地文件路径
            output_path: 输出文件完整路径
            output_root: 输出根目录（用于计算相对路径）

        Returns:
            推送任务
        """
        import uuid
        push_task_id = f"push_{uuid.uuid4().hex[:12]}"
        push_task = PushTask(push_task_id, source_task_id)

        # 计算相对路径（去掉 output_root 前缀）
        # 例如：/runtime/task_A/Ascend_310P/yolo11s_v1.om
        # 相对路径：task_A/Ascend_310P/yolo11s_v1.om
        local_path = Path(local_file)
        output_root_path = Path(output_root)

        try:
            relative_path = local_path.relative_to(output_root_path)
        except ValueError:
            # 如果不在 output_root 下，使用文件名
            relative_path = Path(local_path.name)

        # 为每个设备创建推送项
        for device in devices:
            # 远程文件路径 = device.target_path + relative_path
            remote_file = str(Path(device.target_path) / relative_path)

            item = PushTaskItem(
                device=device,
                local_file=str(local_file),
                remote_file=remote_file
            )
            push_task.items.append(item)

        self.tasks[push_task_id] = push_task
        return push_task

    async def execute_push(self, push_task: PushTask) -> PushTask:
        """
        执行推送任务

        Args:
            push_task: 推送任务

        Returns:
            推送任务（更新后）
        """
        print(f"[推送] 开始执行推送任务 {push_task.push_task_id}，共 {push_task.total} 台设备")
        push_task.status = PushStatusEnum.RUNNING
        push_task.updated_at = datetime.now()

        # 并行推送所有设备
        tasks = [self._push_to_device(item) for item in push_task.items]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"[推送] 推送过程中发生异常：{e}")

        # 更新整体状态
        if push_task.failed_count == 0:
            push_task.status = PushStatusEnum.SUCCESS
            print(f"[推送] 推送成功，共 {push_task.success_count} 台设备")
        elif push_task.success_count > 0:
            push_task.status = PushStatusEnum.SUCCESS  # 部分成功也算成功
            print(f"[推送] 部分成功，{push_task.success_count}/{push_task.total} 台设备成功")
        else:
            push_task.status = PushStatusEnum.FAILED
            print(f"[推送] 推送失败，{push_task.failed_count}/{push_task.total} 台设备失败")

        push_task.completed_at = datetime.now()
        push_task.updated_at = datetime.now()

        return push_task

    async def _push_to_device(self, item: PushTaskItem) -> None:
        """
        推送文件到单个设备

        Args:
            item: 推送项
        """
        device = item.device
        print(f"[推送] 开始推送到设备：{device.name} ({device.ip_address})")
        item.status = PushStatusEnum.RUNNING
        item.message = "正在连接..."
        item.progress = 10

        conn = None
        try:
            import asyncssh

            # 连接 SSH
            item.message = f"连接到 {device.ip_address}..."
            print(f"[推送] 正在连接到 {device.ip_address}:{device.port}...")
            conn = await asyncssh.connect(
                host=device.ip_address,
                port=device.port,
                username=device.username,
                password=device.password,
                known_hosts=None  # 不验证主机密钥
            )

            item.progress = 30
            item.message = "连接成功，验证目标路径..."
            print(f"[推送] 连接成功，开始验证目标路径")

            sftp = await conn.start_sftp_client()

            # 先检查 target_path 是否存在（这是用户的基础目录）
            try:
                attrs = await sftp.stat(device.target_path)
                print(f"[推送] target_path 属性：type={attrs.type}, 完整 attrs={attrs}")
                # asyncssh 中 type 可能是整数或字符串
                # 整数：2=directory, 1=file, 3=symlink 等
                # 字符串：'dir', 'file', 'symlink' 等
                is_dir = False
                if attrs.type == 'dir' or attrs.type == 2:
                    is_dir = True
                elif attrs.type == 'file' or attrs.type == 1:
                    raise Exception(f"target_path {device.target_path} 存在但是一个文件，不是目录")
                elif attrs.type in ('symlink', 'link', 3):
                    print(f"[推送] target_path 是符号链接，继续...")
                    is_dir = True  # 假设符号链接指向目录
                else:
                    # 其他类型，尝试继续使用
                    print(f"[推送] 警告：target_path 类型未知：{attrs.type}，继续尝试...")
                    is_dir = True

                if is_dir:
                    print(f"[推送] 目标根目录存在：{device.target_path}")
            except FileNotFoundError:
                raise Exception(f"目标根目录不存在：{device.target_path}，请先在设备上创建此目录")

            # 计算相对路径（去掉 target_path 前缀）
            remote_file = item.remote_file
            try:
                remote_path_obj = Path(remote_file)
                target_path_obj = Path(device.target_path)
                relative_to_target = remote_path_obj.relative_to(target_path_obj)
                # 需要创建的目录是 target_path + 相对路径的父目录
                dir_to_create = str(target_path_obj / relative_to_target.parent) if relative_to_target.parent != Path('.') else device.target_path
            except ValueError:
                # 如果不在 target_path 下，直接使用 remote_file 的父目录
                dir_to_create = str(Path(remote_file).parent)

            print(f"[推送] 需要创建的目录：{dir_to_create}")

            # 创建远程目录（从 target_path 开始）
            await self._mkdir_recursive(sftp, dir_to_create, base_path=device.target_path)

            item.progress = 50
            item.message = "目录创建成功，开始上传文件..."
            print(f"[推送] 开始上传文件：{item.local_file} -> {item.remote_file}")

            # 获取文件大小
            file_size = Path(item.local_file).stat().st_size
            item.file_size = file_size

            # SFTP 上传
            item.message = f"上传中... (0/{file_size} bytes)"

            def transfer_progress(src: str, dst: str, bytes_transferred: int, total_bytes: int):
                """传输进度回调 (sync function, not async)"""
                progress = 50 + int((bytes_transferred / total_bytes) * 40)
                item.progress = progress
                item.message = f"上传中... ({bytes_transferred}/{total_bytes} bytes)"

            await sftp.put(
                item.local_file,
                item.remote_file,
                progress_handler=transfer_progress
            )

            item.progress = 95
            item.message = "上传完成，验证文件..."
            print(f"[推送] 上传完成，开始验证文件")

            # 验证文件大小
            attrs = await sftp.stat(item.remote_file)
            if attrs.size != file_size:
                raise Exception(f"文件大小不匹配：本地={file_size}, 远程={attrs.size}")

            conn.close()  # 某些版本的 asyncssh 中 close() 不是 async 方法

            # 推送成功
            item.status = PushStatusEnum.SUCCESS
            item.message = "推送成功"
            item.progress = 100
            item.pushed_at = datetime.now()
            print(f"[推送] 设备 {device.name} 推送成功")

        except asyncio.CancelledError:
            item.status = PushStatusEnum.FAILED
            item.message = "推送已取消"
            item.error_message = "用户取消"
            print(f"[推送] 设备 {device.name} 推送已取消")

        except Exception as e:
            item.status = PushStatusEnum.FAILED
            item.message = "推送失败"
            item.error_message = str(e)
            item.progress = 0
            print(f"[推送] 设备 {device.name} 推送失败：{e}")
            # 关闭连接
            if conn:
                try:
                    conn.close()
                except:
                    pass

    async def _mkdir_recursive(self, sftp, path: str, base_path: str = None) -> None:
        """
        递归创建远程目录（从已存在的基础目录开始）

        Args:
            sftp: SFTP 客户端
            path: 要创建的完整路径
            base_path: 已存在的基础目录（默认从根目录开始检查）
        """
        path = str(path)

        # 忽略根目录
        if not path or path == '/':
            return

        # 如果指定了 base_path，只创建 base_path 之后的部分
        if base_path:
            try:
                relative = Path(path).relative_to(base_path)
                # 从 base_path 开始逐级创建
                return await self._mkdir_from_base(sftp, base_path, relative)
            except ValueError:
                # path 不在 base_path 下，直接创建 path
                pass

        # 没有 base_path，使用原有逻辑
        return await self._mkdir_recursive_full(sftp, path)

    async def _mkdir_from_base(self, sftp, base_path: str, relative_path) -> None:
        """
        从已存在的基础目录开始创建子目录

        Args:
            sftp: SFTP 客户端
            base_path: 已存在的基础目录
            relative_path: 相对于 base_path 的路径
        """
        base = Path(base_path)

        # 收集所有需要创建的层级
        dirs_to_create = []
        current = relative_path

        while current and str(current) != '.':
            dirs_to_create.insert(0, str(base / current))
            current = current.parent

        print(f"[推送] 从基础目录开始创建：{dirs_to_create}")

        for dir_path in dirs_to_create:
            # 先检查目录是否已存在
            try:
                attrs = await sftp.stat(dir_path)
                # type=2 表示目录
                if attrs.type == 'dir' or attrs.type == 2:
                    print(f"[推送] 目录已存在：{dir_path}")
                    continue  # 已存在，跳过创建
                else:
                    # 存在但不是目录，可能是文件
                    print(f"[推送] 警告：{dir_path} 存在但不是目录，类型为 {attrs.type}")
                    continue
            except FileNotFoundError:
                # 目录不存在，需要创建
                pass
            except Exception as e:
                # 其他错误（如权限问题），记录但继续尝试创建
                print(f"[推送] 检查目录失败 {dir_path}: {e}")

            # 尝试创建目录
            try:
                await sftp.mkdir(dir_path)
                print(f"[推送] 目录创建成功：{dir_path}")
            except FileExistsError:
                # 目录已存在（并发情况）
                print(f"[推送] 目录已存在（FileExistsError）：{dir_path}")
            except PermissionError as e:
                print(f"[推送] 权限不足，无法创建 {dir_path}: {e}")
                raise
            except Exception as e:
                # 再次检查目录是否存在（可能其他进程创建了）
                try:
                    attrs = await sftp.stat(dir_path)
                    if attrs.type == 'dir' or attrs.type == 2:
                        print(f"[推送] 目录已存在：{dir_path}")
                        continue
                except:
                    pass
                print(f"[推送] 创建目录失败 {dir_path}: {e}")
                raise

    async def _mkdir_recursive_full(self, sftp, path: str) -> None:
        """
        从根目录开始检查并创建目录（完整版本）

        Args:
            sftp: SFTP 客户端
            path: 远程路径
        """
        path = str(path)

        # 忽略根目录
        if not path or path == '/':
            return

        # 构建需要创建的所有目录层级
        dirs_to_create = []
        current = path

        while current and current != '/':
            dirs_to_create.insert(0, current)
            parent = str(Path(current).parent)
            if parent == current or not parent:
                break
            current = parent

        print(f"[推送] 需要创建的目录层级：{dirs_to_create}")

        # 从最深的已存在目录开始，向上创建
        base_exist_dir = None
        for dir_path in dirs_to_create:
            try:
                attrs = await sftp.stat(dir_path)
                if attrs.type == 'dir':
                    base_exist_dir = dir_path
                    print(f"[推送] 已存在目录：{dir_path}")
                else:
                    print(f"[推送] {dir_path} 存在但不是目录")
            except FileNotFoundError:
                # 目录不存在，需要从这一层开始创建
                break
            except Exception as e:
                # 其他错误，记录但继续
                print(f"[推送] 检查 {dir_path} 失败：{e}")
                break

        # 从已存在的基础目录开始，创建剩余目录
        start_idx = 0
        if base_exist_dir:
            try:
                start_idx = dirs_to_create.index(base_exist_dir) + 1
            except ValueError:
                start_idx = 0

        for dir_path in dirs_to_create[start_idx:]:
            try:
                await sftp.mkdir(dir_path)
                print(f"[推送] 目录创建成功：{dir_path}")
            except FileExistsError:
                print(f"[推送] 目录已存在：{dir_path}")
            except PermissionError as e:
                print(f"[推送] 权限不足，无法创建 {dir_path}: {e}")
                raise
            except Exception as e:
                print(f"[推送] 创建目录失败 {dir_path}: {e}")
                raise

    def get_push_task(self, push_task_id: str) -> Optional[PushTask]:
        """获取推送任务"""
        return self.tasks.get(push_task_id)


# 全局推送服务实例
_push_service: Optional[PushService] = None


def get_push_service() -> PushService:
    """获取推送服务单例"""
    global _push_service
    if _push_service is None:
        _push_service = PushService()
    return _push_service
