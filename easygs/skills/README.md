# nanobot Skills

This directory contains built-in skills that extend nanobot's capabilities.

## Skill Format

Each skill is a directory containing a `SKILL.md` file with:
- YAML frontmatter (name, description, metadata)
- Markdown instructions for the agent

## Attribution

These skills are adapted from [OpenClaw](https://github.com/openclaw/openclaw)'s skill system.
The skill format and metadata structure follow OpenClaw's conventions to maintain compatibility.

## Available Skills

| Skill | Description |
|-------|-------------|
| `admixture_analysis` | Run ADMIXTURE across a K range and summarize the best K |
| `allele_count_analysis` | Run vcftools allele-count analysis and summarize polymorphic-site count |
| `allele_frequency_analysis` | Run vcftools allele-frequency analysis and summarize polymorphic-site proportion |
| `allele_frequency_spectrum_analysis` | Run PLINK `--freqx` on a BFILE dataset and summarize allele-frequency spectrum |
| `bfile_extract_analysis` | Extract variants from a BFILE into a new BED/BIM/FAM dataset |
| `candidate_gene_extraction_analysis` | Extract candidate genes from a user-provided BED file by LD expansion and gene annotation overlap |
| `combining_ability_analysis` | Estimate female GCA, male GCA, and hybrid SCA from a hybrid phenotype CSV |
| `cvf_split_analysis` | Generate a CVF CSV from a one-column material LIST TXT |
| `env_factor_correlation_analysis` | Compute region-specific environmental-factor correlations and render a heatmap |
| `environment_index_analysis` | Run the CERIS-style environment index workflow from EnvPheno text inputs |
| `env_region_correlation_analysis` | Compute cross-region correlations from combined environmental-factor profiles |
| `gene_environment_interaction_analysis` | Run SNP-by-environment-factor interaction ANOVA from a VCF and EnvPheno CSV inputs |
| `gene_function_annotation_analysis` | Run maize GO/KEGG enrichment from a gene list TXT using built-in Zm V4 gene-to-ENTREZ mapping |
| `genebody_locus_annotation_analysis` | Annotate locus IDs that fall inside maize V4 gene bodies using the built-in allV4gene.bed |
| `gebv_analysis` | Estimate genomic breeding values from a GRM prefix and phenotype file |
| `genotype_encoding_analysis` | Run PLINK `--recodeA` to encode genotypes as a 0/1/2 additive matrix |
| `gwas_analysis` | Run rMVP GWAS from a PLINK BFILE prefix, phenotype CSV, and kinship TXT |
| `github` | Interact with GitHub using the `gh` CLI |
| `genotype_imputation_analysis` | Run Beagle genotype imputation on a VCF/VCF.GZ file |
| `grm_analysis` | Construct a genomic relationship matrix from a BFILE dataset |
| `heritability` | Calculate single-trait heritability from VCF genotypes with the built-in GCTA pipeline |
| `ld_decay_analysis` | Run PopLDdecay on a VCF/VCF.GZ dataset and summarize LD decay statistics |
| `ld_prune_analysis` | Run standalone PLINK LD pruning |
| `locus_locus_interaction_analysis` | Run gene-by-gene interaction analysis from a VCF, phenotype CSV, and gene-map file |
| `locus_subset_analysis` | Keep or remove specified loci from a BFILE dataset and export subset outputs |
| `maf_distribution_analysis` | Run PLINK `--freq` on a BFILE dataset and summarize MAF distribution bins |
| `missingness_analysis` | Run standalone PLINK missingness analysis and reporting |
| `mean_nucleotide_diversity_analysis` | Compute average pi from a user-provided vcftools .sites.pi file |
| `nucleotide_diversity_analysis` | Run vcftools site-pi or window-pi analysis and summarize nucleotide diversity |
| `ortholog_extraction_analysis` | Extract ortholog rows from a user-provided gene list TXT and ortholog matrix TSV |
| `pca_analysis` | Run PCA on a BFILE dataset and generate a variance report |
| `peak_annotation_analysis` | Run ChIPseeker-based locus structural annotation from GFF3/GFF and BED inputs |
| `protein_function_annotation_analysis` | Extract maize protein function/domain annotation rows for a user-provided gene list without enrichment |
| `pfam_enrichment_analysis` | Extract candidate proteins and run maize-only PFAM/domain enrichment with user-managed longest-CDS and proteins annotation resources |
| `phenotype_blup_analysis` | Compute BLUP values from a multi-environment phenotype CSV using a mixed model |
| `phenotype_region_correlation_analysis` | Compute cross-region phenotype correlations from a phe.csv file |
| `population_structure_kinship_analysis` | Run the combined LD-pruned PCA, GRM, and ADMIXTURE workflow |
| `qei_detection_analysis` | Run Fast3VmrMLM multi-environment QEI detection from BFILE, phenotype, and Q inputs |
| `reaction_norm_analysis` | Convert a phenotype CSV to long format and compute intercept/slope values with FW |
| `rrblup_prediction_analysis` | Run rrBLUP genomic prediction from explicit genotype, phenotype, and CV CSV files |
| `region_r2_analysis` | Run PLINK `--r2` within a specified genomic region on a BFILE dataset |
| `sample_subset_analysis` | Keep or remove specified samples from a BFILE dataset and export subset outputs |
| `tajima_d_analysis` | Run vcftools Tajima's D analysis and summarize diversity statistics |
| `variance_decomposition_analysis` | Decompose phenotype variance into genotype, environment, and residual percentages |
| `vcf_format_conversion_analysis` | Convert between VCF, PED/MAP, and PLINK BED/BIM/FAM or exported VCF |
| `vcftools_analysis` | Run generic vcftools operations with structured argument arrays |
| `vcf_variant_extract_analysis` | Extract a subset VCF from a VCF/VCF.GZ input by variant ID list using bcftools |
| `variant_filter_analysis` | Run standalone PLINK variant filtering and filtered VCF export |
| `vcf_stats` | Generate VCF basic statistics with the built-in bcftools workflow |
| `weather` | Get weather info using wttr.in and Open-Meteo |
| `summarize` | Summarize URLs, files, and YouTube videos |
| `tmux` | Remote-control tmux sessions |
| `skill-creator` | Create new skills |
