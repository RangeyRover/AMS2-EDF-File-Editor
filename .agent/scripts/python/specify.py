import os
import sys
import json
import argparse
import re
from common import get_repo_root, has_git, run_cmd

def clean_branch_name(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9]', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def generate_branch_name(description):
    stop_words = {"i","a","an","the","to","for","of","in","on","at","by","with","from",
                  "is","are","was","were","be","been","being","have","has","had","do","does","did",
                  "will","would","should","could","can","may","might","must","shall",
                  "this","that","these","those","my","your","our","their",
                  "want","need","add","get","set"}
    
    clean_desc = re.sub(r'[^a-zA-Z0-9]', ' ', description)
    words = clean_desc.split()
    
    meaningful_words = []
    for w in words:
        wl = w.lower()
        if wl in stop_words:
            continue
            
        if len(wl) >= 3:
            meaningful_words.append(wl)
        elif bool(re.search(r'\b' + re.escape(w.upper()) + r'\b', description)):
            meaningful_words.append(wl)
            
    if meaningful_words:
        max_words = 4 if len(meaningful_words) == 4 else 3
        return '-'.join(meaningful_words[:max_words])
        
    cleaned = clean_branch_name(description)
    return '-'.join(cleaned.split('-')[:3])

def get_highest_from_specs(specs_dir):
    highest = 0
    if os.path.isdir(specs_dir):
        for d in os.listdir(specs_dir):
            if os.path.isdir(os.path.join(specs_dir, d)):
                match = re.match(r'^([0-9]+)', d)
                if match:
                    try:
                        num = int(match.group(1))
                        if num > highest:
                            highest = num
                    except ValueError:
                        pass
    return highest

def get_highest_from_branches():
    highest = 0
    branches = run_cmd(["git", "branch", "-a"])
    if branches:
        for line in branches.split('\n'):
            clean = line.strip()
            clean = re.sub(r'^[\*\s]+', '', clean)
            clean = re.sub(r'^remotes/[^/]*/', '', clean)
            
            match = re.search(r'^([0-9]{3})-', clean)
            if match:
                try:
                    num = int(match.group(1))
                    if num > highest:
                        highest = num
                except ValueError:
                    pass
    return highest

def check_existing_branches(specs_dir):
    run_cmd(["git", "fetch", "--all", "--prune"])
    highest_branch = get_highest_from_branches()
    highest_spec = get_highest_from_specs(specs_dir)
    return max(highest_branch, highest_spec) + 1

def main():
    parser = argparse.ArgumentParser(description="Create a new feature branch and spec")
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--short-name', type=str, help='Provide a custom short name (2-4 words)')
    parser.add_argument('--number', type=int, help='Specify branch number manually')
    parser.add_argument('description', nargs='+', help='Feature description')
    
    args = parser.parse_args()
    feature_desc = " ".join(args.description).strip()
    
    if not feature_desc:
        sys.stderr.write("Usage: specify.py [--json] [--short-name <name>] [--number N] <feature_description>\n")
        sys.exit(1)
        
    repo_root = get_repo_root()
    if not repo_root:
        sys.stderr.write("Error: Could not determine project root.\n")
        sys.exit(1)
        
    is_git = has_git()
    specs_dir = os.path.join(repo_root, "specs")
    os.makedirs(specs_dir, exist_ok=True)
    
    if args.short_name:
        branch_suffix = clean_branch_name(args.short_name)
    else:
        branch_suffix = generate_branch_name(feature_desc)
        
    if args.number is not None:
        branch_number = args.number
    else:
        if is_git:
            branch_number = check_existing_branches(specs_dir)
        else:
            branch_number = get_highest_from_specs(specs_dir) + 1
            
    feature_num_str = f"{branch_number:03d}"
    branch_name = f"{feature_num_str}-{branch_suffix}"
    
    max_branch_length = 244
    encoded_length = len(branch_name.encode('utf-8'))
    
    if encoded_length > max_branch_length:
        max_suffix_bytes = max_branch_length - 4
        suffix_bytes = branch_suffix.encode('utf-8')
        if len(suffix_bytes) > max_suffix_bytes:
            truncated_suffix = suffix_bytes[:max_suffix_bytes].decode('utf-8', errors='ignore')
        else:
            truncated_suffix = branch_suffix
            
        truncated_suffix = truncated_suffix.rstrip('-')
        
        sys.stderr.write("[specify] Warning: Branch name exceeded GitHub's 244-byte limit\n")
        sys.stderr.write(f"[specify] Original: {branch_name} ({encoded_length} bytes)\n")
        branch_name = f"{feature_num_str}-{truncated_suffix}"
        sys.stderr.write(f"[specify] Truncated to: {branch_name} ({len(branch_name.encode('utf-8'))} bytes)\n")
        
    if is_git:
        run_cmd(["git", "checkout", "-b", branch_name], cwd=repo_root)
    else:
        sys.stderr.write(f"[specify] Warning: Git repository not detected; skipped branch creation for {branch_name}\n")
        
    feature_dir = os.path.join(specs_dir, branch_name)
    os.makedirs(feature_dir, exist_ok=True)
    
    template = os.path.join(repo_root, ".agent", "skills", "speckit.specify", "templates", "spec-template.md")
    spec_file = os.path.join(feature_dir, "spec.md")
    
    if os.path.isfile(template):
        with open(template, 'r', encoding='utf-8') as src, open(spec_file, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    else:
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write('')
            
    os.environ['SPECIFY_FEATURE'] = branch_name
    
    if args.json:
        print(json.dumps({
            "BRANCH_NAME": branch_name,
            "SPEC_FILE": spec_file,
            "FEATURE_NUM": feature_num_str
        }))
    else:
        print(f"BRANCH_NAME: {branch_name}")
        print(f"SPEC_FILE: {spec_file}")
        print(f"FEATURE_NUM: {feature_num_str}")
        print(f"SPECIFY_FEATURE environment variable set to: {branch_name}")

if __name__ == "__main__":
    main()
