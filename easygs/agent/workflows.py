"""Analysis workflow definitions used by the agent loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from easygs.agent.tools.admixture import RunAdmixtureTool
from easygs.agent.tools.allele_count import RunAlleleCountTool
from easygs.agent.tools.allele_frequency import RunAlleleFrequencyTool
from easygs.agent.tools.allele_frequency_spectrum import RunAlleleFrequencySpectrumTool
from easygs.agent.tools.bfile_extract import RunBfileExtractTool
from easygs.agent.tools.candidate_gene_extraction import RunCandidateGeneExtractionTool
from easygs.agent.tools.combining_ability import RunCombiningAbilityTool
from easygs.agent.tools.cvf_split import RunCvfSplitTool
from easygs.agent.tools.env_factor_correlation import RunEnvFactorCorrelationTool
from easygs.agent.tools.env_region_correlation import RunEnvRegionCorrelationTool
from easygs.agent.tools.environment_index import RunEnvironmentIndexTool
from easygs.agent.tools.gebv import RunGebvTool
from easygs.agent.tools.gene_environment_interaction import RunGeneEnvironmentInteractionTool
from easygs.agent.tools.gene_function_annotation import RunGeneFunctionAnnotationTool
from easygs.agent.tools.genebody_locus_annotation import RunGenebodyLocusAnnotationTool
from easygs.agent.tools.genotype_encoding import RunGenotypeEncodingTool
from easygs.agent.tools.genotype_imputation import RunGenotypeImputationTool
from easygs.agent.tools.grm import RunGrmTool
from easygs.agent.tools.gwas import RunGwasTool
from easygs.agent.tools.heritability import RunHeritabilityTool
from easygs.agent.tools.ld_decay import RunLdDecayTool
from easygs.agent.tools.ld_prune import RunLdPruneTool
from easygs.agent.tools.locus_locus_interaction import RunLocusLocusInteractionTool
from easygs.agent.tools.locus_subset import RunLocusSubsetTool
from easygs.agent.tools.maf_distribution import RunMafDistributionTool
from easygs.agent.tools.mean_nucleotide_diversity import RunMeanNucleotideDiversityTool
from easygs.agent.tools.missingness import RunMissingnessTool
from easygs.agent.tools.nucleotide_diversity import RunNucleotideDiversityTool
from easygs.agent.tools.ortholog_extraction import RunOrthologExtractionTool
from easygs.agent.tools.pca import RunPcaTool
from easygs.agent.tools.peak_annotation import RunPeakAnnotationTool
from easygs.agent.tools.pfam_enrichment import RunPfamEnrichmentTool
from easygs.agent.tools.phenotype_blup import RunPhenotypeBlupTool
from easygs.agent.tools.phenotype_region_correlation import RunPhenotypeRegionCorrelationTool
from easygs.agent.tools.population_structure_kinship import RunPopulationStructureKinshipTool
from easygs.agent.tools.protein_function_annotation import RunProteinFunctionAnnotationTool
from easygs.agent.tools.qei_detection import RunQeiDetectionTool
from easygs.agent.tools.reaction_norm import RunReactionNormTool
from easygs.agent.tools.region_r2 import RunRegionR2Tool
from easygs.agent.tools.rrblup_prediction import RunRrblupPredictionTool
from easygs.agent.tools.sample_subset import RunSampleSubsetTool
from easygs.agent.tools.tajima_d import RunTajimaDTool
from easygs.agent.tools.variance_decomposition import RunVarianceDecompositionTool
from easygs.agent.tools.variant_filter import RunVariantFilterTool
from easygs.agent.tools.vcf_format_conversion import RunVcfFormatConversionTool
from easygs.agent.tools.vcf_genomic_prediction_csv import RunVcfGenomicPredictionCsvTool
from easygs.agent.tools.vcf_stats import RunVcfStatsTool
from easygs.agent.tools.vcf_variant_extract import RunVcfVariantExtractTool
from easygs.agent.tools.vcftools import RunVcftoolsTool
from easygs.agent.tools.workflow import WorkflowDefinition


@dataclass(frozen=True)
class RegisteredWorkflow:
    """Registered analysis capability for workflow action execution."""

    definition: WorkflowDefinition


def _with_action_output_dir(
    kwargs: dict[str, Any],
    action_dir: Path,
    default_output_dir: Path,
) -> dict[str, Any]:
    prepared = dict(kwargs)
    prepared["output_dir"] = prepared.get("output_dir") or str(default_output_dir)
    return prepared


def _with_action_vcf_outputs(
    kwargs: dict[str, Any],
    action_dir: Path,
    default_output_dir: Path,
) -> dict[str, Any]:
    prepared = dict(kwargs)
    if not prepared.get("output_dir") and not (
        prepared.get("stats_output") and prepared.get("summary_output")
    ):
        prepared["output_dir"] = str(default_output_dir)
    return prepared


def _with_action_heritability_outputs(
    kwargs: dict[str, Any],
    action_dir: Path,
    default_output_dir: Path,
) -> dict[str, Any]:
    prepared = dict(kwargs)
    if not prepared.get("output_dir") and not (
        prepared.get("bed_dir") and prepared.get("grm_dir") and prepared.get("result_dir")
    ):
        prepared["output_dir"] = str(default_output_dir)
    prepared["work_root"] = action_dir / "work"
    return prepared


def build_analysis_workflows(
    workspace: Path,
    restrict_to_workspace: bool,
) -> list[RegisteredWorkflow]:
    """Create the built-in analysis workflow definitions."""
    allele_count = RunAlleleCountTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    allele_frequency = RunAlleleFrequencyTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    maf_distribution = RunMafDistributionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    allele_frequency_spectrum = RunAlleleFrequencySpectrumTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    bfile_extract = RunBfileExtractTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    candidate_gene_extraction = RunCandidateGeneExtractionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    combining_ability = RunCombiningAbilityTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    env_factor_correlation = RunEnvFactorCorrelationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    environment_index = RunEnvironmentIndexTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    env_region_correlation = RunEnvRegionCorrelationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    gene_environment_interaction = RunGeneEnvironmentInteractionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    gene_function_annotation = RunGeneFunctionAnnotationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    genebody_locus_annotation = RunGenebodyLocusAnnotationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    gwas = RunGwasTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    qei_detection = RunQeiDetectionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    locus_locus_interaction = RunLocusLocusInteractionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    phenotype_blup = RunPhenotypeBlupTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    reaction_norm = RunReactionNormTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    rrblup_prediction = RunRrblupPredictionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    cvf_split = RunCvfSplitTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    variance_decomposition = RunVarianceDecompositionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    phenotype_region_correlation = RunPhenotypeRegionCorrelationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    gebv = RunGebvTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    nucleotide_diversity = RunNucleotideDiversityTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    mean_nucleotide_diversity = RunMeanNucleotideDiversityTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    peak_annotation = RunPeakAnnotationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    pfam_enrichment = RunPfamEnrichmentTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    protein_function_annotation = RunProteinFunctionAnnotationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    ortholog_extraction = RunOrthologExtractionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    pca = RunPcaTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    region_r2 = RunRegionR2Tool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    ld_decay = RunLdDecayTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    tajima_d = RunTajimaDTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    grm = RunGrmTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    admixture = RunAdmixtureTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    population_structure_kinship = RunPopulationStructureKinshipTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    heritability = RunHeritabilityTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    missingness = RunMissingnessTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    variant_filter = RunVariantFilterTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    ld_prune = RunLdPruneTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    vcf_stats = RunVcfStatsTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    vcf_variant_extract = RunVcfVariantExtractTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    vcf_format_conversion = RunVcfFormatConversionTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    vcf_genomic_prediction_csv = RunVcfGenomicPredictionCsvTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    vcftools = RunVcftoolsTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    genotype_encoding = RunGenotypeEncodingTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    genotype_imputation = RunGenotypeImputationTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    locus_subset = RunLocusSubsetTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )
    sample_subset = RunSampleSubsetTool(
        workspace=workspace,
        restrict_to_workspace=restrict_to_workspace,
    )

    return [
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="allele_count",
                tool_name="allele_count_analysis",
                description=(
                    "Run vcftools allele-count analysis on a VCF/VCF.GZ input and summarize "
                    "the polymorphic-site count."
                ),
                run_tool=allele_count,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="allele_frequency",
                tool_name="allele_frequency_analysis",
                description=(
                    "Run vcftools allele-frequency analysis on a VCF/VCF.GZ input and summarize "
                    "the polymorphic-site proportion."
                ),
                run_tool=allele_frequency,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="maf_distribution",
                tool_name="maf_distribution_analysis",
                description=(
                    "Run PLINK allele-frequency analysis on a BFILE dataset and summarize "
                    "the variant distribution across standard minor-allele-frequency bins."
                ),
                run_tool=maf_distribution,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="allele_frequency_spectrum",
                tool_name="allele_frequency_spectrum_analysis",
                description=(
                    "Run PLINK genotype-count frequency analysis on a BFILE dataset and summarize "
                    "the allele-frequency spectrum from the resulting .frqx report."
                ),
                run_tool=allele_frequency_spectrum,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="region_r2",
                tool_name="region_r2_analysis",
                description=(
                    "Run PLINK pairwise R2 calculation within a specified chromosome region "
                    "on a BFILE dataset and summarize the resulting .ld report."
                ),
                run_tool=region_r2,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="ld_decay",
                tool_name="ld_decay_analysis",
                description=(
                    "Run PopLDdecay on a VCF/VCF.GZ dataset and summarize the resulting "
                    "LD decay statistics file."
                ),
                run_tool=ld_decay,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="env_factor_correlation",
                tool_name="env_factor_correlation_analysis",
                description=(
                    "Compute the environmental-factor correlation matrix for a specified region "
                    "from an env.csv dataset and render a heatmap PDF."
                ),
                run_tool=env_factor_correlation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="environment_index",
                tool_name="environment_index_analysis",
                description=(
                    "Run the CERIS-style environment index workflow from environment metadata, "
                    "trait records, and environment-parameter text files, with optional downstream "
                    "selected-window outputs."
                ),
                run_tool=environment_index,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="env_region_correlation",
                tool_name="env_region_correlation_analysis",
                description=(
                    "Compute the correlation matrix between regions after combining all "
                    "environmental-factor profiles from an env.csv dataset."
                ),
                run_tool=env_region_correlation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="phenotype_blup",
                tool_name="phenotype_blup_analysis",
                description=(
                    "Compute phenotype BLUP values from a multi-environment phenotype CSV "
                    "by fitting a mixed model across regions."
                ),
                run_tool=phenotype_blup,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="peak_annotation",
                tool_name="peak_annotation_analysis",
                description=(
                    "Run ChIPseeker-based locus structural annotation from a GFF3/GFF file and "
                    "a BED file, then export annotation TSV and PNG outputs."
                ),
                run_tool=peak_annotation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="reaction_norm",
                tool_name="reaction_norm_analysis",
                description=(
                    "Convert a multi-environment phenotype CSV into long format and compute "
                    "reaction norm intercept/slope values with a Finlay-Wilkinson-style "
                    "environment-index regression."
                ),
                run_tool=reaction_norm,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="rrblup_prediction",
                tool_name="rrblup_prediction_analysis",
                description=(
                    "Run rrBLUP genomic prediction from explicit genotype CSVs, phenotype CSVs, "
                    "and CV CSVs, then export fold predictions and average marker effects."
                ),
                run_tool=rrblup_prediction,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="cvf_split",
                tool_name="cvf_split_analysis",
                description=(
                    "Generate a cross-validation fold CSV from a one-column material LIST TXT, "
                    "requiring the first line to be a supported sample column header such as ID or list_id."
                ),
                run_tool=cvf_split,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="variance_decomposition",
                tool_name="variance_decomposition_analysis",
                description=(
                    "Decompose phenotype variance into genotype, environment, and residual "
                    "percentages from a long-format phenotype CSV."
                ),
                run_tool=variance_decomposition,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="phenotype_region_correlation",
                tool_name="phenotype_region_correlation_analysis",
                description=(
                    "Compute the correlation matrix between region-level phenotype columns "
                    "from a phe.csv dataset and render a heatmap PDF."
                ),
                run_tool=phenotype_region_correlation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="gene_environment_interaction",
                tool_name="gene_environment_interaction_analysis",
                description=(
                    "Run SNP-by-environment-factor interaction ANOVA from a VCF, a wide "
                    "phenotype CSV with TraitEnv columns, and a region-level environment-factor mean CSV."
                ),
                run_tool=gene_environment_interaction,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="gwas_rmvp",
                tool_name="gwas_analysis",
                description=(
                    "Run rMVP GWAS from a PLINK BFILE prefix and phenotype CSV, "
                    "then internally generate kinship/PC files and export result CSVs and plots."
                ),
                run_tool=gwas,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="qei_detection",
                tool_name="qei_detection_analysis",
                description=(
                    "Run Fast3VmrMLM multi-environment QEI detection from a PLINK BFILE "
                    "prefix, a phenotype CSV, and a Q/structure CSV."
                ),
                run_tool=qei_detection,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="locus_locus_interaction",
                tool_name="locus_locus_interaction_analysis",
                description=(
                    "Run gene-by-gene interaction analysis from a VCF file, a phenotype "
                    "CSV with ID and Phenotype columns, and a locus-to-gene mapping file."
                ),
                run_tool=locus_locus_interaction,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="genebody_locus_annotation",
                tool_name="genebody_locus_annotation_analysis",
                description=(
                    "Annotate user-provided loci that fall inside maize V4 gene bodies "
                    "using the built-in allV4gene.bed and export locus-to-gene pairs."
                ),
                run_tool=genebody_locus_annotation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="gebv",
                tool_name="gebv_analysis",
                description=(
                    "Run GCTA REML random-effect prediction from an existing GRM prefix and "
                    "phenotype file, then extract and rank GEBV values."
                ),
                run_tool=gebv,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="bfile_extract",
                tool_name="bfile_extract_analysis",
                description=(
                    "Extract a specified variant list from a PLINK BFILE dataset into a new "
                    "BED/BIM/FAM dataset."
                ),
                run_tool=bfile_extract,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="candidate_gene_extraction",
                tool_name="candidate_gene_extraction_analysis",
                description=(
                    "Extract candidate genes from a user-provided BED file by expanding loci "
                    "with an LD distance and intersecting them with gene annotations."
                ),
                run_tool=candidate_gene_extraction,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="pfam_enrichment",
                tool_name="pfam_enrichment_analysis",
                description=(
                    "Extract candidate proteins from a gene list using built-in maize longest-CDS "
                    "mapping and built-in maize protein-annotation TSV, then "
                    "run PFAM/domain enrichment "
                    "(maize-only)."
                ),
                run_tool=pfam_enrichment,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="protein_function_annotation",
                tool_name="protein_function_annotation_analysis",
                description=(
                    "Map maize genes to proteins using user-managed longest-CDS resources and "
                    "extract matching protein function/domain annotation rows without running enrichment."
                ),
                run_tool=protein_function_annotation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="ortholog_extraction",
                tool_name="ortholog_extraction_analysis",
                description=(
                    "Extract ortholog rows from a user-provided gene list TXT and maize "
                    "ortholog matrix TSV into a matched .ortholog.tsv file."
                ),
                run_tool=ortholog_extraction,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="gene_function_annotation",
                tool_name="gene_function_annotation_analysis",
                description=(
                    "Run GO and KEGG enrichment from a user-provided gene list TXT and "
                    "gene-to-ENTREZ CSV using AnnotationHub resources."
                ),
                run_tool=gene_function_annotation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="combining_ability",
                tool_name="combining_ability_analysis",
                description=(
                    "Estimate female GCA, male GCA, and hybrid SCA from a hybrid phenotype "
                    "CSV using a sommer mixed model."
                ),
                run_tool=combining_ability,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="nucleotide_diversity",
                tool_name="nucleotide_diversity_analysis",
                description=(
                    "Run vcftools nucleotide-diversity analysis on a VCF/VCF.GZ input using "
                    "either site-pi mode or window-pi mode."
                ),
                run_tool=nucleotide_diversity,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="mean_nucleotide_diversity",
                tool_name="mean_nucleotide_diversity_analysis",
                description=(
                    "Compute the average nucleotide diversity (pi) from a required user-provided "
                    "vcftools .sites.pi file."
                ),
                run_tool=mean_nucleotide_diversity,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="pca",
                tool_name="pca_analysis",
                description=(
                    "Run PLINK PCA on a BFILE dataset and summarize variance explained by each principal component."
                ),
                run_tool=pca,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="tajima_d",
                tool_name="tajima_d_analysis",
                description=(
                    "Run vcftools Tajima's D analysis on a VCF/VCF.GZ input using a configurable "
                    "window size."
                ),
                run_tool=tajima_d,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="grm",
                tool_name="grm_analysis",
                description=(
                    "Construct a genomic relationship matrix from a BFILE dataset using GCTA."
                ),
                run_tool=grm,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="admixture",
                tool_name="admixture_analysis",
                description=(
                    "Run ADMIXTURE across a K range on a BFILE dataset and summarize the best cross-validation K."
                ),
                run_tool=admixture,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="population_structure_kinship",
                tool_name="population_structure_kinship_analysis",
                description=(
                    "Run the combined workflow for LD-pruned PCA, GRM construction, and ADMIXTURE "
                    "population-structure analysis."
                ),
                run_tool=population_structure_kinship,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="heritability",
                tool_name="heritability_analysis",
                description=(
                    "Calculate single-trait heritability from VCF genotype data using the "
                    "bundled GCTA pipeline, with optional sample subsetting."
                ),
                run_tool=heritability,
                prepare_background_kwargs=_with_action_heritability_outputs,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="vcf_variant_extract",
                tool_name="vcf_variant_extract_analysis",
                description=(
                    "Extract a subset VCF from a VCF/VCF.GZ input by variant ID list using bcftools."
                ),
                run_tool=vcf_variant_extract,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="vcf_format_conversion",
                tool_name="vcf_format_conversion_analysis",
                description=(
                    "Convert between VCF input, PED/MAP input, and PLINK BED/BIM/FAM, PED/MAP, or exported VCF outputs."
                ),
                run_tool=vcf_format_conversion,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="vcf_genomic_prediction_csv",
                tool_name="vcf_genomic_prediction_csv_analysis",
                description=(
                    "Prepare a genomic-prediction-ready 0/1/2 genotype CSV matrix from VCF/VCF.GZ "
                    "calls. Defaults to samples as rows and variant IDs as columns."
                ),
                run_tool=vcf_genomic_prediction_csv,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="vcftools",
                tool_name="vcftools_analysis",
                description=(
                    "Run any vcftools-supported VCF operation through a structured argument array. "
                    "EasyGS manages --vcf/--gzvcf and --out."
                ),
                run_tool=vcftools,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="genotype_encoding",
                tool_name="genotype_encoding_analysis",
                description=(
                    "Run PLINK --recodeA to encode PED/MAP or BED/BIM/FAM genotype data "
                    "as a 0/1/2 additive dosage .raw matrix using EasyGS_2."
                ),
                run_tool=genotype_encoding,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="sample_subset",
                tool_name="sample_subset_analysis",
                description=(
                    "Keep or remove a specified set of samples from a PLINK BFILE dataset, export PED/MAP, "
                    "rebuild BED/BIM/FAM, and export a subset VCF."
                ),
                run_tool=sample_subset,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="locus_subset",
                tool_name="locus_subset_analysis",
                description=(
                    "Keep or remove a specified set of loci from a PLINK BFILE dataset, export PED/MAP, "
                    "rebuild BED/BIM/FAM, and export a subset VCF."
                ),
                run_tool=locus_subset,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="genotype_imputation",
                tool_name="genotype_imputation_analysis",
                description=(
                    "Run Beagle genotype imputation on a VCF/VCF.GZ input, producing an imputed "
                    "VCF.GZ and Beagle log."
                ),
                run_tool=genotype_imputation,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="missingness",
                tool_name="missingness_analysis",
                description=(
                    "Run PLINK missingness analysis and produce sample/variant missingness summaries."
                ),
                run_tool=missingness,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="variant_filter",
                tool_name="variant_filter_analysis",
                description=(
                    "Run PLINK variant and sample filtering, export a filtered VCF.GZ, and "
                    "build summary text."
                ),
                run_tool=variant_filter,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="ld_prune",
                tool_name="ld_prune_analysis",
                description=(
                    "Run PLINK LD pruning from either a VCF input or a PLINK bfile prefix."
                ),
                run_tool=ld_prune,
                prepare_background_kwargs=_with_action_output_dir,
            ),
        ),
        RegisteredWorkflow(
            definition=WorkflowDefinition(
                kind="vcf_stats",
                tool_name="vcf_stats_analysis",
                description=(
                    "Generate basic VCF statistics using bcftools stats and extract key "
                    "summary lines into cal.txt-style output."
                ),
                run_tool=vcf_stats,
                prepare_background_kwargs=_with_action_vcf_outputs,
            ),
        ),
    ]
