import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from easygs.agent.loop import AgentLoop
from easygs.agent.tools.base import Tool
from easygs.agent.tools.candidate_gene_extraction import RunCandidateGeneExtractionTool
from easygs.agent.tools.fastq_to_vcf import RunFastqToVcfTool
from easygs.agent.tools.heritability import RunHeritabilityTool
from easygs.agent.tools.ortholog_extraction import RunOrthologExtractionTool
from easygs.agent.tools.peak_annotation import RunPeakAnnotationTool
from easygs.agent.tools.pfam_enrichment import RunPfamEnrichmentTool
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.agent.tools.protein_function_annotation import RunProteinFunctionAnnotationTool
from easygs.agent.tools.qei_detection import RunQeiDetectionTool
from easygs.agent.tools.registry import ToolRegistry
from easygs.agent.tools.shell import ExecTool
from easygs.agent.tools.vcf_stats import RunVcfStatsTool
from easygs.agent.tools.vcftools import PreparedVcftoolsRun
from easygs.agent.tools.wheat_rice_gene_function_enrichment import (
    RunWheatRiceGeneFunctionEnrichmentTool,
)
from easygs.agent.tools.workflow import (
    AnalysisActionTool,
    WorkflowDefinition,
    _discovery_roots_from_outputs,
)
from easygs.agent.tools.workflows import CancelWorkflowTool
from easygs.agent.workflows import (
    _with_action_heritability_outputs,
    _with_action_output_dir,
    _with_action_vcf_outputs,
    build_analysis_workflows,
)
from easygs.bus.queue import MessageBus
from easygs.providers.base import (
    LLMResponse,
    TokenUsageAccumulator,
    ToolCallRequest,
    normalize_token_usage,
)
from easygs.workflows.schema import WorkflowRecord
from easygs.workflows.service import WorkflowService

PFAM_RESOURCE_PATHS = [
    Path("easygs/skills/pfam_enrichment_analysis/scripts/all_maize_genes_proteins.fa.tsv"),
    Path("easygs/skills/pfam_enrichment_analysis/scripts/all_maize_longest_cds.txt"),
]
PEAK_GFF3_FILENAMES = {
    "maize": "Zea_mays.B73_RefGen_v4.43_modify.gff3",
    "wheat": "Taestivumcv_ChineseSpring_725_v2.1.gene.gff3",
    "rice": "Osativa_323_v7.0.gene.gff3",
}
ORTHOLOG_MATRIX_FILENAMES = {
    "maize": "maize_ortholog_matrix.tsv",
    "wheat": "wheat_ortholog_matrix.tsv",
    "rice": "rice_ortholog_matrix.tsv",
}
FASTQ_TO_VCF_RESOURCE_FILENAMES = (
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa",
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa.amb",
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa.ann",
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa.bwt",
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa.pac",
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa.sa",
    "Zm-B73-REFERENCE-GRAMENE-4.0.fa.fai",
    "Zm-B73-REFERENCE-GRAMENE-4.0.dict",
)


def test_ccload_usage_counts_cached_input_exactly_once() -> None:
    assert normalize_token_usage(
        {
            "prompt_tokens": 258_126,
            "completion_tokens": 4_412,
            "total_tokens": 262_538,
            "cache_read_input_tokens": 239_168,
        }
    ) == (258_126, 4_412)


def test_anthropic_usage_adds_separate_cache_fields() -> None:
    assert normalize_token_usage(
        {
            "input_tokens": 759,
            "output_tokens": 303,
            "cache_read_input_tokens": 34_496,
            "cache_creation_input_tokens": 100,
        }
    ) == (35_355, 303)


