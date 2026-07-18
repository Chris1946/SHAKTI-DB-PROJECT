import os
import ast
from typing import Dict, Any, List, Set

class StaticAnalyzer:
    """
    High-performance Static Code Intelligence Engine.
    Excludes large binaries and vendor directories, parsing only raw source code.
    """
    
    # Directories to completely ignore to prevent hanging on massive repos
    EXCLUDED_DIRS = {
        ".git", "node_modules", "venv", ".venv", "env", ".env",
        "__pycache__", "build", "dist", "vendor", "target", "bin", "obj"
    }
    
    # Supported source extensions
    SUPPORTED_EXTS = {
        ".py", ".js", ".ts", ".go", ".c", ".cpp", ".h", ".hpp", ".java", ".rs"
    }

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.architecture_graph = {
            "nodes": [],
            "edges": [],
            "stats": {
                "total_files": 0,
                "parsed_files": 0,
                "classes": 0,
                "functions": 0
            },
            "components": {
                "database": False,
                "network": False,
                "filesystem": False,
                "web_framework": False,
                "threads": False,
                "ipc": False,
                "gpu": False,
                "message_queue": False
            }
        }
        
    def analyze(self) -> Dict[str, Any]:
        """Runs the complete static analysis pipeline."""
        if not os.path.exists(self.project_path):
            raise ValueError(f"Project path {self.project_path} does not exist.")
            
        for root, dirs, files in os.walk(self.project_path):
            # Prune excluded directories from traversal
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            
            for file in files:
                self.architecture_graph["stats"]["total_files"] += 1
                ext = os.path.splitext(file)[1].lower()
                
                if ext in self.SUPPORTED_EXTS:
                    file_path = os.path.join(root, file)
                    self._parse_file(file_path, ext)
                    
        return self.architecture_graph

    def _parse_file(self, filepath: str, ext: str):
        """Dispatches to the correct parser based on extension."""
        self.architecture_graph["stats"]["parsed_files"] += 1
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            if ext == ".py":
                self._parse_python_ast(content, filepath)
            else:
                # Basic string matching fallback for non-Python languages for MVP
                self._basic_heuristic_scan(content, filepath)
                
        except Exception as e:
            # Skip unreadable or corrupted files
            pass

    def _parse_python_ast(self, content: str, filepath: str):
        """Uses Python's native AST for deep structural analysis."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
            
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.architecture_graph["stats"]["classes"] += 1
                self.architecture_graph["nodes"].append({
                    "id": node.name,
                    "type": "class",
                    "file": filepath
                })
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self.architecture_graph["stats"]["functions"] += 1
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                # Detect frameworks and libraries
                for alias in node.names:
                    name = alias.name.lower()
                    if "sqlalchemy" in name or "psycopg" in name or "sqlite" in name:
                        self.architecture_graph["components"]["database"] = True
                    if "fastapi" in name or "flask" in name or "django" in name:
                        self.architecture_graph["components"]["web_framework"] = True
                    if "socket" in name or "requests" in name or "httpx" in name:
                        self.architecture_graph["components"]["network"] = True
                    if "os" in name or "pathlib" in name or "shutil" in name:
                        self.architecture_graph["components"]["filesystem"] = True
                    # Expanded feature detection
                    if "threading" in name or "multiprocessing" in name or "asyncio" in name or "concurrent" in name:
                        self.architecture_graph["components"]["threads"] = True
                    if "mmap" in name or "subprocess" in name:
                        self.architecture_graph["components"]["ipc"] = True
                    if "cuda" in name or "torch" in name or "tensorflow" in name or "pyopencl" in name:
                        self.architecture_graph["components"]["gpu"] = True
                    if "celery" in name or "pika" in name or "kafka" in name or "redis" in name:
                        self.architecture_graph["components"]["message_queue"] = True

    def _basic_heuristic_scan(self, content: str, filepath: str):
        """Fallback regex/keyword scanning for languages without native AST support yet."""
        content = content.lower()
        
        if "sql" in content or "db" in content or "postgres" in content or "mongo" in content:
            self.architecture_graph["components"]["database"] = True
            
        if "http" in content or "fetch" in content or "axios" in content or "socket" in content:
            self.architecture_graph["components"]["network"] = True
            
        if "express" in content or "spring" in content or "react" in content:
            self.architecture_graph["components"]["web_framework"] = True
            
        if "fs." in content or "file" in content:
            self.architecture_graph["components"]["filesystem"] = True
