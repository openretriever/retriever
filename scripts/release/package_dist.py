import shutil
import subprocess
from pathlib import Path


_BUNDLE_ONLY_TASKS = {
    "build",
    "package",
    "test",
    "test-control",
    "export-notebook-ready",
    "check-notebook-ready",
}


def _strip_bundle_only_tasks(pixi_content: str) -> str:
    """Remove maintainer-only Pixi tasks from the shipped distribution surface."""
    lines = pixi_content.splitlines()
    cleaned: list[str] = []
    in_tasks = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            in_tasks = stripped == "[tasks]"
            cleaned.append(line)
            continue

        if in_tasks:
            if stripped in {
                "# Build the wheel",
                "# Run: pixi run build",
                "# Create distribution bundle (Wheel + Examples + Config)",
                "# Run: pixi run package",
                "# Test tasks",
            }:
                continue

            if "=" in line:
                task_name = line.split("=", 1)[0].strip()
                if task_name in _BUNDLE_ONLY_TASKS:
                    continue

        cleaned.append(line)

    return "\n".join(cleaned) + "\n"


def main():
    # Define paths first so this script works from any current directory.
    root_dir = Path(__file__).resolve().parents[2]
    dist_dir = root_dir / "dist"
    bundle_name = "retriever_dist"
    bundle_dir = dist_dir / bundle_name

    # 1. Build the wheel from a clean local dist surface. Stale wheels can make
    # the bundled Pixi config point at the wrong distribution name.
    dist_dir.mkdir(exist_ok=True)
    for pattern in ("*.whl", "*.tar.gz"):
        for artifact in dist_dir.glob(pattern):
            artifact.unlink()

    print("Building wheel...")
    subprocess.run(["python", "-m", "build"], cwd=root_dir, check=True)

    # 2. Create bundle directory
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    # 3. Copy artifacts

    # Copy wheel(s)
    install_dir = bundle_dir / "install"
    install_dir.mkdir()
    for file in dist_dir.glob("*.whl"):
        shutil.copy(file, install_dir)
        print(f"Copied {file.name} to install/")

    # Copy examples
    examples_src = root_dir / "examples"
    examples_dst = bundle_dir / "examples"
    shutil.copytree(examples_src, examples_dst)
    print("Copied examples/")

    # Copy config and patch pixi.toml
    # Note: We do NOT copy pixi.lock because the source location changes, invalidating the lock.
    # Users will generate a new lock file on first install.

    # Get the freshly built retriever-core wheel.
    wheel_files = sorted(dist_dir.glob("retriever_core-*.whl"))
    if not wheel_files:
        raise RuntimeError("No retriever-core wheel found after build")
    else:
        wheel_name = wheel_files[0].name
        # Read and patch pixi.toml
        with open(root_dir / "pixi.toml", "r") as f:
            pixi_content = f.read()

        # Replace the local editable retriever-core dependency with the bundled wheel.
        target_str = 'retriever-core = { path = ".", editable = true'
        if target_str not in pixi_content:
            print(f"WARNING: Could not find dependency line '{target_str}' in pixi.toml")
        
        pixi_patched = pixi_content.replace(
            target_str,
            f'retriever-core = {{ path = "./install/{wheel_name}", editable = false'
        )
        pixi_patched = _strip_bundle_only_tasks(pixi_patched)

        with open(bundle_dir / "pixi.toml", "w") as f:
            f.write(pixi_patched)
        print(f"Copied and patched pixi.toml pointing to {wheel_name}")

    # Create README_DIST.md
    readme_content = f"""# Retriever Distribution

## Installation

### Option 1: Using Pixi (Recommended)

This distribution contains a `pixi.toml` configured to install the included wheel and dependencies.

1.  Install Pixi: `curl -fsSL https://pixi.sh/install.sh | bash`
2.  Install environment:
    ```bash
    pixi install
    ```
3.  Run examples:
    ```bash
    pixi run python examples/tutorial/b_ir_and_execution/06_dora_perception.py
    ```
4.  Enter shell:
    ```bash
    pixi shell
    ```

5.  Interactive Python (IPython):
    ```bash
    pixi run ipython
    # Then: import retriever
    ```

### Option 2: Standard Pip

1.  Create a virtual environment (optional).
2.  Install the wheel:
   ```bash
   pip install install/{wheel_name}
   ```
3.  Install example dependencies manually (numpy, opencv-python, etc).

## Running Examples

The `examples/` directory contains tutorial and advanced examples.

```bash
# Via Pixi
pixi run python examples/tutorial/b_ir_and_execution/06_dora_perception.py

# Or
pixi run demo-webcam-detection

# Via Pip environment
python examples/tutorial/b_ir_and_execution/06_dora_perception.py
```
"""
    with open(bundle_dir / "README.md", "w") as f:
        f.write(readme_content)

    # 4. Zip it up
    zip_path = dist_dir / f"{bundle_name}.zip"
    print(f"Zipping to {zip_path}...")
    shutil.make_archive(str(dist_dir / bundle_name), "zip", dist_dir, bundle_name)

    print(f"\nSUCCESS: Bundle created at {zip_path}")


if __name__ == "__main__":
    main()
