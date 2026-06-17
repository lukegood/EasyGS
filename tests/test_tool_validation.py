import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from easygs.agent.tools.base import Tool
from easygs.agent.tools.heritability import RunHeritabilityTool
from easygs.agent.tools.pfam_enrichment import RunPfamEnrichmentTool
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.agent.tools.peak_annotation import RunPeakAnnotationTool
from easygs.agent.tools.protein_function_annotation import RunProteinFunctionAnnotationTool
from easygs.agent.tools.qei_detection import RunQeiDetectionTool
from easygs.agent.tools.registry import ToolRegistry
from easygs.agent.tools.shell import ExecTool
from easygs.agent.tools.vcf_stats import RunVcfStatsTool
from easygs.agent.tools.vcftools import PreparedVcftoolsRun
from easygs.agent.tools.workflow import (
    AnalysisActionTool,
    WorkflowDefinition,
    _discovery_roots_from_outputs,
)
from easygs.agent.workflows import (
    _with_action_heritability_outputs,
    _with_action_output_dir,
    _with_action_vcf_outputs,
)
from easygs.bus.queue import MessageBus
from easygs.workflows.service import WorkflowService

PFAM_RESOURCE_PATHS = [
    Path("easygs/skills/pfam_enrichment_analysis/scripts/all_maize_genes_proteins.fa.tsv"),
    Path("easygs/skills/pfam_enrichment_analysis/scripts/all_maize_longest_cds.txt"),
]
PEAK_GFF3_FILENAME = "Zea_mays.B73_RefGen_v4.43_modify.gff3"


class _ProbePlinkTool(PlinkToolBase):
    def __init__(self, workspace):
        super().__init__(
            workspace=workspace,
            restrict_to_workspace=False,
            timeout=30,
            skill_name="variant_filter_analysis",
            default_output_subdir="variant_filter",
            env_name="EasyGS_2",
        )


class SampleTool(Tool):
    @property
    def name(self) -> str:
        return "sample"

    @property
    def description(self) -> str:
        return "sample tool"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2},
                "count": {"type": "integer", "minimum": 1, "maximum": 10},
                "mode": {"type": "string", "enum": ["fast", "full"]},
                "meta": {
                    "type": "object",
                    "properties": {
                        "tag": {"type": "string"},
                        "flags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["tag"],
                },
            },
            "required": ["query", "count"],
        }

    async def execute(self, **kwargs: Any) -> str:
        return "ok"


def test_validate_params_missing_required() -> None:
    tool = SampleTool()
    errors = tool.validate_params({"query": "hi"})
    assert "missing required count" in "; ".join(errors)


def test_validate_params_type_and_range() -> None:
    tool = SampleTool()
    errors = tool.validate_params({"query": "hi", "count": 0})
    assert any("count must be >= 1" in e for e in errors)

    errors = tool.validate_params({"query": "hi", "count": "2"})
    assert any("count should be integer" in e for e in errors)


def test_validate_params_enum_and_min_length() -> None:
    tool = SampleTool()
    errors = tool.validate_params({"query": "h", "count": 2, "mode": "slow"})
    assert any("query must be at least 2 chars" in e for e in errors)
    assert any("mode must be one of" in e for e in errors)


def test_validate_params_nested_object_and_array() -> None:
    tool = SampleTool()
    errors = tool.validate_params(
        {
            "query": "hi",
            "count": 2,
            "meta": {"flags": [1, "ok"]},
        }
    )
    assert any("missing required meta.tag" in e for e in errors)
    assert any("meta.flags[0] should be string" in e for e in errors)


def test_validate_params_ignores_unknown_fields() -> None:
    tool = SampleTool()
    errors = tool.validate_params({"query": "hi", "count": 2, "extra": "x"})
    assert errors == []


def test_exec_tool_schema_explains_timeout_override() -> None:
    tool = ExecTool(timeout=60)
    schema = tool.parameters

    assert "timeout_seconds" in tool.description
    assert "tools.exec.timeout" not in tool.description
    assert schema["properties"]["timeout_seconds"]["minimum"] == 1
    assert "per-command timeout" in schema["properties"]["timeout_seconds"]["description"]


