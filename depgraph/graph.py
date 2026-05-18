"""
依赖图谱构建模块 / Dependency graph builder module

使用邻接表构建依赖关系图谱，支持拓扑排序、环检测和传递依赖计算。
Builds dependency relationship graph using adjacency list, supports topological
sorting, cycle detection, and transitive dependency calculation.

数据结构 / Data structures:
- 邻接表: {package_name: [dependency_names]}
- 反向邻接表: {package_name: [dependent_names]}
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .parsers.base import Dependency, DepFileType
from .utils import normalize_name


@dataclass
class GraphNode:
    """
    图节点数据类 / Graph node data class

    表示依赖图谱中的一个包节点。
    Represents a package node in the dependency graph.

    Attributes:
        name: 包名称 / Package name
        version: 版本号 / Version
        dependencies: 直接依赖名称列表 / Direct dependency names
        dependents: 被依赖者名称列表 / Dependent names (reverse edges)
        depth: 依赖深度 / Dependency depth
        is_dev: 是否为开发依赖 / Whether dev dependency
        file_type: 来源文件类型 / Source file type
    """
    name: str
    version: str = ""
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    depth: int = 0
    is_dev: bool = False
    file_type: DepFileType = DepFileType.UNKNOWN

    def to_dict(self) -> Dict:
        """转换为字典 / Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "depth": self.depth,
            "is_dev": self.is_dev,
            "file_type": self.file_type.value,
        }


@dataclass
class CycleInfo:
    """
    环信息数据类 / Cycle information data class

    Attributes:
        nodes: 构成环的节点列表 / Nodes forming the cycle
        has_cycle: 是否存在环 / Whether a cycle exists
    """
    has_cycle: bool = False
    nodes: List[str] = field(default_factory=list)


