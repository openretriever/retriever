import shutil
import subprocess
from pathlib import Path


def main():
    # 1. Build the wheel
    print("Building wheel...")
    subprocess.run(["python", "-m", "build"], check=True)

    # Define paths
    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"
    bundle_name = "retriever_dist"
    bundle_dir = dist_dir / bundle_name

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

    # Get the wheel filename (assuming one wheel)
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("Warning: No wheel found to patch pixi.toml")
        shutil.copy(root_dir / "pixi.toml", bundle_dir)
        wheel_name = "retriever-0.0.0-py3-none-any.whl"  # Fallback for readme
    else:
        wheel_name = wheel_files[0].name
        # Read and patch pixi.toml
        with open(root_dir / "pixi.toml", "r") as f:
            pixi_content = f.read()

        # Replace the retriever dependency line
        # We look for the line starting with 'retriever = { path = "."'
        target_str = 'retriever = { path = ".", editable = true'
        if target_str not in pixi_content:
            print(f"WARNING: Could not find dependency line '{target_str}' in pixi.toml")
        
        pixi_patched = pixi_content.replace(
            target_str,
            f'retriever = {{ path = "./install/{wheel_name}", editable = false'
        )

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
    pixi run demo-webcam-detection
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
pixi run demo-webcam-detection

# Or
pixi run demo-webcam-detection

# Via Pip environment
python -m examples.tutorial.b_ir_and_execution.06_dora_perception
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
