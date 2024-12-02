<div align="center">
  <a href="https://github.com/linfeng-z/Retriever"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg"></a>
</div>



# 🐕 Retriever

**Retriever: open-world robot planning and learning**

> This is an early-stage repository that maintains some infrastructure and research code for open-world robot bilevel planning and learning. The code is not necessarily associated with specific research projects.

> See the [Notion page](https://www.notion.so/retriever-dev/Retriever-Dev-Homepage-bfd5d802e1f346ac81a1ea773f6418e9?pvs=4) for tracking and documents.

We use e.g., _bilevel planning_, _skill learning_, _pretrained foundation models_.
For `bilevel planning` or `task and motion planning` (TAMP), see the following resources:
- (Paper) [Practice Makes Perfect: Planning to Learn Skill Parameter Policies](http://ees.csail.mit.edu)
- (Blog) [Bilevel Planning for Robots: An Illustrated Introduction](https://lis.csail.mit.edu/bilevel-planning-for-robots-an-illustrated-introduction/)
- (Codebase) LIS [`predicators`](https://github.com/Learning-and-Intelligent-Systems/predicators) and BDAI [`predicators`](https://github.com/bdaiinstitute/predicators)

Two levels here:
- High-level task planning and perception (AI planners or VLMs driven)
- Low-level skills and parameters (scripted functions or learned models)


## Development

- See our Notion page for more documents and tracking progress.
- Steps for pushing your code:
    1. create a new branch with `<type>/<short-description>-<date>`
        1. use e.g., `bugfix/<name>-<date>`
        2. different types: e.g., `general/...`, `bugfix/...`, `feature/...`, …
    2. make commits to your branch
    3. push the branch to remote
    4. submit pull request on GitHub
    5. ask people to review & get pass
        1. (to decide more detail)


## Setup

### Pre-commit Hooks

To maintain code quality and consistency, we use pre-commit hooks. These hooks automatically run checks and formatting tools before you make a commit. To set up pre-commit hooks:

1. Install pre-commit:
    ```sh
    pip install pre-commit
    ```

2. Install the git hooks:
    ```sh
    pre-commit install
    ```

3. (Optional) Run hooks manually on all files:
    ```sh
    pre-commit run --all-files
    ```

### Installation

This project uses `pyproject.toml` for dependency management.

1. Ensure you have Python 3.10 or higher installed.

2. Basic installation (core dependencies only):
    ```sh
    pip install .
    ```

3. Install with optional dependencies:
    ```sh
    # Install all optional dependencies
    pip install .[all]

    # Or install specific groups:
    pip install .[dev]     # Development tools only
    pip install .[mapper]  # Mapper dependencies only
    ```

### Dependencies Overview

#### Core Dependencies
- Installed automatically with `pip install .`
- Includes essential packages needed to run the project

#### Development Dependencies (`.[dev]`)
- `black` - Code formatter
- `ruff` - Fast Python linter
- `mypy` - Static type checker
- `pytest` - Testing framework
- `pre-commit` - Git hooks manager
- `pytest-cov` - Code coverage tool

#### Mapper Dependencies (`.[mapper]`)
- `dgl` - Deep Graph Library
- `open3d` - 3D data processing
- `lxml` - XML/HTML processing

#### All Dependencies (`.[all]`)
- Installs everything: core, dev, and mapper dependencies

