import os
import subprocess
import pathspec
from langchain_core.tools import tool

def get_workspace_context(root_path: str = ".") -> str:
    """Generates a tree of the workspace, ignoring files in .gitignore and .git."""
    gitignore_path = os.path.join(root_path, ".gitignore")
    patterns = [".git/", ".venv/", "__pycache__/"] 
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            patterns.extend(f.readlines())
            
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)
    
    tree = []
    for root, dirs, files in os.walk(root_path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if not spec.match_file(os.path.relpath(os.path.join(root, d), root_path))]
        
        level = root.replace(root_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree.append(f"{indent}{os.path.basename(root)}/")
        
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), root_path)
            if not spec.match_file(rel_path):
                tree.append(f"{subindent}{f}")
                
    return "\n".join(tree)

@tool
def list_directory(path: str = ".") -> str:
    """Lists all files and directories in the given local path."""
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
        return f"{output}{errors}" if (output or errors) else "Command executed successfully with no output returns."
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

LOCAL_DEV_TOOLS = [list_directory, view_file, write_file, execute_command]