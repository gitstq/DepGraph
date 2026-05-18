"""
Python 依赖文件解析器 / Python dependency file parser

解析 requirements.txt 和 pyproject.toml 文件。
Parses requirements.txt and pyproject.toml files.

requirements.txt 支持格式 / Supported requirements.txt formats:
    flask==2.0.1
    requests>=2.25.0
    numpy~=1.21.0
    pandas  # 无版本约束 / no version constraint
    -r other-requirements.txt  # 引用其他文件 / reference other files
    -e ./my-package  # 可编辑安装 / editable install

pyproject.toml 支持格式 / Supported pyproject.toml formats:
    [project]
    dependencies = ["flask>=2.0", "requests"]

    [tool.poetry.dependencies]
    python = "^3.8"
    flask = "^2.0"
"""

import re
from typing import List, Optional

from .base import BaseParser, Dependency, DepFileType


class RequirementsTxtParser(BaseParser):
    """
    requirements.txt 解析器 / requirements.txt parser

    解析 Python pip requirements.txt 文件。
    Parses Python pip requirements.txt files.
    """

    file_type = DepFileType.REQUIREMENTS_TXT
    display_name = "Python (requirements.txt)"

    # 匹配包名和版本约束的正则表达式
    # Regex for matching package name and version constraint
    _REQ_PATTERN = re.compile(
        r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)"
        r"\s*([<>=!~]+[\w.*+-]+)?"
    )

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 requirements.txt 内容
        Parse requirements.txt content.

        Args:
            content: 文件内容 / File content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        for line in content.splitlines():
            line = line.strip()

            # 跳过空行和注释 / Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # 跳过选项行 / Skip option lines
            if line.startswith("-") and not line.startswith("-e "):
                continue

            # 处理可编辑安装 / Handle editable installs
            if line.startswith("-e "):
                # 提取包名 / Extract package name
                pkg_ref = line[3:].strip()
                if pkg_ref.startswith("git+") or pkg_ref.startswith("http"):
                    name = pkg_ref.split("/")[-1].replace(".git", "")
                else:
                    name = pkg_ref.split("/")[-1]
                dependencies.append(
                    Dependency(
                        name=self._clean_name(name),
                        version="editable",
                        source=self.file_type,
                        is_dev=False,
                        extras={"editable": True},
                    )
                )
                continue

            # 标准依赖行 / Standard dependency line
            # 处理行内注释 / Handle inline comments
            if " #" in line:
                line = line[: line.index(" #")].strip()

            # 处理环境标记 / Handle environment markers
            if ";" in line:
                line = line[: line.index(";")].strip()

            match = self._REQ_PATTERN.match(line)
            if match:
                name = match.group(1)
                version = match.group(3) or ""
                dependencies.append(
                    Dependency(
                        name=self._clean_name(name),
                        version=self._clean_version(version),
                        source=self.file_type,
                    )
                )

        return dependencies


