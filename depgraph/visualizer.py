"""
可视化模块 / Visualization module

提供终端彩色输出和Mermaid图生成功能。
Provides terminal colored output and Mermaid diagram generation.

功能 / Features:
- 终端彩色树形图 / Terminal colored tree diagram
- ANSI颜色支持 / ANSI color support
- Mermaid图生成 / Mermaid diagram generation
- 依赖关系可视化 / Dependency relationship visualization
"""

import os
import sys
from typing import Dict, List, Optional, Set

from .graph import DependencyGraph, GraphNode
from .parsers.base import Dependency, DepFileType


# ============================================================
# ANSI 颜色定义 / ANSI color definitions
# ============================================================

class Colors:
    """
    ANSI 终端颜色代码 / ANSI terminal color codes

    使用方法 / Usage:
        print(f"{Colors.RED}Error{Colors.RESET}")
    """

    # 基本颜色 / Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # 前景色 / Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # 背景色 / Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @classmethod
    def disable(cls) -> None:
        """禁用颜色输出（非TTY环境）/ Disable colors (non-TTY)."""
        for attr in dir(cls):
            if attr.startswith("_"):
                continue
            value = getattr(cls, attr)
            if isinstance(value, str) and value.startswith("\033"):
                setattr(cls, attr, "")

    @classmethod
    def is_supported(cls) -> bool:
        """
        检测终端是否支持颜色
        Check if terminal supports colors.

        Returns:
            True 如果支持 / True if supported
        """
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("TERM") in ("dumb", ""):
            return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# 如果不支持颜色则禁用 / Disable if not supported
if not Colors.is_supported():
    Colors.disable()


# ============================================================
# 树形图绘制 / Tree diagram drawing
# ============================================================

# 树形连接符 / Tree connectors
TREE_BRANCH = "├── "
TREE_LAST = "└── "
TREE_VERT = "│   "
TREE_SPACE = "    "


class TreeVisualizer:
    """
    树形图可视化器 / Tree diagram visualizer

    在终端中以彩色树形结构展示依赖关系。
    Displays dependency relationships as colored tree structure in terminal.

    使用方法 / Usage:
        viz = TreeVisualizer()
        viz.print_tree(dependencies)
    """

    def __init__(self, show_dev: bool = True, max_depth: int = 10):
        """
        初始化可视化器 / Initialize visualizer.

        Args:
            show_dev: 是否显示开发依赖 / Whether to show dev dependencies
            max_depth: 最大显示深度 / Maximum display depth
        """
        self.show_dev = show_dev
        self.max_depth = max_depth

    def print_tree(
        self,
        dependencies: List[Dependency],
        title: str = "Dependencies",
    ) -> str:
        """
        生成树形图字符串
        Generate tree diagram string.

        Args:
            dependencies: 依赖列表 / Dependency list
            title: 标题 / Title

        Returns:
            树形图字符串 / Tree diagram string
        """
        lines: List[str] = []

        # 标题 / Title
        lines.append(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'─' * 40}{Colors.RESET}")

        if not dependencies:
            lines.append(f"{Colors.YELLOW}(empty){Colors.RESET}")
            return "\n".join(lines)

        # 按来源分组 / Group by source
        groups: Dict[str, List[Dependency]] = {}
        for dep in dependencies:
            if not self.show_dev and dep.is_dev:
                continue
            source = dep.source.value
            if source not in groups:
                groups[source] = []
            groups[source].append(dep)

        # 按来源渲染 / Render by source
        source_list = sorted(groups.keys())
        for i, source in enumerate(source_list):
            is_last_source = (i == len(source_list) - 1)
            prefix = TREE_LAST if is_last_source else TREE_BRANCH

            # 来源节点 / Source node
            lines.append(
                f"{prefix}{Colors.BOLD}{Colors.BLUE}"
                f"[{source}]{Colors.RESET} "
                f"({len(groups[source])} deps)"
            )

            # 该来源下的依赖 / Dependencies under this source
            deps = sorted(groups[source], key=lambda d: d.name.lower())
            child_prefix = (
                TREE_SPACE if is_last_source else TREE_VERT
            )

            for j, dep in enumerate(deps):
                is_last = (j == len(deps) - 1)
                self._render_dep(lines, dep, child_prefix, is_last)

        return "\n".join(lines)

    def _render_dep(
        self,
        lines: List[str],
        dep: Dependency,
        prefix: str,
        is_last: bool,
    ) -> None:
        """
        渲染单个依赖节点
        Render a single dependency node.

        Args:
            lines: 输出行列表 / Output line list
            dep: 依赖项 / Dependency
            prefix: 前缀 / Prefix
            is_last: 是否为最后一个 / Whether last in list
        """
        connector = TREE_LAST if is_last else TREE_BRANCH
        child_prefix = prefix + (TREE_SPACE if is_last else TREE_VERT)

        # 颜色选择 / Color selection
        if dep.is_dev:
            name_color = Colors.MAGENTA
            dev_tag = f"{Colors.DIM}[dev]{Colors.RESET} "
        else:
            name_color = Colors.GREEN
            dev_tag = ""

        # 版本信息 / Version info
        version_str = ""
        if dep.version:
            version_str = f"{Colors.YELLOW}{dep.version}{Colors.RESET}"

        # 许可证信息 / License info
        license_str = ""
        if dep.license:
            license_str = f" {Colors.DIM}({dep.license}){Colors.RESET}"

        lines.append(
            f"{prefix}{connector}{dev_tag}"
            f"{name_color}{dep.name}{Colors.RESET} "
            f"{version_str}{license_str}"
        )


