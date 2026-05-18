"""
解析器基类模块 / Parser base module

定义所有依赖解析器的公共接口和数据结构。
Defines common interfaces and data structures for all dependency parsers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class DepFileType(Enum):
    """
    依赖文件类型枚举 / Dependency file type enumeration
    """
    PACKAGE_JSON = "package.json"           # Node.js
    REQUIREMENTS_TXT = "requirements.txt"   # Python pip
    PYPROJECT_TOML = "pyproject.toml"       # Python modern
    GO_MOD = "go.mod"                       # Go
    CARGO_TOML = "Cargo.toml"               # Rust
    POM_XML = "pom.xml"                     # Java Maven
    BUILD_GRADLE = "build.gradle"           # Java Gradle
    GEMFILE = "Gemfile"                     # Ruby
    COMPOSER_JSON = "composer.json"         # PHP
    UNKNOWN = "unknown"


@dataclass
class Dependency:
    """
    依赖项数据类 / Dependency data class

    表示一个解析后的依赖项，包含名称、版本、来源等信息。
    Represents a parsed dependency with name, version, source, etc.

    Attributes:
        name: 依赖包名称 / Package name
        version: 版本约束 / Version constraint
        source: 来源文件类型 / Source file type
        license: 许可证信息 / License information
        is_dev: 是否为开发依赖 / Whether it's a dev dependency
        extras: 额外元数据 / Extra metadata
    """
    name: str
    version: str = ""
    source: DepFileType = DepFileType.UNKNOWN
    license: str = ""
    is_dev: bool = False
    extras: Dict = field(default_factory=dict)

    def __hash__(self) -> int:
        """基于名称的哈希值 / Hash based on name"""
        return hash(self.name.lower())

    def __eq__(self, other: object) -> bool:
        """基于名称的相等比较 / Equality based on name"""
        if not isinstance(other, Dependency):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def to_dict(self) -> Dict:
        """
        转换为字典 / Convert to dictionary.

        Returns:
            包含所有属性的字典 / Dictionary with all attributes
        """
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source.value if isinstance(self.source, DepFileType) else str(self.source),
            "license": self.license,
            "is_dev": self.is_dev,
            "extras": self.extras,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Dependency":
        """
        从字典创建实例 / Create instance from dictionary.

        Args:
            data: 字典数据 / Dictionary data

        Returns:
            Dependency实例 / Dependency instance
        """
        source = data.get("source", "unknown")
        if isinstance(source, str):
            try:
                source = DepFileType(source)
            except ValueError:
                source = DepFileType.UNKNOWN

        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            source=source,
            license=data.get("license", ""),
            is_dev=data.get("is_dev", False),
            extras=data.get("extras", {}),
        )


class BaseParser:
    """
    解析器抽象基类 / Parser abstract base class

    所有依赖文件解析器必须继承此类并实现 parse 方法。
    All dependency file parsers must inherit from this class and implement parse.

    使用方法 / Usage:
        class MyParser(BaseParser):
            def parse(self, content: str) -> List[Dependency]:
                # 实现解析逻辑 / Implement parsing logic
                ...
    """

    # 解析器支持的文件类型 / File types supported by this parser
    file_type: DepFileType = DepFileType.UNKNOWN

    # 解析器显示名称 / Parser display name
    display_name: str = "Base Parser"

    def parse(self, content: str) -> List[Dependency]:
        """
        解析依赖文件内容
        Parse dependency file content.

        Args:
            content: 文件内容字符串 / File content string

        Returns:
            解析后的依赖列表 / Parsed dependency list

        Raises:
            NotImplementedError: 子类必须实现此方法 / Subclass must implement
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.parse() must be implemented"
        )

    def can_parse(self, filename: str) -> bool:
        """
        检查是否能解析指定文件
        Check if this parser can handle the given file.

        Args:
            filename: 文件名 / Filename

        Returns:
            True 如果可以解析 / True if parsable
        """
        return filename == self.file_type.value

    @staticmethod
    def _clean_version(version: str) -> str:
        """
        清理版本号字符串
        Clean version string.

        移除多余空格和特殊字符 / Remove extra spaces and special characters.

        Args:
            version: 原始版本号 / Raw version string

        Returns:
            清理后的版本号 / Cleaned version string
        """
        if not version:
            return ""
        return version.strip().strip("'\"").strip()

    @staticmethod
    def _clean_name(name: str) -> str:
        """
        清理包名称
        Clean package name.

        Args:
            name: 原始名称 / Raw name

        Returns:
            清理后的名称 / Cleaned name
        """
        if not name:
            return ""
        return name.strip().strip("'\"").strip()