def test_missing_usage_marks_accumulator_partial() -> None:
    usage = TokenUsageAccumulator()
    usage.add({"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12})
    usage.add({})

    assert (usage.input_tokens, usage.output_tokens) == (10, 2)
    assert usage.llm_call_count == 2
    assert usage.usage_reported_call_count == 1
    assert not usage.usage_complete


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


HERITABILITY_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "easygs"
    / "skills"
    / "heritability"
    / "scripts"
    / "heritability.sh"
)


def _write_heritability_test_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _fake_heritability_tool_dir(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_heritability_test_executable(bin_dir / "vcftools", "#!/bin/sh\nexit 0\n")
    _write_heritability_test_executable(
        bin_dir / "plink",
        """#!/bin/sh
out=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --out) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$out")"
: > "${out}.bed"
: > "${out}.bim"
: > "${out}.fam"
exit 0
""",
    )
    _write_heritability_test_executable(
        bin_dir / "gcta64",
        """#!/bin/sh
out=""
pheno=""
make_grm=0
reml=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --out) out="$2"; shift 2 ;;
    --pheno) pheno="$2"; shift 2 ;;
    --make-grm-bin) make_grm=1; shift ;;
    --reml) reml=1; shift ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$out")"
if [ "$make_grm" -eq 1 ]; then
  printf 'F2\tI2\nF3\tI3\nF1\tI1\n' > "${out}.grm.id"
  : > "${out}.grm.bin"
  : > "${out}.grm.N.bin"
  exit 0
fi
if [ "$reml" -eq 1 ]; then
  cp "$pheno" "$CAPTURE_PHENO"
  if [ "${GCTA_REML_FAIL:-0}" -eq 1 ]; then
    printf 'Error: the information matrix is not invertible.\n' > "${out}.log"
    exit 1
  fi
  printf 'REML completed.\n' > "${out}.log"
  if [ "${GCTA_NO_HSQ:-0}" -eq 1 ]; then
    exit 0
  fi
  printf 'Source\tVariance\tSE\nV(G)/Vp\t0.42\t0.08\n' > "${out}.hsq"
  exit 0
fi
exit 2
""",
    )
    return bin_dir


def _run_heritability_test_pipeline(
    tmp_path: Path,
    **extra_env: str,
) -> subprocess.CompletedProcess[str]:
    bin_dir = _fake_heritability_tool_dir(tmp_path)
    vcf = tmp_path / "input.vcf"
    pheno = tmp_path / "pheno.tsv"
    vcf.write_text("##fileformat=VCFv4.2\n", encoding="utf-8")
    pheno.write_text(
        "FID\tIID\ttrait\n"
        "F1\tI1\t1\n"
        "F2\tI2\t2\n"
        "F4\tI4\t4\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CAPTURE_PHENO": str(tmp_path / "gcta.pheno"),
        **extra_env,
    }
    return subprocess.run(
        [
            "bash",
            str(HERITABILITY_SCRIPT_PATH),
            "--vcf",
            str(vcf),
            "--pheno",
            str(pheno),
            "--prefix",
            "test",
            "--bed-dir",
            str(tmp_path / "bed"),
            "--grm-dir",
            str(tmp_path / "grm"),
            "--result-dir",
            str(tmp_path / "result"),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_heritability_matches_exact_fid_iid_order_and_removes_header(tmp_path: Path) -> None:
    result = _run_heritability_test_pipeline(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "phenotype=3, GRM=3, common=2" in result.stdout
    assert (tmp_path / "gcta.pheno").read_text(encoding="utf-8") == (
        "F2\tI2\t2\nF1\tI1\t1\n"
    )


def test_heritability_surfaces_gcta_result_log_on_failure(tmp_path: Path) -> None:
    result = _run_heritability_test_pipeline(tmp_path, GCTA_REML_FAIL="1")

    assert result.returncode != 0
    assert "phenotype=3, GRM=3, common=2" in result.stderr
    assert "information matrix is not invertible" in result.stderr


def test_heritability_requires_valid_hsq_result(tmp_path: Path) -> None:
    result = _run_heritability_test_pipeline(tmp_path, GCTA_NO_HSQ="1")

    assert result.returncode != 0
    assert "without a valid heritability result" in result.stderr


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            "FID\tIID\ttrait\nS1\tS1\t1\nS2\tS2\tnot-a-number\n",
            "Phenotype value must be numeric",
        ),
        (
            "FID\tIID\ttrait\nS1\tS1\t1\nS1\tS1\t2\n",
            "duplicate FID/IID pair",
        ),
        (
            "FID\tIID\ttrait\nS1\tS1\t1\nS2\tS2\t2\textra\n",
            "exactly three columns",
        ),
    ],
)
def test_heritability_phenotype_validation_checks_every_row(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    pheno = tmp_path / "pheno.tsv"
    pheno.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        RunHeritabilityTool(tmp_path)._validate_phenotype_file(pheno)


def test_heritability_phenotype_validation_allows_supported_missing_values(
    tmp_path: Path,
) -> None:
    pheno = tmp_path / "pheno.tsv"
    pheno.write_text(
        "FID\tIID\ttrait\nS1\tS1\tNA\nS2\tS2\t-9\nS3\tS3\t1.5\n",
        encoding="utf-8",
    )

    RunHeritabilityTool(tmp_path)._validate_phenotype_file(pheno)


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


def _write_candidate_gene_resources(resources_root: Path) -> dict[str, Path]:
    resource_dir = resources_root / "candidate_gene_extraction_analysis"
    resource_dir.mkdir(parents=True, exist_ok=True)
    contents = {
        "maize": ("allV4gene.bed", "1\t100\t200\tZm00001d000001\n"),
        "wheat": ("allwheatgene.bed", "Chr1A\t100\t200\tTraesCS1A03G0000200\n"),
        "rice": ("allricegene.bed", "Chr1\t100\t200\tLOC_Os01g01010\n"),
    }
    paths = {}
    for species, (filename, content) in contents.items():
        path = resource_dir / filename
        path.write_text(content, encoding="utf-8")
        paths[species] = path
    return paths


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
    (resource_dir / "wheat_interpro.tsv").write_text(
        "TraesCS1A03G0000200.1\thash\t100\tPfam\tPF00001\n",
        encoding="utf-8",
    )
    (resource_dir / "Osativa_323_v7.0.protein_primaryTranscriptOnly.fa.tsv").write_text(
        "LOC_Os01g01010.1\thash\t100\tPfam\tPF00002\n",
        encoding="utf-8",
    )


def test_candidate_gene_schema_exposes_species_and_hides_gene_bed(tmp_path) -> None:
    schema = RunCandidateGeneExtractionTool(tmp_path).parameters
    properties = schema["properties"]

    assert properties["species"]["enum"] == ["maize", "wheat", "rice"]
    assert properties["species"]["default"] == "maize"
    assert "output_prefix" in properties
    assert "gene_bed" not in properties
    assert schema["required"] == ["bed"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("species", "chromosome", "filename"),
    [
        ("maize", "1", "allV4gene.bed"),
        ("wheat", "Chr1A", "allwheatgene.bed"),
        ("rice", "Chr1", "allricegene.bed"),
    ],
)
async def test_candidate_gene_selects_species_resource_and_outputs(
    monkeypatch,
    tmp_path,
    species,
    chromosome,
    filename,
) -> None:
    resources_root = tmp_path / "resources"
    _write_candidate_gene_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    bed = tmp_path / "locilist.bed"
    bed.write_text(f"{chromosome}\t150\t151\n", encoding="utf-8")
    output_dir = tmp_path / "results"

    tool = RunCandidateGeneExtractionTool(tmp_path)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)
    prepared = await tool.prepare_run(
        bed=str(bed),
        species=species.upper(),
        ld_distance=100000,
        output_dir=str(output_dir),
        output_prefix="testgenes",
    )

    expected_resource = resources_root / "candidate_gene_extraction_analysis" / filename
    assert prepared.species == species
    assert prepared.gene_bed_path == expected_resource
    assert prepared.ld_distance == 100000
    assert prepared.extended_bed_path == output_dir / "testgenes.extend.bed"
    assert prepared.gene_list_path == output_dir / "testgenes.txt"
    assert prepared.detailed_tsv_path == output_dir / "testgenes.detailed.tsv"
    assert prepared.summary_path == output_dir / "testgenes_summary.txt"
    assert str(expected_resource) in prepared.command
    assert "--detailed-output" in prepared.command


@pytest.mark.asyncio
async def test_candidate_gene_rejects_unknown_species(tmp_path) -> None:
    with pytest.raises(ValueError, match="species must be one of"):
        await RunCandidateGeneExtractionTool(tmp_path).prepare_run(
            bed="unused.bed",
            species="barley",
        )


@pytest.mark.asyncio
async def test_candidate_gene_rejects_chromosome_mismatch(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    _write_candidate_gene_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    bed = tmp_path / "locilist.bed"
    bed.write_text("Chr1A\t150\t151\n", encoding="utf-8")

    with pytest.raises(ValueError, match="do not match the selected species gene BED"):
        await RunCandidateGeneExtractionTool(tmp_path).prepare_run(
            bed=str(bed),
            species="rice",
        )


@pytest.mark.asyncio
async def test_candidate_gene_execute_rejects_public_gene_bed(tmp_path) -> None:
    result = await RunCandidateGeneExtractionTool(tmp_path).execute(
        bed="unused.bed",
        species="wheat",
        gene_bed="allwheatgene.bed",
    )

    assert "gene_bed is no longer a public parameter" in result


def _write_peak_resource(
    resources_root: Path,
    species: str = "maize",
    chromosome: str = "1",
) -> Path:
    resource_dir = resources_root / "peak_annotation_analysis"
    resource_dir.mkdir(parents=True, exist_ok=True)
    gff3_path = resource_dir / PEAK_GFF3_FILENAMES[species]
    gff3_path.write_text(
        "\n".join(
            [
                "##gff-version 3",
                f"{chromosome}\ttest\tgene\t100\t200\t.\t+\t.\tID=test_gene",
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
    assert pfam_run.species == "maize"
    assert pfam_run.min_count_in_candidates == 5
    assert pfam_run.output_prefix == "pfam_enrichment"
    assert protein_run.longest_cds_txt_path == expected_longest
    assert protein_run.proteins_tsv_path == expected_proteins
    assert str(expected_longest) in pfam_run.command
    assert str(expected_proteins) in pfam_run.command
    assert str(expected_longest) in protein_run.command
    assert str(expected_proteins) in protein_run.command


def test_pfam_schema_exposes_species_and_hides_annotation_resources(tmp_path) -> None:
    properties = RunPfamEnrichmentTool(tmp_path).parameters["properties"]

    assert properties["species"]["enum"] == ["maize", "wheat", "rice"]
    assert properties["species"]["default"] == "maize"
    assert "proteins_tsv" not in properties
    assert "longest_cds_txt" not in properties


@pytest.mark.asyncio
async def test_pfam_rejects_unknown_species(tmp_path) -> None:
    with pytest.raises(ValueError, match="species must be one of"):
        await RunPfamEnrichmentTool(tmp_path).prepare_run(
            genelist_txt="unused.txt",
            species="barley",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("species", "gene", "filename"),
    [
        ("wheat", "TraesCS1A03G0000200", "wheat_interpro.tsv"),
        (
            "rice",
            "LOC_Os01g01010",
            "Osativa_323_v7.0.protein_primaryTranscriptOnly.fa.tsv",
        ),
    ],
)
async def test_pfam_selects_wheat_rice_resources(
    monkeypatch,
    tmp_path,
    species,
    gene,
    filename,
) -> None:
    resources_root = tmp_path / "resources"
    _write_test_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    genelist = tmp_path / "genes.txt"
    genelist.write_text(f"{gene}\n", encoding="utf-8")
    tool = RunPfamEnrichmentTool(tmp_path)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)

    prepared = await tool.prepare_run(genelist_txt=str(genelist), species=species.upper())

    assert prepared.species == species
    assert prepared.longest_cds_txt_path is None
    assert prepared.proteins_tsv_path == (
        resources_root / "pfam_enrichment_analysis" / filename
    )
    assert prepared.output_prefix == f"{species}_pfam_enrichment"
    assert prepared.min_count_in_candidates == 2
    assert "--longest-cds-txt" not in prepared.command


@pytest.mark.asyncio
async def test_pfam_rejects_species_gene_id_mismatch(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    _write_test_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    genelist = tmp_path / "genes.txt"
    genelist.write_text("TraesCS1A03G0000200\n", encoding="utf-8")

    with pytest.raises(ValueError, match="do not look like rice IDs"):
        await RunPfamEnrichmentTool(tmp_path).prepare_run(
            genelist_txt=str(genelist),
            species="rice",
        )


def test_pfam_preprocessor_streams_and_normalizes_gene_ids(tmp_path) -> None:
    genelist = tmp_path / "genes.txt"
    genelist.write_text("LOC_Os01g01010\n", encoding="utf-8")
    annotation = tmp_path / "rice.tsv"
    annotation.write_text(
        "LOC_Os01g01010.1\th1\t100\tPfam\tPF00001\tdesc\n"
        "LOC_Os01g01010.2\th2\t100\tSMART\tSM00001\tdesc\n"
        "LOC_Os01g01020.1\th3\t100\tPfam\tPF00002\tdesc\n",
        encoding="utf-8",
    )
    protlist = tmp_path / "protlist.txt"
    candidate_rows = tmp_path / "candidate.tsv"
    source_rows = tmp_path / "source.tsv"
    script = Path(
        "easygs/skills/pfam_enrichment_analysis/scripts/prepare_pfam_annotations.py"
    ).resolve()

    subprocess.run(
        [
            os.sys.executable,
            str(script),
            "--genelist-txt",
            str(genelist),
            "--proteins-tsv",
            str(annotation),
            "--annotation-source",
            "Pfam",
            "--protlist-output",
            str(protlist),
            "--protlist-stranno-output",
            str(candidate_rows),
            "--source-annotation-tsv-output",
            str(source_rows),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert protlist.read_text(encoding="utf-8") == "LOC_Os01g01010\n"
    assert candidate_rows.read_text(encoding="utf-8").splitlines() == [
        "LOC_Os01g01010\th1\t100\tPfam\tPF00001\tdesc",
        "LOC_Os01g01010\th2\t100\tSMART\tSM00001\tdesc",
    ]
    assert source_rows.read_text(encoding="utf-8").splitlines() == [
        "LOC_Os01g01010\th1\t100\tPfam\tPF00001",
        "LOC_Os01g01020\th3\t100\tPfam\tPF00002",
    ]


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
    assert prepared.species == "maize"
    assert str(expected_gff3) in prepared.command


def test_peak_annotation_schema_hides_gff3_and_exposes_species(tmp_path) -> None:
    properties = RunPeakAnnotationTool(tmp_path).parameters["properties"]

    assert "gff3" not in properties
    assert properties["species"]["enum"] == ["maize", "wheat", "rice"]
    assert properties["species"]["default"] == "maize"


@pytest.mark.asyncio
async def test_peak_annotation_rejects_explicit_gff3_parameter(tmp_path) -> None:
    result = await RunPeakAnnotationTool(tmp_path).execute(
        bed="unused.bed",
        gff3="custom.gff3",
    )

    assert result.startswith("Error: gff3 is no longer a public parameter")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("species", "chromosome"),
    [("wheat", "Chr1A"), ("rice", "Chr1")],
)
async def test_peak_annotation_selects_species_resource(
    monkeypatch,
    tmp_path,
    species,
    chromosome,
) -> None:
    resources_root = tmp_path / "resources"
    expected_gff3 = _write_peak_resource(resources_root, species, chromosome)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    bed = tmp_path / f"{species}.bed"
    bed.write_text(f"{chromosome}\t100\t101\n", encoding="utf-8")

    tool = RunPeakAnnotationTool(tmp_path)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)
    prepared = await tool.prepare_run(bed=str(bed), species=species.upper())

    assert prepared.species == species
    assert prepared.gff3_path == expected_gff3
    assert prepared.command[prepared.command.index("--species") + 1] == species


@pytest.mark.asyncio
async def test_peak_annotation_rejects_unknown_species(tmp_path) -> None:
    tool = RunPeakAnnotationTool(tmp_path)

    with pytest.raises(ValueError, match="species must be one of"):
        await tool.prepare_run(bed="unused.bed", species="barley")


@pytest.mark.asyncio
async def test_peak_annotation_reports_selected_missing_resource(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    tool = RunPeakAnnotationTool(tmp_path)

    with pytest.raises(ValueError, match=PEAK_GFF3_FILENAMES["rice"]):
        await tool.prepare_run(bed="unused.bed", species="rice")


@pytest.mark.asyncio
async def test_peak_annotation_rejects_bed_gff_chromosome_mismatch(
    monkeypatch,
    tmp_path,
) -> None:
    resources_root = tmp_path / "resources"
    _write_peak_resource(resources_root, "rice", "Chr1")
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    bed = tmp_path / "wrong_species.bed"
    bed.write_text("Chr1A\t100\t101\n", encoding="utf-8")
    tool = RunPeakAnnotationTool(tmp_path)

    with pytest.raises(ValueError, match="Missing from GFF3: Chr1A"):
        await tool.prepare_run(bed=str(bed), species="rice")


@pytest.mark.asyncio
async def test_peak_annotation_rejects_invalid_bed_interval(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    _write_peak_resource(resources_root, "rice", "Chr1")
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    bed = tmp_path / "invalid.bed"
    bed.write_text("Chr1\t101\t100\n", encoding="utf-8")
    tool = RunPeakAnnotationTool(tmp_path)

    with pytest.raises(ValueError, match="0 <= start < end"):
        await tool.prepare_run(bed=str(bed), species="rice")


def _write_ortholog_resource(
    resources_root: Path,
    species: str,
    rows: list[str] | None = None,
) -> Path:
    resource_dir = resources_root / "ortholog_extraction_analysis"
    resource_dir.mkdir(parents=True, exist_ok=True)
    matrix = resource_dir / ORTHOLOG_MATRIX_FILENAMES[species]
    matrix.write_text(
        "\n".join(
            [
                f"{species.title()}\tArabidopsis\tRice",
                *(rows or ["Gene1\tAT1G01010\tLOC_Os01g01010"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return matrix


def test_ortholog_schema_hides_matrix_and_exposes_species(tmp_path) -> None:
    properties = RunOrthologExtractionTool(tmp_path).parameters["properties"]

    assert "ortholog_matrix_tsv" not in properties
    assert properties["species"]["enum"] == ["maize", "wheat", "rice"]
    assert properties["species"]["default"] == "maize"


@pytest.mark.asyncio
async def test_ortholog_rejects_explicit_matrix_parameter(tmp_path) -> None:
    result = await RunOrthologExtractionTool(tmp_path).execute(
        genelist_txt="unused.txt",
        ortholog_matrix_tsv="custom.tsv",
    )

    assert result.startswith("Error: ortholog_matrix_tsv is no longer a public parameter")


@pytest.mark.asyncio
async def test_ortholog_rejects_unknown_species(tmp_path) -> None:
    with pytest.raises(ValueError, match="species must be one of"):
        await RunOrthologExtractionTool(tmp_path).prepare_run(
            genelist_txt="unused.txt",
            species="barley",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("species", ["maize", "wheat", "rice"])
async def test_ortholog_selects_species_resource(monkeypatch, tmp_path, species) -> None:
    resources_root = tmp_path / "resources"
    expected_matrix = _write_ortholog_resource(resources_root, species)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    genelist = tmp_path / "100_test_genes.txt"
    genelist.write_text("Gene1\n", encoding="utf-8")
    tool = RunOrthologExtractionTool(tmp_path)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)

    prepared = await tool.prepare_run(genelist_txt=str(genelist), species=species.upper())

    assert prepared.species == species
    assert prepared.ortholog_matrix_tsv_path == expected_matrix
    assert prepared.output_tsv_path.name == "100_test.ortholog.tsv"
    assert prepared.command[prepared.command.index("--species") + 1] == species


@pytest.mark.asyncio
async def test_ortholog_reports_selected_missing_resource(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    genelist = tmp_path / "genes.txt"
    genelist.write_text("Gene1\n", encoding="utf-8")

    with pytest.raises(ValueError, match=ORTHOLOG_MATRIX_FILENAMES["wheat"]):
        await RunOrthologExtractionTool(tmp_path).prepare_run(
            genelist_txt=str(genelist),
            species="wheat",
        )


@pytest.mark.asyncio
async def test_ortholog_rejects_wrong_matrix_header(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    matrix = _write_ortholog_resource(resources_root, "rice")
    matrix.write_text("Wheat\tArabidopsis\nGene1\tAT1G01010\n", encoding="utf-8")
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    genelist = tmp_path / "genes.txt"
    genelist.write_text("Gene1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="first header must be 'Rice'"):
        await RunOrthologExtractionTool(tmp_path).prepare_run(
            genelist_txt=str(genelist),
            species="rice",
        )


def test_ortholog_extractor_matches_first_column_exactly(tmp_path) -> None:
    genelist = tmp_path / "genes.txt"
    genelist.write_text("Gene1\n\nGene10\n", encoding="utf-8")
    matrix = tmp_path / "matrix.tsv"
    matrix.write_text(
        "Source\tTarget\n"
        "Gene1\tA\n"
        "Gene10\tB\n"
        "Gene100\tC\n"
        "Other\tGene1\n",
        encoding="utf-8",
    )
    output = tmp_path / "matched.tsv"
    script = Path(
        "easygs/skills/ortholog_extraction_analysis/scripts/extract_orthologs.py"
    ).resolve()

    subprocess.run(
        [
            str(Path(os.sys.executable)),
            str(script),
            "--genelist-txt",
            str(genelist),
            "--ortholog-matrix-tsv",
            str(matrix),
            "--output-tsv",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.read_text(encoding="utf-8") == "Gene1\tA\nGene10\tB\n"


def _write_gene_function_table(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _write_wheat_gene_function_resources(
    resource_dir: Path,
    *,
    go: bool = True,
    kegg: bool = True,
) -> None:
    if kegg:
        _write_gene_function_table(
            resource_dir / "wheat_gene_KO_one2one.tsv",
            "locusName\tKO",
            ["TraesCS1\tK00001", "TraesCS2\tK00002"],
        )
        _write_gene_function_table(
            resource_dir / "taes_KEGG_annotation.txt",
            "KO\tPathway_ID\tPathway_Name",
            ["K00001\t00010\tPathway A", "K00002\t00020\tPathway B"],
        )
    if go:
        _write_gene_function_table(
            resource_dir / "wheat_gene_GO_one2one.tsv",
            "locusName\tGO",
            ["TraesCS1\tGO:0000001", "TraesCS2\tGO:0000002"],
        )
        _write_gene_function_table(
            resource_dir / "GO_term_table_2026.7.16.tsv",
            "GOID\tTERM\tONTOLOGY",
            ["GO:0000001\tTerm A\tBP", "GO:0000002\tTerm B\tMF"],
        )


def _write_rice_go_resources(resource_dir: Path) -> None:
    _write_gene_function_table(
        resource_dir / "rice_gene_GO_one2one.tsv",
        "locusName\tGO",
        ["LOC_Os01g00010\tGO:0000001", "LOC_Os01g00020\tGO:0000002"],
    )
    _write_gene_function_table(
        resource_dir / "GO_term_table_2026.7.16.tsv",
        "GOID\tTERM\tONTOLOGY",
        ["GO:0000001\tTerm A\tBP", "GO:0000002\tTerm B\tMF"],
    )


def _write_gene_list(workspace: Path, values: list[str]) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "genes.txt"
    path.write_text("\n".join(values) + "\n", encoding="utf-8")
    return path


def test_wheat_rice_gene_function_schema_hides_resource_paths(tmp_path) -> None:
    tool = RunWheatRiceGeneFunctionEnrichmentTool(tmp_path)
    properties = tool.parameters["properties"]

    assert tool.parameters["required"] == ["genelist_txt", "species"]
    assert properties["species"]["enum"] == ["wheat", "rice"]
    assert properties["analysis_type"]["enum"] == ["ALL", "GO", "KEGG"]
    assert "gene2ko_tsv" not in properties
    assert "gene2go_tsv" not in properties
    assert "kegg_annotation_tsv" not in properties
    assert "go_term_tsv" not in properties


@pytest.mark.asyncio
async def test_wheat_rice_gene_function_uses_wheat_resources(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    resource_dir = resources_root / "wheat_rice_gene_function_enrichment_analysis"
    _write_wheat_gene_function_resources(resource_dir)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    genelist = _write_gene_list(workspace, ["TraesCS1", "TraesCS2"])
    tool = RunWheatRiceGeneFunctionEnrichmentTool(workspace)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)

    prepared = await tool.prepare_run(
        genelist_txt=str(genelist), species="wheat", analysis_type="ALL"
    )

    assert prepared.resource_dir == resource_dir
    assert prepared.gene2ko_path == resource_dir / "wheat_gene_KO_one2one.tsv"
    assert prepared.kegg_annotation_path == resource_dir / "taes_KEGG_annotation.txt"
    assert prepared.gene2go_path == resource_dir / "wheat_gene_GO_one2one.tsv"
    assert prepared.go_term_path == resource_dir / "GO_term_table_2026.7.16.tsv"
    assert prepared.kegg_all_path.name == "wheat_KEGG_KEGG_enrichment_all_p1.0.tsv"
    assert prepared.go_all_path.name == "wheat_GO_GO_enrichment_all_p1.0.tsv"
    assert str(prepared.gene2ko_path) in prepared.command
    assert str(prepared.gene2go_path) in prepared.command


@pytest.mark.asyncio
async def test_wheat_rice_gene_function_kegg_only_skips_go_resources(
    monkeypatch, tmp_path
) -> None:
    resources_root = tmp_path / "resources"
    resource_dir = resources_root / "wheat_rice_gene_function_enrichment_analysis"
    _write_wheat_gene_function_resources(resource_dir, go=False)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    genelist = _write_gene_list(workspace, ["TraesCS1"])
    tool = RunWheatRiceGeneFunctionEnrichmentTool(workspace)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)

    prepared = await tool.prepare_run(
        genelist_txt=str(genelist), species="wheat", analysis_type="KEGG"
    )

    assert prepared.gene2ko_path is not None
    assert prepared.gene2go_path is None
    assert prepared.go_all_path is None
    assert "--gene2go-tsv" not in prepared.command


@pytest.mark.asyncio
async def test_wheat_rice_gene_function_go_only_selects_rice(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    resource_dir = resources_root / "wheat_rice_gene_function_enrichment_analysis"
    _write_rice_go_resources(resource_dir)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    genelist = _write_gene_list(workspace, ["LOC_Os01g00010"])
    tool = RunWheatRiceGeneFunctionEnrichmentTool(workspace)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)

    prepared = await tool.prepare_run(
        genelist_txt=str(genelist), species="rice", analysis_type="GO"
    )

    assert prepared.gene2go_path == resource_dir / "rice_gene_GO_one2one.tsv"
    assert prepared.gene2ko_path is None
    assert prepared.go_plot_path.name == "rice_GO_GO_enrichment.png"


@pytest.mark.asyncio
async def test_wheat_rice_gene_function_reports_missing_resource(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    genelist = _write_gene_list(workspace, ["TraesCS1"])
    tool = RunWheatRiceGeneFunctionEnrichmentTool(workspace)

    with pytest.raises(ValueError, match="wheat_gene_KO_one2one.tsv") as error:
        await tool.prepare_run(
            genelist_txt=str(genelist), species="wheat", analysis_type="KEGG"
        )

    expected = (
        resources_root
        / "wheat_rice_gene_function_enrichment_analysis"
        / "wheat_gene_KO_one2one.tsv"
    )
    assert str(expected) in str(error.value)
    assert "EASYGS_RESOURCES_DIR" in str(error.value)


@pytest.mark.asyncio
async def test_wheat_rice_gene_function_validates_resource_columns(
    monkeypatch, tmp_path
) -> None:
    resources_root = tmp_path / "resources"
    resource_dir = resources_root / "wheat_rice_gene_function_enrichment_analysis"
    _write_gene_function_table(
        resource_dir / "wheat_gene_GO_one2one.tsv",
        "gene\tGO",
        ["TraesCS1\tGO:0000001"],
    )
    _write_gene_function_table(
        resource_dir / "GO_term_table_2026.7.16.tsv",
        "GOID\tTERM\tONTOLOGY",
        ["GO:0000001\tTerm A\tBP"],
    )
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    genelist = _write_gene_list(workspace, ["TraesCS1"])
    tool = RunWheatRiceGeneFunctionEnrichmentTool(workspace)

    with pytest.raises(ValueError, match="locusName"):
        await tool.prepare_run(genelist_txt=str(genelist), species="wheat", analysis_type="GO")


@pytest.mark.asyncio
async def test_wheat_rice_gene_function_rejects_escaping_prefix(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    resource_dir = resources_root / "wheat_rice_gene_function_enrichment_analysis"
    _write_wheat_gene_function_resources(resource_dir, go=False)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    genelist = _write_gene_list(workspace, ["TraesCS1"])
    tool = RunWheatRiceGeneFunctionEnrichmentTool(workspace)

    with pytest.raises(ValueError, match="without directory components"):
        await tool.prepare_run(
            genelist_txt=str(genelist),
            species="wheat",
            analysis_type="KEGG",
            output_prefix="../escape",
        )


def test_wheat_rice_gene_function_workflow_is_registered(tmp_path) -> None:
    workflows = build_analysis_workflows(tmp_path, restrict_to_workspace=False)
    definitions = {workflow.definition.tool_name: workflow.definition for workflow in workflows}

    definition = definitions["wheat_rice_gene_function_enrichment_analysis"]
    assert definition.kind == "wheat_rice_gene_function_enrichment"
    assert isinstance(definition.run_tool, RunWheatRiceGeneFunctionEnrichmentTool)


def _write_fastq_to_vcf_resources(resources_root: Path) -> Path:
    resource_dir = resources_root / "fastq_to_vcf_analysis"
    resource_dir.mkdir(parents=True, exist_ok=True)
    for filename in FASTQ_TO_VCF_RESOURCE_FILENAMES:
        (resource_dir / filename).write_text("test\n", encoding="utf-8")
    return resource_dir


def _write_fastq_pairs(fastq_dir: Path, sample_ids: list[str]) -> None:
    fastq_dir.mkdir(parents=True, exist_ok=True)
    for sample_id in sample_ids:
        (fastq_dir / f"{sample_id}_1.fq.gz").write_bytes(b"test")
        (fastq_dir / f"{sample_id}_2.fq.gz").write_bytes(b"test")


def test_fastq_to_vcf_schema_hides_internal_resource_paths(tmp_path) -> None:
    tool = RunFastqToVcfTool(tmp_path)
    properties = tool.parameters["properties"]

    assert tool.parameters["required"] == ["fastq_dir"]
    assert set(properties) == {
        "fastq_dir",
        "project_id",
        "threads",
        "parallel_jobs",
        "output_dir",
    }
    assert "reference_fasta" not in properties
    assert "filter_script" not in properties
    assert "stats_script" not in properties


@pytest.mark.asyncio
async def test_fastq_to_vcf_prepares_any_number_of_sample_pairs(
    monkeypatch, tmp_path
) -> None:
    resources_root = tmp_path / "resources"
    resource_dir = _write_fastq_to_vcf_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    fastq_dir = workspace / "E250143075"
    sample_ids = ["E250143075_DH09156", "E250143075_DH09157", "E250143075_DH09158"]
    _write_fastq_pairs(fastq_dir, sample_ids)
    tool = RunFastqToVcfTool(workspace)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)

    prepared = await tool.prepare_run(fastq_dir=str(fastq_dir))

    assert prepared.sample_ids == sample_ids
    assert prepared.project_id == "E250143075"
    assert prepared.reference_fasta_path == (
        resource_dir / "Zm-B73-REFERENCE-GRAMENE-4.0.fa"
    )
    assert prepared.output_dir == (
        workspace / "default_results" / "fastq_to_vcf" / "E250143075"
    )
    assert prepared.final_vcf_path == (
        prepared.output_dir / "04-Output" / "E250143075.vcf.gz"
    )
    assert prepared.command[:5] == [
        "/usr/bin/conda",
        "run",
        "-n",
        "EasyGS_5",
        "bash",
    ]
    assert str(prepared.reference_fasta_path) in prepared.command


@pytest.mark.asyncio
async def test_fastq_to_vcf_uses_custom_project_and_parallel_settings(
    monkeypatch, tmp_path
) -> None:
    resources_root = tmp_path / "resources"
    _write_fastq_to_vcf_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    fastq_dir = workspace / "reads"
    _write_fastq_pairs(fastq_dir, ["sample-A"])
    tool = RunFastqToVcfTool(workspace)
    monkeypatch.setattr(tool, "_get_environment_status", _fake_environment_status)
    output_root = workspace / "results"

    prepared = await tool.prepare_run(
        fastq_dir=str(fastq_dir),
        project_id="maize-batch-2",
        threads=4,
        parallel_jobs=2,
        output_dir=str(output_root),
    )

    assert prepared.project_id == "maize-batch-2"
    assert prepared.threads == 4
    assert prepared.parallel_jobs == 2
    assert prepared.output_dir == output_root / "maize-batch-2"


@pytest.mark.asyncio
async def test_fastq_to_vcf_rejects_missing_mate(monkeypatch, tmp_path) -> None:
    resources_root = tmp_path / "resources"
    _write_fastq_to_vcf_resources(resources_root)
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    fastq_dir = tmp_path / "workspace" / "reads"
    fastq_dir.mkdir(parents=True)
    (fastq_dir / "sample1_1.fq.gz").write_bytes(b"test")
    tool = RunFastqToVcfTool(tmp_path / "workspace")

    with pytest.raises(ValueError, match="Missing R2 mate"):
        await tool.prepare_run(fastq_dir=str(fastq_dir))


@pytest.mark.asyncio
async def test_fastq_to_vcf_reports_missing_managed_resource(
    monkeypatch, tmp_path
) -> None:
    resources_root = tmp_path / "resources"
    monkeypatch.setenv("EASYGS_RESOURCES_DIR", str(resources_root))
    workspace = tmp_path / "workspace"
    fastq_dir = workspace / "reads"
    _write_fastq_pairs(fastq_dir, ["sample1"])
    tool = RunFastqToVcfTool(workspace)

    with pytest.raises(ValueError, match="Zm-B73-REFERENCE-GRAMENE-4.0.fa") as error:
        await tool.prepare_run(fastq_dir=str(fastq_dir))

    assert "EASYGS_RESOURCES_DIR" in str(error.value)


@pytest.mark.asyncio
async def test_fastq_to_vcf_rejects_public_reference_parameter(tmp_path) -> None:
    tool = RunFastqToVcfTool(tmp_path)

    result = await tool.execute(
        fastq_dir=str(tmp_path),
        reference_fasta="/tmp/reference.fa",
    )

    assert result.startswith("Error: reference and helper-script paths are not public")


def test_fastq_to_vcf_workflow_is_registered(tmp_path) -> None:
    workflows = build_analysis_workflows(tmp_path, restrict_to_workspace=False)
    definitions = {workflow.definition.tool_name: workflow.definition for workflow in workflows}

    definition = definitions["fastq_to_vcf_analysis"]
    assert definition.kind == "fastq_to_vcf"
    assert isinstance(definition.run_tool, RunFastqToVcfTool)


def test_workflow_runtime_excludes_only_background_queue_wait() -> None:
    workflow = WorkflowRecord(
        id="wf_runtime",
        name="runtime",
        status="succeeded",
        task_started_at_ms=1_000,
        created_at_ms=2_000,
        started_at_ms=7_000,
        completed_at_ms=10_000,
    )

    assert workflow.runtime_ms() == 4_000

    workflow.status = "queued"
    workflow.started_at_ms = None
    workflow.completed_at_ms = None
    assert workflow.runtime_ms(now_ms=8_000) == 1_000
    assert workflow.runtime_ms(now_ms=80_000) == 1_000

    workflow.status = "cancelled"
    workflow.completed_at_ms = 80_000
    assert workflow.runtime_ms() == 1_000


def test_multiple_workflow_metrics_keep_original_tokens_isolated(tmp_path) -> None:
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=MessageBus(),
        workspace=tmp_path,
    )
    try:
        first = WorkflowRecord(
            id="wf_metrics_first",
            name="first",
            status="succeeded",
            request="first",
            work_dir=str(tmp_path / "first"),
            task_started_at_ms=1_000,
            created_at_ms=2_000,
            updated_at_ms=6_000,
            started_at_ms=3_000,
            completed_at_ms=6_000,
            input_tokens=11,
            output_tokens=1,
            llm_call_count=1,
            usage_reported_call_count=1,
        )
        second = WorkflowRecord(
            id="wf_metrics_second",
            name="second",
            status="succeeded",
            request="second",
            work_dir=str(tmp_path / "second"),
            task_started_at_ms=1_000,
            created_at_ms=2_500,
            updated_at_ms=10_000,
            started_at_ms=9_000,
            completed_at_ms=10_000,
            input_tokens=22,
            output_tokens=2,
            llm_call_count=1,
            usage_reported_call_count=1,
        )
        service._insert_workflow(first)
        service._insert_workflow(second)
        service._record_llm_usage(
            first.id,
            {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        )
        service._record_llm_usage(
            second.id,
            {"prompt_tokens": 300, "completion_tokens": 30, "total_tokens": 330},
        )

        stored_first = service.get_workflow(first.id)
        stored_second = service.get_workflow(second.id)
        assert stored_first is not None
        assert stored_second is not None
        assert (stored_first.input_tokens, stored_first.output_tokens) == (111, 11)
        assert (stored_second.input_tokens, stored_second.output_tokens) == (322, 32)
        assert stored_first.llm_call_count == stored_first.usage_reported_call_count == 2
        assert stored_second.llm_call_count == stored_second.usage_reported_call_count == 2
        assert stored_first.runtime_ms() == 4_000
        assert stored_second.runtime_ms() == 2_500

        service._write_metrics(stored_second)
        metrics = json.loads(
            (Path(stored_second.work_dir) / "run_metrics.json").read_text(encoding="utf-8")
        )
        assert metrics["input_tokens"] == 322
        assert metrics["output_tokens"] == 32
        assert metrics["total_tokens"] == 354
        assert metrics["runtime_seconds"] == 2.5
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_background_workflow_marks_llm_error_response_as_failed(tmp_path) -> None:
    class ErrorResponseProvider:
        async def chat(self, **kwargs):
            return LLMResponse(
                content="Error calling LLM: test connection failure.",
                finish_reason="error",
            )

    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=MessageBus(),
        workspace=tmp_path,
        provider=ErrorResponseProvider(),
        tool_registry_factory=lambda workflow: ToolRegistry(),
        max_iterations=1,
    )
    try:
        workflow = await service.submit_workflow(
            request="Run an analysis.",
            origin_channel="test",
            origin_chat_id="chat",
            notify_on_completion=False,
        )
        for _ in range(100):
            finished = service.get_workflow(workflow.id)
            if finished is not None and finished.status in {
                "succeeded",
                "failed",
                "cancelled",
            }:
                break
            await asyncio.sleep(0.01)
        else:
            pytest.fail("workflow did not finish")

        assert finished.status == "failed"
        assert finished.error == "Error calling LLM: test connection failure."
        assert finished.final_summary == ""
        assert service.get_actions(workflow.id) == []
    finally:
        service.stop()


class _CancelGuardService:
    def __init__(self, result: str = "Workflow `wf_deadbeef` cancelled."):
        self.result = result
        self.calls: list[tuple[str, str | None]] = []

    def find_active_for_origin(self, origin_channel: str, origin_chat_id: str):
        raise AssertionError("guardrail cancellation must not infer an active workflow")

    async def cancel_workflow(self, workflow_id: str, reason: str | None = None) -> str:
        self.calls.append((workflow_id, reason))
        return self.result


class _CancelGuardProvider:
    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.tool_names_by_call: list[set[str]] = []

    def get_default_model(self):
        return "fake-model"

    async def chat(
        self,
        messages,
        tools=None,
        model=None,
        max_tokens=4096,
        temperature=0.7,
        reasoning_effort=None,
    ):
        self.tool_names_by_call.append(
            {
                item.get("function", {}).get("name")
                for item in (tools or [])
                if isinstance(item, dict)
            }
        )
        return self.responses.pop(0)


def _build_cancel_guard_agent(tmp_path, monkeypatch, provider, service):
    monkeypatch.setattr("easygs.agent.loop.get_data_dir", lambda: tmp_path)
    agent = AgentLoop(bus=MessageBus(), provider=provider, workspace=tmp_path)
    agent.tools.unregister("cancel_workflow")
    agent.tools.register(CancelWorkflowTool(service))
    return agent


def test_cancel_claim_detector_targets_action_claims_only() -> None:
    assert AgentLoop._looks_like_workflow_cancelled_text(
        "已成功取消工作流 `wf_deadbeef`。"
    )
    assert AgentLoop._looks_like_workflow_cancelled_text(
        "Workflow `wf_deadbeef` cancelled."
    )
    assert not AgentLoop._looks_like_workflow_cancelled_text(
        "工作流 `wf_deadbeef` 当前状态：已取消。"
    )
    assert not AgentLoop._looks_like_workflow_cancelled_text("请问您要取消哪个工作流？")


@pytest.mark.asyncio
async def test_fake_cancel_claim_retries_with_only_cancel_tool(tmp_path, monkeypatch) -> None:
    provider = _CancelGuardProvider(
        [
            LLMResponse(content="已成功取消工作流 `wf_deadbeef`。"),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="cancel_1",
                        name="cancel_workflow",
                        arguments={"workflow_id": "wf_deadbeef"},
                    )
                ],
            ),
        ]
    )
    service = _CancelGuardService()
    agent = _build_cancel_guard_agent(tmp_path, monkeypatch, provider, service)

    response = await agent.process_direct("取消 wf_deadbeef")

    assert response == "Workflow `wf_deadbeef` cancelled."
    assert service.calls == [("wf_deadbeef", None)]
    assert provider.tool_names_by_call[1] == {"cancel_workflow"}


@pytest.mark.asyncio
async def test_cancel_retry_without_explicit_id_does_not_execute(tmp_path, monkeypatch) -> None:
    provider = _CancelGuardProvider(
        [
            LLMResponse(content="已成功取消工作流 `wf_deadbeef`。"),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="cancel_1",
                        name="cancel_workflow",
                        arguments={},
                    )
                ],
            ),
        ]
    )
    service = _CancelGuardService()
    agent = _build_cancel_guard_agent(tmp_path, monkeypatch, provider, service)

    response = await agent.process_direct("取消 wf_deadbeef")

    assert response == "工作流取消未执行，请重试。"
    assert service.calls == []


@pytest.mark.asyncio
async def test_cancel_retry_without_tool_call_returns_safe_failure(
    tmp_path, monkeypatch
) -> None:
    provider = _CancelGuardProvider(
        [
            LLMResponse(content="已成功取消工作流 `wf_deadbeef`。"),
            LLMResponse(content="I cannot call the cancellation tool."),
        ]
    )
    service = _CancelGuardService()
    agent = _build_cancel_guard_agent(tmp_path, monkeypatch, provider, service)

    response = await agent.process_direct("取消 wf_deadbeef")

    assert response == "工作流取消未执行，请重试。"
    assert service.calls == []


@pytest.mark.asyncio
async def test_real_cancel_tool_result_is_terminal(tmp_path, monkeypatch) -> None:
    provider = _CancelGuardProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="cancel_1",
                        name="cancel_workflow",
                        arguments={"workflow_id": "wf_deadbeef"},
                    )
                ],
            )
        ]
    )
    service = _CancelGuardService(
        "Workflow `wf_deadbeef` already finished with status `cancelled`."
    )
    agent = _build_cancel_guard_agent(tmp_path, monkeypatch, provider, service)

    response = await agent.process_direct("再次取消 wf_deadbeef")

    assert response == "Workflow `wf_deadbeef` already finished with status `cancelled`."
    assert service.calls == [("wf_deadbeef", None)]
    assert len(provider.tool_names_by_call) == 1


@pytest.mark.asyncio
async def test_plain_cancel_question_does_not_trigger_retry(tmp_path, monkeypatch) -> None:
    provider = _CancelGuardProvider([LLMResponse(content="请问您要取消哪个工作流？")])
    service = _CancelGuardService()
    agent = _build_cancel_guard_agent(tmp_path, monkeypatch, provider, service)

    response = await agent.process_direct("取消")

    assert response == "请问您要取消哪个工作流？"
    assert service.calls == []
    assert len(provider.tool_names_by_call) == 1


class _SubmissionGuardProvider:
    def __init__(self, responses: list[LLMResponse]):
        self.responses = list(responses)
        self.tool_names_by_call: list[set[str]] = []

    def get_default_model(self) -> str:
        return "fake-model"

    async def chat(
        self,
        messages,
        tools=None,
        model=None,
        max_tokens=4096,
        temperature=0.7,
        reasoning_effort=None,
    ) -> LLMResponse:
        self.tool_names_by_call.append(
            {
                item.get("function", {}).get("name")
                for item in (tools or [])
                if isinstance(item, dict)
            }
        )
        if not self.responses:
            raise AssertionError("unexpected extra provider call")
        return self.responses.pop(0)


class _RecordingSubmitWorkflowTool(Tool):
    def __init__(self, workflow_id: str = "wf_cafebabe"):
        self.workflow_id = workflow_id
        self.calls: list[dict[str, Any]] = []
        self._metadata: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "submit_workflow"

    @property
    def description(self) -> str:
        return "Submit a test workflow."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"request": {"type": "string"}},
            "required": ["request"],
        }

    @property
    def terminal_after_execution(self) -> bool:
        return True

    @property
    def last_execution_metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    async def execute(self, request: str, **kwargs: Any) -> str:
        self.calls.append({"request": request, **kwargs})
        self._metadata = {
            "active_workflow_id": self.workflow_id,
            "workflow_id": self.workflow_id,
            "workflow_name": "verified_submission",
        }
        return (
            f"Background workflow submitted: `{self.workflow_id}`\n"
            "Name: verified_submission\n"
            "Status: queued"
        )


def _build_submission_guard_agent(tmp_path, monkeypatch, provider):
    monkeypatch.setattr("easygs.agent.loop.get_data_dir", lambda: tmp_path)
    agent = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=tmp_path,
        max_iterations=3,
    )
    submit_tool = _RecordingSubmitWorkflowTool()
    agent.tools.unregister("submit_workflow")
    agent.tools.register(submit_tool)
    return agent, submit_tool


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claimed_submission",
    [
        "后台工作流已提交：`wf_deadbeef`，状态：已排队。",
        "Background workflow submitted: `wf_deadbeef`.",
        "バックグラウンドワークフロー `wf_deadbeef` を送信しました。",
    ],
)
async def test_unverified_submission_id_forces_real_tool_call(
    tmp_path,
    monkeypatch,
    claimed_submission: str,
) -> None:
    provider = _SubmissionGuardProvider(
        [
            LLMResponse(content=claimed_submission),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="submit_1",
                        name="submit_workflow",
                        arguments={"request": "执行 Q013 分析"},
                    )
                ],
            ),
        ]
    )
    agent, submit_tool = _build_submission_guard_agent(tmp_path, monkeypatch, provider)
    try:
        response = await agent.process_direct("执行 Q013 分析")

        assert "wf_cafebabe" in response
        assert "wf_deadbeef" not in response
        assert submit_tool.calls == [{"request": "执行 Q013 分析"}]
        assert provider.tool_names_by_call[1] == {"submit_workflow"}
    finally:
        agent.workflows.stop()


