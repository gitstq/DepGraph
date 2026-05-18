"""
工具函数模块 / Utility functions module

提供项目中通用的辅助函数，包括：
- 版本号比较与解析
- 文件读写辅助
- 日期时间处理
- 通用数据转换

Provides common utility functions used across the project:
- Version comparison and parsing
- File I/O helpers
- Date/time processing
- General data conversion
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 版本号相关 / Version related utilities
# ============================================================

def parse_version(version_str: str) -> Tuple[int, ...]:
    """
    解析语义化版本号为可比较的元组
    Parse semantic version string into a comparable tuple.

    支持格式 / Supported formats:
    - "1.2.3" -> (1, 2, 3)
    - "1.2.3-beta" -> (1, 2, 3)
    - "^1.2.3" -> (1, 2, 3)
    - "~1.2.3" -> (1, 2, 3)
    - ">=1.2.3" -> (1, 2, 3)
    - "v1.2.3" -> (1, 2, 3)

    Args:
        version_str: 版本号字符串 / Version string

    Returns:
        版本号元组 / Version tuple
    """
    if not version_str:
        return (0, 0, 0)

    # 移除常见前缀和修饰符 / Remove common prefixes and modifiers
    cleaned = version_str.strip()
    for prefix in ("^", "~", ">=", "<=", ">", "<", "=", "v", "V"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    # 提取数字部分 / Extract numeric parts
    match = re.match(r"(\d+(?:\.\d+)*)", cleaned)
    if match:
        return tuple(int(x) for x in match.group(1).split("."))

    return (0, 0, 0)


def compare_versions(v1: str, v2: str) -> int:
    """
    比较两个版本号
    Compare two version strings.

    Args:
        v1: 第一个版本号 / First version string
        v2: 第二个版本号 / Second version string

    Returns:
        -1 如果 v1 < v2 / if v1 < v2
         0 如果 v1 == v2 / if v1 == v2
         1 如果 v1 > v2 / if v1 > v2
    """
    p1 = parse_version(v1)
    p2 = parse_version(v2)

    # 补齐长度 / Pad to equal length
    max_len = max(len(p1), len(p2))
    p1 = p1 + (0,) * (max_len - len(p1))
    p2 = p2 + (0,) * (max_len - len(p2))

    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


def is_version_outdated(current: str, latest: str) -> bool:
    """
    检查当前版本是否过时
    Check if the current version is outdated.

    Args:
        current: 当前版本号 / Current version
        latest: 最新版本号 / Latest version

    Returns:
        True 如果当前版本过时 / True if current version is outdated
    """
    return compare_versions(current, latest) < 0


# ============================================================
# 文件相关 / File related utilities
# ============================================================

def read_file_safe(filepath: str, encoding: str = "utf-8") -> Optional[str]:
    """
    安全读取文件内容
    Safely read file contents.

    Args:
        filepath: 文件路径 / File path
        encoding: 文件编码 / File encoding

    Returns:
        文件内容字符串，读取失败返回None / File content string, None on failure
    """
    try:
        with open(filepath, "r", encoding=encoding) as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def read_json_safe(filepath: str, encoding: str = "utf-8") -> Optional[dict]:
    """
    安全读取JSON文件
    Safely read JSON file.

    Args:
        filepath: 文件路径 / File path
        encoding: 文件编码 / File encoding

    Returns:
        解析后的字典，失败返回None / Parsed dict, None on failure
    """
    try:
        content = read_file_safe(filepath, encoding)
        if content is None:
            return None
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None


def write_file_safe(
    filepath: str,
    content: str,
    encoding: str = "utf-8"
) -> bool:
    """
    安全写入文件
    Safely write file contents.

    Args:
        filepath: 文件路径 / File path
        content: 文件内容 / File content
        encoding: 文件编码 / File encoding

    Returns:
        True 写入成功 / True on success
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except (IOError, OSError):
        return False


def write_json_safe(
    filepath: str,
    data: Any,
    indent: int = 2,
    encoding: str = "utf-8"
) -> bool:
    """
    安全写入JSON文件
    Safely write JSON file.

    Args:
        filepath: 文件路径 / File path
        data: 要写入的数据 / Data to write
        indent: 缩进级别 / Indentation level
        encoding: 文件编码 / File encoding

    Returns:
        True 写入成功 / True on success
    """
    try:
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        return write_file_safe(filepath, content, encoding)
    except (TypeError, ValueError):
        return False


