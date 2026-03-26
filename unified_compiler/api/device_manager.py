"""
目标设备管理模块
管理可推送的局域网设备配置
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TargetDevice(BaseModel):
    """目标设备配置"""
    id: str = Field(..., description="设备 ID")
    name: str = Field(..., description="设备名称")
    ip_address: str = Field(..., description="IP 地址")
    port: int = Field(default=22, description="SSH 端口")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码（明文存储）")
    target_path: str = Field(..., description="目标根路径")
    description: str = Field(default="", description="设备描述")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class DeviceManager:
    """设备管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化设备管理器

        Args:
            config_path: 配置文件路径，默认 ~/.unified_compiler/devices.json
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 默认配置文件路径
            self.config_path = Path.home() / ".unified_compiler" / "devices.json"

        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载设备配置
        self.devices: Dict[str, TargetDevice] = {}
        self._load_devices()

    def _load_devices(self):
        """从文件加载设备配置"""
        if not self.config_path.exists():
            # 创建空配置文件
            self._save_devices()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for device_data in data.get("devices", []):
                device = TargetDevice(**device_data)
                self.devices[device.id] = device

        except Exception as e:
            print(f"加载设备配置失败：{e}")
            self.devices = {}

    def _save_devices(self):
        """保存设备配置到文件"""
        data = {
            "devices": [device.model_dump() for device in self.devices.values()],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_devices(self, enabled_only: bool = False) -> List[TargetDevice]:
        """
        获取设备列表

        Args:
            enabled_only: 是否只返回启用的设备

        Returns:
            设备列表
        """
        devices = list(self.devices.values())
        if enabled_only:
            devices = [d for d in devices if d.enabled]
        return sorted(devices, key=lambda x: x.created_at, reverse=True)

    def get_device(self, device_id: str) -> Optional[TargetDevice]:
        """
        获取单个设备

        Args:
            device_id: 设备 ID

        Returns:
            设备配置，不存在返回 None
        """
        return self.devices.get(device_id)

    def add_device(self, device: TargetDevice) -> TargetDevice:
        """
        添加设备

        Args:
            device: 设备配置

        Returns:
            添加后的设备
        """
        self.devices[device.id] = device
        self._save_devices()
        return device

    def create_device(
        self,
        name: str,
        ip_address: str,
        username: str,
        password: str,
        target_path: str,
        port: int = 22,
        description: str = "",
        enabled: bool = True
    ) -> TargetDevice:
        """
        创建新设备

        Args:
            name: 设备名称
            ip_address: IP 地址
            username: 用户名
            password: 密码
            target_path: 目标路径
            port: SSH 端口
            description: 设备描述
            enabled: 是否启用

        Returns:
            新创建的设备
        """
        device = TargetDevice(
            id=f"dev_{uuid.uuid4().hex[:8]}",
            name=name,
            ip_address=ip_address,
            port=port,
            username=username,
            password=password,
            target_path=target_path,
            description=description,
            enabled=enabled
        )
        return self.add_device(device)

    def update_device(self, device_id: str, **kwargs) -> Optional[TargetDevice]:
        """
        更新设备配置

        Args:
            device_id: 设备 ID
            **kwargs: 要更新的字段

        Returns:
            更新后的设备，不存在返回 None
        """
        device = self.get_device(device_id)
        if not device:
            return None

        for key, value in kwargs.items():
            if hasattr(device, key) and value is not None:
                setattr(device, key, value)

        self._save_devices()
        return device

    def delete_device(self, device_id: str) -> bool:
        """
        删除设备

        Args:
            device_id: 设备 ID

        Returns:
            是否删除成功
        """
        if device_id in self.devices:
            del self.devices[device_id]
            self._save_devices()
            return True
        return False

    def enable_device(self, device_id: str) -> Optional[TargetDevice]:
        """启用设备"""
        return self.update_device(device_id, enabled=True)

    def disable_device(self, device_id: str) -> Optional[TargetDevice]:
        """禁用设备"""
        return self.update_device(device_id, enabled=False)

    def test_connection(self, device_id: str) -> Dict:
        """
        测试设备连接

        Args:
            device_id: 设备 ID

        Returns:
            测试结果
        """
        import asyncio
        try:
            # 尝试使用 asyncssh 连接
            import asyncssh

            async def test():
                conn = await asyncssh.connect(
                    host=device.ip_address,
                    port=device.port,
                    username=device.username,
                    password=device.password,
                    known_hosts=None  # 不验证主机密钥
                )
                await conn.close()
                return {"success": True, "message": "连接成功"}

            device = self.get_device(device_id)
            if not device:
                return {"success": False, "message": "设备不存在"}

            result = asyncio.run(test())
            return result

        except Exception as e:
            return {"success": False, "message": f"连接失败：{str(e)}"}


# 全局设备管理器实例
_device_manager: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    """获取设备管理器单例"""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager
