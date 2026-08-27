# Adding a New Skill and Tool to EasyGS

EasyGS analysis capabilities can be added at any time as plugins. To add a new capability, follow the templates in this guide and adapt them to the capability you want to implement. After completing these steps, you will be able to add a new analysis capability to EasyGS.

## Step 1: Understand the EasyGS Capability Flow

EasyGS processes analysis requests through the following flow:

```text
User request
  -> The main Agent reads the Skill and collects parameters
  -> submit_workflow submits a background task
  -> The background Workflow calls AnalysisActionTool
  -> AnalysisActionTool calls prepare_run() on the concrete Tool
  -> The analysis script runs
  -> Output files and the summary return to the Workflow
```

The three core components have the following responsibilities:

| Component | Responsibility |
| --- | --- |
| Skill | Tells the model when to use the capability, which parameters to collect, and how to interpret the results |
| Tool | Defines the parameter Schema, validates paths, prepares commands, and describes outputs |
| WorkflowDefinition | Registers the Tool as an action available to a background Workflow |

Built-in Skills are discovered automatically from `easygs/skills/<skill_name>/SKILL.md`. Python Tools are not discovered automatically and must be registered in `easygs/agent/workflows.py`.

## Step 2: Define Inputs and Outputs

Before adding a new analysis capability, determine the following:

| Item | What to define |
| --- | --- |
| Required inputs | File, directory, text, or numeric parameters |
| Optional inputs | Defaults, switches, thresholds, and output prefixes |
| Input format | File extensions, column names, encoding, and data constraints |
| Output format | The result files most important to the user |
| Runtime environment | EasyGS_1 through EasyGS_5 or the main Python environment |
| Default duration | Used to set the Tool timeout |

Only expose parameters that users need to configure in the Tool's public Schema. The Tool should manage reference files, internal script paths, and fixed resource paths.

## Step 3: Create the File Structure

Adding an EasyGS analysis capability typically requires the following files:

```text
easygs/
├── agent/
│   ├── tools/
│   │   └── custom_analysis.py
│   └── workflows.py
└── skills/
    └── custom_analysis/
        ├── SKILL.md
        └── scripts/
            └── run_custom_analysis.py
tests/
└── test_custom_analysis.py
```

## Step 4: Implement the Analysis Program

Organize the capability you want to add and place its implementation in:

```text
easygs/skills/custom_analysis/scripts/
```

The analysis program may use Python, R, Shell, or an existing bioinformatics program. Regardless of the implementation, it should meet these requirements:

1. Receive input and output paths through explicit command-line arguments.
2. Do not infer user file locations from the current working directory.
3. Do not generate files in undeclared locations.
4. Return exit code `0` on success.
5. Write clear errors to `stderr` and return a nonzero exit code on failure.
6. Provide a configurable random seed for randomized algorithms.

## Step 5: Create the Tool Module

Create and modify:

```text
easygs/agent/tools/custom_analysis.py
```

The Tool converts parameters supplied by the model into a safe and deterministic execution plan.

### 5.1 Define the Prepared Result

The prepared result contains the command, output directory, and primary result paths. Adapt the following template to your capability:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PreparedCustomAnalysisRun:
    command: list[str]
    input_path: Path
    output_dir: Path
    result_path: Path
    summary_path: Path

    def to_metadata(self) -> dict[str, Any]:
        return {
            "input_path": str(self.input_path),
            "output_dir": str(self.output_dir),
            "result_path": str(self.result_path),
            "summary_path": str(self.summary_path),
        }
```

Paths in `to_metadata()` are used for Workflow result display and file discovery. Prefer established names such as `output_dir`, `result_path`, and `summary_path`.

### 5.2 Implement the Tool Interface

Every Tool must inherit from `Tool` and implement the following members. Adapt this template to your capability:

```python
from typing import Any

from easygs.agent.tools.base import Tool


class RunCustomAnalysisTool(Tool):
    @property
    def name(self) -> str:
        return "run_custom_analysis"

    @property
    def description(self) -> str:
        return "Run the custom analysis and produce its result files."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Path to the required input.",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Optional output directory.",
                },
                "prefix": {
                    "type": "string",
                    "description": "Optional output basename.",
                },
            },
            "required": ["input_path"],
        }

    async def execute(self, **kwargs: Any) -> str:
        prepared = await self.prepare_run(**kwargs)
        # Execute prepared.command and handle timeout, exit code, stdout, and stderr.
        ...

    async def prepare_run(self, **kwargs: Any) -> PreparedCustomAnalysisRun:
        # Validate parameters and dependencies, resolve paths, build the command,
        # and return output metadata.
        ...
