# 为EasyGS增加新的Skill和工具

EasyGS的分析能力可随时通过插件形式添加。在增加新的功能时，只需要按照本教程提供的模板，参照您想增加的功能进行修改即可。完成以下步骤后，您将能够为EasyGS增加一项新的分析功能。

## Step1: 理解EasyGS的功能链路

EasyGS中的分析请求按以下链路执行：

```text
用户请求
  -> 主Agent读取Skill并收集参数
  -> submit_workflow提交后台任务
  -> 后台Workflow调用AnalysisActionTool
  -> AnalysisActionTool调用具体Tool的prepare_run()
  -> 分析脚本执行
  -> 输出文件和摘要返回Workflow
```

三个核心组件的职责如下：

| 组件 | 职责 |
| --- | --- |
| Skill | 告诉模型何时使用能力、收集哪些参数、如何解释结果 | 
| Tool | 定义参数Schema、校验路径、准备命令、描述输出 | 
| WorkflowDefinition | 把Tool注册为后台Workflow可调用的动作 | 

内置Skill会从`easygs/skills/<skill_name>/SKILL.md`自动发现。Python Tool不会自动发现，必须在`easygs/agent/workflows.py`中注册。


## Step2: 确定输入和输出

在增加新的分析功能前，需要确定以下事项：

| 项目 | 需要确定的内容 |
| --- | --- |
| 必需输入 | 文件、目录、文本或数值参数 |
| 可选输入 | 默认值、开关、阈值、输出前缀 |
| 输入格式 | 文件扩展名、列名、编码和数据约束 |
| 输出格式 | 用户最需要的结果文件 |
| 运行环境 | EasyGS_1到EasyGS_5或主Python环境 |
| 默认时长 | 用于设置Tool超时 |

只把用户需要设置的参数放入Tool的公共Schema。参考文件、内部脚本路径和固定资源路径应由Tool管理。

## Step3: 创建文件结构

新增一个EasyGS分析能力通常需要以下文件：

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

## Step4: 实现分析程序

整理您想要添加的功能，并将实现这个功能的逻辑放入：

```text
easygs/skills/custom_analysis/scripts/
```

分析程序可以使用Python、R、Shell或现有生信软件。无论使用哪种实现，都应满足以下要求：

1. 通过明确的命令行参数接收输入和输出路径。
2. 不依赖当前工作目录推测用户文件位置。
3. 不在未声明的位置生成文件。
4. 成功时返回退出码`0`。
5. 失败时把清楚的错误写入`stderr`并返回非零退出码。
6. 对随机算法提供可设置的随机种子。

## Step5: 创建Tool模块

创建并修改：

```text
easygs/agent/tools/custom_analysis.py
```

Tool负责把模型提供的参数转换为安全、确定的执行计划。

### 5.1定义准备结果

准备结果包含命令、输出目录和主要结果输出路径。您只需参照以下模板，按照您的实际功能修改相应内容即可：

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

`to_metadata()`中的路径会用于Workflow结果展示和文件发现。推荐使用`output_dir`、`result_path`和`summary_path`等现有约定名称。

### 5.2实现Tool接口

每个Tool必须继承`Tool`并实现以下成员。您只需参照以下模板，按照您的实际功能修改相应内容即可：

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
        # 执行prepared.command并处理超时、退出码、stdout和stderr。
        ...

    async def prepare_run(self, **kwargs: Any) -> PreparedCustomAnalysisRun:
        # 校验参数和依赖，解析路径，构造命令并返回输出元数据。
        ...
```

### 5.3校验路径

用户提供的路径应通过`_resolve_path()`处理：

```python
from easygs.agent.tools.filesystem import _resolve_path

input_path = _resolve_path(kwargs["input_path"], self.allowed_dir)
```

路径校验至少包括：

1. 输入是否存在。
2. 输入是文件还是目录。
3. 文件扩展名是否符合要求。
4. `restrict_to_workspace=True`时路径是否位于工作区内。
5. 输出前缀是否只是文件名，不能包含`..`或目录分隔符。

### 5.4实现prepare_run()

`prepare_run()`只准备执行计划，不直接运行分析。按以下顺序实现：

1. 读取并校验公共参数。
2. 解析输入路径。
3. 确定默认输出目录。
4. 检查分析脚本和固定资源。
5. 检查运行环境和必需命令。
6. 使用参数列表构造命令。
7. 返回`PreparedCustomAnalysisRun`。

### 5.5实现execute()

`execute()`应：

1. 调用`prepare_run()`。
2. 捕获参数、权限和依赖错误。
3. 启动子进程。
4. 应用超时。
5. 检查退出码。
6. 失败时返回可操作的错误信息。
7. 成功时返回结果路径和摘要预览。

可复用`PlinkToolBase`中的环境检查、子进程和结果预览辅助方法。即使新分析不使用PLINK，也应先判断这些辅助方法是否适合，避免重复实现相同逻辑。

## Step6: 注册Workflow

编辑`easygs/agent/workflows.py`。

### 6.1导入Tool

```python
from easygs.agent.tools.custom_analysis import RunCustomAnalysisTool
```

### 6.2实例化Tool

在`build_analysis_workflows()`中加入：

```python
custom_analysis = RunCustomAnalysisTool(
    workspace=workspace,
    restrict_to_workspace=restrict_to_workspace,
)
```

### 6.3添加WorkflowDefinition

在返回的`RegisteredWorkflow`列表中加入：

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

只有以下情况需要新增专用的`prepare_background_kwargs`函数：

- 一个动作需要多个输出目录。
- 多个输出参数必须同时设置或同时省略。
- 后台执行需要额外的工作目录。
- Tool参数需要在后台运行前转换。

普通的单输出目录分析使用`_with_action_output_dir`。

## Step7: 创建SKILL.md

创建：

```text
easygs/skills/custom_analysis/SKILL.md
```

使用以下结构：

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

Skill内容应与Tool的`parameters`保持一致。Tool没有公开的参数，不应出现在Skill中。

Skill只描述模型需要知道的内容：

- 何时使用能力。
- 需要收集什么。
- 输入格式是什么。
- 可以使用哪些默认值。
- 如何报告结果。

不要把完整算法、内部命令或固定资源路径写入Skill。

## Step8: 处理运行环境

如果新能力只使用EasyGS主Python环境中已有的包，不需要新增环境。

如果需要额外依赖：

1. 在EasyGS_1到EasyGS_5中选择职责匹配的环境。
2. 同步修改`env_all/EasyGS_N.yml`和`container/envs/EasyGS_N.yml`。
3. 本机安装或更新对应环境。
4. 在Tool中设置正确的`env_name`。

