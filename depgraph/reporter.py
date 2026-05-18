"""
报告生成器模块 / Report generator module

生成多格式的依赖分析报告。
Generates dependency analysis reports in multiple formats.

支持格式 / Supported formats:
- JSON: 结构化数据 / Structured data
- HTML: 交互式网页报告（内联CSS，零外部依赖）/ Interactive web report (inline CSS)
- Markdown: 文本报告 / Text report
- SARIF: 静态分析结果交换格式 / Static Analysis Results Interchange Format
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .analyzer import RiskReport
from .differ import DiffResult
from .graph import DependencyGraph
from .parsers.base import Dependency
from .scanner import ScanResult
from .utils import format_timestamp, write_file_safe, write_json_safe


class ReportGenerator:
    """
    报告生成器 / Report generator

    根据扫描和分析结果生成多格式报告。
    Generates multi-format reports from scan and analysis results.

    使用方法 / Usage:
        generator = ReportGenerator()
        generator.generate_json(result, "output.json")
        generator.generate_html(result, "output.html")
    """

    def __init__(self):
        """初始化报告生成器 / Initialize report generator."""
        self.generated_at = format_timestamp()

    def generate_json(
        self,
        data: Any,
        output_path: str,
    ) -> bool:
        """
        生成JSON报告
        Generate JSON report.

        Args:
            data: 要输出的数据 / Data to output
            output_path: 输出文件路径 / Output file path

        Returns:
            是否成功 / Whether successful
        """
        report_data = {
            "generated_at": self.generated_at,
            "tool": "depgraph",
            "version": "1.0.0",
        }

        if isinstance(data, ScanResult):
            report_data.update(data.to_dict())
        elif isinstance(data, RiskReport):
            report_data.update(data.to_dict())
        elif isinstance(data, DiffResult):
            report_data.update(data.to_dict())
        elif isinstance(data, dict):
            report_data.update(data)
        else:
            report_data["data"] = str(data)

        return write_json_safe(output_path, report_data)

    def generate_markdown(
        self,
        scan_result: Optional[ScanResult] = None,
        risk_report: Optional[RiskReport] = None,
        diff_result: Optional[DiffResult] = None,
        graph: Optional[DependencyGraph] = None,
        output_path: str = "",
    ) -> str:
        """
        生成Markdown报告
        Generate Markdown report.

        Args:
            scan_result: 扫描结果 / Scan result
            risk_report: 风险报告 / Risk report
            diff_result: 变更检测结果 / Diff result
            graph: 依赖图谱 / Dependency graph
            output_path: 输出文件路径 / Output file path

        Returns:
            Markdown报告字符串 / Markdown report string
        """
        lines: List[str] = []

        # 标题 / Title
        lines.append("# DepGraph 依赖分析报告")
        lines.append(f"> 生成时间: {self.generated_at}")
        lines.append("")

        # 扫描结果部分 / Scan result section
        if scan_result:
            lines.extend(self._render_scan_markdown(scan_result))

        # 风险报告部分 / Risk report section
        if risk_report:
            lines.extend(self._render_risk_markdown(risk_report))

        # 变更检测部分 / Diff section
        if diff_result:
            lines.extend(self._render_diff_markdown(diff_result))

        # 图谱部分 / Graph section
        if graph:
            lines.extend(self._render_graph_markdown(graph))

        content = "\n".join(lines)

        if output_path:
            write_file_safe(output_path, content)

        return content

    def generate_html(
        self,
        scan_result: Optional[ScanResult] = None,
        risk_report: Optional[RiskReport] = None,
        diff_result: Optional[DiffResult] = None,
        graph: Optional[DependencyGraph] = None,
        output_path: str = "",
    ) -> str:
        """
        生成HTML报告
        Generate HTML report.

        使用内联CSS，无外部依赖。
        Uses inline CSS, no external dependencies.

        Args:
            scan_result: 扫描结果 / Scan result
            risk_report: 风险报告 / Risk report
            diff_result: 变更检测结果 / Diff result
            graph: 依赖图谱 / Dependency graph
            output_path: 输出文件路径 / Output file path

        Returns:
            HTML报告字符串 / HTML report string
        """
        html_parts: List[str] = []

        # HTML头部和样式 / HTML header and styles
        html_parts.append(self._get_html_header())

        # 内容区域 / Content area
        html_parts.append('<div class="container">')
        html_parts.append('<h1>DepGraph 依赖分析报告</h1>')
        html_parts.append(f'<p class="timestamp">生成时间: {self.generated_at}</p>')

        if scan_result:
            html_parts.append(self._render_scan_html(scan_result))

        if risk_report:
            html_parts.append(self._render_risk_html(risk_report))

        if diff_result:
            html_parts.append(self._render_diff_html(diff_result))

        if graph:
            html_parts.append(self._render_graph_html(graph))

        html_parts.append('</div>')
        html_parts.append('</body></html>')

        content = "\n".join(html_parts)

        if output_path:
            write_file_safe(output_path, content)

        return content

    def generate_sarif(
        self,
        scan_result: Optional[ScanResult] = None,
        risk_report: Optional[RiskReport] = None,
        output_path: str = "",
    ) -> str:
        """
        生成SARIF格式报告
        Generate SARIF format report.

        SARIF (Static Analysis Results Interchange Format) 是微软定义的
        静态分析结果标准格式，可被GitHub Code Scanning等工具消费。

        Args:
            scan_result: 扫描结果 / Scan result
            risk_report: 风险报告 / Risk report
            output_path: 输出文件路径 / Output file path

        Returns:
            SARIF JSON字符串 / SARIF JSON string
        """
        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [],
        }

        rules: List[Dict] = []
        results: List[Dict] = []

        if risk_report:
            # 许可证风险规则 / License risk rules
            rules.append({
                "id": "DEP001",
                "name": "License Risk",
                "shortDescription": {"text": "依赖许可证风险"},
                "fullDescription": {"text": "检测到可能存在许可证合规风险的依赖"},
                "helpUri": "https://example.com/help/license-risk",
            })

            for risk in risk_report.license_risks:
                if risk.risk_score > 20:
                    results.append({
                        "ruleId": "DEP001",
                        "level": "warning" if risk.risk_score < 50 else "error",
                        "message": {
                            "text": f"{risk.name}: {risk.reason} "
                                    f"(评分: {risk.risk_score}, "
                                    f"许可证: {risk.license})"
                        },
                        "locations": [{
                            "physicalLocation": {
                                "artifactLocation": {"uri": risk.name}
                            }
                        }],
                        "properties": {
                            "risk_score": risk.risk_score,
                            "license": risk.license,
                            "classification": risk.classification,
                        },
                    })

            # 过时依赖规则 / Outdated dependency rules
            rules.append({
                "id": "DEP002",
                "name": "Outdated Dependency",
                "shortDescription": {"text": "过时依赖"},
                "fullDescription": {"text": "检测到可能过时的依赖"},
            })

            for fresh in risk_report.freshness_issues:
                if fresh.is_outdated:
                    results.append({
                        "ruleId": "DEP002",
                        "level": "note",
                        "message": {
                            "text": f"{fresh.name}: 版本约束为 {fresh.current_version}, "
                                    f"状态: {fresh.version_status}"
                        },
                        "locations": [{
                            "physicalLocation": {
                                "artifactLocation": {"uri": fresh.name}
                            }
                        }],
                    })

        sarif["runs"].append({
            "tool": {
                "driver": {
                    "name": "DepGraph",
                    "version": "1.0.0",
                    "informationUri": "https://github.com/depgraph",
                    "rules": rules,
                }
            },
            "results": results,
        })

        content = json.dumps(sarif, indent=2, ensure_ascii=False)

        if output_path:
            write_file_safe(output_path, content)

        return content

    # ============================================================
    # Markdown 渲染方法 / Markdown rendering methods
    # ============================================================

    def _render_scan_markdown(self, result: ScanResult) -> List[str]:
        """渲染扫描结果为Markdown / Render scan result as Markdown."""
        lines: List[str] = []
        lines.append("## 扫描概览")
        lines.append("")
        lines.append(f"- **扫描路径**: `{result.root_path}`")
        lines.append(f"- **发现文件**: {len(result.files_found)}")
        lines.append(f"- **总依赖数**: {result.stats.get('total_dependencies', 0)}")
        lines.append(f"- **生产依赖**: {result.stats.get('production_dependencies', 0)}")
        lines.append(f"- **开发依赖**: {result.stats.get('development_dependencies', 0)}")
        lines.append(f"- **唯一包数**: {result.stats.get('unique_packages', 0)}")
        lines.append("")

        if result.files_found:
            lines.append("### 发现的文件")
            lines.append("")
            for f in result.files_found:
                lines.append(f"- `{f}`")
            lines.append("")

        if result.dependencies:
            lines.append("### 依赖列表")
            lines.append("")
            lines.append("| 名称 | 版本 | 类型 | 开发依赖 |")
            lines.append("|------|------|------|----------|")
            for dep in result.dependencies:
                dev_flag = "Yes" if dep.is_dev else "No"
                lines.append(
                    f"| {dep.name} | {dep.version} | "
                    f"{dep.source.value} | {dev_flag} |"
                )
            lines.append("")

        if result.errors:
            lines.append("### 错误")
            lines.append("")
            for err in result.errors:
                lines.append(f"- :warning: {err}")
            lines.append("")

        return lines

    def _render_risk_markdown(self, report: RiskReport) -> List[str]:
        """渲染风险报告为Markdown / Render risk report as Markdown."""
        lines: List[str] = []
        level = report._score_to_level(report.overall_score)
        lines.append("## 风险评估")
        lines.append("")
        lines.append(f"**综合风险评分**: {report.overall_score}/100 ({level})")
        lines.append("")

        if report.summary:
            lines.append("### 摘要")
            lines.append("")
            for key, value in report.summary.items():
                if key != "recommendations":
                    lines.append(f"- **{key}**: {value}")
            lines.append("")

            if "recommendations" in report.summary:
                lines.append("### 建议")
                lines.append("")
                for rec in report.summary["recommendations"]:
                    lines.append(f"- {rec}")
                lines.append("")

        if report.license_risks:
            lines.append("### 许可证风险")
            lines.append("")
            lines.append("| 包名 | 许可证 | 分类 | 评分 | 等级 |")
            lines.append("|------|--------|------|------|------|")
            for risk in report.license_risks:
                lines.append(
                    f"| {risk.name} | {risk.license} | "
                    f"{risk.classification} | {risk.risk_score} | "
                    f"{risk.risk_level} |"
                )
            lines.append("")

        return lines

    def _render_diff_markdown(self, result: DiffResult) -> List[str]:
        """渲染变更检测为Markdown / Render diff result as Markdown."""
        lines: List[str] = []
        lines.append("## 依赖变更检测")
        lines.append("")

        if not result.has_changes:
            lines.append("未检测到变更。")
            lines.append("")
            return lines

        lines.append(f"- **新增**: {len(result.added)}")
        lines.append(f"- **删除**: {len(result.removed)}")
        lines.append(f"- **变更**: {len(result.changed)}")
        lines.append("")

        if result.added:
            lines.append("### 新增依赖")
            lines.append("")
            for change in result.added:
                lines.append(f"- `+ {change.name}` ({change.new_version})")
            lines.append("")

        if result.removed:
            lines.append("### 删除依赖")
            lines.append("")
            for change in result.removed:
                lines.append(f"- `- {change.name}` ({change.old_version})")
            lines.append("")

        if result.changed:
            lines.append("### 版本变更")
            lines.append("")
            lines.append("| 包名 | 旧版本 | 新版本 | 变更类型 |")
            lines.append("|------|--------|--------|----------|")
            for change in result.changed:
                change_type = ""
                if change.is_major:
                    change_type = "主版本"
                elif change.is_minor:
                    change_type = "次版本"
                elif change.is_patch:
                    change_type = "补丁"
                lines.append(
                    f"| {change.name} | {change.old_version} | "
                    f"{change.new_version} | {change_type} |"
                )
            lines.append("")

        return lines

    def _render_graph_markdown(self, graph: DependencyGraph) -> List[str]:
        """渲染图谱信息为Markdown / Render graph info as Markdown."""
        lines: List[str] = []
        lines.append("## 依赖图谱")
        lines.append("")
        lines.append(f"- **节点数**: {graph.node_count}")
        lines.append(f"- **边数**: {graph.edge_count}")
        lines.append(f"- **根节点**: {len(graph.get_root_nodes())}")
        lines.append(f"- **叶子节点**: {len(graph.get_leaf_nodes())}")
        lines.append("")

        cycle = graph.detect_cycles()
        if cycle.has_cycle:
            lines.append(f":warning: **检测到循环依赖**: {' -> '.join(cycle.nodes)}")
            lines.append("")

        # Mermaid图 / Mermaid diagram
        lines.append("### Mermaid 图")
        lines.append("")
        lines.append("```mermaid")
        lines.append(graph.to_mermaid())
        lines.append("```")
        lines.append("")

        return lines

    # ============================================================
    # HTML 渲染方法 / HTML rendering methods
    # ============================================================

    def _get_html_header(self) -> str:
        """获取HTML头部和样式 / Get HTML header and styles."""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DepGraph 依赖分析报告</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #f5f7fa; color: #333; line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
h1 { color: #1a1a2e; margin-bottom: 8px; font-size: 1.8em; }
h2 { color: #16213e; margin: 24px 0 12px; padding-bottom: 8px;
     border-bottom: 2px solid #e94560; }
h3 { color: #0f3460; margin: 16px 0 8px; }
.timestamp { color: #666; margin-bottom: 20px; }
.card { background: white; border-radius: 8px; padding: 20px;
        margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
         gap: 12px; margin: 16px 0; }
.stat { background: #f8f9fa; padding: 16px; border-radius: 6px; text-align: center; }
.stat-value { font-size: 1.8em; font-weight: bold; color: #e94560; }
.stat-label { font-size: 0.85em; color: #666; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; }
th { background: #1a1a2e; color: white; padding: 10px 12px; text-align: left; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; }
tr:hover { background: #f8f9fa; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
         font-size: 0.8em; font-weight: 500; }
.badge-low { background: #d4edda; color: #155724; }
.badge-medium { background: #fff3cd; color: #856404; }
.badge-high { background: #f8d7da; color: #721c24; }
.badge-critical { background: #721c24; color: white; }
.badge-added { background: #d4edda; color: #155724; }
.badge-removed { background: #f8d7da; color: #721c24; }
.badge-changed { background: #fff3cd; color: #856404; }
.score-bar { height: 24px; border-radius: 12px; background: #eee; overflow: hidden; }
.score-fill { height: 100%; border-radius: 12px; transition: width 0.3s; }
.score-low { background: #28a745; }
.score-medium { background: #ffc107; }
.score-high { background: #fd7e14; }
.score-critical { background: #dc3545; }
.file-list { list-style: none; padding: 0; }
.file-list li { padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.file-list code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
.recommendations { list-style: none; padding: 0; }
.recommendations li { padding: 10px; margin: 6px 0; background: #fff3cd;
                       border-left: 4px solid #ffc107; border-radius: 0 4px 4px 0; }
.mermaid-container { background: #f8f9fa; padding: 16px; border-radius: 6px;
                     overflow-x: auto; }
.mermaid-container pre { white-space: pre-wrap; font-size: 0.9em; }
</style>
</head>
<body>
"""

    def _render_scan_html(self, result: ScanResult) -> str:
        """渲染扫描结果为HTML / Render scan result as HTML."""
        parts: List[str] = []
        parts.append('<div class="card">')
        parts.append('<h2>扫描概览</h2>')
        parts.append('<div class="stats">')

        stats = result.stats
        for label, value in [
            ("发现文件", len(result.files_found)),
            ("总依赖数", stats.get("total_dependencies", 0)),
            ("生产依赖", stats.get("production_dependencies", 0)),
            ("开发依赖", stats.get("development_dependencies", 0)),
            ("唯一包数", stats.get("unique_packages", 0)),
        ]:
            parts.append(f'<div class="stat"><div class="stat-value">{value}</div>'
                         f'<div class="stat-label">{label}</div></div>')

        parts.append('</div>')

        if result.files_found:
            parts.append('<h3>发现的文件</h3>')
            parts.append('<ul class="file-list">')
            for f in result.files_found:
                parts.append(f'<li><code>{f}</code></li>')
            parts.append('</ul>')

        if result.dependencies:
            parts.append('<h3>依赖列表</h3>')
            parts.append('<table><thead><tr><th>名称</th><th>版本</th>'
                         '<th>类型</th><th>开发依赖</th></tr></thead><tbody>')
            for dep in result.dependencies:
                dev_badge = '<span class="badge badge-medium">Dev</span>' if dep.is_dev else ""
                parts.append(
                    f'<tr><td>{dep.name}</td><td>{dep.version}</td>'
                    f'<td>{dep.source.value}</td><td>{dev_badge}</td></tr>'
                )
            parts.append('</tbody></table>')

        if result.errors:
            parts.append('<h3>错误</h3>')
            for err in result.errors:
                parts.append(f'<p style="color:#dc3545">{err}</p>')

        parts.append('</div>')
        return "\n".join(parts)

    def _render_risk_html(self, report: RiskReport) -> str:
        """渲染风险报告为HTML / Render risk report as HTML."""
        parts: List[str] = []
        level = report._score_to_level(report.overall_score)
        score_class = f"score-{level}"

        parts.append('<div class="card">')
        parts.append('<h2>风险评估</h2>')
        parts.append(f'<h3>综合风险评分: {report.overall_score}/100 '
                     f'<span class="badge badge-{level}">{level}</span></h3>')
        parts.append(f'<div class="score-bar"><div class="score-fill {score_class}" '
                     f'style="width:{report.overall_score}%"></div></div>')

        if report.summary:
            parts.append('<h3>摘要</h3>')
            parts.append('<div class="stats">')
            for key, value in report.summary.items():
                if key != "recommendations":
                    parts.append(f'<div class="stat"><div class="stat-value">{value}</div>'
                                 f'<div class="stat-label">{key}</div></div>')
            parts.append('</div>')

            if "recommendations" in report.summary:
                parts.append('<h3>建议</h3>')
                parts.append('<ul class="recommendations">')
                for rec in report.summary["recommendations"]:
                    parts.append(f'<li>{rec}</li>')
                parts.append('</ul>')

        if report.license_risks:
            parts.append('<h3>许可证风险</h3>')
            parts.append('<table><thead><tr><th>包名</th><th>许可证</th>'
                         '<th>分类</th><th>评分</th><th>等级</th></tr></thead><tbody>')
            for risk in report.license_risks:
                parts.append(
                    f'<tr><td>{risk.name}</td><td>{risk.license}</td>'
                    f'<td>{risk.classification}</td><td>{risk.risk_score}</td>'
                    f'<td><span class="badge badge-{risk.risk_level}">'
                    f'{risk.risk_level}</span></td></tr>'
                )
            parts.append('</tbody></table>')

        parts.append('</div>')
        return "\n".join(parts)

    def _render_diff_html(self, result: DiffResult) -> str:
        """渲染变更检测为HTML / Render diff result as HTML."""
        parts: List[str] = []
        parts.append('<div class="card">')
        parts.append('<h2>依赖变更检测</h2>')

        if not result.has_changes:
            parts.append('<p>未检测到变更。</p>')
            parts.append('</div>')
            return "\n".join(parts)

        parts.append('<div class="stats">')
        for label, value, cls in [
            ("新增", len(result.added), "badge-added"),
            ("删除", len(result.removed), "badge-removed"),
            ("变更", len(result.changed), "badge-changed"),
        ]:
            parts.append(f'<div class="stat"><div class="stat-value">{value}</div>'
                         f'<div class="stat-label"><span class="badge {cls}">'
                         f'{label}</span></div></div>')
        parts.append('</div>')

        if result.added:
            parts.append('<h3>新增依赖</h3>')
            parts.append('<table><thead><tr><th>包名</th><th>版本</th></tr></thead><tbody>')
            for change in result.added:
                parts.append(
                    f'<tr><td><span class="badge badge-added">+</span> {change.name}</td>'
                    f'<td>{change.new_version}</td></tr>'
                )
            parts.append('</tbody></table>')

        if result.removed:
            parts.append('<h3>删除依赖</h3>')
            parts.append('<table><thead><tr><th>包名</th><th>版本</th></tr></thead><tbody>')
            for change in result.removed:
                parts.append(
                    f'<tr><td><span class="badge badge-removed">-</span> {change.name}</td>'
                    f'<td>{change.old_version}</td></tr>'
                )
            parts.append('</tbody></table>')

        if result.changed:
            parts.append('<h3>版本变更</h3>')
            parts.append('<table><thead><tr><th>包名</th><th>旧版本</th>'
                         '<th>新版本</th><th>变更类型</th></tr></thead><tbody>')
            for change in result.changed:
                change_type = ""
                if change.is_major:
                    change_type = '<span class="badge badge-critical">主版本</span>'
                elif change.is_minor:
                    change_type = '<span class="badge badge-changed">次版本</span>'
                elif change.is_patch:
                    change_type = '<span class="badge badge-low">补丁</span>'
                parts.append(
                    f'<tr><td>{change.name}</td><td>{change.old_version}</td>'
                    f'<td>{change.new_version}</td><td>{change_type}</td></tr>'
                )
            parts.append('</tbody></table>')

        parts.append('</div>')
        return "\n".join(parts)

    def _render_graph_html(self, graph: DependencyGraph) -> str:
        """渲染图谱信息为HTML / Render graph info as HTML."""
        parts: List[str] = []
        parts.append('<div class="card">')
        parts.append('<h2>依赖图谱</h2>')
        parts.append('<div class="stats">')
        for label, value in [
            ("节点数", graph.node_count),
            ("边数", graph.edge_count),
            ("根节点", len(graph.get_root_nodes())),
            ("叶子节点", len(graph.get_leaf_nodes())),
        ]:
            parts.append(f'<div class="stat"><div class="stat-value">{value}</div>'
                         f'<div class="stat-label">{label}</div></div>')
        parts.append('</div>')

        cycle = graph.detect_cycles()
        if cycle.has_cycle:
            parts.append(f'<p style="color:#dc3545;font-weight:bold">'
                         f'检测到循环依赖: {" -> ".join(cycle.nodes)}</p>')

        parts.append('<h3>Mermaid 图</h3>')
        parts.append('<div class="mermaid-container"><pre>')
        parts.append(graph.to_mermaid())
        parts.append('</pre></div>')
        parts.append('</div>')

        return "\n".join(parts)