```

### 5.3 Validate Paths

Process user-provided paths with `_resolve_path()`:

```python
from easygs.agent.tools.filesystem import _resolve_path

input_path = _resolve_path(kwargs["input_path"], self.allowed_dir)
```

Path validation should cover at least:

1. Whether the input exists.
2. Whether the input is a file or directory.
3. Whether the file extension is supported.
4. Whether the path is inside the workspace when `restrict_to_workspace=True`.
5. Whether the output prefix is a plain filename without `..` or directory separators.

### 5.4 Implement prepare_run()

`prepare_run()` prepares the execution plan without running the analysis. Implement it in this order:

1. Read and validate public parameters.
2. Resolve input paths.
3. Determine the default output directory.
4. Check the analysis script and fixed resources.
5. Check the runtime environment and required commands.
6. Build the command as an argument list.
7. Return `PreparedCustomAnalysisRun`.

### 5.5 Implement execute()

`execute()` should:

1. Call `prepare_run()`.
2. Catch parameter, permission, and dependency errors.
3. Start the subprocess.
4. Apply the timeout.
5. Check the exit code.
6. Return an actionable error message on failure.
7. Return result paths and a summary preview on success.

You can reuse environment checks, subprocess helpers, and result preview helpers from `PlinkToolBase`. Even when the new analysis does not use PLINK, first determine whether these helpers are suitable to avoid implementing the same logic again.

## Step 6: Register the Workflow

Edit `easygs/agent/workflows.py`.

### 6.1 Import the Tool

```python
from easygs.agent.tools.custom_analysis import RunCustomAnalysisTool
```

### 6.2 Instantiate the Tool

Add the following inside `build_analysis_workflows()`:

```python
custom_analysis = RunCustomAnalysisTool(
    workspace=workspace,
    restrict_to_workspace=restrict_to_workspace,
)
```

### 6.3 Add WorkflowDefinition

Add the following to the returned `RegisteredWorkflow` list:

```python
RegisteredWorkflow(
    definition=WorkflowDefinition(
        kind="custom_analysis",
        tool_name="custom_analysis",
        description="Run the custom analysis and return its result files.",
        run_tool=custom_analysis,
        prepare_background_kwargs=_with_action_output_dir,
    ),
),
```

Add a dedicated `prepare_background_kwargs` function only when:

- One action needs multiple output directories.
- Multiple output parameters must be set or omitted together.
- Background execution needs an additional working directory.
- Tool parameters must be transformed before background execution.

Use `_with_action_output_dir` for a regular analysis with one output directory.

## Step 7: Create SKILL.md

Create:

```text
easygs/skills/custom_analysis/SKILL.md
```

Use the following structure:

````markdown
---
name: custom_analysis
description: Run the custom analysis for the supported user request.
metadata: {"easygs":{"os":["linux"]}}
---

# Custom Analysis

Use `custom_analysis(...)` when the user requests the supported analysis.

## Required inputs

- `input_path`: describe the accepted input and format.

## Optional parameters

- `output_dir`: optional result directory
- `prefix`: optional output basename

## Parameter collection rules

1. Ask for each missing required input.
2. Do not invent paths or column names.
3. Keep defaults when the user does not override them.

## Result reporting

After completion, report the primary result, summary, and important counts.
````

The Skill content must match the Tool's `parameters`. Parameters that are not public in the Tool should not appear in the Skill.

The Skill should describe only what the model needs to know:

- When to use the capability.
- Which values to collect.
- The expected input format.
- Which defaults are available.
- How to report the results.

Do not put the complete algorithm, internal commands, or fixed resource paths in the Skill.

## Step 8: Handle the Runtime Environment

If the new capability uses only packages already available in the main EasyGS Python environment, no new environment is required.

If additional dependencies are required:

1. Select the appropriate environment from EasyGS_1 through EasyGS_5.
2. Update both `env_all/EasyGS_N.yml` and `container/envs/EasyGS_N.yml`.
3. Install or update the corresponding local environment.
4. Set the correct `env_name` in the Tool.