@pytest.mark.asyncio
async def test_user_supplied_unknown_id_does_not_submit(
    tmp_path,
    monkeypatch,
) -> None:
    provider = _SubmissionGuardProvider(
        [LLMResponse(content="工作流 `wf_deadbeef` 不存在。")]
    )
    agent, submit_tool = _build_submission_guard_agent(tmp_path, monkeypatch, provider)
    try:
        response = await agent.process_direct("查询工作流 wf_deadbeef")

        assert response == "工作流 `wf_deadbeef` 不存在。"
        assert submit_tool.calls == []
        assert len(provider.tool_names_by_call) == 1
    finally:
        agent.workflows.stop()


@pytest.mark.asyncio
async def test_workflow_id_from_status_tool_is_trusted(
    tmp_path,
    monkeypatch,
) -> None:
    provider = _SubmissionGuardProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="status_1",
                        name="get_workflow_status",
                        arguments={"workflow_id": "wf_deadbeef"},
                    )
                ],
            ),
            LLMResponse(content="工作流 `wf_deadbeef` 不存在。"),
        ]
    )
    agent, submit_tool = _build_submission_guard_agent(tmp_path, monkeypatch, provider)
    try:
        response = await agent.process_direct("检查当前工作流")

        assert response == "工作流 `wf_deadbeef` 不存在。"
        assert submit_tool.calls == []
        assert len(provider.tool_names_by_call) == 2
    finally:
        agent.workflows.stop()


