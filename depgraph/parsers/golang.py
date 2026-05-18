"""
Go go.mod 解析器 / Go go.mod parser

解析 Go 语言的 go.mod 文件，提取模块依赖信息。
Parses Go language go.mod files, extracts module dependency info.

支持格式 / Supported formats:
    module github.com/user/project

    go 1.21

    require (
        github.com/gin-gonic/gin v1.9.1
        github.com/go-sql-driver/mysql v1.7.1 // indirect
    )

    require github.com/stretchr/testify v1.8.4
"""

import re
from typing import List, Optional

from .base import BaseParser, Dependency, DepFileType


class GoModParser(BaseParser):
    """
    go.mod 解析器 / go.mod parser

    解析 Go 模块依赖文件。
    Parses Go module dependency files.
    """

    file_type = DepFileType.GO_MOD
    display_name = "Go (go.mod)"

    # 匹配 require 块中的依赖行
    # Regex for matching dependency lines in require block
    _DEP_PATTERN = re.compile(
        r"^\s*([a-zA-Z0-9._~/-]+/[a-zA-Z0-9._~/-]+(/[a-zA-Z0-9._~-]+)*)"
        r"\s+(v[\d.]+(?:-[a-zA-Z0-9.]+)?(?:\+[a-zA-Z0-9.]+)?)"
    )

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 go.mod 内容
        Parse go.mod content.

        Args:
            content: go.mod 文件内容 / go.mod file content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        # 查找 require 块 / Find require blocks
        in_require_block = False

        for line in content.splitlines():
            stripped = line.strip()

            # 检测 require 块 / Detect require block
            if stripped.startswith("require ("):
                in_require_block = True
                continue

            if in_require_block:
                if stripped == ")":
                    in_require_block = False
                    continue

                dep = self._parse_require_line(stripped)
                if dep:
                    dependencies.append(dep)
                continue

            # 单行 require / Single-line require
            if stripped.startswith("require "):
                dep = self._parse_require_line(stripped[8:].strip())
                if dep:
                    dependencies.append(dep)

        return dependencies

    def _parse_require_line(self, line: str) -> Optional[Dependency]:
        """
        解析单行 require 语句
        Parse a single require statement line.

        Args:
            line: 依赖行 / Dependency line

        Returns:
            Dependency对象或None / Dependency object or None
        """
        if not line or line.startswith("//"):
            return None

        # 在移除注释前检测 indirect 标记 / Detect indirect before removing comments
        is_indirect = "indirect" in line

        # 移除行尾注释 / Remove trailing comments
        if "//" in line:
            line = line[: line.index("//")].strip()

        match = self._DEP_PATTERN.match(line)
        if match:
            module_path = match.group(1)
            version = match.group(3)

            # 提取包名（模块路径最后一段）/ Extract package name
            name = module_path.split("/")[-1]

            return Dependency(
                name=self._clean_name(module_path),
                version=self._clean_version(version),
                source=self.file_type,
                is_dev=False,
                extras={
                    "module_path": module_path,
                    "indirect": is_indirect,
                },
            )

        return None
