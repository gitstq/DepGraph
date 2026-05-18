"""
CLI 入口模块 / CLI entry point module

DepGraph 命令行工具的主入口，处理子命令分发。
Main entry point for DepGraph CLI tool, handles subcommand dispatch.

使用方法 / Usage:
    python -m depgraph scan
    python -m depgraph report -f html -o report.html
    python -m depgraph diff old.txt new.txt
    python -m depgraph graph -f mermaid
"""

import sys
import os

from .cli import parse_args
from .scanner import DependencyScanner
from .graph import DependencyGraph
from .analyzer import SupplyChainAnalyzer
from .differ import DependencyDiffer
from .reporter import ReportGenerator
from .visualizer import Visualizer
from . import __version__


def cmd_scan(args) -> int:
    """
    执行 scan 子命令
    Execute scan subcommand.

    Args:
        args: 解析后的命令行参数 / Parsed CLI arguments

    Returns:
        退出码 / Exit code
    """
    scanner = DependencyScanner(max_depth=args.max_depth)
    result = scanner.scan(args.path)

    if args.json:
        import json
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        viz = Visualizer(show_dev=not args.no_dev)
        if result.dependencies:
            print(viz.print_tree(result.dependencies))
            print()
            print(viz.print_summary(result.dependencies))
        else:
            print("未找到依赖文件或无法解析依赖。")
            if result.errors:
                for err in result.errors:
                    print(f"  错误: {err}")

    if args.output:
        import json
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")

    return 0 if result.dependencies else 1


def cmd_report(args) -> int:
    """
    执行 report 子命令
    Execute report subcommand.

    Args:
        args: 解析后的命令行参数 / Parsed CLI arguments

    Returns:
        退出码 / Exit code
    """
    # 扫描依赖 / Scan dependencies
    scanner = DependencyScanner()
    scan_result = scanner.scan(args.path)

    if not scan_result.dependencies:
        print("未找到依赖文件或无法解析依赖。")
        if scan_result.errors:
            for err in scan_result.errors:
                print(f"  错误: {err}")
        return 1

    # 风险分析 / Risk analysis
    risk_report = None
    if not args.no_risk:
        graph = DependencyGraph()
        graph.build_from_dependencies(scan_result.dependencies)
        analyzer = SupplyChainAnalyzer()
        risk_report = analyzer.analyze(scan_result.dependencies, graph)

    # 生成报告 / Generate report
    generator = ReportGenerator()
    fmt = args.format.lower()

    if fmt == "json":
        data = scan_result.to_dict()
        if risk_report:
            data["risk_analysis"] = risk_report.to_dict()
        success = generator.generate_json(data, args.output)
        if not args.output:
            import json
            print(json.dumps(data, indent=2, ensure_ascii=False))

    elif fmt in ("markdown", "md"):
        graph = DependencyGraph()
        graph.build_from_dependencies(scan_result.dependencies)
        content = generator.generate_markdown(
            scan_result=scan_result,
            risk_report=risk_report,
            graph=graph,
            output_path=args.output,
        )
        if not args.output:
            print(content)

    elif fmt == "html":
        graph = DependencyGraph()
        graph.build_from_dependencies(scan_result.dependencies)
        content = generator.generate_html(
            scan_result=scan_result,
            risk_report=risk_report,
            graph=graph,
            output_path=args.output,
        )
        if not args.output:
            print(content)

    elif fmt == "sarif":
        content = generator.generate_sarif(
            scan_result=scan_result,
            risk_report=risk_report,
            output_path=args.output,
        )
        if not args.output:
            print(content)

    if args.output:
        print(f"报告已生成: {args.output}")

    return 0


