"""
CLI 参数解析模块 / CLI argument parsing module

使用 argparse 实现命令行接口，支持子命令：
Implements CLI using argparse, supports subcommands:
- scan: 扫描当前目录的依赖文件 / Scan dependency files in current directory
- report: 生成分析报告 / Generate analysis report
- diff: 对比依赖变更 / Compare dependency changes
- graph: 生成依赖图 / Generate dependency graph
"""

import argparse
import os
import sys
from typing import List, Optional


def create_parser() -> argparse.ArgumentParser:
    """
    创建CLI参数解析器
    Create CLI argument parser.

    Returns:
        配置好的ArgumentParser实例 / Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description=(
            "DepGraph - 轻量级Git仓库依赖图谱与供应链风险智能分析引擎\n"
            "Lightweight Git Repository Dependency Graph & Supply Chain Risk Analyzer"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例 / Examples:\n"
            "  depgraph scan                    # 扫描当前目录\n"
            "  depgraph scan /path/to/project   # 扫描指定目录\n"
            "  depgraph report -f html -o report.html\n"
            "  depgraph diff old.txt new.txt\n"
            "  depgraph graph -f mermaid\n"
        ),
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s 1.0.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="子命令 / Subcommands",
        description="可用子命令 / Available subcommands",
        help="使用 'depgraph <command> -h' 查看帮助",
    )

    # ============================================================
    # scan 子命令 / scan subcommand
    # ============================================================
    scan_parser = subparsers.add_parser(
        "scan",
        help="扫描依赖文件 / Scan dependency files",
        description="递归扫描目录中的依赖文件并解析 / Recursively scan and parse dependency files",
    )
    scan_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="扫描路径（默认当前目录）/ Scan path (default: current directory)",
    )
    scan_parser.add_argument(
        "--no-dev",
        action="store_true",
        default=False,
        help="排除开发依赖 / Exclude dev dependencies",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="以JSON格式输出 / Output in JSON format",
    )
    scan_parser.add_argument(
        "-o", "--output",
        type=str,
        default="",
        help="输出文件路径 / Output file path",
    )
    scan_parser.add_argument(
        "--max-depth",
        type=int,
        default=20,
        help="最大递归深度（默认20）/ Max recursion depth (default: 20)",
    )

    # ============================================================
    # report 子命令 / report subcommand
    # ============================================================
    report_parser = subparsers.add_parser(
        "report",
        help="生成分析报告 / Generate analysis report",
        description="扫描依赖并生成风险分析报告 / Scan dependencies and generate risk report",
    )
    report_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="项目路径 / Project path",
    )
    report_parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["json", "html", "markdown", "md", "sarif"],
        default="markdown",
        help="报告格式（默认markdown）/ Report format (default: markdown)",
    )
    report_parser.add_argument(
        "-o", "--output",
        type=str,
        default="",
        help="输出文件路径 / Output file path",
    )
    report_parser.add_argument(
        "--no-risk",
        action="store_true",
        default=False,
        help="跳过风险分析 / Skip risk analysis",
    )
    report_parser.add_argument(
        "--no-dev",
        action="store_true",
        default=False,
        help="排除开发依赖 / Exclude dev dependencies",
    )

    # ============================================================
    # diff 子命令 / diff subcommand
    # ============================================================
    diff_parser = subparsers.add_parser(
        "diff",
        help="对比依赖变更 / Compare dependency changes",
        description="对比两个依赖文件或目录的差异 / Compare differences between two files or directories",
    )
    diff_parser.add_argument(
        "old",
        help="旧文件或目录路径 / Old file or directory path",
    )
    diff_parser.add_argument(
        "new",
        help="新文件或目录路径 / New file or directory path",
    )
    diff_parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["text", "json", "markdown", "md"],
        default="text",
        help="输出格式（默认text）/ Output format (default: text)",
    )
    diff_parser.add_argument(
        "-o", "--output",
        type=str,
        default="",
        help="输出文件路径 / Output file path",
    )

    # ============================================================
    # graph 子命令 / graph subcommand
    # ============================================================
    graph_parser = subparsers.add_parser(
        "graph",
        help="生成依赖图 / Generate dependency graph",
        description="生成依赖关系图（树形或Mermaid）/ Generate dependency graph (tree or Mermaid)",
    )
    graph_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="项目路径 / Project path",
    )
    graph_parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["tree", "mermaid", "json"],
        default="tree",
        help="图格式（默认tree）/ Graph format (default: tree)",
    )
    graph_parser.add_argument(
        "-o", "--output",
        type=str,
        default="",
        help="输出文件路径 / Output file path",
    )
    graph_parser.add_argument(
        "--direction",
        type=str,
        choices=["TD", "LR", "BT", "RL"],
        default="TD",
        help="Mermaid图方向（默认TD）/ Mermaid direction (default: TD)",
    )
    graph_parser.add_argument(
        "--no-dev",
        action="store_true",
        default=False,
        help="排除开发依赖 / Exclude dev dependencies",
    )

    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    解析命令行参数
    Parse command line arguments.

    Args:
        args: 参数列表（默认使用sys.argv）/ Argument list (default: sys.argv)

    Returns:
        解析后的命名空间 / Parsed namespace
    """
    parser = create_parser()
    return parser.parse_args(args)