@pytest.mark.asyncio
async def test_exec_tool_timeout_seconds_overrides_default(tmp_path) -> None:
    tool = ExecTool(timeout=1, working_dir=str(tmp_path))

    result = await tool.execute(
        command="sleep 1.2; printf done",
        timeout_seconds=3,
    )

    assert result == "done"


def test_prepared_vcftools_metadata_matches_other_prepared_runs(tmp_path) -> None:
    prepared = PreparedVcftoolsRun(
        launcher="conda",
        prefix="vcftools",
        command=["vcftools"],
        vcf_path=tmp_path / "input.vcf.gz",
        vcftools_args=["--freq"],
        output_dir=tmp_path,
        output_prefix_path=tmp_path / "vcftools",
        log_path=tmp_path / "vcftools.log",
        summary_path=tmp_path / "vcftools_summary.txt",
    )

    metadata = prepared.to_metadata()

    assert metadata["output_prefix_path"] == str(tmp_path / "vcftools")
    assert metadata["summary_path"] == str(tmp_path / "vcftools_summary.txt")
    assert "output_files" not in metadata


def test_background_output_helpers_use_workflow_default_dir(tmp_path) -> None:
    action_dir = tmp_path / "action"
    workflow_default = tmp_path / "results" / "act_001"

    assert _with_action_output_dir({}, action_dir, workflow_default)["output_dir"] == str(workflow_default)
    assert _with_action_vcf_outputs({}, action_dir, workflow_default)["output_dir"] == str(workflow_default)
    heritability = _with_action_heritability_outputs({}, action_dir, workflow_default)
    assert heritability["output_dir"] == str(workflow_default)
    assert heritability["work_root"] == action_dir / "work"


def test_background_output_helpers_preserve_explicit_paths(tmp_path) -> None:
    action_dir = tmp_path / "action"
    workflow_default = tmp_path / "results" / "act_001"
    explicit = tmp_path / "explicit"

    assert _with_action_output_dir({"output_dir": str(explicit)}, action_dir, workflow_default)["output_dir"] == str(explicit)
    vcf_outputs = _with_action_vcf_outputs(
        {"stats_output": "stats.txt", "summary_output": "summary.txt"},
        action_dir,
        workflow_default,
    )
    assert "output_dir" not in vcf_outputs
    heritability = _with_action_heritability_outputs(
        {"bed_dir": "bed", "grm_dir": "grm", "result_dir": "result"},
        action_dir,
        workflow_default,
    )
    assert "output_dir" not in heritability


def test_peak_annotation_relative_output_prefix_stays_in_output_dir(tmp_path) -> None:
    tool = RunPeakAnnotationTool(workspace=tmp_path)
    output_root = tmp_path / "custom_results"
    bed_path = tmp_path / "locilist.bed"

    resolved = tool._resolve_output_prefix("my_run", output_root, bed_path)

    assert resolved == (output_root / "my_run").resolve()


def test_qei_relative_output_prefix_stays_in_output_dir(tmp_path) -> None:
    tool = RunQeiDetectionTool(workspace=tmp_path)
    output_root = tmp_path / "custom_results"

    resolved = tool._resolve_output_prefix("qei_run", output_root)

    assert resolved == (output_root / "qei_run").resolve()


def test_workflow_action_schema_uses_workflow_output_guidance(tmp_path) -> None:
    run_tool = RunVcfStatsTool(workspace=tmp_path)
    action_tool = AnalysisActionTool(
        WorkflowDefinition(
            kind="vcf_stats",
            tool_name="run_vcf_stats",
            description="Run VCF stats.",
            run_tool=run_tool,
            prepare_background_kwargs=_with_action_vcf_outputs,
        )
    )

    description = action_tool.parameters["properties"]["output_dir"]["description"]

    assert "workspace/default_results" not in description
    assert "current workflow action output directory" in description


