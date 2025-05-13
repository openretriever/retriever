# 🐕 Retriever

**Retriever: open-world robot planning and learning**

<div align="center">
  <strong>Retriever</strong>
</div>

<div align="center">
  <img src="assets/codebase-diagram.svg" width="800" alt="Retriever Codebase Architecture">
</div>

Retriever is a framework for open-world robot bilevel planning and learning. It provides tools and infrastructure for:
- Integrating pretrained foundation models with robotics
- Planning and executing complex tasks
- Learning and deploying robot skills

## Key Features

### 1. Foundation Model Integration
- Vision-Language Models for open-world perception and goal specification
- Segmentation Models for object detection and manipulation targets
- Large Language Models for high-level task planning and reasoning

### 2. Flexible Task Planning 
- Commandline interface (CLI) for direct interaction
- Classical symbolic planning with PDDL
- Learning-based planning with pretrained models
- Hybrid approaches combining symbolic and learned components

### 3. Extensible Skills Library
- Basic manipulation primitives (pick, place, push, etc.)
- Navigation behaviors (e.g., move to a target location, landmark, or object)
- Compound skills composed of primitives

## Getting Started

- [Installation Guide](getting-started/installation.md) - Set up your environment
- [Quick Start](getting-started/quick-start.md) - Run your first example
- [System Setup](setup.md) - Configure your system
- [Usage Guide](usage.md) - Learn how to use Retriever

## Advanced Topics

- [Running the System](run-system.md) - System architecture and execution
- [Training](run-train.md) - Training custom models and skills
- [Ray Cluster Setup](run-ray-cluster.md) - Distributed computing setup

## Development Resources

- [Contributing Guide](contributing.md) - How to contribute to Retriever
- [Code Style Guide](development/code-style.md) - Coding standards and practices

## Examples and Tutorials

- [Examples](examples/) - Ready-to-run examples
- [Robots](robots/) - Robot-specific documentation

## Getting Help

If you encounter any issues or have questions:

1. Check the [documentation](usage.md)
2. Open an issue on [GitHub](https://github.com/linfeng-z/Retriever)
3. Visit our [Notion page](https://www.notion.so/retriever-dev/Retriever-Dev-Homepage-bfd5d802e1f346ac81a1ea773f6418e9?pvs=4) for additional resources

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 