def cmd_diff(args) -> int:
    """
    执行 diff 子命令
    Execute diff subcommand.

    Args:
        args: 解析后的命令行参数 / Parsed CLI arguments

    Returns:
        退出码 / Exit code
    """
    differ = DependencyDiffer()

    old_path = args.old
    new_path = args.new

    # 判断是文件还是目录 / Determine if file or directory
    if os.path.isfile(old_path) and os.path.isfile(new_path):
        # 文件对比 / File comparison
        result = differ.diff_files(old_path, new_path)
    else:
        # 目录对比 / Directory comparison
        scanner = DependencyScanner()
        old_result = scanner.scan(old_path)
        new_result = scanner.scan(new_path)
        result = differ.diff(
            old_result.dependencies,
            new_result.dependencies,
            old_path,
            new_path,
        )

    fmt = args.format.lower()

    if fmt == "json":
        import json
        output = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        print(output)
    elif fmt in ("markdown", "md"):
        from .reporter import ReportGenerator
        gen = ReportGenerator()
        content = gen.generate_markdown(diff_result=result, output_path=args.output)
        if not args.output:
            print(content)
    else:
        # 文本输出 / Text output
        from .visualizer import Colors
        if not result.has_changes:
            print(f"{Colors.GREEN}未检测到依赖变更。{Colors.RESET}")
        else:
            print(f"{Colors.BOLD}依赖变更检测{Colors.RESET}")
            print(f"{Colors.DIM}{'─' * 40}{Colors.RESET}")
            print(f"  新增: {Colors.GREEN}{len(result.added)}{Colors.RESET}")
            print(f"  删除: {Colors.RED}{len(result.removed)}{Colors.RESET}")
            print(f"  变更: {Colors.YELLOW}{len(result.changed)}{Colors.RESET}")
            print()

            if result.added:
                print(f"{Colors.GREEN}新增依赖:{Colors.RESET}")
                for change in result.added:
                    print(f"  + {change.name} ({change.new_version})")
                print()

            if result.removed:
                print(f"{Colors.RED}删除依赖:{Colors.RESET}")
                for change in result.removed:
                    print(f"  - {change.name} ({change.old_version})")
                print()

            if result.changed:
                print(f"{Colors.YELLOW}版本变更:{Colors.RESET}")
                for change in result.changed:
                    change_type = ""
                    if change.is_major:
                        change_type = " [主版本!]"
                    elif change.is_minor:
                        change_type = " [次版本]"
                    elif change.is_patch:
                        change_type = " [补丁]"
                    print(
                        f"  ~ {change.name}: "
                        f"{change.old_version} -> {change.new_version}"
                        f"{Colors.YELLOW}{change_type}{Colors.RESET}"
                    )

    if args.output and fmt == "text":
        # 保存JSON到文件 / Save JSON to file
        import json
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")

    return 0


def cmd_graph(args) -> int:
    """
    执行 graph 子命令
    Execute graph subcommand.

    Args:
        args: 解析后的命令行参数 / Parsed CLI arguments

    Returns:
        退出码 / Exit code
    """
    # 扫描依赖 / Scan dependencies
    scanner = DependencyScanner()
    result = scanner.scan(args.path)

    if not result.dependencies:
        print("未找到依赖文件或无法解析依赖。")
        return 1

    # 构建图谱 / Build graph
    graph = DependencyGraph()
    graph.build_from_dependencies(result.dependencies)

    fmt = args.format.lower()
    viz = Visualizer(show_dev=not args.no_dev)

    if fmt == "tree":
        tree_output = viz.print_tree(result.dependencies, "Dependency Graph")
        print(tree_output)

        # 图谱统计 / Graph statistics
        from .visualizer import Colors
        print()
        print(f"{Colors.BOLD}图谱统计:{Colors.RESET}")
        print(f"  节点数: {graph.node_count}")
        print(f"  边数: {graph.edge_count}")
        print(f"  根节点: {len(graph.get_root_nodes())}")
        print(f"  叶子节点: {len(graph.get_leaf_nodes())}")

        cycle = graph.detect_cycles()
        if cycle.has_cycle:
            print(f"  {Colors.RED}检测到循环依赖: {' -> '.join(cycle.nodes)}{Colors.RESET}")
        else:
            print(f"  {Colors.GREEN}无循环依赖{Colors.RESET}")

    elif fmt == "mermaid":
        mermaid_output = viz.to_mermaid(
            result.dependencies,
            direction=args.direction,
        )
        print(mermaid_output)

    elif fmt == "json":
        import json
        output = json.dumps(graph.to_dict(), indent=2, ensure_ascii=False)
        print(output)

    if args.output:
        if fmt == "tree":
            tree_output = viz.print_tree(result.dependencies, "Dependency Graph")
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(tree_output)
        elif fmt == "mermaid":
            mermaid_output = viz.to_mermaid(
                result.dependencies,
                direction=args.direction,
            )
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(mermaid_output)
        elif fmt == "json":
            import json
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: {args.output}")

    return 0


def main(args=None) -> int:
    """
    CLI 主入口函数
    CLI main entry function.

    Args:
        args: 命令行参数（默认使用sys.argv）/ CLI arguments (default: sys.argv)

    Returns:
        退出码（0成功，1失败）/ Exit code (0 success, 1 failure)
    """
    parsed = parse_args(args)

    if not parsed.command:
        parse_args(["--help"])
        return 1

    # 子命令分发 / Subcommand dispatch
    handlers = {
        "scan": cmd_scan,
        "report": cmd_report,
        "diff": cmd_diff,
        "graph": cmd_graph,
    }

    handler = handlers.get(parsed.command)
    if handler is None:
        print(f"未知命令: {parsed.command}")
        parse_args(["--help"])
        return 1

    try:
        return handler(parsed)
    except KeyboardInterrupt:
        print("\n操作已取消。")
        return 130
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
