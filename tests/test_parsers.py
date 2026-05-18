"""
解析器测试 / Parser tests

测试所有依赖文件解析器的正确性。
Tests correctness of all dependency file parsers.
"""

import json
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from depgraph.parsers.base import Dependency, DepFileType
from depgraph.parsers.nodejs import PackageJsonParser
from depgraph.parsers.python import RequirementsTxtParser, PyprojectTomlParser
from depgraph.parsers.golang import GoModParser
from depgraph.parsers.rust import CargoTomlParser
from depgraph.parsers.java import PomXmlParser, BuildGradleParser
from depgraph.parsers.ruby import GemfileParser
from depgraph.parsers.php import ComposerJsonParser


class TestPackageJsonParser(unittest.TestCase):
    """package.json 解析器测试 / package.json parser tests."""

    def setUp(self):
        self.parser = PackageJsonParser()

    def test_basic_dependencies(self):
        """测试基本依赖解析 / Test basic dependency parsing."""
        content = json.dumps({
            "dependencies": {
                "express": "^4.18.2",
                "lodash": "~4.17.21",
            }
        })
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)
        self.assertEqual(deps[0].name, "express")
        self.assertEqual(deps[0].version, "^4.18.2")
        self.assertFalse(deps[0].is_dev)

    def test_dev_dependencies(self):
        """测试开发依赖解析 / Test dev dependency parsing."""
        content = json.dumps({
            "devDependencies": {
                "jest": "^29.0.0",
            }
        })
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertTrue(deps[0].is_dev)

    def test_mixed_dependencies(self):
        """测试混合依赖解析 / Test mixed dependency parsing."""
        content = json.dumps({
            "dependencies": {"express": "^4.18.2"},
            "devDependencies": {"jest": "^29.0.0"},
            "peerDependencies": {"react": ">=17.0.0"},
        })
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 3)

    def test_license_extraction(self):
        """测试许可证提取 / Test license extraction."""
        content = json.dumps({
            "license": "MIT",
            "dependencies": {"express": "^4.18.2"},
        })
        deps = self.parser.parse(content)
        self.assertEqual(deps[0].license, "MIT")

    def test_invalid_json(self):
        """测试无效JSON / Test invalid JSON."""
        deps = self.parser.parse("not json")
        self.assertEqual(len(deps), 0)

    def test_empty_content(self):
        """测试空内容 / Test empty content."""
        deps = self.parser.parse("")
        self.assertEqual(len(deps), 0)


class TestRequirementsTxtParser(unittest.TestCase):
    """requirements.txt 解析器测试 / requirements.txt parser tests."""

    def setUp(self):
        self.parser = RequirementsTxtParser()

    def test_basic_requirements(self):
        """测试基本依赖 / Test basic requirements."""
        content = "flask==2.0.1\nrequests>=2.25.0\n"
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)
        self.assertEqual(deps[0].name, "flask")
        self.assertEqual(deps[0].version, "==2.0.1")

    def test_comments_and_blank_lines(self):
        """测试注释和空行 / Test comments and blank lines."""
        content = "# This is a comment\n\nflask==2.0.1\n  \n"
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)

    def test_inline_comments(self):
        """测试行内注释 / Test inline comments."""
        content = "flask==2.0.1  # web framework\n"
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].version, "==2.0.1")

    def test_environment_markers(self):
        """测试环境标记 / Test environment markers."""
        content = "pywin32>=300; sys_platform == 'win32'\n"
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].name, "pywin32")

    def test_no_version(self):
        """测试无版本约束 / Test no version constraint."""
        content = "pandas\n"
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].name, "pandas")

    def test_tilde_version(self):
        """测试波浪号版本 / Test tilde version."""
        content = "numpy~=1.21.0\n"
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].version, "~=1.21.0")


class TestPyprojectTomlParser(unittest.TestCase):
    """pyproject.toml 解析器测试 / pyproject.toml parser tests."""

    def setUp(self):
        self.parser = PyprojectTomlParser()

    def test_pep621_format(self):
        """测试PEP 621格式 / Test PEP 621 format."""
        content = """
[project]
name = "myproject"
dependencies = [
    "flask>=2.0",
    "requests",
]
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)
        names = [d.name for d in deps]
        self.assertIn("flask", names)
        self.assertIn("requests", names)

    def test_poetry_format(self):
        """测试Poetry格式 / Test Poetry format."""
        content = """
[tool.poetry.dependencies]
python = "^3.8"
flask = "^2.0"
requests = "*"
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)  # python 被跳过
        names = [d.name for d in deps]
        self.assertIn("flask", names)
        self.assertIn("requests", names)

    def test_poetry_dev_group(self):
        """测试Poetry开发组 / Test Poetry dev group."""
        content = """
[tool.poetry.dependencies]
flask = "^2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)
        # pytest 应该是开发依赖
        pytest_dep = [d for d in deps if d.name == "pytest"]
        self.assertEqual(len(pytest_dep), 1)
        self.assertTrue(pytest_dep[0].is_dev)


class TestGoModParser(unittest.TestCase):
    """go.mod 解析器测试 / go.mod parser tests."""

    def setUp(self):
        self.parser = GoModParser()

    def test_basic_go_mod(self):
        """测试基本go.mod / Test basic go.mod."""
        content = """
