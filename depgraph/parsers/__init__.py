"""
解析器包初始化 / Parser package initialization

提供解析器注册和自动发现机制。
Provides parser registration and auto-discovery mechanism.
"""

from typing import Dict, List, Optional, Type

from .base import BaseParser, DepFileType


# 解析器注册表 / Parser registry
_PARSER_REGISTRY: Dict[DepFileType, Type[BaseParser]] = {}


def register_parser(file_type: DepFileType, parser_class: Type[BaseParser]) -> None:
    """
    注册解析器 / Register a parser.

    Args:
        file_type: 文件类型 / File type
        parser_class: 解析器类 / Parser class
    """
    _PARSER_REGISTRY[file_type] = parser_class


def get_parser(file_type: DepFileType) -> Optional[BaseParser]:
    """
    获取指定文件类型的解析器实例
    Get parser instance for the specified file type.

    Args:
        file_type: 文件类型 / File type

    Returns:
        解析器实例，未找到返回None / Parser instance, None if not found
    """
    parser_class = _PARSER_REGISTRY.get(file_type)
    if parser_class:
        return parser_class()
    return None


def get_parser_by_filename(filename: str) -> Optional[BaseParser]:
    """
    根据文件名获取解析器实例
    Get parser instance by filename.

    Args:
        filename: 文件名 / Filename

    Returns:
        解析器实例，未找到返回None / Parser instance, None if not found
    """
    try:
        file_type = DepFileType(filename)
        return get_parser(file_type)
    except ValueError:
        return None


def get_all_parsers() -> List[BaseParser]:
    """
    获取所有已注册的解析器实例
    Get all registered parser instances.

    Returns:
        解析器实例列表 / List of parser instances
    """
    return [parser_class() for parser_class in _PARSER_REGISTRY.values()]


def get_supported_types() -> List[str]:
    """
    获取所有支持的文件类型
    Get all supported file types.

    Returns:
        文件类型名称列表 / List of file type names
    """
    return [ft.value for ft in _PARSER_REGISTRY.keys()]


# 导入所有解析器模块并注册 / Import all parser modules and register
from .nodejs import PackageJsonParser  # noqa: E402, F811
from .python import RequirementsTxtParser, PyprojectTomlParser  # noqa: E402, F811
from .golang import GoModParser  # noqa: E402, F811
from .rust import CargoTomlParser  # noqa: E402, F811
from .java import PomXmlParser, BuildGradleParser  # noqa: E402, F811
from .ruby import GemfileParser  # noqa: E402, F811
from .php import ComposerJsonParser  # noqa: E402, F811

# 注册所有解析器 / Register all parsers
register_parser(DepFileType.PACKAGE_JSON, PackageJsonParser)
register_parser(DepFileType.REQUIREMENTS_TXT, RequirementsTxtParser)
register_parser(DepFileType.PYPROJECT_TOML, PyprojectTomlParser)
register_parser(DepFileType.GO_MOD, GoModParser)
register_parser(DepFileType.CARGO_TOML, CargoTomlParser)
register_parser(DepFileType.POM_XML, PomXmlParser)
register_parser(DepFileType.BUILD_GRADLE, BuildGradleParser)
register_parser(DepFileType.GEMFILE, GemfileParser)
register_parser(DepFileType.COMPOSER_JSON, ComposerJsonParser)
