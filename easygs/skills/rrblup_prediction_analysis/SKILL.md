---
name: rrblup_prediction_analysis
description: Run rrBLUP genomic prediction from explicit user-provided genotype, phenotype, and CV CSV files using the built-in rrblup_prediction_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# rrBLUP Genomic Prediction Skill

Run rrBLUP-based genomic prediction using the built-in `rrblup_prediction_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate one or more user-provided genotype CSV files
2. validate one or more user-provided phenotype CSV files
3. validate one or more user-provided CV-assignment CSV files
4. merge each input group in order
5. reorder genotype and phenotype rows by the CV file
6. fit rrBLUP across folds and export per-fold predictions
7. export mean marker effects, mean intercept, fold metrics, and a compact summary

Do not split this into separate public tools for matrix merging, fold creation, or rrBLUP-only model fitting. Those stay internal inside one complete workflow.

## Tool-First Rule

Use `rrblup_prediction_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads one or more genotype CSV files
2. reads one or more phenotype CSV files
3. reads one or more CV CSV files
4. merges each file group by row binding
5. aligns genotype and phenotype rows to the CV file order
6. runs rrBLUP 10-fold-style prediction with `mixed.solve()`
7. writes train/test prediction CSV files for each fold
8. writes `<output_prefix>_fold_metrics.csv`
9. writes `<output_prefix>_mean_effect.csv`
10. writes `<output_prefix>_mean_intercept.csv`
11. writes a compact summary text file

## Required Inputs

- `genotype_csvs`: one or more user-provided genotype CSV files. Example rows:

```text
ID,ZMPV01aSNPC01P000049527,ZMPV01aSNPC01P000172921,ZMPV01aSNPC01P000277229,ZMPV01aSNPC01P000277887
04K5672,0,0,0,0
04K5686,0,0,0,0
04K5702,2,2,0,0
05W002,2,0,2,2
```

- `phenotype_csvs`: one or more user-provided phenotype CSV files. Example rows:

```text
ID,Plantheight,Earheight,Earleafwidth,Earleaflength
04K5672,-1.3060108678835813,-0.33363640998930855,-1.9886244144669243,-0.4752590274927541
04K5686,-0.9900750166857649,-1.337881288370562,-2.2065216365462392,-1.010483071516264
04K5702,-0.6050885223173679,-0.8208113705636478,-1.3213004287428514,-0.03339737340988433
05W002,-0.11894641928673357,-0.004839335792526001,0.15557827597605214,-0.3097918084832566
```

- `cv_csvs`: one or more user-provided cross-validation assignment CSV files. Example rows:

```text
ID,cv_1
04K5672,1
04K5686,9
04K5702,1
05W002,4
```

- `trait_name`: trait column name to predict, for example `X100grainweight`

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `output_prefix`: output filename prefix. Default: `rrBLUP_<trait_name>`
- `id_column`: sample-ID column name. Default: `ID`
- `cv_column`: CV fold column name. Default: `cv_1`
- `expected_folds`: expected number of folds. Default: `10`

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/<output_prefix>_train_pred_1.csv` ... `<output_prefix>_train_pred_10.csv`
- `<output_dir>/<output_prefix>_test_pred_1.csv` ... `<output_prefix>_test_pred_10.csv`
- `<output_dir>/<output_prefix>_fold_metrics.csv`
- `<output_dir>/<output_prefix>_mean_effect.csv`
- `<output_dir>/<output_prefix>_mean_intercept.csv`
- `<output_dir>/<output_prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_3`

Behavior rules:

- The tool will stop automatically if the `EasyGS_3` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_3`
- The pipeline will stop automatically if the required R package is unavailable:
  `rrBLUP`
- All required local files must be explicitly supplied by the user
- Do not invent file paths
- Do not hide required local files inside the script

## Parameter Collection Rules

Before calling `rrblup_prediction_analysis(...)`, collect the required genotype CSV list, phenotype CSV list, CV CSV list, and `trait_name` unless they are already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- All required files must be explicitly supplied by the user and must not be hidden in the script

## Result Interpretation

After a successful run, the summary should highlight:

- the trait used for prediction
- the average train and test correlations across folds
- the fold metrics CSV
- the mean effect and mean intercept outputs