@pytest.mark.asyncio
async def test_workflow_service_uses_requested_output_dir_as_work_dir(tmp_path) -> None:
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=MessageBus(),
        workspace=tmp_path,
    )
    try:
        expected = str((tmp_path / "requested_results").resolve())
        workflow = await service.submit_workflow(
            request="Run an analysis.",
            origin_channel="test",
            origin_chat_id="chat",
            output_dir=str(tmp_path / "requested_results"),
            notify_on_completion=False,
        )

        assert workflow.work_dir == expected
        assert service.get_workflow(workflow.id).work_dir == expected
        assert expected in workflow.state["messages"][0]["content"]
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_workflow_service_uses_requested_output_dir_for_action_tree(tmp_path) -> None:
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=MessageBus(),
        workspace=tmp_path,
    )
    try:
        workflow = await service.submit_workflow(
            request="Run an analysis.",
            origin_channel="test",
            origin_chat_id="chat",
            output_dir=str(tmp_path / "requested_results"),
            notify_on_completion=False,
        )

        action_dir = service._action_dir(workflow, "act_001_demo")

        assert action_dir == (tmp_path / "requested_results" / "actions" / "act_001_demo").resolve()
    finally:
        service.stop()


def test_discovery_roots_follow_actual_prepared_outputs(tmp_path) -> None:
    fallback = tmp_path / "fallback"
    explicit = tmp_path / "explicit"
    stats_dir = tmp_path / "stats"

    assert _discovery_roots_from_outputs(
        {"output_dir": str(explicit)},
        fallback=fallback,
    ) == [explicit]
    assert _discovery_roots_from_outputs(
        {
            "stats_path": str(stats_dir / "vcf_stats.txt"),
            "summary_path": str(stats_dir / "cal.txt"),
        },
        fallback=fallback,
    ) == [stats_dir]
    assert _discovery_roots_from_outputs({}, fallback=fallback) == [fallback]


async def test_registry_returns_validation_error() -> None:
    reg = ToolRegistry()
    reg.register(SampleTool())
    result = await reg.execute("sample", {"query": "hi"})
    assert "Invalid parameters" in result


async def _capture_environment_check(tool, required_tools=None):
    commands = []

    def fake_launchers():
        return ["/opt/conda/bin/conda"]

    async def fake_run_command(command, timeout):
        commands.append(command)
        if command[1:3] == ["env", "list"]:
            return {
                "stdout": f"{tool.env_name}        /opt/conda/envs/{tool.env_name}",
                "stderr": "",
                "returncode": 0,
            }
        return {"stdout": "", "stderr": "", "returncode": 0}

    tool._find_launchers = fake_launchers
    tool._run_command = fake_run_command

    if required_tools is None:
        result = await tool._get_environment_status()
    else:
        result = await tool._get_environment_status(required_tools)

    assert result["error"] == ""
    return commands


@pytest.mark.asyncio
async def test_shared_conda_environment_check_uses_non_login_shell(tmp_path) -> None:
    commands = await _capture_environment_check(_ProbePlinkTool(tmp_path), ["plink", "bgzip"])

    tool_check = commands[1]
    assert tool_check[:6] == ["/opt/conda/bin/conda", "run", "-n", "EasyGS_2", "bash", "-c"]
    assert "-lc" not in tool_check


@pytest.mark.asyncio
async def test_vcf_stats_environment_check_uses_non_login_shell(tmp_path) -> None:
    commands = await _capture_environment_check(RunVcfStatsTool(tmp_path))

    tool_check = commands[1]
    assert tool_check[:6] == ["/opt/conda/bin/conda", "run", "-n", "EasyGS_1", "bash", "-c"]
    assert "-lc" not in tool_check


@pytest.mark.asyncio
async def test_heritability_environment_check_uses_non_login_shell(tmp_path) -> None:
    commands = await _capture_environment_check(RunHeritabilityTool(tmp_path))

    tool_check = commands[1]
    assert tool_check[:6] == ["/opt/conda/bin/conda", "run", "-n", "EasyGS_2", "bash", "-c"]
    assert "-lc" not in tool_check


