import os
import re

DOCS_DIR = "docs"

def revert_frontmatter(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Regex to capture title from frontmatter
    # Matches:
    # ---
    # title: "Some Title"
    # ---
    # (optional newlines)
    # (rest of content)
    match = re.match(r"^---\n+title: [\"']?(.+?)[\"']?\n+---\n+(.*)", content, re.DOTALL)
    
    if match:
        title = match.group(1).strip()
        body = match.group(2).strip()
        
        # Restore as H1
        new_content = f"# {title}\n\n{body}\n"
        
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Reverted {filepath}: Restored header '# {title}'")
    else:
        print(f"Skipping {filepath}: No matching frontmatter found")

for root, _, files in os.walk(DOCS_DIR):
    for file in files:
        if file.endswith(".md"):
            revert_frontmatter(os.path.join(root, file))
