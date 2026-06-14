import os
from git import Repo, GitCommandError
from langchain_core.tools import tool

def get_repo() -> Repo:
    try:
        return Repo(os.getcwd(), search_parent_directories=True)
    except Exception:
        raise ValueError("The current directory is not a valid Git repository.")

@tool
def get_git_status() -> str:
    """Returns the current git status, including staged, unstaged, and untracked files."""
    try:
        repo = get_repo()
        status_msg = f"On branch: {repo.active_branch.name}\n"
        
        diff_staged = repo.git.diff("--cached", name_status=True)
        diff_unstaged = repo.git.diff(name_status=True)
        untracked = repo.untracked_files
        
        status_msg += f"Staged changes:\n{diff_staged or 'None'}\n\n"
        status_msg += f"Unstaged changes:\n{diff_unstaged or 'None'}\n\n"
        status_msg += f"Untracked files:\n{', '.join(untracked) or 'None'}"
        return status_msg
    except Exception as e:
        return f"Error gathering git status: {str(e)}"

@tool
def create_and_checkout_branch(branch_name: str) -> str:
    """Creates a brand new git branch and hooks the environment to it immediately."""
    try:
        repo = get_repo()
        # Clean naming schema optimization
        clean_branch = branch_name.strip().replace(" ", "-").lower()
        new_branch = repo.create_head(clean_branch)
        new_branch.checkout()
        return f"Successfully created and checked out branch: '{clean_branch}'"
    except GitCommandError as e:
        return f"Git Error: Branch might already exist. Details: {str(e)}"

@tool
def commit_all_changes(message: str) -> str:
    """Stages genuine modifications while completely ignoring development artifacts via .gitignore rules."""
    try:
        repo = get_repo()
        repo.git.add(".") 
        
        # Double check if anything was actually staged to avoid empty commit crashes
        if not repo.index.diff("HEAD") and not repo.untracked_files:
            return "No valid code modifications detected to commit."
            
        commit = repo.index.commit(message)
        return f"Committed structural modifications cleanly. Commit SHA: {commit.hexsha}"
    except Exception as e:
        return f"Commit processing failure: {str(e)}"

@tool
def create_merge_request(title: str, description: str) -> str:
    """
    Pushes the active automated feature branch up to the remote origin server 
    and instantiates an isolated web link to quickly launch/review the Merge Request.
    """
    try:
        repo = get_repo()
        active_branch = repo.active_branch.name
        
        # Guardrail check against deploying directly over master/main production trunks
        if active_branch in ["main", "master", "develop"]:
            return f"Operation Refused: Cannot open a Merge Request targeting base origin branch '{active_branch}' directly."
        
        # Push branch up to origin remote server
        origin = repo.remote(name="origin")
        origin.push(active_branch)
        
        # Generate the dynamic GitLab / GitHub interface hyperlink string based on upstream remote layout
        remote_url = origin.url.replace(".git", "")
        mr_link = f"{remote_url}/-/merge_requests/new?merge_request%5Bsource_branch%5D={active_branch}"
        
        return f"🚀 Code base pushed upstream successfully!\n👉 Review and finalize your Merge Request here: {mr_link}"
    except Exception as e:
        return f"Upstream remote transport layer synchronization crashed: {str(e)}"