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

    # Copy config
    shutil.copy(root_dir / "pixi.toml", bundle_dir)
    shutil.copy(root_dir / "pixi.lock", bundle_dir)
    print("Copied pixi config")

    # Create README_DIST.md
    readme_content = """# Retriever Distribution

## Installation

1.  Navigate to the `install/` directory.
2.  Run `pip install retriever-*.whl`.

   ```bash
   pip install install/retriever-0.0.0-py3-none-any.whl
   ```

## Running Examples

You can run the examples in the `examples/` directory using your python environment.

```bash
python examples/tutorial/009_dora_perception.py
```

## Reproducing Environment (Optional)

If you need to reproduce the exact development environment, you can use `pixi` with the provided `pixi.toml` and `pixi.lock` files.
"""
    with open(bundle_dir / "README.md", "w") as f:
        f.write(readme_content)
    
    # 4. Zip it up
    zip_path = dist_dir / f"{bundle_name}.zip"
    print(f"Zipping to {zip_path}...")
    shutil.make_archive(str(dist_dir / bundle_name), 'zip', dist_dir, bundle_name)
    
    print(f"\nSUCCESS: Bundle created at {zip_path}")

if __name__ == "__main__":
    main()
