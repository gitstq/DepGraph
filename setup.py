"""
DepGraph - 轻量级Git仓库依赖图谱与供应链风险智能分析引擎
Lightweight Git Repository Dependency Graph & Supply Chain Risk Analyzer
"""

from setuptools import setup, find_packages

setup(
    name="depgraph",
    version="1.0.0",
    description="Lightweight dependency graph & supply chain risk analyzer",
    long_description=open("README.md", encoding="utf-8").read() if __import__('os').path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="DepGraph Team",
    license="MIT",
    python_requires=">=3.8",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "depgraph=depgraph.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Security",
    ],
)
