"""
依赖变更检测模块 / Dependency change detection module

对比两个时间点的依赖快照，检测新增、删除和版本变更。
Compares dependency snapshots at two points in time, detects additions,
deletions, and version changes.

功能 / Features:
- 对比两个依赖列表的差异 / Compare differences between two dependency lists
- 对比声明文件与lock文件的差异 / Compare declared files with lock files
- 生成结构化的变更报告 / Generate structured change report
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .parsers.base import Dependency, DepFileType
from .utils import compare_versions, normalize_name


@dataclass
class VersionChange:
    """
    版本变更信息 / Version change information

    Attributes:
        name: 包名称 / Package name
        old_version: 旧版本 / Old version
        new_version: 新版本 / New version
        change_type: 变更类型 / Change type
        is_major: 是否为主版本变更 / Whether major version change
        is_minor: 是否为次版本变更 / Whether minor version change
        is_patch: 是否为补丁版本变更 / Whether patch version change
    """
    name: str
    old_version: str = ""
    new_version: str = ""
    change_type: str = "changed"  # added, removed, changed
    is_major: bool = False
    is_minor: bool = False
    is_patch: bool = False

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "name": self.name,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "change_type": self.change_type,
            "is_major": self.is_major,
            "is_minor": self.is_minor,
            "is_patch": self.is_patch,
        }


@dataclass
class DiffResult:
    """
    变更检测结果 / Change detection result

    Attributes:
        added: 新增的依赖 / Added dependencies
        removed: 删除的依赖 / Removed dependencies
        changed: 版本变更的依赖 / Changed dependencies
        unchanged: 未变更的依赖 / Unchanged dependencies
        summary: 变更摘要 / Change summary
    """
    added: List[VersionChange] = field(default_factory=list)
    removed: List[VersionChange] = field(default_factory=list)
    changed: List[VersionChange] = field(default_factory=list)
    unchanged: List[Dependency] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """是否存在变更 / Whether there are changes."""
        return bool(self.added or self.removed or self.changed)

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "has_changes": self.has_changes,
            "added": [c.to_dict() for c in self.added],
            "removed": [c.to_dict() for c in self.removed],
            "changed": [c.to_dict() for c in self.changed],
            "unchanged_count": len(self.unchanged),
            "summary": self.summary,
        }


class DependencyDiffer:
    """
    依赖变更检测器 / Dependency change detector

    对比两组依赖列表，识别新增、删除和版本变更。
    Compares two dependency lists, identifies additions, deletions, and version changes.

    使用方法 / Usage:
        differ = DependencyDiffer()
        result = differ.diff(old_deps, new_deps)
        if result.has_changes:
            print(f"Found {len(result.added)} additions")
    """

    def diff(
        self,
        old_deps: List[Dependency],
        new_deps: List[Dependency],
        source_label_old: str = "old",
        source_label_new: str = "new",
    ) -> DiffResult:
        """
        对比两组依赖列表
        Compare two dependency lists.

        Args:
            old_deps: 旧依赖列表 / Old dependency list
            new_deps: 新依赖列表 / New dependency list
            source_label_old: 旧来源标签 / Old source label
            source_label_new: 新来源标签 / New source label

        Returns:
            变更检测结果 / Diff result
        """
        result = DiffResult()

        # 构建名称到依赖的映射 / Build name-to-dependency mapping
        old_map: Dict[str, Dependency] = {}
        for dep in old_deps:
            key = normalize_name(dep.name)
            if key not in old_map:
                old_map[key] = dep

        new_map: Dict[str, Dependency] = {}
        for dep in new_deps:
            key = normalize_name(dep.name)
            if key not in new_map:
                new_map[key] = dep

        old_names = set(old_map.keys())
        new_names = set(new_map.keys())

        # 检测新增 / Detect additions
        added_names = new_names - old_names
        for name in sorted(added_names):
            dep = new_map[name]
            result.added.append(VersionChange(
                name=dep.name,
                new_version=dep.version,
                change_type="added",
            ))

        # 检测删除 / Detect removals
        removed_names = old_names - new_names
        for name in sorted(removed_names):
            dep = old_map[name]
            result.removed.append(VersionChange(
                name=dep.name,
                old_version=dep.version,
                change_type="removed",
            ))

        # 检测版本变更 / Detect version changes
        common_names = old_names & new_names
        for name in sorted(common_names):
            old_dep = old_map[name]
            new_dep = new_map[name]

            if old_dep.version != new_dep.version:
                cmp = compare_versions(old_dep.version, new_dep.version)
                is_major = False
                is_minor = False
                is_patch = False

                # 简化的语义化版本比较 / Simplified semver comparison
                old_parts = old_dep.version.lstrip("^~>=<").split(".")
                new_parts = new_dep.version.lstrip("^~>=<").split(".")

                if len(old_parts) >= 1 and len(new_parts) >= 1:
                    try:
                        if int(new_parts[0]) > int(old_parts[0]):
                            is_major = True
                        elif len(old_parts) >= 2 and len(new_parts) >= 2:
                            if int(new_parts[1]) > int(old_parts[1]):
                                is_minor = True
                            elif len(old_parts) >= 3 and len(new_parts) >= 3:
                                if int(new_parts[2]) > int(old_parts[2]):
                                    is_patch = True
                    except ValueError:
                        pass

                result.changed.append(VersionChange(
                    name=old_dep.name,
                    old_version=old_dep.version,
                    new_version=new_dep.version,
                    change_type="changed",
                    is_major=is_major,
                    is_minor=is_minor,
                    is_patch=is_patch,
                ))
            else:
                result.unchanged.append(old_dep)

        # 生成摘要 / Generate summary
        result.summary = {
            "source_old": source_label_old,
            "source_new": source_label_new,
            "total_added": len(result.added),
            "total_removed": len(result.removed),
            "total_changed": len(result.changed),
            "total_unchanged": len(result.unchanged),
            "major_changes": len([c for c in result.changed if c.is_major]),
            "minor_changes": len([c for c in result.changed if c.is_minor]),
            "patch_changes": len([c for c in result.changed if c.is_patch]),
        }

        return result

    @staticmethod
    def _detect_parser_by_content(content: str):
        """
        通过文件内容自动检测解析器
        Auto-detect parser by file content.

        Args:
            content: 文件内容 / File content

        Returns:
            解析器实例或None / Parser instance or None
        """
        from .parsers import get_parser, get_all_parsers
        from .parsers.base import DepFileType

        if not content:
            return None

        stripped = content.strip()

        # JSON 格式检测 / JSON format detection
        if stripped.startswith("{"):
            try:
                import json
                data = json.loads(stripped)
                if "dependencies" in data or "devDependencies" in data:
                    return get_parser(DepFileType.PACKAGE_JSON)
                if "require" in data or "require-dev" in data:
                    return get_parser(DepFileType.COMPOSER_JSON)
            except (json.JSONDecodeError, TypeError):
                pass

        # Go mod 检测 / Go mod detection
        if stripped.startswith("module "):
            return get_parser(DepFileType.GO_MOD)

        # XML 格式检测 / XML format detection
        if stripped.startswith("<"):
            if "<project>" in stripped or "<dependencies>" in stripped:
                return get_parser(DepFileType.POM_XML)

        # Gemfile 检测 / Gemfile detection
        if "gem " in stripped and ("source" in stripped or "ruby" in stripped):
            return get_parser(DepFileType.GEMFILE)

        # Gradle 检测 / Gradle detection
        if "dependencies {" in stripped or "dependencies {" in stripped:
            return get_parser(DepFileType.BUILD_GRADLE)

        # TOML 格式检测 / TOML format detection
        if "[dependencies]" in stripped or "[package]" in stripped:
            if "name = " in stripped and "version = " in stripped:
                return get_parser(DepFileType.CARGO_TOML)

        # Python requirements 检测 / Python requirements detection
        lines = stripped.splitlines()
        if any(line.strip().startswith(("pip", "setuptools", "wheel", "flask",
                                         "requests", "django", "numpy", "pandas"))
               for line in lines[:5]):
            return get_parser(DepFileType.REQUIREMENTS_TXT)

        # 尝试所有解析器 / Try all parsers
        for parser in get_all_parsers():
            try:
                deps = parser.parse(content)
                if deps:
                    return parser
            except Exception:
                continue

        return None

    def diff_files(
        self,
        old_file: str,
        new_file: str,
        file_type: Optional[DepFileType] = None,
    ) -> DiffResult:
        """
        对比两个依赖文件
        Compare two dependency files.

        Args:
            old_file: 旧文件路径 / Old file path
            new_file: 新文件路径 / New file path
            file_type: 文件类型（自动检测）/ File type (auto-detect)

        Returns:
            变更检测结果 / Diff result
        """
        from .parsers import get_parser_by_filename
        from .utils import read_file_safe
        import os

        # 读取旧文件 / Read old file
        old_content = read_file_safe(old_file)
        if old_content is None:
            return DiffResult(summary={"error": f"无法读取文件: {old_file}"})

        # 读取新文件 / Read new file
        new_content = read_file_safe(new_file)
        if new_content is None:
            return DiffResult(summary={"error": f"无法读取文件: {new_file}"})

        # 获取解析器（使用文件名而非完整路径）/ Get parser (use filename not full path)
        old_parser = get_parser_by_filename(os.path.basename(old_file))
        new_parser = get_parser_by_filename(os.path.basename(new_file))

        # 如果通过文件名无法识别，尝试通过内容自动检测
        # If cannot identify by filename, try content-based auto-detection
        if old_parser is None:
            old_parser = self._detect_parser_by_content(old_content)
        if new_parser is None:
            new_parser = self._detect_parser_by_content(new_content)

        if old_parser is None or new_parser is None:
            return DiffResult(summary={"error": "不支持的文件类型"})

        try:
            old_deps = old_parser.parse(old_content)
            new_deps = new_parser.parse(new_content)
        except Exception as e:
            return DiffResult(summary={"error": f"解析错误: {str(e)}"})

        return self.diff(old_deps, new_deps, old_file, new_file)

    def diff_lock_vs_declared(
        self,
        declared_deps: List[Dependency],
        lock_deps: List[Dependency],
    ) -> DiffResult:
        """
        对比声明文件与lock文件
        Compare declared dependencies with lock file dependencies.

        检测lock文件中是否存在声明文件中没有的依赖（传递依赖泄露）。
        Detects if lock file contains deps not in declared file (transitive leak).

        Args:
            declared_deps: 声明文件中的依赖 / Declared dependencies
            lock_deps: lock文件中的依赖 / Lock file dependencies

        Returns:
            变更检测结果 / Diff result
        """
        result = self.diff(declared_deps, lock_deps, "declared", "lock")

        # 标记额外的分析 / Mark additional analysis
        if result.summary:
            result.summary["analysis_type"] = "lock_vs_declared"
            result.summary["undeclared_in_lock"] = len(result.added)
            result.summary["missing_in_lock"] = len(result.removed)

        return result
