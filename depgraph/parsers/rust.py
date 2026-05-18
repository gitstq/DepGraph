"""
Rust Cargo.toml 解析器 / Rust Cargo.toml parser

解析 Rust 语言的 Cargo.toml 文件，提取依赖信息。
Parses Rust language Cargo.toml files, extracts dependency info.

支持格式 / Supported formats:
    [dependencies]
    serde = { version = "1.0", features = ["derive"] }
    tokio = { version = "1.0", features = ["full"] }
    clap = "4.0"

    [dev-dependencies]
    proptest = "1.0"

    [build-dependencies]
    cc = "1.0"
"""

import re
from typing import List, Optional

from .base import BaseParser, Dependency, DepFileType


class CargoTomlParser(BaseParser):
    """
    Cargo.toml 解析器 / Cargo.toml parser

    解析 Rust Cargo.toml 文件中的依赖声明。
    Parses dependency declarations in Rust Cargo.toml files.
    """

    file_type = DepFileType.CARGO_TOML
    display_name = "Rust (Cargo.toml)"

    # 匹配简单依赖 / Regex for simple dependencies
    _SIMPLE_DEP = re.compile(r'^([A-Za-z0-9_-]+)\s*=\s*"([^"]*)"')

    # 匹配表格依赖 / Regex for table dependencies
    _TABLE_DEP = re.compile(r'^([A-Za-z0-9_-]+)\s*=\s*\{')

    # 匹配版本号 / Regex for version number
    _VERSION_IN_TABLE = re.compile(r'version\s*=\s*"([^"]*)"')

    # 匹配 git 依赖 / Regex for git dependencies
    _GIT_IN_TABLE = re.compile(r'git\s*=\s*"([^"]*)"')

    # 匹配 path 依赖 / Regex for path dependencies
    _PATH_IN_TABLE = re.compile(r'path\s*=\s*"([^"]*)"')

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 Cargo.toml 内容
        Parse Cargo.toml content.

        Args:
            content: Cargo.toml 文件内容 / Cargo.toml file content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        # 解析不同类型的依赖节 / Parse different dependency sections
        dependencies.extend(
            self._parse_section(content, "[dependencies]", is_dev=False)
        )
        dependencies.extend(
            self._parse_section(content, "[dev-dependencies]", is_dev=True)
        )
        dependencies.extend(
            self._parse_section(content, "[build-dependencies]", is_dev=False)
        )
        dependencies.extend(
            self._parse_section(content, "[build-dependencies]", is_dev=True)
        )

        return dependencies

    def _parse_section(
        self, content: str, section_header: str, is_dev: bool
    ) -> List[Dependency]:
        """
        解析指定依赖节
        Parse a specific dependency section.

        Args:
            content: 完整文件内容 / Full file content
            section_header: 节头名称 / Section header name
            is_dev: 是否为开发依赖 / Whether dev dependency

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []
        lines = content.splitlines()

        # 找到节起始位置 / Find section start
        start_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith(section_header):
                start_idx = i
                break

        if start_idx < 0:
            return dependencies

        # 收集节内容 / Collect section content
        section_lines: List[str] = []
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            stripped = line.strip()

            # 遇到新节或文件结束 / New section or end of file
            if stripped.startswith("[") and not stripped.startswith("[["):
                break

            section_lines.append(line)

        # 解析节中的依赖 / Parse dependencies in section
        i = 0
        while i < len(section_lines):
            line = section_lines[i].strip()

            if not line or line.startswith("#"):
                i += 1
                continue

            dep = self._parse_dep_line(line)
            if dep:
                dep.is_dev = is_dev
                dependencies.append(dep)

            i += 1

        return dependencies

    def _parse_dep_line(self, line: str) -> Optional[Dependency]:
        """
        解析单行依赖声明
        Parse a single dependency declaration line.

        Args:
            line: 依赖行 / Dependency line

        Returns:
            Dependency对象或None / Dependency object or None
        """
        # 简单格式: name = "version" / Simple format
        match = self._SIMPLE_DEP.match(line)
        if match:
            name = match.group(1)
            version = match.group(2)
            return Dependency(
                name=self._clean_name(name),
                version=self._clean_version(version),
                source=self.file_type,
            )

        # 表格格式: name = { ... } / Table format
        match = self._TABLE_DEP.match(line)
        if match:
            name = match.group(1)
            version = ""

            # 尝试在同一行找版本 / Try to find version on same line
            ver_match = self._VERSION_IN_TABLE.search(line)
            if ver_match:
                version = ver_match.group(1)

            git_match = self._GIT_IN_TABLE.search(line)
            path_match = self._PATH_IN_TABLE.search(line)

            extras = {}
            if git_match:
                extras["git"] = git_match.group(1)
                version = f"git:{git_match.group(1)}"
            if path_match:
                extras["path"] = path_match.group(1)
                version = f"path:{path_match.group(1)}"

            return Dependency(
                name=self._clean_name(name),
                version=self._clean_version(version),
                source=self.file_type,
                extras=extras,
            )

        return None
