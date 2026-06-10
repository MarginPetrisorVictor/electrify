import os
import ast
import subprocess
import pathspec
from langchain_core.tools import tool

def _get_python_structure(filepath: str) -> str:
    """Parses a Python file and returns a lightweight structural outline (Classes/Methods)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            node = ast.parse(f.read(), filename=filepath)
        
        outline = []
        for top_level in node.body:
            if isinstance(top_level, ast.ClassDef):
                outline.append(f"    class {top_level.name}:")
                for sub in top_level.body:
                    if isinstance(sub, ast.FunctionDef):
                        outline.append(f"        def {sub.name}(...)")
            elif isinstance(top_level, ast.FunctionDef):
                outline.append(f"    def {top_level.name}(...)")
        return "\n".join(outline) if outline else "    [Empty or script logic only]"
    except Exception:
        return "    [Parsing Error]"

def get_workspace_context(root_path: str = ".") -> str:
    """Generates an AST-pruned tree of the workspace, ignoring files in .gitignore."""
    gitignore_path = os.path.join(root_path, ".gitignore")
    patterns = [".git/", ".venv/", "__pycache__/", "node_modules/", "*.pyc"] 
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            patterns.extend(f.readlines())
            
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)
    
    tree = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), root_path))]
        
        level = root.replace(root_path, '').count(os.sep)
        indent = ' ' * 4 * level
        rel_root = os.path.relpath(root, root_path)
        
        if rel_root != ".":
            tree.append(f"{indent}📁 {os.path.basename(root)}/")
        
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), root_path)
            if not spec.match_file(rel_path):
                file_indent = ' ' * 4 * (level + 1)
                tree.append(f"{file_indent}📄 {f}")
                # If it's a python file, extract its structural anatomy
                if f.endswith(".py"):
                    structure = _get_python_structure(os.path.join(root, f))
                    if structure:
                        # Indent the structure to line up neatly under the file
                        indented_struct = "\n".join([f"{file_indent}{line}" for line in structure.split("\n")])
                        tree.append(indented_struct)
                        
    return "\n".join(tree)

@tool
def list_directory(path: str = ".") -> str:
    """Lists files and directories in the given local path."""
    try:
        items = os.listdir(path)
        return "\n".join(items) if items else f"Directory '{path}' is empty."
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool
def view_file(filepath: str) -> str:
    """Reads and returns the complete text contents of a local file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {filepath}: {str(e)}"

@tool
def write_file(filepath: str, content: str) -> str:
    """Writes or overwrites text content to a specific file path."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to file: {filepath}"
    except Exception as e:
        return f"Error writing file {filepath}: {str(e)}"

@tool
def execute_command(command: str) -> str:
    """Executes a terminal bash command safely inside the local environment and returns stdout/stderr."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = f"STDOUT:\n{result.stdout}\n" if result.stdout else ""
        errors = f"STDERR:\n{result.stderr}\n" if result.stderr else ""
        # Return status code explicitly to aid the Self-Healing test engines
        return f"EXIT CODE: {result.returncode}\n{output}{errors}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

LOCAL_DEV_TOOLS = [list_directory, view_file, write_file, execute_command]