class PyprojectTomlParser(BaseParser):
    """
    pyproject.toml 解析器 / pyproject.toml parser

    解析 Python pyproject.toml 文件，支持 PEP 621 和 Poetry 格式。
    Parses Python pyproject.toml files, supports PEP 621 and Poetry formats.
    """

    file_type = DepFileType.PYPROJECT_TOML
    display_name = "Python (pyproject.toml)"

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 pyproject.toml 内容
        Parse pyproject.toml content.

        使用简单的文本解析而非TOML库（零依赖原则）。
        Uses simple text parsing instead of TOML library (zero-dependency principle).

        Args:
            content: 文件内容 / File content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        # 尝试 PEP 621 格式 / Try PEP 621 format
        deps = self._parse_pep621(content)
        if deps:
            return deps

        # 尝试 Poetry 格式 / Try Poetry format
        deps = self._parse_poetry(content)
        if deps:
            return deps

        return dependencies

    def _parse_pep621(self, content: str) -> List[Dependency]:
        """
        解析 PEP 621 格式的依赖
        Parse PEP 621 format dependencies.

        [project]
        dependencies = [
            "flask>=2.0",
            "requests",
        ]

        Args:
            content: 文件内容 / File content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        # 查找 [project] 部分 / Find [project] section
        in_project = False
        in_deps = False
        bracket_depth = 0

        for line in content.splitlines():
            stripped = line.strip()

            # 检测节头 / Detect section headers
            if stripped.startswith("["):
                in_project = stripped == "[project]"
                in_deps = False
                bracket_depth = stripped.count("[")
                continue

            # 检测 dependencies 列表 / Detect dependencies list
            if in_project and stripped.startswith("dependencies"):
                if "=" in stripped:
                    in_deps = True
                    # 处理单行格式 / Handle single-line format
                    after_eq = stripped.split("=", 1)[1].strip()
                    if after_eq.startswith("["):
                        continue
                    # 单行列表 / Single-line list
                    deps_str = after_eq.strip("[]").strip()
                    if deps_str:
                        for dep_str in self._split_deps(deps_str):
                            dep = self._parse_dep_string(dep_str)
                            if dep:
                                dependencies.append(dep)
                    in_deps = False
                continue

            if in_deps:
                if stripped.startswith("]"):
                    in_deps = False
                    continue

                dep_str = stripped.strip(",").strip().strip('"').strip("'")
                if dep_str:
                    dep = self._parse_dep_string(dep_str)
                    if dep:
                        dependencies.append(dep)

        return dependencies

    def _parse_poetry(self, content: str) -> List[Dependency]:
        """
        解析 Poetry 格式的依赖
        Parse Poetry format dependencies.

        [tool.poetry.dependencies]
        flask = "^2.0"
        requests = "*"

        Args:
            content: 文件内容 / File content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        in_poetry_deps = False
        in_poetry_group = False
        in_dev_group = False

        for line in content.splitlines():
            stripped = line.strip()

            # 检测 Poetry 依赖节 / Detect Poetry dependency sections
            if stripped.startswith("["):
                if stripped == "[tool.poetry.dependencies]":
                    in_poetry_deps = True
                    in_poetry_group = False
                    in_dev_group = False
                elif stripped.startswith("[tool.poetry.group.") and ".dependencies]" in stripped:
                    in_poetry_deps = False
                    in_poetry_group = True
                    in_dev_group = "dev" in stripped
                else:
                    in_poetry_deps = False
                    in_poetry_group = False
                    in_dev_group = False
                continue

            if in_poetry_deps or in_poetry_group:
                if not stripped or stripped.startswith("#"):
                    continue

                # 跳过 python 版本约束 / Skip python version constraint
                if stripped.startswith("python"):
                    continue

                # 解析 key = "value" 格式 / Parse key = "value" format
                if "=" in stripped:
                    parts = stripped.split("=", 1)
                    name = parts[0].strip()
                    version = parts[1].strip().strip('"').strip("'")

                    # 跳过复杂对象 / Skip complex objects
                    if version.startswith("{"):
                        continue

                    dependencies.append(
                        Dependency(
                            name=self._clean_name(name),
                            version=self._clean_version(version),
                            source=self.file_type,
                            is_dev=in_dev_group,
                        )
                    )

        return dependencies

    def _parse_dep_string(self, dep_str: str) -> Optional[Dependency]:
        """
        解析单个依赖字符串
        Parse a single dependency string.

        Args:
            dep_str: 依赖字符串 / Dependency string

        Returns:
            Dependency对象或None / Dependency object or None
        """
        if not dep_str:
            return None

        dep_str = dep_str.strip().strip('"').strip("'").strip()

        # 分离包名和版本 / Separate name and version
        match = re.match(
            r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)\s*([<>=!~]+.*)?$",
            dep_str,
        )
        if match:
            name = match.group(1)
            version = match.group(3) or ""
            return Dependency(
                name=self._clean_name(name),
                version=self._clean_version(version),
                source=self.file_type,
            )

        return None

    @staticmethod
    def _split_deps(deps_str: str) -> List[str]:
        """
        分割逗号分隔的依赖字符串
        Split comma-separated dependency string.

        Args:
            deps_str: 依赖字符串 / Dependency string

        Returns:
            依赖字符串列表 / List of dependency strings
        """
        result: List[str] = []
        current = ""
        in_quote = False
        quote_char = ""

        for char in deps_str:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
                current += char
            elif char == quote_char and in_quote:
                in_quote = False
                current += char
            elif char == "," and not in_quote:
                if current.strip():
                    result.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            result.append(current.strip())

        return result
