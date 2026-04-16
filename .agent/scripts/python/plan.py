import os
import sys
import json
import argparse
from common import get_feature_paths, check_feature_branch

def main():
    parser = argparse.ArgumentParser(description="Setup implementation plan")
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    args = parser.parse_args()
    
    paths = get_feature_paths()
    
    repo_root = paths["REPO_ROOT"]
    current_branch = paths["CURRENT_BRANCH"]
    has_git = paths["HAS_GIT"]
    feature_dir = paths["FEATURE_DIR"]
    feature_spec = paths["FEATURE_SPEC"]
    impl_plan = paths["IMPL_PLAN"]
    
    if not check_feature_branch(current_branch, has_git):
        sys.exit(1)
        
    os.makedirs(feature_dir, exist_ok=True)
    
    template = os.path.join(repo_root, ".agent", "skills", "speckit.plan", "templates", "plan-template.md")
    
    if os.path.isfile(template):
        with open(template, 'r', encoding='utf-8') as src, open(impl_plan, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        sys.stderr.write(f"Copied plan template to {impl_plan}\n")
    else:
        sys.stderr.write(f"Warning: Plan template not found at {template}\n")
        if not os.path.exists(impl_plan):
            with open(impl_plan, 'w', encoding='utf-8') as f:
                f.write('')
                
    if args.json:
        print(json.dumps({
            "FEATURE_SPEC": feature_spec,
            "IMPL_PLAN": impl_plan,
            "SPECS_DIR": feature_dir,
            "BRANCH": current_branch,
            "HAS_GIT": str(has_git).lower()
        }))
    else:
        print(f"FEATURE_SPEC: {feature_spec}")
        print(f"IMPL_PLAN: {impl_plan}")
        print(f"SPECS_DIR: {feature_dir}")
        print(f"BRANCH: {current_branch}")
        print(f"HAS_GIT: {str(has_git).lower()}")

if __name__ == "__main__":
    main()
