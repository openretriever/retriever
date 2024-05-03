<div align="center">
  <a href="https://github.com/zhao0625/Retriever"><img width="400px" height="auto" src="assets/retriever-illustrative.jpeg"></a>
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
