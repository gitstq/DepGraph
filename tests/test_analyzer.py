"""
风险分析器测试 / Risk analyzer tests

测试供应链风险分析器的核心功能。
Tests core functionality of the supply chain risk analyzer.
"""

import json
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from depgraph.analyzer import SupplyChainAnalyzer, RiskReport
from depgraph.graph import DependencyGraph
from depgraph.parsers.base import Dependency, DepFileType


class TestSupplyChainAnalyzer(unittest.TestCase):
    """供应链风险分析器测试 / Supply chain risk analyzer tests."""

    def setUp(self):
        self.analyzer = SupplyChainAnalyzer()

    def test_empty_dependencies(self):
        """测试空依赖列表 / Test empty dependency list."""
        report = self.analyzer.analyze([])
        self.assertIsInstance(report, RiskReport)
        self.assertEqual(report.overall_score, 0)

    def test_license_risk_unknown(self):
        """测试未知许可证风险 / Test unknown license risk."""
        deps = [
            Dependency(name="pkg-a", version="1.0", license="UnknownLicense"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(len(report.license_risks), 1)
        self.assertEqual(report.license_risks[0].classification, "unknown")

    def test_license_risk_permissive(self):
        """测试宽松许可证无风险 / Test permissive license no risk."""
        deps = [
            Dependency(name="pkg-a", version="1.0", license="MIT"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(len(report.license_risks), 1)
        self.assertEqual(report.license_risks[0].classification, "permissive")
        self.assertEqual(report.license_risks[0].risk_score, 0)

    def test_license_risk_copyleft(self):
        """测试Copyleft许可证风险 / Test copyleft license risk."""
        deps = [
            Dependency(name="pkg-a", version="1.0", license="GPL-3.0"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(len(report.license_risks), 1)
        self.assertGreater(report.license_risks[0].risk_score, 50)

    def test_no_license(self):
        """测试无许可证信息 / Test no license info."""
        deps = [
            Dependency(name="pkg-a", version="1.0", license=""),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(len(report.license_risks), 1)
        self.assertEqual(report.license_risks[0].classification, "unknown")

    def test_freshness_pinned_version(self):
        """测试精确版本约束 / Test pinned version constraint."""
        deps = [
            Dependency(name="pkg-a", version="==1.0.0"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(len(report.freshness_issues), 1)
        self.assertEqual(report.freshness_issues[0].version_status, "pinned")

    def test_freshness_caret_range(self):
        """测试caret版本范围 / Test caret version range."""
        deps = [
            Dependency(name="pkg-a", version="^1.0.0"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(report.freshness_issues[0].version_status, "caret_range")

    def test_overall_score_range(self):
        """测试综合评分范围 / Test overall score range."""
        deps = [
            Dependency(name="pkg-a", version="1.0", license="MIT"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertGreaterEqual(report.overall_score, 0)
        self.assertLessEqual(report.overall_score, 100)

    def test_summary_has_recommendations(self):
        """测试摘要包含建议 / Test summary has recommendations."""
        deps = [
            Dependency(name="pkg-a", version="1.0", license="MIT"),
        ]
        report = self.analyzer.analyze(deps)
        self.assertIn("recommendations", report.summary)
        self.assertGreater(len(report.summary["recommendations"]), 0)

    def test_summary_dependency_counts(self):
        """测试摘要依赖计数 / Test summary dependency counts."""
        deps = [
            Dependency(name="pkg-a", version="1.0", is_dev=False),
            Dependency(name="pkg-b", version="2.0", is_dev=True),
        ]
        report = self.analyzer.analyze(deps)
        self.assertEqual(report.summary["total_dependencies"], 2)
        self.assertEqual(report.summary["production_dependencies"], 1)
        self.assertEqual(report.summary["development_dependencies"], 1)

    def test_with_graph_depth_analysis(self):
        """测试带图谱的深度分析 / Test depth analysis with graph."""
        deps = [
            Dependency(name="pkg-a", version="1.0"),
            Dependency(name="pkg-b", version="2.0"),
        ]
        graph = DependencyGraph()
        graph.build_from_dict({
            "pkg-a": ["pkg-b"],
            "pkg-b": [],
        })

        report = self.analyzer.analyze(deps, graph)
        self.assertGreater(len(report.depth_analyses), 0)


class TestDependencyGraph(unittest.TestCase):
    """依赖图谱测试 / Dependency graph tests."""

    def setUp(self):
        self.graph = DependencyGraph()

    def test_empty_graph(self):
        """测试空图谱 / Test empty graph."""
        self.assertEqual(self.graph.node_count, 0)
        self.assertEqual(self.graph.edge_count, 0)

    def test_build_from_dict(self):
        """测试从字典构建 / Test build from dict."""
        self.graph.build_from_dict({
            "a": ["b", "c"],
            "b": ["c"],
            "c": [],
        })
        self.assertEqual(self.graph.node_count, 3)
        self.assertEqual(self.graph.edge_count, 3)

    def test_topological_sort(self):
        """测试拓扑排序 / Test topological sort."""
        self.graph.build_from_dict({
            "a": ["b", "c"],
            "b": ["c"],
            "c": [],
        })
        sorted_nodes = self.graph.topological_sort()
        self.assertEqual(len(sorted_nodes), 3)
        # c 应该在 a 和 b 之前 / c should come before a and b
        self.assertIn("c", sorted_nodes)

    def test_cycle_detection(self):
        """测试环检测 / Test cycle detection."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": ["c"],
            "c": ["a"],
        })
        cycle = self.graph.detect_cycles()
        self.assertTrue(cycle.has_cycle)

    def test_no_cycle(self):
        """测试无环 / Test no cycle."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": ["c"],
            "c": [],
        })
        cycle = self.graph.detect_cycles()
        self.assertFalse(cycle.has_cycle)

    def test_transitive_dependencies(self):
        """测试传递依赖 / Test transitive dependencies."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": ["c"],
            "c": [],
        })
        trans = self.graph.get_transitive_dependencies("a")
        self.assertEqual(trans, {"b", "c"})

    def test_leaf_nodes(self):
        """测试叶子节点 / Test leaf nodes."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": [],
            "c": [],
        })
        leaves = self.graph.get_leaf_nodes()
        self.assertIn("b", leaves)
        self.assertIn("c", leaves)
        self.assertNotIn("a", leaves)

    def test_root_nodes(self):
        """测试根节点 / Test root nodes."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": [],
            "c": [],
        })
        roots = self.graph.get_root_nodes()
        self.assertIn("a", roots)
        self.assertIn("c", roots)
        self.assertNotIn("b", roots)

    def test_to_mermaid(self):
        """测试Mermaid图生成 / Test Mermaid diagram generation."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": [],
        })
        mermaid = self.graph.to_mermaid()
        self.assertIn("graph TD", mermaid)
        self.assertIn("a", mermaid)
        self.assertIn("b", mermaid)

    def test_compute_depths(self):
        """测试深度计算 / Test depth computation."""
        self.graph.build_from_dict({
            "a": ["b"],
            "b": ["c"],
            "c": [],
        })
        depths = self.graph.compute_depths()
        self.assertEqual(depths["c"], 0)
        self.assertEqual(depths["b"], 1)
        self.assertEqual(depths["a"], 2)


if __name__ == "__main__":
    unittest.main()
