import os
import sys
import json
import argparse
from common import get_feature_paths, check_feature_branch

def main():
    parser = argparse.ArgumentParser(description="Consolidated prerequisite checking for Spec-Driven Development workflow.")
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--require-tasks', action='store_true', help='Require tasks.md to exist')
    parser.add_argument('--include-tasks', action='store_true', help='Include tasks.md in AVAILABLE_DOCS list')
    parser.add_argument('--paths-only', action='store_true', help='Only output path variables')
    
    args = parser.parse_args()
    
    paths = get_feature_paths()
    repo_root = paths["REPO_ROOT"]
    current_branch = paths["CURRENT_BRANCH"]
    has_git = paths["HAS_GIT"]
    
    feature_dir = paths["FEATURE_DIR"]
    feature_spec = paths["FEATURE_SPEC"]
    impl_plan = paths["IMPL_PLAN"]
    tasks = paths["TASKS"]
    research = paths["RESEARCH"]
    data_model = paths["DATA_MODEL"]
    contracts_dir = paths["CONTRACTS_DIR"]
    quickstart = paths["QUICKSTART"]
    
    if not check_feature_branch(current_branch, has_git):
        sys.exit(1)
        
    if args.paths_only:
        if args.json:
            print(json.dumps({
                "REPO_ROOT": repo_root,
                "BRANCH": current_branch,
                "FEATURE_DIR": feature_dir,
                "FEATURE_SPEC": feature_spec,
                "IMPL_PLAN": impl_plan,
                "TASKS": tasks
            }))
        else:
            print(f"REPO_ROOT: {repo_root}")
            print(f"BRANCH: {current_branch}")
            print(f"FEATURE_DIR: {feature_dir}")
            print(f"FEATURE_SPEC: {feature_spec}")
            print(f"IMPL_PLAN: {impl_plan}")
            print(f"TASKS: {tasks}")
        sys.exit(0)
        
    if not os.path.exists(feature_dir) or not os.path.isdir(feature_dir):
        sys.stderr.write(f"ERROR: Feature directory not found: {feature_dir}\n")
        sys.stderr.write("Run /speckit.specify first to create the feature structure.\n")
        sys.exit(1)
        
    if not os.path.isfile(impl_plan):
        sys.stderr.write(f"ERROR: plan.md not found in {feature_dir}\n")
        sys.stderr.write("Run /speckit.plan first to create the implementation plan.\n")
        sys.exit(1)
        
    if args.require_tasks and not os.path.isfile(tasks):
        sys.stderr.write(f"ERROR: tasks.md not found in {feature_dir}\n")
        sys.stderr.write("Run /speckit.tasks first to create the task list.\n")
        sys.exit(1)
        
    docs = []
    if os.path.isfile(research): docs.append("research.md")
    if os.path.isfile(data_model): docs.append("data-model.md")
    
    if os.path.isdir(contracts_dir) and any(os.path.isfile(os.path.join(contracts_dir, f)) for f in os.listdir(contracts_dir)):
        docs.append("contracts/")
        
    if os.path.isfile(quickstart): docs.append("quickstart.md")
    if args.include_tasks and os.path.isfile(tasks): docs.append("tasks.md")
    
    if args.json:
        print(json.dumps({
            "FEATURE_DIR": feature_dir,
            "AVAILABLE_DOCS": docs
        }))
    else:
        print(f"FEATURE_DIR:{feature_dir}")
        print("AVAILABLE_DOCS:")
        print(f"  {'✓' if os.path.isfile(research) else '✗'} research.md")
        print(f"  {'✓' if os.path.isfile(data_model) else '✗'} data-model.md")
        print(f"  {'✓' if 'contracts/' in docs else '✗'} contracts/")
        print(f"  {'✓' if os.path.isfile(quickstart) else '✗'} quickstart.md")
        if args.include_tasks:
            print(f"  {'✓' if os.path.isfile(tasks) else '✗'} tasks.md")

if __name__ == "__main__":
    main()
