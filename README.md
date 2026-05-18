# DepGraph

轻量级Git仓库依赖图谱与供应链风险智能分析引擎

Lightweight Git Repository Dependency Graph & Supply Chain Risk Analysis Engine

## 特性 / Features

- 零外部依赖，纯Python 3.8+标准库实现
- 支持9种依赖文件解析
- 供应链风险评估
- 依赖变更检测
- 多格式报告导出

## 安装 / Installation

```bash
pip install -e .
```

## 使用 / Usage

```bash
# 扫描当前目录
depgraph scan

# 生成HTML报告
depgraph report -f html -o report.html

# 对比依赖变更
depgraph diff old.txt new.txt

# 生成Mermaid依赖图
depgraph graph -f mermaid
```

## 支持的文件类型 / Supported File Types

| 文件 | 语言 |
|------|------|
| package.json | Node.js |
| requirements.txt | Python |
| pyproject.toml | Python |
| go.mod | Go |
| Cargo.toml | Rust |
| pom.xml | Java (Maven) |
| build.gradle | Java (Gradle) |
| Gemfile | Ruby |
| composer.json | PHP |

## License

MIT