class DependencyGraph:
    """
    依赖图谱 / Dependency graph

    使用邻接表存储依赖关系，提供图分析算法。
    Stores dependency relationships using adjacency list, provides graph analysis algorithms.

    使用方法 / Usage:
        graph = DependencyGraph()
        graph.build_from_dependencies(dependencies)
        print(graph.topological_sort())
        print(graph.detect_cycles())
    """

    def __init__(self):
        """初始化空图谱 / Initialize empty graph."""
        # 邻接表: 节点 -> 依赖列表 / Adjacency list: node -> dependencies
        self._adjacency: Dict[str, GraphNode] = {}
        # 反向邻接表: 节点 -> 被依赖列表 / Reverse adjacency: node -> dependents
        self._reverse: Dict[str, Set[str]] = defaultdict(set)

    @property
    def nodes(self) -> Dict[str, GraphNode]:
        """获取所有节点 / Get all nodes."""
        return self._adjacency

    @property
    def node_count(self) -> int:
        """获取节点数量 / Get node count."""
        return len(self._adjacency)

    @property
    def edge_count(self) -> int:
        """获取边数量 / Get edge count."""
        return sum(len(node.dependencies) for node in self._adjacency.values())

    def build_from_dependencies(self, dependencies: List[Dependency]) -> None:
        """
        从依赖列表构建图谱
        Build graph from dependency list.

        Args:
            dependencies: 依赖列表 / Dependency list
        """
        # 创建所有节点 / Create all nodes
        for dep in dependencies:
            name = normalize_name(dep.name)
            if name not in self._adjacency:
                self._adjacency[name] = GraphNode(
                    name=name,
                    version=dep.version,
                    is_dev=dep.is_dev,
                    file_type=dep.source,
                )
            else:
                # 更新已有节点的信息 / Update existing node info
                node = self._adjacency[name]
                if not node.version and dep.version:
                    node.version = dep.version
                if dep.is_dev:
                    node.is_dev = True

        # 构建边关系（简化模型：假设所有依赖都在同一层级）
        # Build edge relationships (simplified model: all deps at same level)
        # 在实际场景中，传递依赖需要通过lock文件或注册表解析
        # In practice, transitive deps need lock file or registry resolution
        for dep in dependencies:
            name = normalize_name(dep.name)
            # 在简化模型中，我们记录依赖来源文件作为边
            # In simplified model, we record source file as edge
            pass

    def build_from_dict(self, dep_dict: Dict[str, List[str]]) -> None:
        """
        从字典构建图谱（用于测试和高级用法）
        Build graph from dictionary (for testing and advanced usage).

        Args:
            dep_dict: 依赖字典 {package: [dependencies]} / Dependency dict
        """
        for name, deps in dep_dict.items():
            norm_name = normalize_name(name)
            if norm_name not in self._adjacency:
                self._adjacency[norm_name] = GraphNode(name=norm_name)

            self._adjacency[norm_name].dependencies = [
                normalize_name(d) for d in deps
            ]

            # 确保依赖节点存在 / Ensure dependency nodes exist
            for dep_name in deps:
                norm_dep = normalize_name(dep_name)
                if norm_dep not in self._adjacency:
                    self._adjacency[norm_dep] = GraphNode(name=norm_dep)

                # 构建反向边 / Build reverse edges
                self._reverse[norm_dep].add(norm_name)

        # 构建反向邻接表 / Build reverse adjacency list
        for name, node in self._adjacency.items():
            for dep in node.dependencies:
                self._reverse[dep].add(name)
                if dep in self._adjacency:
                    self._adjacency[dep].dependents.append(name)

    def add_edge(self, from_node: str, to_node: str) -> None:
        """
        添加边 / Add edge.

        Args:
            from_node: 源节点 / Source node
            to_node: 目标节点 / Target node
        """
        norm_from = normalize_name(from_node)
        norm_to = normalize_name(to_node)

        # 确保节点存在 / Ensure nodes exist
        if norm_from not in self._adjacency:
            self._adjacency[norm_from] = GraphNode(name=norm_from)
        if norm_to not in self._adjacency:
            self._adjacency[norm_to] = GraphNode(name=norm_to)

        # 添加边 / Add edge
        if norm_to not in self._adjacency[norm_from].dependencies:
            self._adjacency[norm_from].dependencies.append(norm_to)
        self._reverse[norm_to].add(norm_from)
        if norm_from not in self._adjacency[norm_to].dependents:
            self._adjacency[norm_to].dependents.append(norm_from)

    def get_node(self, name: str) -> Optional[GraphNode]:
        """
        获取节点 / Get node.

        Args:
            name: 节点名称 / Node name

        Returns:
            GraphNode 或 None / GraphNode or None
        """
        return self._adjacency.get(normalize_name(name))

    def get_dependencies(self, name: str) -> List[str]:
        """
        获取直接依赖 / Get direct dependencies.

        Args:
            name: 节点名称 / Node name

        Returns:
            依赖名称列表 / Dependency name list
        """
        node = self.get_node(name)
        return node.dependencies if node else []

    def get_dependents(self, name: str) -> List[str]:
        """
        获取被谁依赖 / Get dependents.

        Args:
            name: 节点名称 / Node name

        Returns:
            依赖者名称列表 / Dependent name list
        """
        node = self.get_node(name)
        return node.dependents if node else []

    def get_transitive_dependencies(self, name: str) -> Set[str]:
        """
        获取传递依赖（所有直接和间接依赖）
        Get transitive dependencies (all direct and indirect dependencies).

        使用BFS遍历 / Uses BFS traversal.

        Args:
            name: 节点名称 / Node name

        Returns:
            传递依赖集合 / Transitive dependency set
        """
        visited: Set[str] = set()
        queue = deque()

        node = self.get_node(name)
        if node:
            for dep in node.dependencies:
                queue.append(dep)

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            current_node = self.get_node(current)
            if current_node:
                for dep in current_node.dependencies:
                    if dep not in visited:
                        queue.append(dep)

        return visited

    def get_transitive_dependents(self, name: str) -> Set[str]:
        """
        获取传递被依赖者（所有直接和间接依赖此包的包）
        Get transitive dependents (all packages that depend on this directly or indirectly).

        Args:
            name: 节点名称 / Node name

        Returns:
            传递被依赖者集合 / Transitive dependent set
        """
        visited: Set[str] = set()
        queue = deque()

        dependents = self._reverse.get(normalize_name(name), set())
        for dep in dependents:
            queue.append(dep)

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for dep in self._reverse.get(current, set()):
                if dep not in visited:
                    queue.append(dep)

        return visited

    def topological_sort(self) -> List[str]:
        """
        拓扑排序
        Topological sort.

        使用Kahn算法 / Uses Kahn's algorithm.

        Returns:
            拓扑排序后的节点列表 / Topologically sorted node list
        """
        # 计算入度 / Calculate in-degrees
        in_degree: Dict[str, int] = {name: 0 for name in self._adjacency}
        for name, node in self._adjacency.items():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[dep] = in_degree.get(dep, 0)

        # 统计入度 / Count in-degrees
        for name, node in self._adjacency.items():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[dep] += 1

        # 入度为0的节点入队 / Enqueue nodes with 0 in-degree
        queue = deque()
        for name, degree in in_degree.items():
            if degree == 0:
                queue.append(name)

        result: List[str] = []
        while queue:
            current = queue.popleft()
            result.append(current)

            node = self.get_node(current)
            if node:
                for dep in node.dependencies:
                    if dep in in_degree:
                        in_degree[dep] -= 1
                        if in_degree[dep] == 0:
                            queue.append(dep)

        return result

    def detect_cycles(self) -> CycleInfo:
        """
        检测环
        Detect cycles.

        使用DFS检测 / Uses DFS detection.

        Returns:
            环信息 / Cycle information
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {name: WHITE for name in self._adjacency}
        parent: Dict[str, Optional[str]] = {name: None for name in self._adjacency}

        def dfs(node_name: str) -> Optional[List[str]]:
            """DFS遍历 / DFS traversal."""
            color[node_name] = GRAY
            node = self.get_node(node_name)

            if node:
                for dep in node.dependencies:
                    if dep not in color:
                        continue
                    if color[dep] == GRAY:
                        # 找到环 / Found cycle
                        cycle = [dep, node_name]
                        current = node_name
                        while parent[current] is not None and parent[current] != dep:
                            current = parent[current]
                            cycle.append(current)
                        cycle.append(dep)
                        return list(reversed(cycle))
                    elif color[dep] == WHITE:
                        parent[dep] = node_name
                        result = dfs(dep)
                        if result:
                            return result

            color[node_name] = BLACK
            return None

        for name in self._adjacency:
            if color[name] == WHITE:
                cycle = dfs(name)
                if cycle:
                    return CycleInfo(has_cycle=True, nodes=cycle)

        return CycleInfo(has_cycle=False)

    def compute_depths(self) -> Dict[str, int]:
        """
        计算每个节点的依赖深度
        Compute dependency depth for each node.

        深度定义：从叶子节点（无依赖）到当前节点的最长路径长度。
        Depth definition: longest path from leaf node (no deps) to current node.

        Returns:
            节点名称到深度的映射 / Node name to depth mapping
        """
        depths: Dict[str, int] = {}

        def compute_depth(name: str) -> int:
            """递归计算深度 / Recursively compute depth."""
            if name in depths:
                return depths[name]

            node = self.get_node(name)
            if not node or not node.dependencies:
                depths[name] = 0
                return 0

            max_dep_depth = 0
            for dep in node.dependencies:
                max_dep_depth = max(max_dep_depth, compute_depth(dep) + 1)

            depths[name] = max_dep_depth
            return max_dep_depth

        for name in self._adjacency:
            compute_depth(name)

        # 更新节点深度 / Update node depths
        for name, depth in depths.items():
            node = self.get_node(name)
            if node:
                node.depth = depth

        return depths

    def find_duplicates(self) -> Dict[str, List[str]]:
        """
        查找重复依赖（同名但不同版本的依赖）
        Find duplicate dependencies (same name but different versions).

        Returns:
            重复依赖映射 / Duplicate dependency mapping
        """
        version_map: Dict[str, Set[str]] = defaultdict(set)

        for name, node in self._adjacency.items():
            if node.version:
                version_map[name].add(node.version)

        duplicates = {}
        for name, versions in version_map.items():
            if len(versions) > 1:
                duplicates[name] = sorted(versions)

        return duplicates

    def get_root_nodes(self) -> List[str]:
        """
        获取根节点（不被任何其他节点依赖的节点）
        Get root nodes (nodes not depended on by any other node).

        Returns:
            根节点列表 / Root node list
        """
        all_depended = set()
        for name, node in self._adjacency.items():
            all_depended.update(node.dependencies)

        return [name for name in self._adjacency if name not in all_depended]

    def get_leaf_nodes(self) -> List[str]:
        """
        获取叶子节点（没有依赖的节点）
        Get leaf nodes (nodes with no dependencies).

        Returns:
            叶子节点列表 / Leaf node list
        """
        return [
            name for name, node in self._adjacency.items()
            if not node.dependencies
        ]

    def to_dict(self) -> Dict:
        """
        转换为字典
        Convert to dictionary.

        Returns:
            图谱字典表示 / Graph dictionary representation
        """
        return {
            "nodes": {name: node.to_dict() for name, node in self._adjacency.items()},
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "root_nodes": self.get_root_nodes(),
            "leaf_nodes": self.get_leaf_nodes(),
        }

    def to_mermaid(self) -> str:
        """
        生成Mermaid图定义
        Generate Mermaid graph definition.

        Returns:
            Mermaid图字符串 / Mermaid graph string
        """
        lines = ["graph TD"]

        # 添加节点和边 / Add nodes and edges
        for name, node in self._adjacency.items():
            for dep in node.dependencies:
                safe_name = name.replace("-", "_").replace(".", "_").replace("/", "_")
                safe_dep = dep.replace("-", "_").replace(".", "_").replace("/", "_")
                lines.append(f"    {safe_name}[\"{name}\"] --> {safe_dep}[\"{dep}\"]")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"DependencyGraph(nodes={self.node_count}, "
            f"edges={self.edge_count})"
        )
