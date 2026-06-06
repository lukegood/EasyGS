"""Combined population-structure and kinship analysis workflow."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedPopulationStructureKinshipRun:
    """Prepared combined population-structure and kinship workflow."""

    launcher: str
    command: list[str]
    bfile_prefix_path: Path
    output_dir: Path
    ld_prune_prefix_path: Path
    ld_bfile_prefix_path: Path
    pca_prefix_path: Path
    grm_prefix_path: Path
    admixture_dataset_prefix_path: Path
    best_k_result_path: Path
    summary_path: Path
    reuse_existing_ld_bfile: bool
    existing_ld_bfile_prefix_path: Path | None
    pca_components: int
    k_min: int
    k_max: int
    ld_window_size: int
    ld_step_size: int
    ld_r2_threshold: float
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "output_dir": str(self.output_dir),
            "ld_prune_prefix_path": str(self.ld_prune_prefix_path),
            "ld_bfile_prefix_path": str(self.ld_bfile_prefix_path),
            "pca_prefix_path": str(self.pca_prefix_path),
            "grm_prefix_path": str(self.grm_prefix_path),
            "admixture_dataset_prefix_path": str(self.admixture_dataset_prefix_path),
            "best_k_result_path": str(self.best_k_result_path),
            "summary_path": str(self.summary_path),
            "reuse_existing_ld_bfile": self.reuse_existing_ld_bfile,
            "existing_ld_bfile_prefix_path": (
                str(self.existing_ld_bfile_prefix_path) if self.existing_ld_bfile_prefix_path else ""
            ),
            "pca_components": self.pca_components,
            "k_min": self.k_min,
            "k_max": self.k_max,
            "ld_window_size": self.ld_window_size,
            "ld_step_size": self.ld_step_size,
            "ld_r2_threshold": self.ld_r2_threshold,
            "notes": list(self.notes),
        }



class RunPopulationStructureKinshipTool(PlinkToolBase, Tool):
    """Run LD-pruned PCA, GRM construction, and ADMIXTURE in one workflow."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 14400):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="population_structure_kinship_analysis",
            default_output_subdir="population_structure_kinship",
        )
        self.script_path = self.skill_dir / "population_structure_kinship.sh"
        self.summary_script_path = self.skill_dir / "summarize_population_structure_kinship.py"
        self.ld_prune_script = Path(__file__).resolve().parents[2] / "skills" / "ld_prune_analysis" / "scripts" / "ld_prune.sh"
        self.ld_prune_summary_script = (
            Path(__file__).resolve().parents[2] / "skills" / "ld_prune_analysis" / "scripts" / "summarize_ld_prune.py"
        )
        self.bfile_extract_script = self.skill_dir.parents[1] / "bfile_extract_analysis" / "scripts" / "bfile_extract.sh"
        self.bfile_extract_summary_script = (
            self.skill_dir.parents[1] / "bfile_extract_analysis" / "scripts" / "summarize_bfile_extract.py"
        )
        self.pca_script = self.skill_dir.parents[1] / "pca_analysis" / "scripts" / "pca.sh"
        self.pca_summary_script = self.skill_dir.parents[1] / "pca_analysis" / "scripts" / "summarize_pca.py"
        self.grm_script = self.skill_dir.parents[1] / "grm_analysis" / "scripts" / "grm.sh"
        self.grm_summary_script = self.skill_dir.parents[1] / "grm_analysis" / "scripts" / "summarize_grm.py"
        self.admixture_script = self.skill_dir.parents[1] / "admixture_analysis" / "scripts" / "admixture.sh"
        self.admixture_summary_script = (
            self.skill_dir.parents[1] / "admixture_analysis" / "scripts" / "summarize_admixture.py"
        )

    @property
    def name(self) -> str:
        return "run_population_structure_kinship"

    @property
    def description(self) -> str:
        return (
            "Run LD pruning, pruned-SNP extraction, PCA, GRM construction, and ADMIXTURE "
            "population-structure analysis as one combined workflow using the EasyGS_2 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bfile_prefix": {
                    "type": "string",
                    "description": "Input BED/BIM/FAM prefix, such as filter.",
                },
                "ld_bfile_prefix": {
                    "type": "string",
                    "description": (
                        "Optional existing LD-pruned BED/BIM/FAM prefix. When provided, the workflow "
                        "skips the LD-prune and extract steps and reuses this dataset for PCA."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/population_structure_kinship/."
                    ),
                },
                "ld_prune_prefix": {
                    "type": "string",
                    "description": "Prefix for LD-prune outputs. Defaults to 'data_pruned'.",
                },
                "ld_bfile_output_prefix": {
                    "type": "string",
                    "description": "Prefix for extracted non-linked BFILE outputs. Defaults to 'data_ld_pruned'.",
                },
                "pca_prefix": {
                    "type": "string",
                    "description": "Prefix for PCA outputs. Defaults to 'data_pca_pruned'.",
                },
                "grm_prefix": {
                    "type": "string",
                    "description": "Prefix for GRM outputs. Defaults to 'grm'.",
                },
                "admixture_prefix": {
                    "type": "string",
                    "description": (
                        "Dataset basename used for ADMIXTURE outputs. Defaults to the basename of the input BFILE."
                    ),
                },
                "ld_window_size": {
                    "type": "integer",
                    "description": "PLINK indep-pairwise window size. Defaults to 50.",
                },
                "ld_step_size": {
                    "type": "integer",
                    "description": "PLINK indep-pairwise step size. Defaults to 5.",
                },
                "ld_r2_threshold": {
                    "type": "number",
                    "description": "PLINK indep-pairwise r^2 threshold. Defaults to 0.2.",
                },
                "pca_components": {
                    "type": "integer",
                    "description": "Number of PCA components. Defaults to 20.",
                },
                "k_min": {
                    "type": "integer",
                    "description": "Minimum K for ADMIXTURE. Defaults to 2.",
                },
                "k_max": {
                    "type": "integer",
                    "description": "Maximum K for ADMIXTURE. Defaults to 10.",
                },
            },
            "required": ["bfile_prefix"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        ld_bfile_prefix: str | None = None,
        output_dir: str | None = None,
        ld_prune_prefix: str | None = None,
        ld_bfile_output_prefix: str | None = None,
        pca_prefix: str | None = None,
        grm_prefix: str | None = None,
        admixture_prefix: str | None = None,
        ld_window_size: int = 50,
        ld_step_size: int = 5,
        ld_r2_threshold: float = 0.2,
        pca_components: int = 20,
        k_min: int = 2,
        k_max: int = 10,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                ld_bfile_prefix=ld_bfile_prefix,
                output_dir=output_dir,
                ld_prune_prefix=ld_prune_prefix,
                ld_bfile_output_prefix=ld_bfile_output_prefix,
                pca_prefix=pca_prefix,
                grm_prefix=grm_prefix,
                admixture_prefix=admixture_prefix,
                ld_window_size=ld_window_size,
                ld_step_size=ld_step_size,
                ld_r2_threshold=ld_r2_threshold,
                pca_components=pca_components,
                k_min=k_min,
                k_max=k_max,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Population structure and kinship workflow failed.\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Population structure and kinship workflow completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- LD-prune prefix: {prepared.ld_prune_prefix_path}",
            f"- LD-pruned BFILE prefix: {prepared.ld_bfile_prefix_path}",
            f"- PCA prefix: {prepared.pca_prefix_path}",
            f"- GRM prefix: {prepared.grm_prefix_path}",
            f"- ADMIXTURE dataset prefix: {prepared.admixture_dataset_prefix_path}",
            f"- Best K result: {prepared.best_k_result_path}",
            f"- Summary file: {prepared.summary_path}",
        ]
        if prepared.reuse_existing_ld_bfile and prepared.existing_ld_bfile_prefix_path:
            lines.append(f"- Reused existing LD-pruned BFILE: {prepared.existing_ld_bfile_prefix_path}")
        preview = self._read_preview(prepared.summary_path)
        if preview:
            lines.extend(["", "Summary preview:", preview])
        details = self._join_output(run_result["stdout"], run_result["stderr"])
        if details:
            lines.extend(["", details])
        return "\n".join(lines)

    async def prepare_run(
        self,
        *,
        bfile_prefix: str,
        ld_bfile_prefix: str | None = None,
        output_dir: str | None = None,
        ld_prune_prefix: str | None = None,
        ld_bfile_output_prefix: str | None = None,
        pca_prefix: str | None = None,
        grm_prefix: str | None = None,
        admixture_prefix: str | None = None,
        ld_window_size: int = 50,
        ld_step_size: int = 5,
        ld_r2_threshold: float = 0.2,
        pca_components: int = 20,
        k_min: int = 2,
        k_max: int = 10,
    ) -> PreparedPopulationStructureKinshipRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)

        if int(ld_window_size) <= 0 or int(ld_step_size) <= 0:
            raise ValueError("ld_window_size and ld_step_size must be positive integers.")
        if float(ld_r2_threshold) <= 0 or float(ld_r2_threshold) > 1:
            raise ValueError("ld_r2_threshold must be between 0 and 1.")
        if int(pca_components) <= 0:
            raise ValueError("pca_components must be a positive integer.")
        if int(k_min) < 2:
            raise ValueError("k_min must be at least 2.")
        if int(k_max) < int(k_min):
            raise ValueError("k_max must be greater than or equal to k_min.")

        output_root = self._resolve_output_dir(output_dir)
        ld_prune_prefix_name = self._normalize_prefix_name(ld_prune_prefix, "data_pruned")
        ld_bfile_prefix_name = self._normalize_prefix_name(ld_bfile_output_prefix, "data_ld_pruned")
        pca_prefix_name = self._normalize_prefix_name(pca_prefix, "data_pca_pruned")
        grm_prefix_name = self._normalize_prefix_name(grm_prefix, "grm")
        admixture_prefix_name = self._normalize_prefix_name(admixture_prefix, bfile_prefix_path.name)

        reuse_existing_ld_bfile = bool((ld_bfile_prefix or "").strip())
        existing_ld_bfile_prefix_path: Path | None = None
        if reuse_existing_ld_bfile:
            existing_ld_bfile_prefix_path = self._resolve_bfile_prefix(str(ld_bfile_prefix))

        ld_prune_prefix_path = output_root / ld_prune_prefix_name
        ld_bfile_prefix_path = (
            existing_ld_bfile_prefix_path if existing_ld_bfile_prefix_path else output_root / ld_bfile_prefix_name
        )
        pca_prefix_path = output_root / pca_prefix_name
        grm_prefix_path = output_root / grm_prefix_name
        admixture_dataset_prefix_path = output_root / admixture_prefix_name
        best_k_result_path = output_root / "best_k_result.txt"
        summary_path = output_root / "population_structure_kinship_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "workflow summary script": self.summary_script_path,
            "ld-prune script": self.ld_prune_script,
            "ld-prune summary script": self.ld_prune_summary_script,
            "bfile extract script": self.bfile_extract_script,
            "bfile extract summary script": self.bfile_extract_summary_script,
            "pca script": self.pca_script,
            "pca summary script": self.pca_summary_script,
            "grm script": self.grm_script,
            "grm summary script": self.grm_summary_script,
            "admixture script": self.admixture_script,
            "admixture summary script": self.admixture_summary_script,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["plink", "gcta64", "admixture", "python3"])
        if env_status["error"]:
            error = env_status["error"]
            raise ValueError(error[7:] if error.startswith("Error: ") else error)

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "bash",
            str(self.script_path),
            "--bfile",
            str(bfile_prefix_path),
            "--output-dir",
            str(output_root),
            "--ld-window-size",
            str(int(ld_window_size)),
            "--ld-step-size",
            str(int(ld_step_size)),
            "--ld-r2-threshold",
            str(float(ld_r2_threshold)),
            "--pca-components",
            str(int(pca_components)),
            "--k-min",
            str(int(k_min)),
            "--k-max",
            str(int(k_max)),
            "--ld-prune-prefix",
            str(ld_prune_prefix_path),
            "--ld-bfile-prefix",
            str(ld_bfile_prefix_path),
            "--pca-prefix",
            str(pca_prefix_path),
            "--grm-prefix",
            str(grm_prefix_path),
            "--admixture-prefix",
            admixture_prefix_name,
            "--best-k-output",
            str(best_k_result_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--ld-prune-script",
            str(self.ld_prune_script),
            "--ld-prune-summary-script",
            str(self.ld_prune_summary_script),
            "--bfile-extract-script",
            str(self.bfile_extract_script),
            "--bfile-extract-summary-script",
            str(self.bfile_extract_summary_script),
            "--pca-script",
            str(self.pca_script),
            "--pca-summary-script",
            str(self.pca_summary_script),
            "--grm-script",
            str(self.grm_script),
            "--grm-summary-script",
            str(self.grm_summary_script),
            "--admixture-script",
            str(self.admixture_script),
            "--admixture-summary-script",
            str(self.admixture_summary_script),
        ]
        if existing_ld_bfile_prefix_path:
            command.extend(["--existing-ld-bfile", str(existing_ld_bfile_prefix_path)])

        notes: list[str] = []
        if existing_ld_bfile_prefix_path:
            notes.append(f"Reusing existing LD-pruned BFILE for PCA: {existing_ld_bfile_prefix_path}")

        return PreparedPopulationStructureKinshipRun(
            launcher=env_status["launcher"],
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            output_dir=output_root,
            ld_prune_prefix_path=ld_prune_prefix_path,
            ld_bfile_prefix_path=ld_bfile_prefix_path,
            pca_prefix_path=pca_prefix_path,
            grm_prefix_path=grm_prefix_path,
            admixture_dataset_prefix_path=admixture_dataset_prefix_path,
            best_k_result_path=best_k_result_path,
            summary_path=summary_path,
            reuse_existing_ld_bfile=reuse_existing_ld_bfile,
            existing_ld_bfile_prefix_path=existing_ld_bfile_prefix_path,
            pca_components=int(pca_components),
            k_min=int(k_min),
            k_max=int(k_max),
            ld_window_size=int(ld_window_size),
            ld_step_size=int(ld_step_size),
            ld_r2_threshold=float(ld_r2_threshold),
            notes=notes,
        )