module github.com/user/project

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/go-sql-driver/mysql v1.7.1 // indirect
)
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)

    def test_single_line_require(self):
        """测试单行require / Test single-line require."""
        content = """
module github.com/user/project

go 1.21

require github.com/gin-gonic/gin v1.9.1
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].name, "github.com/gin-gonic/gin")
        self.assertEqual(deps[0].version, "v1.9.1")

    def test_indirect_detection(self):
        """测试indirect标记检测 / Test indirect marker detection."""
        content = """
module github.com/user/project

go 1.21

require github.com/gin-gonic/gin v1.9.1 // indirect
"""
        deps = self.parser.parse(content)
        self.assertTrue(deps[0].extras.get("indirect", False))


class TestCargoTomlParser(unittest.TestCase):
    """Cargo.toml 解析器测试 / Cargo.toml parser tests."""

    def setUp(self):
        self.parser = CargoTomlParser()

    def test_basic_dependencies(self):
        """测试基本依赖 / Test basic dependencies."""
        content = """
[dependencies]
serde = "1.0"
tokio = "1.0"
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)

    def test_dev_dependencies(self):
        """测试开发依赖 / Test dev dependencies."""
        content = """
[dependencies]
serde = "1.0"

[dev-dependencies]
proptest = "1.0"
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)
        proptest = [d for d in deps if d.name == "proptest"]
        self.assertEqual(len(proptest), 1)

    def test_table_dependency(self):
        """测试表格格式依赖 / Test table format dependency."""
        content = """
[dependencies]
serde = { version = "1.0", features = ["derive"] }
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].version, "1.0")


class TestPomXmlParser(unittest.TestCase):
    """pom.xml 解析器测试 / pom.xml parser tests."""

    def setUp(self):
        self.parser = PomXmlParser()

    def test_basic_pom(self):
        """测试基本pom.xml / Test basic pom.xml."""
        content = """
<project>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>3.1.0</version>
        </dependency>
    </dependencies>
</project>
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertIn("spring-boot-starter-web", deps[0].name)

    def test_test_scope(self):
        """测试测试scope / Test test scope."""
        content = """
<project>
    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertTrue(deps[0].is_dev)


class TestBuildGradleParser(unittest.TestCase):
    """build.gradle 解析器测试 / build.gradle parser tests."""

    def setUp(self):
        self.parser = BuildGradleParser()

    def test_basic_gradle(self):
        """测试基本build.gradle / Test basic build.gradle."""
        content = """
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web:3.1.0'
    testImplementation 'junit:junit:4.13.2'
}
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)

    def test_dev_detection(self):
        """测试开发依赖检测 / Test dev dependency detection."""
        content = """
dependencies {
    testImplementation 'junit:junit:4.13.2'
}
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertTrue(deps[0].is_dev)


class TestGemfileParser(unittest.TestCase):
    """Gemfile 解析器测试 / Gemfile parser tests."""

    def setUp(self):
        self.parser = GemfileParser()

    def test_basic_gemfile(self):
        """测试基本Gemfile / Test basic Gemfile."""
        content = """
source 'https://rubygems.org'

gem 'rails', '~> 7.0'
gem 'pg', '~> 1.4'
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 2)

    def test_group_detection(self):
        """测试group检测 / Test group detection."""
        content = """
group :development, :test do
  gem 'rspec-rails', '~> 5.0'
end
"""
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)
        self.assertTrue(deps[0].is_dev)


class TestComposerJsonParser(unittest.TestCase):
    """composer.json 解析器测试 / composer.json parser tests."""

    def setUp(self):
        self.parser = ComposerJsonParser()

    def test_basic_composer(self):
        """测试基本composer.json / Test basic composer.json."""
        content = json.dumps({
            "require": {
                "laravel/framework": "^10.0",
                "guzzlehttp/guzzle": "^7.5",
            },
            "require-dev": {
                "phpunit/phpunit": "^10.0",
            },
        })
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 3)

    def test_php_version_skipped(self):
        """测试PHP版本约束被跳过 / Test PHP version constraint skipped."""
        content = json.dumps({
            "require": {
                "php": "^8.1",
                "laravel/framework": "^10.0",
            },
        })
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)

    def test_ext_skipped(self):
        """测试扩展要求被跳过 / Test extension requirements skipped."""
        content = json.dumps({
            "require": {
                "ext-curl": "*",
                "laravel/framework": "^10.0",
            },
        })
        deps = self.parser.parse(content)
        self.assertEqual(len(deps), 1)


if __name__ == "__main__":
    unittest.main()
