import os
import re

DOCS_DIR = "docs"

def process_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Check if frontmatter already exists
    if content.startswith("---"):
        print(f"Skipping {filepath}: Already has frontmatter")
        return

    # Find first H1
    match = re.search(r"^#\s+(.*?)(\n|$)", content, re.MULTILINE)
    
    if match:
        title = match.group(1).strip()
        # Create new content with FRONTMATTER + ORIGINAL CONTENT (including H1)
        # We quote the title to be safe
        new_content = f'---\ntitle: "{title}"\n---\n\n{content}'
        
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Updated {filepath}: Added frontmatter for '{title}'")
    else:
        print(f"Skipping {filepath}: No H1 found")

for root, _, files in os.walk(DOCS_DIR):
    for file in files:
        if file.endswith(".md"):
            process_file(os.path.join(root, file))
