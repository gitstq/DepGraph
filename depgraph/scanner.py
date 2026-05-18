"""
依赖文件扫描器模块 / Dependency file scanner module

递归扫描目录，自动识别和解析依赖文件。
Recursively scans directories, automatically identifies and parses dependency files.

功能 / Features:
- 递归目录扫描 / Recursive directory scanning
- 自动识别依赖文件类型 / Auto-detect dependency file types
- 支持忽略目录和文件 / Support ignoring directories and files
- 多文件类型并行解析 / Multi-file-type parsing
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .parsers import get_parser_by_filename, get_all_parsers
from .parsers.base import BaseParser, Dependency, DepFileType
from .utils import read_file_safe


# 默认忽略的目录名 / Default ignored directory names
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git", ".svn", ".hg",           # 版本控制 / Version control
    "node_modules", "vendor",         # 依赖目录 / Dependency directories
    ".venv", "venv", "env",           # Python虚拟环境 / Python virtual envs
    "__pycache__", ".pytest_cache",   # Python缓存 / Python caches
    ".tox", ".mypy_cache",            # Python工具缓存 / Python tool caches
    "build", "dist", "target",        # 构建输出 / Build outputs
    ".gradle", ".mvn",                # Java工具缓存 / Java tool caches
    "vendor/bundle", ".bundle",       # Ruby vendor / Ruby vendor
    "bower_components",               # Bower组件 / Bower components
    ".idea", ".vscode",               # IDE配置 / IDE configs
    "coverage", ".nyc_output",        # 测试覆盖率 / Test coverage
    ".next", ".nuxt",                 # 框架构建 / Framework builds
    "site-packages",                  # Python site-packages
}

# 默认忽略的文件名模式 / Default ignored file patterns
DEFAULT_IGNORE_FILES: Set[str] = {
    "package-lock.json",              # npm lock文件 / npm lock file
    "yarn.lock",                      # yarn lock文件 / yarn lock file
    "pnpm-lock.yaml",                 # pnpm lock文件 / pnpm lock file
    "Pipfile.lock",                   # pip lock文件 / pip lock file
    "poetry.lock",                    # poetry lock文件 / poetry lock file
    "composer.lock",                  # composer lock文件 / composer lock file
    "Gemfile.lock",                   # gem lock文件 / gem lock file
    "Cargo.lock",                     # cargo lock文件 / cargo lock file
    "go.sum",                         # go sum文件 / go sum file
    "gradle.lockfile",                # gradle lock文件 / gradle lock file
}

# 依赖文件名到类型的映射 / Dependency filename to type mapping
DEPENDENCY_FILES: Dict[str, DepFileType] = {
    "package.json": DepFileType.PACKAGE_JSON,
    "requirements.txt": DepFileType.REQUIREMENTS_TXT,
    "pyproject.toml": DepFileType.PYPROJECT_TOML,
    "go.mod": DepFileType.GO_MOD,
    "Cargo.toml": DepFileType.CARGO_TOML,
    "pom.xml": DepFileType.POM_XML,
    "build.gradle": DepFileType.BUILD_GRADLE,
    "Gemfile": DepFileType.GEMFILE,
    "composer.json": DepFileType.COMPOSER_JSON,
}


@dataclass
class ScanResult:
    """
    扫描结果数据类 / Scan result data class

    Attributes:
        root_path: 扫描根目录 / Scan root directory
        files_found: 发现的依赖文件列表 / Found dependency files
        dependencies: 解析出的所有依赖 / All parsed dependencies
        errors: 扫描过程中的错误 / Errors during scanning
        stats: 扫描统计信息 / Scan statistics
    """
    root_path: str = ""
    files_found: List[str] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "root_path": self.root_path,
            "files_found": self.files_found,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "dependency_count": len(self.dependencies),
            "errors": self.errors,
            "stats": self.stats,
        }


class DependencyScanner:
    """
    依赖文件扫描器 / Dependency file scanner

    递归扫描目录树，识别并解析所有依赖文件。
    Recursively scans directory tree, identifies and parses all dependency files.

    使用方法 / Usage:
        scanner = DependencyScanner()
        result = scanner.scan("/path/to/project")
        for dep in result.dependencies:
            print(f"{dep.name} @ {dep.version}")
    """

    def __init__(
        self,
        ignore_dirs: Optional[Set[str]] = None,
        ignore_files: Optional[Set[str]] = None,
        max_depth: int = 20,
        follow_symlinks: bool = False,
    ):
        """
        初始化扫描器 / Initialize scanner.

        Args:
            ignore_dirs: 要忽略的目录名集合 / Directory names to ignore
            ignore_files: 要忽略的文件名集合 / File names to ignore
            max_depth: 最大递归深度 / Maximum recursion depth
            follow_symlinks: 是否跟随符号链接 / Whether to follow symlinks
        """
        self.ignore_dirs = ignore_dirs or DEFAULT_IGNORE_DIRS
        self.ignore_files = ignore_files or DEFAULT_IGNORE_FILES
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks

    def scan(self, path: str) -> ScanResult:
        """
        扫描指定目录
        Scan the specified directory.

        Args:
            path: 要扫描的目录路径 / Directory path to scan

        Returns:
            扫描结果 / Scan result
        """
        result = ScanResult(root_path=os.path.abspath(path))

        if not os.path.isdir(path):
            result.errors.append(f"目录不存在: {path}")
            return result

        # 收集依赖文件 / Collect dependency files
        dep_files = self._find_dependency_files(path)

        if not dep_files:
            result.errors.append("未找到依赖文件 / No dependency files found")
            return result

        result.files_found = dep_files

        # 解析每个文件 / Parse each file
        file_type_counts: Dict[str, int] = {}
        for filepath in dep_files:
            filename = os.path.basename(filepath)
            file_type = DEPENDENCY_FILES.get(filename, DepFileType.UNKNOWN)

            parser = get_parser_by_filename(filename)
            if parser is None:
                result.errors.append(f"不支持的文件类型: {filename}")
                continue

            content = read_file_safe(filepath)
            if content is None:
                result.errors.append(f"无法读取文件: {filepath}")
                continue

            try:
                deps = parser.parse(content)
                result.dependencies.extend(deps)
                file_type_counts[file_type.value] = (
                    file_type_counts.get(file_type.value, 0) + 1
                )
            except Exception as e:
                result.errors.append(f"解析 {filepath} 失败: {str(e)}")

        # 统计信息 / Statistics
        total = len(result.dependencies)
        prod_deps = [d for d in result.dependencies if not d.is_dev]
        dev_deps = [d for d in result.dependencies if d.is_dev]

        result.stats = {
            "total_dependencies": total,
            "production_dependencies": len(prod_deps),
            "development_dependencies": len(dev_deps),
            "files_scanned": len(dep_files),
            "file_types": file_type_counts,
            "unique_packages": len({d.name.lower() for d in result.dependencies}),
        }

        return result

    def _find_dependency_files(self, root: str) -> List[str]:
        """
        递归查找依赖文件
        Recursively find dependency files.

        Args:
            root: 根目录 / Root directory

        Returns:
            依赖文件路径列表 / List of dependency file paths
        """
        found_files: List[str] = []

        for dirpath, dirnames, filenames in os.walk(root, followlinks=self.follow_symlinks):
            # 计算当前深度 / Calculate current depth
            rel_path = os.path.relpath(dirpath, root)
            depth = rel_path.count(os.sep) if rel_path != "." else 0

            if depth > self.max_depth:
                dirnames.clear()
                continue

            # 过滤忽略的目录 / Filter ignored directories
            dirnames[:] = [
                d for d in dirnames
                if d not in self.ignore_dirs and not d.startswith(".")
            ]

            # 查找依赖文件 / Find dependency files
            for filename in filenames:
                if filename in DEPENDENCY_FILES and filename not in self.ignore_files:
                    filepath = os.path.join(dirpath, filename)
                    found_files.append(filepath)

        return found_files

    def scan_single_file(self, filepath: str) -> List[Dependency]:
        """
        扫描单个依赖文件
        Scan a single dependency file.

        Args:
            filepath: 文件路径 / File path

        Returns:
            依赖列表 / Dependency list
        """
        filename = os.path.basename(filepath)
        parser = get_parser_by_filename(filename)

        if parser is None:
            return []

        content = read_file_safe(filepath)
        if content is None:
            return []

        try:
            return parser.parse(content)
        except Exception:
            return []
