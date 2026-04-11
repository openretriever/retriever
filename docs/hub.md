# Retriever Hub Design

## API in a nutshell

```python
from retriever import hub

# For a single flow
LidarSlam = hub.use("company-abc/lidar-slam:LidarSlamFlow")
slam = LidarSlam(resolution=0.05) @ Rate(hz=10)
pipe.connect(pointcloud, slam, sync=Latest())

# For a whole package
lidar = hub.use("company-abc/lidar-slam")
slam = lidar.LidarSlamFlow(resolution=0.05) @ Rate(hz=10)
```

Module reference format:

```plaintext
{org}/{module-name}[:{attribute}][@{version}]
```

- `{org}`: organization name
- `{plugin-name}`: plugin name
- `{attribute}`: attribute name (optional)
- `{version}`: version (optional)

Full example:

```python
LidarSlam = hub.use("company-abc/lidar-slam:LidarSlamFlow@0.1.0")
slam = LidarSlam(resolution=0.05) @ Rate(hz=10)
pipe.connect(pointcloud, slam, sync=Latest())
```

## Packaging a module

Example directory structure:

```plaintext
lidar-slam/
├── pyproject.toml
└── lidar_slam/
    ├── flow.py
    └── config.py
```

`pyproject.toml` contents:

```toml
[project]
name = "lidar-slam"
version = "1.2.0"
dependencies = [
    "numpy>=1.24,<2",
]

[tool.retriever.module]
module = "lidar_slam"
min_retriever_version = "1.0.0"

[tool.retriever.module.exports]
LidarSlamFlow = "lidar_slam.flow:LidarSlamFlow"
LidarConfig = "lidar_slam.config:LidarConfig"
```

The `[tool.retriever.module]` section in `pyproject.toml` is what the Hub loader looks for. Standard Python metadata (`name`, `version`, `dependencies`) lives in the normal `[project]` table, while Retriever-specific fields live under `[tool.retriever.module]`.

Modules are expected to be published as a GitHub repository (or on other similar Git hosting services).

At least one semver Git tag is required for the module for versioning.

## Hub Index

Retriever Hub uses an official Git repository as the index for modules.

```plaintext
retriever-index/
├── schema.json                  # JSON schema for plugin entries
└── modules/
    ├── company-abc/
    │   ├── lidar-slam.toml
    │   └── imu-fusion.toml
    └── organization-xyz/
        └── hello-world.toml
```

Module entry example:

```toml
[module]
repo = "<https://github.com/company-abc/lidar-slam>"
description = "LiDAR SLAM pipeline"
author = "Company ABC"
license = "MIT"
tags = ["lidar", "slam", "mapping", "pointcloud"]

[module.links]
docs = "<https://company-abc.com/products/lidar-slam>"
support = "<https://github.com/company-abc/lidar-slam/issues>"
```

### Submission Process

Module authors submit their module to the Hub Index by opening a PR that adds a new module entry (toml file) under `modules/{org}/{name}.toml`.

Prerequisites before submitting:

- The module's Git repository is publicly accessible.
- The repository contains a valid `pyproject.toml` with a `[tool.retriever.module]` section.
- At least one semver Git tag is present in the repository.

Once the PR is opened, there should be some CI checks to validate the submission. Steps could be something like:

- The repo URL is reachable.
- Verify the `pyproject.toml` contains a valid `[tool.retriever.module]` section.
- At least one semver Git tag is present in the repository.
- The module name declared in `pyproject.toml` matches the filename in the PR.
- The module is importable in a clean environment.

## Loading process

1. Parse the `hub.use` string. Extract org, module name, export name, version, etc.
2. Check the local plugin cache. If exists, return from cache.
3. Look up `plugins/{org}/{name}.toml` in the index (fetch from GitHub, optionally cached?) -> get repo URL
4. Resolve version. If none specified, list Git tags via GitHub API and pick latest semver
5. Download the tarball for that tag
6. Extract it, read `pyproject.toml` from the archive root and parse the `[tool.retriever.module]` section
7. Check `min_retriever_version` against the running library version
8. Check `[project].dependencies` against installed packages via `importlib.metadata`
9. Add the extracted directory to `sys.path`, import the declared module and return the object
