"""
Ruby Gemfile 解析器 / Ruby Gemfile parser

解析 Ruby 语言的 Gemfile 文件，提取 gem 依赖信息。
Parses Ruby language Gemfile files, extracts gem dependency info.

支持格式 / Supported formats:
    source 'https://rubygems.org'

    gem 'rails', '~> 7.0'
    gem 'pg', '~> 1.4'
    gem 'sassc-rails'

    group :development, :test do
        gem 'rspec-rails', '~> 5.0'
        gem 'byebug'
    end

    gem 'devise', git: 'https://github.com/plataformatec/devise.git'
"""

import re
from typing import List, Optional

from .base import BaseParser, Dependency, DepFileType


class GemfileParser(BaseParser):
    """
    Gemfile 解析器 / Gemfile parser

    解析 Ruby 项目的 Gemfile 文件。
    Parses Ruby project Gemfile files.
    """

    file_type = DepFileType.GEMFILE
    display_name = "Ruby (Gemfile)"

    # 匹配 gem 声明 / Regex for gem declarations
    _GEM_PATTERN = re.compile(
        r"""^gem\s+['"]([^'"]+)['"]"""  # gem 'name'
        r"""(?:\s*,\s*['"]([^'"]*)['"])?"""  # optional version
    )

    # 匹配 group 块 / Regex for group blocks
    _GROUP_PATTERN = re.compile(
        r"^group\s+[:](\w+)"
    )

    # 开发/测试组 / Development/test groups
    DEV_GROUPS = {"development", "test"}

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 Gemfile 内容
        Parse Gemfile content.

        Args:
            content: Gemfile 文件内容 / Gemfile file content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        in_group = False
        is_dev_group = False
        group_depth = 0

        for line in content.splitlines():
            stripped = line.strip()

            # 跳过空行和注释 / Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # 检测 group 块 / Detect group blocks
            if stripped.startswith("group"):
                in_group = True
                group_depth = 1
                # 检查是否为开发组 / Check if dev group
                is_dev_group = any(
                    g in self.DEV_GROUPS
                    for g in re.findall(r":(\w+)", stripped)
                )
                continue

            # 跟踪块深度 / Track block depth
            if in_group:
                group_depth += stripped.count("do") - stripped.count("end")
                if group_depth <= 0:
                    in_group = False
                    is_dev_group = False
                    continue

            # 解析 gem 声明 / Parse gem declarations
            dep = self._parse_gem_line(stripped, is_dev=in_group and is_dev_group)
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_gem_line(self, line: str, is_dev: bool = False) -> Optional[Dependency]:
        """
        解析单行 gem 声明
        Parse a single gem declaration line.

        Args:
            line: gem 声明行 / gem declaration line
            is_dev: 是否为开发依赖 / Whether dev dependency

        Returns:
            Dependency对象或None / Dependency object or None
        """
        if not line.startswith("gem"):
            return None

        match = self._GEM_PATTERN.match(line)
        if not match:
            # 尝试更宽松的匹配 / Try more relaxed matching
            match = re.match(r"""gem\s+['"]([^'"]+)['"]""", line)
            if not match:
                return None
            name = match.group(1)
            version = ""
        else:
            name = match.group(1)
            version = match.group(2) or ""

        # 检查 git 源 / Check for git source
        extras = {}
        git_match = re.search(r"git:\s*['\"]([^'\"]+)['\"]", line)
        if git_match:
            extras["git"] = git_match.group(1)
            version = f"git:{git_match.group(1)}"

        # 检查 path 源 / Check for path source
        path_match = re.search(r"path:\s*['\"]([^'\"]+)['\"]", line)
        if path_match:
            extras["path"] = path_match.group(1)
            version = f"path:{path_match.group(1)}"

        # 检查平台限制 / Check platform constraints
        platform_match = re.search(r"platforms:\s*\[([^\]]+)\]", line)
        if platform_match:
            extras["platforms"] = [
                p.strip().strip(":").strip('"').strip("'")
                for p in platform_match.group(1).split(",")
            ]

        return Dependency(
            name=self._clean_name(name),
            version=self._clean_version(version),
            source=self.file_type,
            is_dev=is_dev,
            extras=extras,
        )
