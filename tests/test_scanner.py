"""
扫描器测试 / Scanner tests

测试依赖文件扫描器的核心功能。
Tests core functionality of the dependency file scanner.
"""

import json
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from depgraph.scanner import DependencyScanner, ScanResult, DEPENDENCY_FILES
from depgraph.parsers.base import DepFileType


class TestDependencyScanner(unittest.TestCase):
    """依赖扫描器测试类 / Dependency scanner test class."""

    def setUp(self):
        """测试前准备 / Setup before tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = DependencyScanner()

    def tearDown(self):
        """测试后清理 / Cleanup after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_empty_directory(self):
        """测试扫描空目录 / Test scanning empty directory."""
        result = self.scanner.scan(self.temp_dir)
        self.assertIsInstance(result, ScanResult)
        self.assertEqual(len(result.dependencies), 0)
        self.assertTrue(len(result.errors) > 0)

    def test_scan_package_json(self):
        """测试扫描 package.json / Test scanning package.json."""
        pkg_json = os.path.join(self.temp_dir, "package.json")
        with open(pkg_json, "w") as f:
            json.dump({
                "name": "test-project",
                "dependencies": {
                    "express": "^4.18.2",
                    "lodash": "~4.17.21",
                },
                "devDependencies": {
                    "jest": "^29.0.0",
                },
                "license": "MIT",
            }, f)

        result = self.scanner.scan(self.temp_dir)
        self.assertEqual(len(result.dependencies), 3)
        names = [d.name for d in result.dependencies]
        self.assertIn("express", names)
        self.assertIn("lodash", names)
        self.assertIn("jest", names)

    def test_scan_requirements_txt(self):
        """测试扫描 requirements.txt / Test scanning requirements.txt."""
        req_file = os.path.join(self.temp_dir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("flask==2.0.1\n")
            f.write("requests>=2.25.0\n")
            f.write("# comment\n")
            f.write("numpy~=1.21.0\n")

        result = self.scanner.scan(self.temp_dir)
        self.assertEqual(len(result.dependencies), 3)

    def test_scan_nested_directory(self):
        """测试扫描嵌套目录 / Test scanning nested directory."""
        sub_dir = os.path.join(self.temp_dir, "sub", "project")
        os.makedirs(sub_dir)

        pkg_json = os.path.join(sub_dir, "package.json")
        with open(pkg_json, "w") as f:
            json.dump({
                "dependencies": {"express": "^4.18.2"},
            }, f)

        result = self.scanner.scan(self.temp_dir)
        self.assertEqual(len(result.dependencies), 1)

    def test_scan_ignores_node_modules(self):
        """测试忽略 node_modules 目录 / Test ignoring node_modules."""
        nm_dir = os.path.join(self.temp_dir, "node_modules")
        os.makedirs(nm_dir)

        # node_modules 中的 package.json 应被忽略
        nm_pkg = os.path.join(nm_dir, "some-package", "package.json")
        os.makedirs(os.path.dirname(nm_pkg))
        with open(nm_pkg, "w") as f:
            json.dump({"dependencies": {"foo": "1.0.0"}}, f)

        # 根目录的 package.json 应被扫描
        root_pkg = os.path.join(self.temp_dir, "package.json")
        with open(root_pkg, "w") as f:
            json.dump({"dependencies": {"bar": "2.0.0"}}, f)

        result = self.scanner.scan(self.temp_dir)
        self.assertEqual(len(result.dependencies), 1)
        self.assertEqual(result.dependencies[0].name, "bar")

    def test_scan_multiple_file_types(self):
        """测试扫描多种文件类型 / Test scanning multiple file types."""
        # package.json
        with open(os.path.join(self.temp_dir, "package.json"), "w") as f:
            json.dump({"dependencies": {"express": "^4.18.2"}}, f)

        # requirements.txt
        with open(os.path.join(self.temp_dir, "requirements.txt"), "w") as f:
            f.write("flask==2.0.1\n")

        # go.mod
        with open(os.path.join(self.temp_dir, "go.mod"), "w") as f:
            f.write("module example.com/myproject\n")
            f.write("go 1.21\n")
            f.write("require github.com/gin-gonic/gin v1.9.1\n")

        result = self.scanner.scan(self.temp_dir)
        self.assertEqual(len(result.dependencies), 3)
        self.assertEqual(result.stats["files_scanned"], 3)

    def test_scan_result_stats(self):
        """测试扫描结果统计 / Test scan result statistics."""
        with open(os.path.join(self.temp_dir, "package.json"), "w") as f:
            json.dump({
                "dependencies": {"express": "^4.18.2"},
                "devDependencies": {"jest": "^29.0.0"},
            }, f)

        result = self.scanner.scan(self.temp_dir)
        self.assertEqual(result.stats["total_dependencies"], 2)
        self.assertEqual(result.stats["production_dependencies"], 1)
        self.assertEqual(result.stats["development_dependencies"], 1)

    def test_scan_single_file(self):
        """测试扫描单个文件 / Test scanning single file."""
        pkg_json = os.path.join(self.temp_dir, "package.json")
        with open(pkg_json, "w") as f:
            json.dump({"dependencies": {"express": "^4.18.2"}}, f)

        deps = self.scanner.scan_single_file(pkg_json)
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0].name, "express")

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件 / Test scanning nonexistent file."""
        deps = self.scanner.scan_single_file("/nonexistent/file.json")
        self.assertEqual(len(deps), 0)

    def test_dependency_files_mapping(self):
        """测试依赖文件映射完整性 / Test dependency files mapping completeness."""
        expected_files = [
            "package.json", "requirements.txt", "pyproject.toml",
            "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
            "Gemfile", "composer.json",
        ]
        for f in expected_files:
            self.assertIn(f, DEPENDENCY_FILES)


if __name__ == "__main__":
    unittest.main()
