import os
import sys
import datetime
import uuid
import shutil
from common import get_feature_paths

def log_info(m): print(f"INFO: {m}")
def log_success(m): print(f"✓ {m}")
def log_warn(m): sys.stderr.write(f"WARNING: {m}\n")
def log_error(m): sys.stderr.write(f"ERROR: {m}\n")

def extract_plan_field(pattern, plan_file):
    prefix = f"**{pattern}**: "
    try:
        with open(plan_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith(prefix):
                    val = line[len(prefix):].strip()
                    if "NEEDS CLARIFICATION" in val or val == "N/A":
                        return ""
                    return val
    except Exception:
        pass
    return ""

def format_tech_stack(lang, fw):
    parts = []
    if lang and lang != "NEEDS CLARIFICATION": parts.append(lang)
    if fw and fw not in ("NEEDS CLARIFICATION", "N/A"): parts.append(fw)
    return " + ".join(parts)

def update_agent_file(target_file, agent_name, new_lang, new_fw, new_db, new_ptype, current_branch, repo_root):
    log_info(f"Updating {agent_name} context file: {target_file}")
    
    project_name = os.path.basename(repo_root)
    current_date = datetime.datetime.now().strftime("%yyyy-%mm-%dd")
    
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    template_file = os.path.join(repo_root, ".agent", "skills", "speckit.plan", "templates", "agent-file-template.md")
    
    tech_stack = format_tech_stack(new_lang, new_fw)
    new_tech_entries = []
    new_change_entry = ""
    
    if tech_stack:
        new_tech_entries.append(f"- {tech_stack} ({current_branch})")
    if new_db:
        new_tech_entries.append(f"- {new_db} ({current_branch})")
        
    if tech_stack:
        new_change_entry = f"- {current_branch}: Added {tech_stack}"
    elif new_db:
        new_change_entry = f"- {current_branch}: Added {new_db}"
        
    if not os.path.isfile(target_file):
        if not os.path.isfile(template_file):
            log_error(f"Template not found at {template_file}")
            return False
            
        with open(template_file, 'r', encoding='utf-8') as f: content = f.read()
        
        project_structure = "backend/\nfrontend/\ntests/" if "web" in new_ptype.lower() else "src/\ntests/"
        commands = "cd src && pytest && ruff check ." if "Python" in new_lang else (
            "cargo test && cargo clippy" if "Rust" in new_lang else (
            "npm test && npm run lint" if "Script" in new_lang else f"# Add commands for {new_lang}"
        ))
        conventions = f"{new_lang}: Follow standard conventions"
        
        ts_str = f"- {tech_stack} ({current_branch})" if tech_stack else f"- ({current_branch})"
        rc_str = f"- {current_branch}: Added {tech_stack}" if tech_stack else f"- {current_branch}: Added"
        
        content = content.replace("[PROJECT NAME]", project_name)\
                         .replace("[DATE]", current_date)\
                         .replace("[EXTRACTED FROM ALL PLAN.MD FILES]", ts_str)\
                         .replace("[ACTUAL STRUCTURE FROM PLANS]", project_structure)\
                         .replace("[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES]", commands)\
                         .replace("[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE]", conventions)\
                         .replace("[LAST 3 FEATURES AND WHAT THEY ADDED]", rc_str)
                         
        with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
        log_success(f"Created new {agent_name} context file")
        return True

    with open(target_file, 'r', encoding='utf-8') as f: lines = f.read().splitlines()
    
    # In-place patch preserving bash logic
    out = []
    in_tech = False
    in_changes = False
    tech_added = False
    existing_changes_count = 0
    
    has_tech = any(l == "## Active Technologies" for l in lines)
    has_recent = any(l == "## Recent Changes" for l in lines)
    
    # Skip entries if already present
    content_str = "\n".join(lines)
    if tech_stack and tech_stack in content_str:
        new_tech_entries = [e for e in new_tech_entries if tech_stack not in e]
    if new_db and new_db in content_str:
        new_tech_entries = [e for e in new_tech_entries if new_db not in e]
        
    for line in lines:
        if line == "## Active Technologies":
            out.append(line)
            in_tech = True
            continue
            
        if in_tech and line.startswith("## "):
            if not tech_added and new_tech_entries:
                out.extend(new_tech_entries)
                tech_added = True
            out.append(line)
            in_tech = False
            continue
            
        if in_tech and line.strip() == "":
            if not tech_added and new_tech_entries:
                out.extend(new_tech_entries)
                tech_added = True
            out.append(line)
            continue
            
        if line == "## Recent Changes":
            out.append(line)
            if new_change_entry: out.append(new_change_entry)
            in_changes = True
            continue
            
        if in_changes and line.startswith("## "):
            out.append(line)
            in_changes = False
            continue
            
        if in_changes and line.startswith("- "):
            if existing_changes_count < 2:
                out.append(line)
                existing_changes_count += 1
            continue
            
        if "**Last updated**:" in line:
            import re
            line = re.sub(r'\d{4}-\d{2}-\d{2}', current_date, line, 1)
            
        out.append(line)
        
    if in_tech and not tech_added and new_tech_entries:
        out.extend(new_tech_entries)
        
    if not has_tech and new_tech_entries:
        out.extend(["", "## Active Technologies"] + new_tech_entries)
        
    if not has_recent and new_change_entry:
        out.extend(["", "## Recent Changes", new_change_entry])
        
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(out) + "\n")
        
    log_success(f"Updated existing {agent_name} context file")
    return True

def main():
    agent_type = sys.argv[1] if len(sys.argv) > 1 else ""
    paths = get_feature_paths()
    
    repo_root = paths["REPO_ROOT"]
    current_branch = paths["CURRENT_BRANCH"]
    
    if not current_branch:
        log_error("Unable to determine current feature")
        sys.exit(1)
        
    plan_file = paths["IMPL_PLAN"]
    if not os.path.isfile(plan_file):
        log_error(f"No plan.md found at {plan_file}")
        sys.exit(1)
        
    new_lang = extract_plan_field("Language/Version", plan_file)
    new_fw = extract_plan_field("Primary Dependencies", plan_file)
    new_db = extract_plan_field("Storage", plan_file)
    new_ptype = extract_plan_field("Project Type", plan_file)
    
    agents = {
        "claude": (os.path.join(repo_root, "CLAUDE.md"), "Claude Code"),
        "gemini": (os.path.join(repo_root, "GEMINI.md"), "Gemini CLI"),
        "copilot": (os.path.join(repo_root, ".github", "agents", "copilot-instructions.md"), "GitHub Copilot"),
        "cursor-agent": (os.path.join(repo_root, ".cursor", "rules", "specify-rules.mdc"), "Cursor IDE"),
        "qwen": (os.path.join(repo_root, "QWEN.md"), "Qwen Code")
    }
    
    if agent_type:
        if agent_type not in agents:
            log_error(f"Unknown agent type '{agent_type}'. Valid options: {', '.join(agents.keys())}")
            sys.exit(1)
        targets = [agents[agent_type]]
    else:
        targets = [v for v in agents.values() if os.path.isfile(v[0])]
        if not targets:
            targets = [agents["claude"]] # Default fallback
            
    for t_file, a_name in targets:
        update_agent_file(t_file, a_name, new_lang, new_fw, new_db, new_ptype, current_branch, repo_root)

if __name__ == "__main__":
    main()
