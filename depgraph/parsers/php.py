"""
PHP composer.json 解析器 / PHP composer.json parser

解析 PHP 项目的 composer.json 文件，提取依赖信息。
Parses PHP project composer.json files, extracts dependency info.

支持格式 / Supported formats:
{
    "require": {
        "php": "^8.1",
        "laravel/framework": "^10.0",
        "guzzlehttp/guzzle": "^7.5"
    },
    "require-dev": {
        "phpunit/phpunit": "^10.0",
        "mockery/mockery": "^1.5"
    },
    "license": "MIT"
}
"""

import json
from typing import List

from .base import BaseParser, Dependency, DepFileType


class ComposerJsonParser(BaseParser):
    """
    composer.json 解析器 / composer.json parser

    解析 PHP Composer 项目的 composer.json 文件。
    Parses PHP Composer project composer.json files.
    """

    file_type = DepFileType.COMPOSER_JSON
    display_name = "PHP (composer.json)"

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 composer.json 内容
        Parse composer.json content.

        Args:
            content: composer.json 文件内容 / composer.json file content

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
            elif isinstance(lic, list):
                project_license = lic[0] if lic else ""

        # 解析 require / Parse require
        deps = data.get("require", {})
        dependencies.extend(
            self._parse_dep_dict(deps, is_dev=False, license_str=project_license)
        )

        # 解析 require-dev / Parse require-dev
        dev_deps = data.get("require-dev", {})
        dependencies.extend(
            self._parse_dep_dict(dev_deps, is_dev=True, license_str=project_license)
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
            deps: 依赖字典 / Dependency dict
            is_dev: 是否为开发依赖 / Whether dev dependency
            license_str: 许可证字符串 / License string

        Returns:
            依赖列表 / Dependency list
        """
        result: List[Dependency] = []
        if not isinstance(deps, dict):
            return result

        # 跳过 PHP 版本约束 / Skip PHP version constraint
        skip_keys = {"php", "ext-*", "lib-*"}

        for name, version in deps.items():
            # 跳过平台要求 / Skip platform requirements
            if name == "php":
                continue
            if name.startswith("ext-") or name.startswith("lib-"):
                continue

            result.append(
                Dependency(
                    name=self._clean_name(name),
                    version=self._clean_version(str(version)),
                    source=self.file_type,
                    license=license_str,
                    is_dev=is_dev,
                )
            )

        return result
