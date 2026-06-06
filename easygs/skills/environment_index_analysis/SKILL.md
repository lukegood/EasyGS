---
name: environment_index_analysis
description: Run the CERIS-style environment index workflow from EnvPheno text inputs and generate allwinds/highest summaries, with optional downstream selected-window outputs.
metadata: {"easygs":{"emoji":"🌾","os":["linux"]}}
---

# Environment Index Skill

Run the CERIS-style environment index workflow using the built-in `environment_index_analysis` tool.

This should be treated as one complete workflow rather than several user-facing subtools, because the whole analysis depends on one tightly coupled chain:

1. read environment metadata
2. read multi-environment trait records
3. read the DAP-by-environment parameter table
4. search critical windows across environmental factors
5. export `allwinds_EF_cor.csv` and `highest_EF.csv`
6. optionally generate downstream selected-window plots, slope/intercept estimates, and LOOCV outputs

Do not split this into separate public tools for "window search", "highest EF extraction", "LOO plot", or "pairwise distribution". Those remain internal steps inside one complete workflow.

## Tool-First Rule

Use `environment_index_analysis(...)` for execution.

## Required Inputs

- `env_meta`: path to `Env_meta_table.txt`. This is typically a UTF-16LE tab-delimited file with environment metadata, for example:

```text
env_code	lat	lon	PlantingDate	TrialYear	env_note
Jilin	43.88	125.35	2014-05-09	2014	14JL
Liaoning	41.48	123.38	2014-05-11	2014	14LN
Beijing	40.13	116.13	2014-05-13	2014	14BJ
Hebei	38.85	115.48	2014-06-11	2014	14HB
Henan	35.31	113.85	2014-06-12	2014	14HN
```

- `trait_records`: path to `Trait_records.txt`. This should be a tab-delimited table with line code, environment code, and the trait column to analyze, for example:

```text
line_code	env_code	PH
MG_49	Jilin	234.6
MG_50	Jilin	217.2
MG_51	Jilin	198.5
MG_52	Jilin	209.8
```

- `env_paras`: path to `5Envs_envParas_DAP150.txt` or a compatible tab-delimited table. The `Date` column must use strict `YYYY-MM-DD` format, for example:

```text
env_code	Date	DL	GDD	dGDD	DTR	PTT	PTR	PTD1	PTD2	TSR	MMR	PR	RH	PRDTR	dPTT	PS	WS	WD	APAR	CPAR	UVA	UVB	SW	SM	TMAX	TMIN
Jilin	2014-05-09	14.554	10.548	0	35.856	153.5156	0.7247	521.8482	2.4637	3812.7836	0.4957	0	54.25	0	0	99.67	1.82	282.5	138.04	143.95	18.14	0.28	0.56	0.58	71.096	35.24
Jilin	2014-05-10	14.596	9.405	1.143	22.716	137.2754	0.6444	331.5627	1.5563	2610.1593	0.6699	0.01	64.12	4.00E-04	16.2402	99.81	1.77	211.25	68.24	103.94	8.38	0.15	0.56	0.58	68.81	46.094
Jilin	2014-05-11	14.637	7.929	1.476	15.678	116.0568	0.5417	229.4789	1.0711	1816.4217	0.7616	7.29	78.81	0.465	21.2186	99.03	2.23	169.31	47.31	121.52	6.59	0.13	0.56	0.58	65.768	50.09
```

## Optional Parameters

- `output_dir`: output root directory
- `trait_label`: output label and subdirectory name. Default: `testPH`
- `trait_column`: trait column to analyze in `Trait_records.txt`. Default: `PH`
- `searching_daps`: searched DAP range. Default: `150`
- `max_window_start`: selected downstream window start when `run_downstream=true`. Default: `13`
- `max_window_end`: selected downstream window end when `run_downstream=true`. Default: `40`
- `key_parameter`: selected downstream environmental parameter when `run_downstream=true`. Default: `PTT`
- `run_downstream`: run downstream selected-window plots, slope/intercept estimation, and LOOCV after writing `highest_EF.csv`. Default: `false`
- `env_meta_encoding`: file encoding for `Env_meta_table.txt`. Default: `UTF-16LE`

## Default Outputs

When defaults are kept, the workflow matches the active portion of `run_CERIS.R` and writes:

- `allwinds_EF_cor.csv`
- `highest_EF.csv`
- `environment_index_summary.txt`
- `testPH/` containing the pairwise-distribution and exhaustive-search outputs produced before `highest_EF.csv`

When `run_downstream=true`, `testPH/` also contains downstream files such as:

  `5Env_meanY_MSE.txt`
  `Intcp_Slope5envs.txt`
  `LbE_table5envs.txt`
  `MaxR_testPH_5Envs_0LOO.png`
  `testPH_5Env_LOO_by_Lines_PTTD13_40.png`
  `testPH_5Env_LOO_by_Lines_PTTD13_40.txt`
  `testPH_5Envs_PTTPTR_0LOO_cor.txt`
  `testPH_dist_5envs.png`
  `testPH_envMeanPara_13_40.txt`
  `testPHMean_5EnvPara.png`
  `testPH_pairwise_dis5envs.png`

## Pre-Run Validation

The tool always checks that the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool stops if `EasyGS_1` is missing
- The tool stops if `Rscript` is not available inside `EasyGS_1`
- The tool stops if the required R packages are unavailable
- The tool does not auto-install packages during workflow execution

## Parameter Collection Rules

Before calling `environment_index_analysis(...)`, collect the three required input paths unless they are already available in the conversation.

Behavior rules:

- When asking for an input file, always provide a data example together with the format description
- `Env_meta_table.txt` is expected to be tab-delimited and often UTF-16LE encoded
- `Trait_records.txt` is expected to be tab-delimited and contain `line_code`, `env_code`, and the chosen trait column
- `5Envs_envParas_DAP150.txt` is expected to be tab-delimited and use strict `YYYY-MM-DD` dates
- If the user does not specify `trait_label`, `trait_column`, `key_parameter`, window values, or `run_downstream`, use the defaults above
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output root directory
- the trait output directory
- the number of generated trait-directory files
- the top result from `highest_EF.csv` when available
- the number of rows written to `allwinds_EF_cor.csv`
