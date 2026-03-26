"""
编译器注册表 - 管理所有可用的编译器
"""

from typing import Dict, Type, Optional
from .base_compiler import BaseCompiler, CompileConfig, PlatformType


class CompilerRegistry:
    """编译器注册表 - 单例模式"""
    
    _instance: Optional['CompilerRegistry'] = None
    _compilers: Dict[str, Type[BaseCompiler]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, platform: PlatformType):
        """
        装饰器：注册编译器类
        
        Usage:
            @CompilerRegistry.register(PlatformType.ASCEND)
            class AscendCompiler(BaseCompiler):
                ...
        """
        def decorator(compiler_class: Type[BaseCompiler]):
            cls._compilers[platform.value] = compiler_class
            return compiler_class
        return decorator
    
    @classmethod
    def get_compiler(cls, platform: PlatformType, config: CompileConfig) -> Optional[BaseCompiler]:
        """
        获取指定平台的编译器实例
        
        Args:
            platform: 平台类型
            config: 编译配置
            
        Returns:
            BaseCompiler: 编译器实例，如果未找到则返回 None
        """
        compiler_class = cls._compilers.get(platform.value)
        if compiler_class is None:
            return None
        return compiler_class(config)
    
    @classmethod
    def get_all_platforms(cls) -> list:
        """获取所有已注册的平台"""
        return list(cls._compilers.keys())
    
    @classmethod
    def is_platform_supported(cls, platform: PlatformType) -> bool:
        """检查平台是否被支持"""
        return platform.value in cls._compilers
    
    @classmethod
    def unregister(cls, platform: PlatformType):
        """注销平台编译器"""
        if platform.value in cls._compilers:
            del cls._compilers[platform.value]
    
    @classmethod
    def clear(cls):
        """清空所有注册"""
        cls._compilers.clear()