# ============================================================
# Mermaid 图生成 / Mermaid diagram generation
# ============================================================

class MermaidVisualizer:
    """
    Mermaid 图生成器 / Mermaid diagram generator

    生成 Mermaid 格式的依赖关系图。
    Generates Mermaid format dependency relationship diagrams.

    使用方法 / Usage:
        viz = MermaidVisualizer()
        print(viz.generate(dependencies))
    """

    def __init__(self, direction: str = "TD"):
        """
        初始化Mermaid可视化器 / Initialize Mermaid visualizer.

        Args:
            direction: 图方向 (TD=上到下, LR=左到右) / Graph direction
        """
        self.direction = direction

    def generate(self, dependencies: List[Dependency]) -> str:
        """
        生成Mermaid图
        Generate Mermaid diagram.

        Args:
            dependencies: 依赖列表 / Dependency list

        Returns:
            Mermaid图字符串 / Mermaid diagram string
        """
        lines: List[str] = []
        lines.append(f"graph {self.direction}")

        # 按来源分组 / Group by source
        groups: Dict[str, List[Dependency]] = {}
        for dep in dependencies:
            source = dep.source.value
            if source not in groups:
                groups[source] = []
            groups[source].append(dep)

        # 创建子图 / Create subgraphs
        for source, deps in sorted(groups.items()):
            safe_source = self._safe_id(source)
            lines.append(f"    subgraph {safe_source}[\"{source}\"]")

            for dep in sorted(deps, key=lambda d: d.name.lower()):
                safe_name = self._safe_id(dep.name)
                label = dep.name
                if dep.version:
                    label += f"\\n{dep.version}"
                if dep.is_dev:
                    label += "\\n[dev]"
                lines.append(f'        {safe_name}["{label}"]')

            lines.append("    end")

        return "\n".join(lines)

    def generate_from_graph(self, graph: DependencyGraph) -> str:
        """
        从依赖图谱生成Mermaid图
        Generate Mermaid diagram from dependency graph.

        Args:
            graph: 依赖图谱 / Dependency graph

        Returns:
            Mermaid图字符串 / Mermaid diagram string
        """
        lines: List[str] = []
        lines.append(f"graph {self.direction}")

        for name, node in graph.nodes.items():
            safe_name = self._safe_id(name)
            label = name
            if node.version:
                label += f"\\n{node.version}"

            for dep in node.dependencies:
                safe_dep = self._safe_id(dep)
                lines.append(f'    {safe_name}["{label}"] --> {safe_dep}')

        return "\n".join(lines)

    @staticmethod
    def _safe_id(name: str) -> str:
        """
        将名称转换为安全的Mermaid ID
        Convert name to safe Mermaid ID.

        Args:
            name: 原始名称 / Original name

        Returns:
            安全ID / Safe ID
        """
        return name.replace("-", "_").replace(".", "_").replace("/", "_").replace("@", "_")