@pytest.mark.asyncio
async def test_real_submission_result_is_unchanged(
    tmp_path,
    monkeypatch,
) -> None:
    provider = _SubmissionGuardProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="submit_1",
                        name="submit_workflow",
                        arguments={"request": "执行真实任务"},
                    )
                ],
            )
        ]
    )
    agent, submit_tool = _build_submission_guard_agent(tmp_path, monkeypatch, provider)
    try:
        response = await agent.process_direct("执行真实任务")

        assert "Background workflow submitted: `wf_cafebabe`" in response
        assert submit_tool.calls == [{"request": "执行真实任务"}]
        assert len(provider.tool_names_by_call) == 1
    finally:
        agent.workflows.stop()


@pytest.mark.asyncio
async def test_unverified_submission_without_retry_tool_call_fails_closed(
    tmp_path,
    monkeypatch,
) -> None:
    provider = _SubmissionGuardProvider(
        [
            LLMResponse(content="后台工作流已提交：`wf_deadbeef`。"),
            LLMResponse(content="我稍后再提交。"),
        ]
    )
    agent, submit_tool = _build_submission_guard_agent(tmp_path, monkeypatch, provider)
    try:
        response = await agent.process_direct("执行 Q013 分析")

        assert response == "后台工作流创建失败，请重试。"
        assert "wf_deadbeef" not in response
        assert submit_tool.calls == []
    finally:
        agent.workflows.stop()