def test_large_pfam_resources_are_not_bundled() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    for relative_path in PFAM_RESOURCE_PATHS:
        path = repo_root / relative_path
        assert not path.exists()
        assert not path.is_symlink()


def test_git_index_has_no_external_symlinks() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "ls-files", "--stage"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    external_links = []
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=3)
        if len(parts) != 4 or parts[0] != "120000":
            continue
        path = repo_root / parts[3]
        if not path.is_symlink():
            continue
        target = os.readlink(path)
        if os.path.isabs(target):
            external_links.append(f"{parts[3]} -> {target}")

    assert external_links == []


async def _fake_environment_status(required_tools):
    return {"launcher": "/usr/bin/conda", "error": ""}


def _write_test_resources(resources_root: Path) -> None:
    resource_dir = resources_root / "pfam_enrichment_analysis"
    resource_dir.mkdir(parents=True)
    (resource_dir / "all_maize_longest_cds.txt").write_text(
        "\n".join(
            [
                "Zm00001d031939\tZm00001d031939_P001",
                "Zm00001d031940\tZm00001d031940_P001",
                "Zm00001d031941\tZm00001d031941_P001",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (resource_dir / "all_maize_genes_proteins.fa.tsv").write_text(
        "\n".join(
            [
                "Zm00001d031939_P001\tpf00001\tDomain A\tPfam\tDescription A",
                "Zm00001d031940_P001\tpf00002\tDomain B\tPfam\tDescription B",
                "Zm00001d031941_P001\tpf00003\tDomain C\tInterPro\tDescription C",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_peak_resource(resources_root: Path) -> Path:
    resource_dir = resources_root / "peak_annotation_analysis"
    resource_dir.mkdir(parents=True)
    gff3_path = resource_dir / PEAK_GFF3_FILENAME
    gff3_path.write_text(
        "\n".join(
            [
                "##gff-version 3",
                "1\ttest\tgene\t100\t200\t.\t+\t.\tID=Zm00001d000001",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return gff3_path


@pytest.mark.asyncio
async def test_pfam_tools_use_user_resource_root(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    _write_test_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    genelist = workspace / "genes.txt"
    genelist.write_text("Zm00001d031939\nZm00001d031940\n", encoding="utf-8")

    pfam_tool = RunPfamEnrichmentTool(workspace)
    monkeypatch.setattr(pfam_tool, "_get_environment_status", _fake_environment_status)
    pfam_run = await pfam_tool.prepare_run(genelist_txt=str(genelist))

    protein_tool = RunProteinFunctionAnnotationTool(workspace)
    monkeypatch.setattr(protein_tool, "_get_environment_status", _fake_environment_status)
    protein_run = await protein_tool.prepare_run(genelist_txt=str(genelist))

    expected_longest = resources_root / "pfam_enrichment_analysis" / "all_maize_longest_cds.txt"
    expected_proteins = (
        resources_root / "pfam_enrichment_analysis" / "all_maize_genes_proteins.fa.tsv"
    )

    assert pfam_run.longest_cds_txt_path == expected_longest
    assert pfam_run.proteins_tsv_path == expected_proteins
    assert protein_run.longest_cds_txt_path == expected_longest
    assert protein_run.proteins_tsv_path == expected_proteins
    assert str(expected_longest) in pfam_run.command
    assert str(expected_proteins) in pfam_run.command
    assert str(expected_longest) in protein_run.command
    assert str(expected_proteins) in protein_run.command


@pytest.mark.asyncio
async def test_peak_annotation_uses_user_resource_root(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    expected_gff3 = _write_peak_resource(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    bed = workspace / "locilist.bed"
    bed.write_text(
        "\n".join(
            [
                "1\t100\t101",
                "1\t150\t151",
                "1\t180\t181",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    tool = RunPeakAnnotationTool(workspace)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)
    prepared = await tool.prepare_run(bed=str(bed))

    assert prepared.gff3_path == expected_gff3
    assert str(expected_gff3) in prepared.command