# ============================================================
# 综合可视化器 / Comprehensive visualizer
# ============================================================

class Visualizer:
    """
    综合可视化器 / Comprehensive visualizer

    整合树形图和Mermaid图功能。
    Integrates tree diagram and Mermaid diagram features.

    使用方法 / Usage:
        viz = Visualizer()
        viz.print_tree(dependencies)
        print(viz.to_mermaid(dependencies))
    """

    def __init__(self, show_dev: bool = True, max_depth: int = 10):
        """
        初始化可视化器 / Initialize visualizer.

        Args:
            show_dev: 是否显示开发依赖 / Whether to show dev dependencies
            max_depth: 最大显示深度 / Maximum display depth
        """
        self.tree = TreeVisualizer(show_dev=show_dev, max_depth=max_depth)
        self.mermaid = MermaidVisualizer()

    def print_tree(
        self,
        dependencies: List[Dependency],
        title: str = "Dependencies",
    ) -> str:
        """
        打印树形图 / Print tree diagram.

        Args:
            dependencies: 依赖列表 / Dependency list
            title: 标题 / Title

        Returns:
            树形图字符串 / Tree diagram string
        """
        return self.tree.print_tree(dependencies, title)

    def to_mermaid(
        self,
        dependencies: List[Dependency],
        direction: str = "TD",
    ) -> str:
        """
        生成Mermaid图 / Generate Mermaid diagram.

        Args:
            dependencies: 依赖列表 / Dependency list
            direction: 图方向 / Graph direction

        Returns:
            Mermaid图字符串 / Mermaid diagram string
        """
        self.mermaid.direction = direction
        return self.mermaid.generate(dependencies)

    def to_mermaid_from_graph(
        self,
        graph: DependencyGraph,
        direction: str = "TD",
    ) -> str:
        """
        从图谱生成Mermaid图 / Generate Mermaid from graph.

        Args:
            graph: 依赖图谱 / Dependency graph
            direction: 图方向 / Graph direction

        Returns:
            Mermaid图字符串 / Mermaid diagram string
        """
        self.mermaid.direction = direction
        return self.mermaid.generate_from_graph(graph)

    def print_summary(self, dependencies: List[Dependency]) -> str:
        """
        打印依赖摘要 / Print dependency summary.

        Args:
            dependencies: 依赖列表 / Dependency list

        Returns:
            摘要字符串 / Summary string
        """
        lines: List[str] = []

        total = len(dependencies)
        prod = len([d for d in dependencies if not d.is_dev])
        dev = len([d for d in dependencies if d.is_dev])
        unique = len({d.name.lower() for d in dependencies})

        # 来源统计 / Source statistics
        sources: Dict[str, int] = {}
        for dep in dependencies:
            src = dep.source.value
            sources[src] = sources.get(src, 0) + 1

        lines.append(f"{Colors.BOLD}DepGraph Summary{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'─' * 30}{Colors.RESET}")
        lines.append(f"  Total:    {Colors.CYAN}{total}{Colors.RESET}")
        lines.append(f"  Prod:     {Colors.GREEN}{prod}{Colors.RESET}")
        lines.append(f"  Dev:      {Colors.MAGENTA}{dev}{Colors.RESET}")
        lines.append(f"  Unique:   {Colors.YELLOW}{unique}{Colors.RESET}")
        lines.append(f"{Colors.DIM}{'─' * 30}{Colors.RESET}")

        for source, count in sorted(sources.items()):
            lines.append(f"  {Colors.BLUE}{source}{Colors.RESET}: {count}")

        return "\n".join(lines)
