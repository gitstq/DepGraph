"""
Java 依赖文件解析器 / Java dependency file parser

解析 pom.xml (Maven) 和 build.gradle (Gradle) 文件。
Parses pom.xml (Maven) and build.gradle (Gradle) files.

pom.xml 支持格式 / Supported pom.xml formats:
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>3.1.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

build.gradle 支持格式 / Supported build.gradle formats:
    dependencies {
        implementation 'org.springframework.boot:spring-boot-starter-web:3.1.0'
        testImplementation 'junit:junit:4.13.2'
    }
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base import BaseParser, Dependency, DepFileType


class PomXmlParser(BaseParser):
    """
    pom.xml (Maven) 解析器 / pom.xml (Maven) parser

    解析 Maven 项目的 pom.xml 文件，提取依赖信息。
    Parses Maven project pom.xml files, extracts dependency info.
    """

    file_type = DepFileType.POM_XML
    display_name = "Java (pom.xml)"

    # 测试 scope 标识 / Test scope identifiers
    TEST_SCOPES = {"test", "provided", "runtime", "system"}

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 pom.xml 内容
        Parse pom.xml content.

        Args:
            content: pom.xml 文件内容 / pom.xml file content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            # XML 解析失败，尝试正则回退 / XML parse failed, try regex fallback
            return self._parse_regex(content)

        # 处理 Maven 命名空间 / Handle Maven namespace
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        # 查找所有 dependencies 元素 / Find all dependencies elements
        deps_elements = root.findall(f".//{ns}dependencies/{ns}dependency")

        for dep_elem in deps_elements:
            group_id = self._get_text(dep_elem, f"{ns}groupId")
            artifact_id = self._get_text(dep_elem, f"{ns}artifactId")
            version = self._get_text(dep_elem, f"{ns}version")
            scope = self._get_text(dep_elem, f"{ns}scope")

            if not artifact_id:
                continue

            name = f"{group_id}:{artifact_id}" if group_id else artifact_id
            is_test = scope.lower() in self.TEST_SCOPES if scope else False

            dependencies.append(
                Dependency(
                    name=self._clean_name(name),
                    version=self._clean_version(version or ""),
                    source=self.file_type,
                    is_dev=is_test,
                    extras={"group_id": group_id, "artifact_id": artifact_id},
                )
            )

        return dependencies

    def _parse_regex(self, content: str) -> List[Dependency]:
        """
        使用正则表达式回退解析（当XML解析失败时）
        Regex fallback parsing (when XML parsing fails).

        Args:
            content: 文件内容 / File content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        # 简单正则匹配 / Simple regex matching
        dep_pattern = re.compile(
            r"<dependency>\s*"
            r"<groupId>([^<]+)</groupId>\s*"
            r"<artifactId>([^<]+)</artifactId>\s*"
            r"(?:<version>([^<]*)</version>)?\s*"
            r"(?:<scope>([^<]*)</scope>)?\s*"
            r"</dependency>",
            re.DOTALL,
        )

        for match in dep_pattern.finditer(content):
            group_id = match.group(1).strip()
            artifact_id = match.group(2).strip()
            version = match.group(3).strip() if match.group(3) else ""
            scope = match.group(4).strip() if match.group(4) else ""

            name = f"{group_id}:{artifact_id}"
            is_test = scope.lower() in self.TEST_SCOPES if scope else False

            dependencies.append(
                Dependency(
                    name=self._clean_name(name),
                    version=self._clean_version(version),
                    source=self.file_type,
                    is_dev=is_test,
                    extras={"group_id": group_id, "artifact_id": artifact_id},
                )
            )

        return dependencies

    @staticmethod
    def _get_text(element: ET.Element, tag: str) -> str:
        """
        安全获取XML元素文本 / Safely get XML element text.

        Args:
            element: XML元素 / XML element
            tag: 标签名 / Tag name

        Returns:
            文本内容，未找到返回空字符串 / Text content, empty string if not found
        """
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return ""


class BuildGradleParser(BaseParser):
    """
    build.gradle (Gradle) 解析器 / build.gradle (Gradle) parser

    解析 Gradle 项目的 build.gradle 文件。
    Parses Gradle project build.gradle files.
    """

    file_type = DepFileType.BUILD_GRADLE
    display_name = "Java (build.gradle)"

    # Gradle 依赖配置类型 / Gradle dependency configuration types
    DEV_CONFIGS = {"testimplementation", "testcompile", "testruntimeonly",
                   "androidtestimplementation"}

    # 匹配依赖声明 / Regex for dependency declarations
    _DEP_PATTERN = re.compile(
        r"^\s*(\w+)\s+['\"]([^'\"]+)['\"]"
    )

    # 匹配 group:name:version 格式 / Regex for group:name:version format
    _COORDS_PATTERN = re.compile(
        r"^([^:]+):([^:]+)(?::([^:]+))?$"
    )

    def parse(self, content: str) -> List[Dependency]:
        """
        解析 build.gradle 内容
        Parse build.gradle content.

        Args:
            content: build.gradle 文件内容 / build.gradle file content

        Returns:
            依赖列表 / Dependency list
        """
        dependencies: List[Dependency] = []

        if not content:
            return dependencies

        in_deps_block = False

        for line in content.splitlines():
            stripped = line.strip()

            # 检测 dependencies 块 / Detect dependencies block
            if stripped.startswith("dependencies") and "{" in stripped:
                in_deps_block = True
                continue

            if in_deps_block:
                if stripped == "}":
                    in_deps_block = False
                    continue

                dep = self._parse_dep_line(stripped)
                if dep:
                    dependencies.append(dep)

        return dependencies

    def _parse_dep_line(self, line: str) -> Optional[Dependency]:
        """
        解析单行依赖声明
        Parse a single dependency declaration line.

        Args:
            line: 依赖行 / Dependency line

        Returns:
            Dependency对象或None / Dependency object or None
        """
        if not line or line.startswith("//") or line.startswith("/*"):
            return None

        match = self._DEP_PATTERN.match(line)
        if not match:
            return None

        config = match.group(1).lower()
        coords = match.group(2)

        coords_match = self._COORDS_PATTERN.match(coords)
        if not coords_match:
            return None

        group = coords_match.group(1)
        name = coords_match.group(2)
        version = coords_match.group(3) or ""

        full_name = f"{group}:{name}"
        is_dev = config in self.DEV_CONFIGS

        return Dependency(
            name=self._clean_name(full_name),
            version=self._clean_version(version),
            source=self.file_type,
            is_dev=is_dev,
            extras={
                "group_id": group,
                "artifact_id": name,
                "configuration": config,
            },
        )
