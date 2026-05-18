"""
供应链风险分析模块 / Supply chain risk analysis module

提供依赖项的风险评估功能，包括：
Provides dependency risk assessment features, including:
- 许可证合规检测 / License compliance detection
- 依赖新鲜度评分 / Dependency freshness scoring
- 依赖深度分析 / Dependency depth analysis
- 重复依赖检测 / Duplicate dependency detection
- 综合风险评分 / Comprehensive risk scoring
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .graph import DependencyGraph, GraphNode
from .parsers.base import Dependency, DepFileType
from .utils import (
    classify_license,
    compare_versions,
    days_since,
    normalize_name,
    parse_date,
    RISKY_LICENSES,
    WEAK_COPYLEFT_LICENSES,
)


@dataclass
class LicenseRisk:
    """
    许可证风险信息 / License risk information

    Attributes:
        name: 包名称 / Package name
        license: 许可证字符串 / License string
        classification: 许可证分类 / License classification
        risk_score: 风险分数(0-100) / Risk score (0-100)
        risk_level: 风险等级 / Risk level
        reason: 风险原因 / Risk reason
    """
    name: str
    license: str
    classification: str = "unknown"
    risk_score: float = 0.0
    risk_level: str = "low"
    reason: str = ""

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "name": self.name,
            "license": self.license,
            "classification": self.classification,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "reason": self.reason,
        }


@dataclass
class FreshnessInfo:
    """
    依赖新鲜度信息 / Dependency freshness information

    Attributes:
        name: 包名称 / Package name
        current_version: 当前版本 / Current version
        is_outdated: 是否过时 / Whether outdated
        version_status: 版本状态 / Version status
    """
    name: str
    current_version: str
    is_outdated: bool = False
    version_status: str = "unknown"

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "name": self.name,
            "current_version": self.current_version,
            "is_outdated": self.is_outdated,
            "version_status": self.version_status,
        }


@dataclass
class DepthAnalysis:
    """
    依赖深度分析结果 / Dependency depth analysis result

    Attributes:
        name: 包名称 / Package name
        depth: 依赖深度 / Dependency depth
        transitive_count: 传递依赖数量 / Transitive dependency count
        risk_level: 风险等级 / Risk level
    """
    name: str
    depth: int = 0
    transitive_count: int = 0
    risk_level: str = "low"

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "name": self.name,
            "depth": self.depth,
            "transitive_count": self.transitive_count,
            "risk_level": self.risk_level,
        }


@dataclass
class RiskReport:
    """
    综合风险报告 / Comprehensive risk report

    Attributes:
        overall_score: 综合风险评分(0-100, 越低越安全) / Overall risk score
        license_risks: 许可证风险列表 / License risk list
        freshness_issues: 新鲜度问题列表 / Freshness issue list
        depth_analyses: 深度分析列表 / Depth analysis list
        duplicates: 重复依赖 / Duplicate dependencies
        summary: 风险摘要 / Risk summary
    """
    overall_score: float = 0.0
    license_risks: List[LicenseRisk] = field(default_factory=list)
    freshness_issues: List[FreshnessInfo] = field(default_factory=list)
    depth_analyses: List[DepthAnalysis] = field(default_factory=list)
    duplicates: Dict[str, List[str]] = field(default_factory=dict)
    summary: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "overall_score": self.overall_score,
            "overall_risk_level": self._score_to_level(self.overall_score),
            "license_risks": [r.to_dict() for r in self.license_risks],
            "freshness_issues": [f.to_dict() for f in self.freshness_issues],
            "depth_analyses": [d.to_dict() for d in self.depth_analyses],
            "duplicates": self.duplicates,
            "summary": self.summary,
        }

    @staticmethod
    def _score_to_level(score: float) -> str:
        """
        将分数转换为风险等级
        Convert score to risk level.

        Args:
            score: 风险分数 / Risk score

        Returns:
            风险等级 / Risk level
        """
        if score <= 20:
            return "low"
        elif score <= 50:
            return "medium"
        elif score <= 75:
            return "high"
        return "critical"


class SupplyChainAnalyzer:
    """
    供应链风险分析器 / Supply chain risk analyzer

    分析依赖项的各种风险因素，生成综合风险评估报告。
    Analyzes various risk factors of dependencies, generates comprehensive risk report.

    使用方法 / Usage:
        analyzer = SupplyChainAnalyzer()
        report = analyzer.analyze(dependencies, graph)
        print(f"Overall risk score: {report.overall_score}")
    """

    def __init__(self):
        """初始化分析器 / Initialize analyzer."""
        # 已知高风险许可证的额外扣分 / Extra penalty for known risky licenses
        self.license_risk_weights = {
            "unknown": 30,       # 未知许可证风险较高 / Unknown license is higher risk
            "copyleft": 50,      # 强Copyleft有传染风险 / Strong copyleft is contagious
            "weak-copyleft": 20, # 弱Copyleft风险较低 / Weak copyleft is lower risk
            "permissive": 0,     # 宽松许可证无风险 / Permissive is no risk
        }

    def analyze(
        self,
        dependencies: List[Dependency],
        graph: Optional[DependencyGraph] = None,
    ) -> RiskReport:
        """
        执行综合风险分析
        Perform comprehensive risk analysis.

        Args:
            dependencies: 依赖列表 / Dependency list
            graph: 依赖图谱（可选）/ Dependency graph (optional)

        Returns:
            风险报告 / Risk report
        """
        report = RiskReport()

        # 1. 许可证风险分析 / License risk analysis
        report.license_risks = self._analyze_licenses(dependencies)

        # 2. 依赖新鲜度分析 / Dependency freshness analysis
        report.freshness_issues = self._analyze_freshness(dependencies)

        # 3. 依赖深度分析 / Dependency depth analysis
        if graph:
            report.depth_analyses = self._analyze_depth(graph)
            report.duplicates = graph.find_duplicates()

        # 4. 计算综合评分 / Calculate overall score
        report.overall_score = self._calculate_overall_score(report)

        # 5. 生成摘要 / Generate summary
        report.summary = self._generate_summary(report, dependencies)

        return report

    def _analyze_licenses(self, dependencies: List[Dependency]) -> List[LicenseRisk]:
        """
        分析许可证风险
        Analyze license risks.

        Args:
            dependencies: 依赖列表 / Dependency list

        Returns:
            许可证风险列表 / License risk list
        """
        risks: List[LicenseRisk] = []

        for dep in dependencies:
            if not dep.license:
                # 无许可证信息 / No license info
                risks.append(LicenseRisk(
                    name=dep.name,
                    license="",
                    classification="unknown",
                    risk_score=40.0,
                    risk_level="medium",
                    reason="未声明许可证 / No license declared",
                ))
                continue

            classification = classify_license(dep.license)
            base_score = self.license_risk_weights.get(classification, 30)

            # 检查是否为已知高风险许可证 / Check if known risky license
            extra_risk = 0
            reason = ""
            if dep.license.lower().strip() in RISKY_LICENSES:
                extra_risk = 20
                reason = "强Copyleft许可证，可能影响项目分发 / Strong copyleft, may affect distribution"
            elif classification == "unknown":
                reason = "无法识别的许可证类型 / Unrecognized license type"
            elif classification == "weak-copyleft":
                reason = "弱Copyleft许可证，注意文件级别传染 / Weak copyleft, note file-level contagion"

            risk_score = min(100.0, base_score + extra_risk)
            risk_level = self._score_to_level(risk_score)

            risks.append(LicenseRisk(
                name=dep.name,
                license=dep.license,
                classification=classification,
                risk_score=risk_score,
                risk_level=risk_level,
                reason=reason,
            ))

        # 按风险分数排序 / Sort by risk score
        risks.sort(key=lambda r: r.risk_score, reverse=True)

        return risks

    def _analyze_freshness(self, dependencies: List[Dependency]) -> List[FreshnessInfo]:
        """
        分析依赖新鲜度
        Analyze dependency freshness.

        基于版本号格式和约束宽松度评估。
        Assessed based on version format and constraint looseness.

        Args:
            dependencies: 依赖列表 / Dependency list

        Returns:
            新鲜度信息列表 / Freshness info list
        """
        issues: List[FreshnessInfo] = []

        for dep in dependencies:
            version = dep.version
            if not version or version in ("editable", "*"):
                issues.append(FreshnessInfo(
                    name=dep.name,
                    current_version=version,
                    is_outdated=False,
                    version_status="unconstrained",
                ))
                continue

            # 分析版本约束 / Analyze version constraint
            status = self._classify_version_constraint(version)
            is_outdated = status in ("pinned_old", "range_wide")

            issues.append(FreshnessInfo(
                name=dep.name,
                current_version=version,
                is_outdated=is_outdated,
                version_status=status,
            ))

        return issues

    def _classify_version_constraint(self, version: str) -> str:
        """
        分类版本约束
        Classify version constraint.

        Args:
            version: 版本约束字符串 / Version constraint string

        Returns:
            版本状态 / Version status
        """
        v = version.lower().strip()

        if v.startswith("^"):
            return "caret_range"     # 兼容版本范围 / Compatible range
        elif v.startswith("~"):
            return "tilde_range"     # 补丁版本范围 / Patch range
        elif v.startswith(">="):
            return "min_version"     # 最低版本 / Minimum version
        elif v.startswith("==") or v.startswith("="):
            return "pinned"          # 精确版本 / Pinned version
        elif v.startswith(">"):
            return "greater_than"    # 大于 / Greater than
        elif v.startswith("<"):
            return "less_than"      # 小于 / Less than
        elif "*" in v:
            return "any"             # 任意版本 / Any version
        else:
            return "exact"           # 精确版本（无前缀）/ Exact (no prefix)

    def _analyze_depth(self, graph: DependencyGraph) -> List[DepthAnalysis]:
        """
        分析依赖深度
        Analyze dependency depth.

        Args:
            graph: 依赖图谱 / Dependency graph

        Returns:
            深度分析列表 / Depth analysis list
        """
        analyses: List[DepthAnalysis] = []
        depths = graph.compute_depths()

        for name, depth in depths.items():
            transitive = graph.get_transitive_dependencies(name)
            risk_level = self._depth_to_risk(depth)

            analyses.append(DepthAnalysis(
                name=name,
                depth=depth,
                transitive_count=len(transitive),
                risk_level=risk_level,
            ))

        # 按深度排序 / Sort by depth
        analyses.sort(key=lambda a: a.depth, reverse=True)

        return analyses

    def _depth_to_risk(self, depth: int) -> str:
        """
        将深度转换为风险等级
        Convert depth to risk level.

        Args:
            depth: 依赖深度 / Dependency depth

        Returns:
            风险等级 / Risk level
        """
        if depth <= 2:
            return "low"
        elif depth <= 5:
            return "medium"
        elif depth <= 8:
            return "high"
        return "critical"

    def _calculate_overall_score(self, report: RiskReport) -> float:
        """
        计算综合风险评分
        Calculate overall risk score.

        评分算法 / Scoring algorithm:
        - 许可证风险权重: 40%
        - 新鲜度问题权重: 20%
        - 深度风险权重: 25%
        - 重复依赖权重: 15%

        Args:
            report: 风险报告 / Risk report

        Returns:
            综合评分(0-100) / Overall score (0-100)
        """
        total = len(report.license_risks) + len(report.freshness_issues) + 1

        # 许可证风险得分 / License risk score
        if report.license_risks:
            license_score = sum(r.risk_score for r in report.license_risks) / len(report.license_risks)
        else:
            license_score = 0

        # 新鲜度得分 / Freshness score
        if report.freshness_issues:
            freshness_score = sum(
                30 if f.is_outdated else 10
                for f in report.freshness_issues
            ) / len(report.freshness_issues)
        else:
            freshness_score = 0

        # 深度风险得分 / Depth risk score
        if report.depth_analyses:
            depth_score = sum(
                min(100, d.depth * 10)
                for d in report.depth_analyses
            ) / len(report.depth_analyses)
        else:
            depth_score = 0

        # 重复依赖得分 / Duplicate score
        if report.duplicates:
            dup_score = min(100, len(report.duplicates) * 25)
        else:
            dup_score = 0

        # 加权平均 / Weighted average
        overall = (
            license_score * 0.40
            + freshness_score * 0.20
            + depth_score * 0.25
            + dup_score * 0.15
        )

        return round(min(100.0, max(0.0, overall)), 1)

    def _generate_summary(
        self,
        report: RiskReport,
        dependencies: List[Dependency],
    ) -> Dict:
        """
        生成风险摘要
        Generate risk summary.

        Args:
            report: 风险报告 / Risk report
            dependencies: 依赖列表 / Dependency list

        Returns:
            摘要字典 / Summary dictionary
        """
        high_license_risks = [
            r for r in report.license_risks if r.risk_level in ("high", "critical")
        ]
        outdated_deps = [
            f for f in report.freshness_issues if f.is_outdated
        ]
        deep_deps = [
            d for d in report.depth_analyses if d.risk_level in ("high", "critical")
        ]

        total_deps = len(dependencies)
        prod_deps = len([d for d in dependencies if not d.is_dev])
        dev_deps = len([d for d in dependencies if d.is_dev])

        return {
            "total_dependencies": total_deps,
            "production_dependencies": prod_deps,
            "development_dependencies": dev_deps,
            "high_risk_licenses": len(high_license_risks),
            "outdated_dependencies": len(outdated_deps),
            "deep_dependencies": len(deep_deps),
            "duplicate_packages": len(report.duplicates),
            "recommendations": self._generate_recommendations(
                high_license_risks, outdated_deps, deep_deps, report.duplicates
            ),
        }

    def _generate_recommendations(
        self,
        license_risks: List[LicenseRisk],
        outdated: List[FreshnessInfo],
        deep: List[DepthAnalysis],
        duplicates: Dict[str, List[str]],
    ) -> List[str]:
        """
        生成改进建议
        Generate improvement recommendations.

        Args:
            license_risks: 高风险许可证 / High-risk licenses
            outdated: 过时依赖 / Outdated dependencies
            deep: 深层依赖 / Deep dependencies
            duplicates: 重复依赖 / Duplicate dependencies

        Returns:
            建议列表 / Recommendation list
        """
        recommendations: List[str] = []

        if license_risks:
            names = [r.name for r in license_risks[:5]]
            recommendations.append(
                f"许可证风险: {', '.join(names)} 等包存在许可证合规问题，"
                f"建议审查许可证兼容性 / License risk: review license compatibility"
            )

        if outdated:
            names = [f.name for f in outdated[:5]]
            recommendations.append(
                f"过时依赖: {', '.join(names)} 等包可能需要更新 / "
                f"Outdated: consider updating these packages"
            )

        if deep:
            names = [d.name for d in deep[:5]]
            recommendations.append(
                f"深层依赖: {', '.join(names)} 等包依赖链较深，"
                f"建议评估是否可以简化 / Deep deps: consider simplifying"
            )

        if duplicates:
            names = list(duplicates.keys())[:5]
            recommendations.append(
                f"重复依赖: {', '.join(names)} 等包存在多版本，"
                f"建议统一版本 / Duplicates: consider unifying versions"
            )

        if not recommendations:
            recommendations.append(
                "未发现明显风险，依赖状态良好 / "
                "No significant risks found, dependency status is good"
            )

        return recommendations

    @staticmethod
    def _score_to_level(score: float) -> str:
        """
        将分数转换为风险等级
        Convert score to risk level.

        Args:
            score: 风险分数 / Risk score

        Returns:
            风险等级 / Risk level
        """
        if score <= 20:
            return "low"
        elif score <= 50:
            return "medium"
        elif score <= 75:
            return "high"
        return "critical"
