import os
import sys
import subprocess
import re

def run_cmd(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd, check=True)
        return result.stdout.strip()
    except Exception:
        return None

def get_repo_root():
    # Check current directory first
    cwd = os.path.abspath(".")
    if os.path.isdir(os.path.join(cwd, "specs")) or os.path.isdir(os.path.join(cwd, ".agent")):
        return cwd
        
    # Fall back to walking up from script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    current = script_dir
    while current and current != os.path.dirname(current):
        if os.path.isdir(os.path.join(current, "specs")) or os.path.isdir(os.path.join(current, ".agent")):
            return current
        current = os.path.dirname(current)
        
    # If we're in a git repo, use git to get the repo root
    top = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if top:
        return top
        
    # Fall back to script location
    return os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".."))

def has_git():
    return run_cmd(["git", "rev-parse", "--show-toplevel"]) is not None

def get_current_branch():
    if os.environ.get("SPECIFY_FEATURE") and os.environ.get("SPECIFY_FEATURE").strip():
        return os.environ.get("SPECIFY_FEATURE").strip()
        
    b = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if b:
        return b
        
    repo_root = get_repo_root()
    specs_dir = os.path.join(repo_root, "specs")
    
    if os.path.isdir(specs_dir):
        highest = -1
        latest = None
        for d in os.listdir(specs_dir):
            if os.path.isdir(os.path.join(specs_dir, d)):
                match = re.match(r'^([0-9]{3})-', d)
                if match:
                    try:
                        num = int(match.group(1))
                        if num > highest:
                            highest = num
                            latest = d
                    except ValueError:
                        pass
        if latest:
            return latest

    return "main"

def check_feature_branch(branch, has_git_repo):
    if not has_git_repo:
        sys.stderr.write(f"[specify] Warning: Git repository not detected; skipped branch validation\n")
        return True
        
    if not re.match(r'^[0-9]{3}-', branch):
        sys.stderr.write(f"ERROR: Not on a feature branch. Current branch: {branch}\n")
        sys.stderr.write("Feature branches should be named like: 001-feature-name\n")
        return False
        
    return True

def find_feature_dir_by_prefix(repo_root, branch_name):
    specs_dir = os.path.join(repo_root, "specs")
    match = re.match(r'^([0-9]{3})-', branch_name)
    
    if not match:
        return os.path.join(specs_dir, branch_name)
        
    prefix = match.group(1)
    matches = []
    
    if os.path.isdir(specs_dir):
        for d in os.listdir(specs_dir):
            if d.startswith(f"{prefix}-") and os.path.isdir(os.path.join(specs_dir, d)):
                matches.append(d)
                
    if len(matches) == 0:
        return os.path.join(specs_dir, branch_name)
    elif len(matches) == 1:
        return os.path.join(specs_dir, matches[0])
    else:
        sys.stderr.write(f"ERROR: Multiple spec directories found with prefix '{prefix}': {' '.join(matches)}\n")
        sys.stderr.write("Please ensure only one spec directory exists per numeric prefix.\n")
        return os.path.join(specs_dir, branch_name)

def get_feature_paths():
    repo_root = get_repo_root()
    current_branch = get_current_branch()
    has_git_repo = has_git()
    
    feature_dir = find_feature_dir_by_prefix(repo_root, current_branch)
    
    return {
        "REPO_ROOT": repo_root,
        "CURRENT_BRANCH": current_branch,
        "HAS_GIT": has_git_repo,
        "FEATURE_DIR": feature_dir,
        "FEATURE_SPEC": os.path.join(feature_dir, "spec.md"),
        "IMPL_PLAN": os.path.join(feature_dir, "plan.md"),
        "TASKS": os.path.join(feature_dir, "tasks.md"),
        "RESEARCH": os.path.join(feature_dir, "research.md"),
        "DATA_MODEL": os.path.join(feature_dir, "data-model.md"),
        "QUICKSTART": os.path.join(feature_dir, "quickstart.md"),
        "CONTRACTS_DIR": os.path.join(feature_dir, "contracts")
    }
