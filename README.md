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

- Development workflow, pre-commit hooks, and QA steps: see `docs/contributing.md`.


## Setup (overview)

Use Python 3.10–3.12 (avoid 3.14; some deps lack wheels).

Quick start with [Pixi](https://pixi.sh):
```sh
curl -fsSL https://pixi.sh/install.sh | bash
pixi run demo-dora
# PyTorch envs:
pixi run -e cpu python your_script.py      # CPU (all platforms)
pixi run -e gpu python your_script.py      # GPU with CUDA 12.4 (Linux only)
```

If dora complains about version/schema, kill stale processes:
```sh
pkill -9 dora && pixi run demo-dora
```

`pixi.lock` is multi-platform (osx-arm64, linux-64). Commit it for reproducible installs; other platforms can re-lock after adding the platform to `pixi.toml` and running `pixi install`.

Pixi manages its own env. If you prefer `uv`/`pip`, use a separate conda/venv to avoid mixing managers.

Pixi installs the PyPI portion using `uv` internally; you usually don't need to run `uv` yourself when using Pixi.

Full installation (Pixi/conda/uv), dora CLI notes, and troubleshooting: see `docs/install.md`.

## Documentation

Docs live in `docs/` (served via MkDocs). See `docs/guide_dev.md` for local preview/build commands.