# ============================================================
# 日期时间相关 / Date/time related utilities
# ============================================================

def parse_date(date_str: str) -> Optional[datetime]:
    """
    解析多种日期格式
    Parse multiple date formats.

    支持的格式 / Supported formats:
    - ISO 8601: "2024-01-15T10:30:00Z"
    - 简单日期: "2024-01-15"
    - 带时区: "2024-01-15T10:30:00+08:00"

    Args:
        date_str: 日期字符串 / Date string

    Returns:
        datetime对象，解析失败返回None / datetime object, None on failure
    """
    if not date_str:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def days_since(date: datetime) -> int:
    """
    计算从给定日期到现在的天数
    Calculate days since the given date.

    Args:
        date: 日期对象 / Date object

    Returns:
        天数 / Number of days
    """
    now = datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return (now - date).days


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    格式化时间戳为ISO 8601格式
    Format timestamp to ISO 8601 format.

    Args:
        dt: datetime对象，默认为当前时间 / datetime object, defaults to now

    Returns:
        ISO 8601格式的时间戳字符串 / ISO 8601 formatted timestamp string
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================
# 数据转换相关 / Data conversion utilities
# ============================================================

def normalize_name(name: str) -> str:
    """
    标准化依赖包名称（统一大小写和分隔符）
    Normalize package name (unify case and separators).

    Args:
        name: 包名称 / Package name

    Returns:
        标准化后的名称 / Normalized name
    """
    return re.sub(r"[-_.]+", "-", name).lower().strip()


def flatten_dict(
    d: Dict[str, Any],
    parent_key: str = "",
    sep: str = "."
) -> Dict[str, Any]:
    """
    展平嵌套字典
    Flatten a nested dictionary.

    Args:
        d: 嵌套字典 / Nested dictionary
        parent_key: 父键前缀 / Parent key prefix
        sep: 分隔符 / Separator

    Returns:
        展平后的字典 / Flattened dictionary
    """
    items: List[Tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法运算，避免除零错误
    Safe division to avoid zero-division errors.

    Args:
        numerator: 分子 / Numerator
        denominator: 分母 / Denominator
        default: 除零时的默认值 / Default value on zero division

    Returns:
        除法结果 / Division result
    """
    if denominator == 0:
        return default
    return numerator / denominator


# ============================================================
# 许可证相关 / License related utilities
# ============================================================

# 已知许可证分类 / Known license classifications
PERMISSIVE_LICENSES = {
    "mit", "apache-2.0", "apache2", "apache 2.0",
    "bsd-2-clause", "bsd-3-clause", "bsd",
    "isc", "0bsd", "x11",
    "unlicense", "cc0-1.0", "cc0", "wtfpl",
    "zlib", "png", "libpng",
}

COPYLEFT_LICENSES = {
    "gpl-2.0", "gpl-3.0", "gpl2", "gpl3",
    "lgpl-2.0", "lgpl-3.0", "lgpl2", "lgpl3",
    "agpl-3.0", "agpl3",
    "mpl-2.0", "mpl2",
    "epl-1.0", "epl2", "cpl-1.0",
    "eupl-1.2",
}

WEAK_COPYLEFT_LICENSES = {
    "lgpl-2.0", "lgpl-2.1", "lgpl-3.0",
    "mpl-2.0", "epl-1.0", "epl-2.0",
    "cpl-1.0", "cecill-2.1",
}

RISKY_LICENSES = {
    "gpl-3.0", "gpl3", "agpl-3.0", "agpl3",
}


def classify_license(license_str: str) -> str:
    """
    分类许可证类型
    Classify license type.

    Args:
        license_str: 许可证字符串 / License string

    Returns:
        分类结果: "permissive", "copyleft", "weak-copyleft", "unknown"
        Classification result
    """
    if not license_str:
        return "unknown"

    normalized = license_str.lower().strip()

    # 处理SPDX表达式 / Handle SPDX expressions
    if " or " in normalized or " and " in normalized:
        # 多重许可证，取第一个 / Multiple licenses, take the first
        normalized = normalized.split(" or ")[0].split(" and ")[0].strip()

    # 移除括号内容 / Remove parenthetical content
    normalized = re.sub(r"\(.*?\)", "", normalized).strip()

    if normalized in PERMISSIVE_LICENSES:
        return "permissive"
    if normalized in WEAK_COPYLEFT_LICENSES:
        return "weak-copyleft"
    if normalized in COPYLEFT_LICENSES:
        return "copyleft"
    return "unknown"
