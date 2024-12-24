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


## Codebase Structure

Our codebase maintains three key components:

### 1. Pretrained Model Integration
We maintain optimized inference pipelines for foundation models, designed for efficient robot perception and planning:

- Vision-Language Models for open-world perception and goal specification
- Segmentation Models for object detection and manipulation targets
- Large Language Models for high-level task planning and reasoning

The models are wrapped in Ray actors/services for distributed inference and easy integration with other components. See `src/models/` for implementations.

### 2. Task Planning Approaches 
We support multiple approaches for high-level task planning or task specification:

- Commandline interface (CLI) for direct interaction with robot
- Classical symbolic planning with PDDL
- Learning-based planning with pretrained models
- Hybrid approaches combining symbolic and learned components

The planning modules are designed to be modular and extensible. Different planners can be easily swapped in/out based on the task requirements.

### 3. Robot Skills Library
We maintain a collection of parameterized robot skills, for e.g., Spot robot:

- Basic manipulation primitives (pick, place, push, etc.)
- Navigation behaviors (e.g., move to a target location, landmark, or object)
- Compound skills composed of primitives

Skills are implemented as configurable functions with clear interfaces. Parameters can be:
- Manually specified by human
- Proposed by pretrained models or learned parameter policies
- Optimized through planning

The modular design allows easy modification of existing skills and addition of new ones. Skills can be composed into more complex behaviors through the task planner.



## Development

- See our Notion page for more documents and tracking progress.
- Steps for pushing your code:
    1. create a new branch with `<type>/<short-description>-<date>`
        1. use e.g., `bugfix/<name>-<date>`
        2. different types: e.g., `general/...`, `bugfix/...`, `feature/...`, …
    2. make commits to your branch
    3. push the branch to remote
    4. submit pull request on GitHub
    5. ask for review & merge


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
Ensure you have Python 3.10 or higher installed.

#### 1. Environment Setup and PyTorch Installation

First, create a conda environment and install PyTorch:
```sh
# Create and activate a conda environment
conda create -n retriever python=3.10
conda activate retriever

# Install PyTorch with CUDA support (choose based on your CUDA version)
conda install pytorch torchvision pytorch-cuda=11.8 -c pytorch -c nvidia  # For CUDA 11.8
```

#### 2. Package Installation

We recommend using `uv` for faster package installation:

```sh
# Install uv (much faster than pip)
pip install uv

# Install basic dependencies
uv pip install -e .

# Optional: Install additional components
uv pip install ".[spot]"      # Boston Dynamics Spot dependencies
uv pip install ".[models]"    # Foundation models and vision components
uv pip install ".[mapper]"    # Mapping related dependencies
uv pip install ".[training]"  # Skill Training related dependencies
uv pip install ".[all]"       # Install all optional dependencies
```

Alternatively, you can use `pip` directly:
```sh
pip install -e .
```

#### Common Issues

- **CUDA Version Conflicts**: Make sure to install PyTorch through conda/mamba with the correct CUDA version before installing the package dependencies. This prevents potential CUDA driver compatibility issues.
