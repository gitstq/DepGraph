"""
Node.js package.json 解析器 / Node.js package.json parser

解析 package.json 文件中的 dependencies 和 devDependencies。
Parses dependencies and devDependencies from package.json files.

支持格式 / Supported formats:
{
    "dependencies": {
        "express": "^4.18.2",
        "lodash": "~4.17.21"
    },
    "devDependencies": {
        "jest": "^29.0.0"
    },
    "license": "MIT"
}
"""

import json
from typing import List

from .base import BaseParser, Dependency, DepFileType


class PackageJsonParser(BaseParser):
    """
    package.json 解析器 / package.json parser

    解析 Node.js 项目的 package.json 文件，提取依赖信息。
    Parses Node.js project package.json files, extracts dependency info.
    """

    file_type = DepFileType.PACKAGE_JSON
    display_name = "Node.js (package.json)"

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 package.json 内容
        Parse package.json content.

        Args:
            content: package.json 文件内容 / package.json file content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return dependencies

        # 获取项目许可证 / Get project license
        project_license = ""
        if "license" in data:
            lic = data["license"]
            if isinstance(lic, str):
                project_license = lic
            elif isinstance(lic, dict):
                project_license = lic.get("type", "")

        # 解析 dependencies / Parse dependencies
        deps = data.get("dependencies", {})
        dependencies.extend(
            self._parse_dep_dict(deps, is_dev=False, license_str=project_license)
        )

        # 解析 devDependencies / Parse dev dependencies
        dev_deps = data.get("devDependencies", {})
        dependencies.extend(
            self._parse_dep_dict(dev_deps, is_dev=True, license_str=project_license)
        )

        # 解析 peerDependencies / Parse peer dependencies
        peer_deps = data.get("peerDependencies", {})
        dependencies.extend(
            self._parse_dep_dict(peer_deps, is_dev=False, license_str=project_license)
        )

        # 解析 optionalDependencies / Parse optional dependencies
        opt_deps = data.get("optionalDependencies", {})
        dependencies.extend(
            self._parse_dep_dict(opt_deps, is_dev=False, license_str=project_license)
        )

        return dependencies

    def _parse_dep_dict(
        self,
        deps: dict,
        is_dev: bool,
        license_str: str = ""
    ) -> List[Dependency]:
        """
        解析依赖字典
        Parse dependency dictionary.

        Args:
            deps: 依赖字典 {name: version} / Dependency dict
            is_dev: 是否为开发依赖 / Whether dev dependency
            license_str: 许可证字符串 / License string

        Returns:
            依赖列表 / Dependency list
        """
        result: List[Dependency] = []
        if not isinstance(deps, dict):
            return result

        for name, version in deps.items():
            dep = Dependency(
                name=self._clean_name(name),
                version=self._clean_version(str(version)),
                source=self.file_type,
                license=license_str,
                is_dev=is_dev,
            )
            result.append(dep)

        return result
