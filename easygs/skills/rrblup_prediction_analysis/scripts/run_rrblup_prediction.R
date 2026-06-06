#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(rrBLUP))

parse_args <- function(args) {
  parsed <- list()
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (!startsWith(key, "--")) {
      stop(sprintf("Unexpected argument: %s", key))
    }
    if (i == length(args)) {
      stop(sprintf("Missing value for argument: %s", key))
    }
    parsed[[substring(key, 3)]] <- args[[i + 1]]
    i <- i + 2
  }
  parsed
}

require_arg <- function(parsed, key) {
  value <- parsed[[key]]
  if (is.null(value) || identical(value, "")) {
    stop(sprintf("Missing required argument: --%s", key))
  }
  value
}

read_and_bind_csvs <- function(csv_arg, row_names = FALSE, ...) {
  files <- strsplit(csv_arg, ",", fixed = TRUE)[[1]]
  files <- trimws(files)
  files <- files[nzchar(files)]
  if (length(files) == 0) {
    stop("No CSV files were provided")
  }
  pieces <- lapply(files, function(file) {
    read.csv(file, row.names = if (row_names) 1 else NULL, check.names = FALSE, stringsAsFactors = FALSE, ...)
  })
  do.call(rbind, pieces)
}

args <- parse_args(commandArgs(trailingOnly = TRUE))

genotype_csvs <- require_arg(args, "genotype-csvs")
phenotype_csvs <- require_arg(args, "phenotype-csvs")
cv_csvs <- require_arg(args, "cv-csvs")
trait_name <- require_arg(args, "trait-name")
id_column <- require_arg(args, "id-column")
cv_column <- require_arg(args, "cv-column")
expected_folds <- as.integer(require_arg(args, "expected-folds"))
output_dir <- require_arg(args, "output-dir")
output_prefix <- require_arg(args, "output-prefix")
fold_metrics_output <- require_arg(args, "fold-metrics-output")
mean_effect_output <- require_arg(args, "mean-effect-output")
mean_intercept_output <- require_arg(args, "mean-intercept-output")

if (is.na(expected_folds) || expected_folds < 2) {
  stop("expected_folds must be an integer >= 2")
}

cat("[进度] 开始读取并合并基因型数据...\n")
G <- as.matrix(read_and_bind_csvs(genotype_csvs, row_names = TRUE))
mode(G) <- "numeric"
cat("合并后基因型数据规模:", dim(G), "\n")

cat("[进度] 开始读取并合并表型数据...\n")
phe <- read_and_bind_csvs(phenotype_csvs, row_names = TRUE)
cat("合并后表型数据规模:", nrow(phe), "样本\n")

cat("[进度] 开始读取并合并CV数据...\n")
CV <- read_and_bind_csvs(cv_csvs, row_names = FALSE)
if (!(id_column %in% colnames(CV))) {
  stop(sprintf("CV文件缺少ID列: %s", id_column))
}
if (!(cv_column %in% colnames(CV))) {
  stop(sprintf("CV文件缺少折列: %s", cv_column))
}
CV[[cv_column]] <- as.integer(CV[[cv_column]])
if (any(is.na(CV[[cv_column]]))) {
  stop(sprintf("CV列 %s 包含无法转换为整数的值", cv_column))
}

if (!(trait_name %in% colnames(phe))) {
  stop(sprintf("表型文件中不存在性状列: %s", trait_name))
}

missing_in_G <- setdiff(CV[[id_column]], rownames(G))
missing_in_phe <- setdiff(CV[[id_column]], rownames(phe))
if (length(missing_in_G) > 0) {
  stop(sprintf("以下CV样本在基因型数据中不存在: %s", paste(missing_in_G, collapse = ", ")))
}
if (length(missing_in_phe) > 0) {
  stop(sprintf("以下CV样本在表型数据中不存在: %s", paste(missing_in_phe, collapse = ", ")))
}

G <- G[CV[[id_column]], , drop = FALSE]
phe_vec <- phe[CV[[id_column]], trait_name, drop = TRUE]

if (nrow(G) != length(phe_vec) || nrow(G) != nrow(CV)) {
  stop(sprintf(
    "数据不一致: 基因型样本数=%d 表型样本数=%d CV样本数=%d",
    nrow(G),
    length(phe_vec),
    nrow(CV)
  ))
}

fold_values <- sort(unique(CV[[cv_column]]))
if (length(fold_values) != expected_folds) {
  stop(sprintf(
    "CV折数不符合预期: 预期=%d 实际=%d (folds=%s)",
    expected_folds,
    length(fold_values),
    paste(fold_values, collapse = ", ")
  ))
}

all_train_cor <- numeric(length(fold_values))
all_test_cor <- numeric(length(fold_values))
all_beta <- numeric(length(fold_values))
all_u <- NULL
fold_metrics <- data.frame(
  fold = integer(0),
  train_n = integer(0),
  test_n = integer(0),
  train_cor = numeric(0),
  test_cor = numeric(0),
  stringsAsFactors = FALSE
)

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

for (idx in seq_along(fold_values)) {
  fold <- fold_values[[idx]]
  cat(sprintf("\n[进度] 开始第 %d 折交叉验证...\n", fold))
  idx_test <- which(CV[[cv_column]] == fold)
  idx_train <- which(CV[[cv_column]] != fold)

  if (length(idx_train) < 10) stop("训练集样本不足！")
  if (length(idx_test) == 0) stop("测试集样本数为0！")

  trainG <- G[idx_train, , drop = FALSE]
  trainPhe <- phe_vec[idx_train]

  model <- mixed.solve(
    y = trainPhe,
    Z = trainG,
    X = NULL,
    SE = FALSE,
    return.Hinv = FALSE
  )

  beta <- as.numeric(model$beta)
  if (is.null(all_u)) {
    all_u <- matrix(model$u, ncol = 1)
    rownames(all_u) <- names(model$u)
  } else {
    all_u <- cbind(all_u, model$u)
  }
  all_beta[[idx]] <- beta

  train_pred <- as.numeric(trainG %*% model$u + beta)
  testG <- G[idx_test, , drop = FALSE]
  test_pred <- as.numeric(testG %*% model$u + beta)

  train_pred_df <- data.frame(
    ID = rownames(trainG),
    observed = trainPhe,
    predicted = train_pred,
    stringsAsFactors = FALSE
  )
  test_pred_df <- data.frame(
    ID = rownames(testG),
    observed = phe_vec[idx_test],
    predicted = test_pred,
    stringsAsFactors = FALSE
  )

  write.csv(
    train_pred_df,
    file = file.path(output_dir, sprintf("%s_train_pred_%d.csv", output_prefix, fold)),
    row.names = FALSE
  )
  write.csv(
    test_pred_df,
    file = file.path(output_dir, sprintf("%s_test_pred_%d.csv", output_prefix, fold)),
    row.names = FALSE
  )

  train_cor <- suppressWarnings(cor(trainPhe, train_pred))
  test_cor <- if (length(idx_test) > 1) suppressWarnings(cor(phe_vec[idx_test], test_pred)) else NA_real_
  all_train_cor[[idx]] <- train_cor
  all_test_cor[[idx]] <- test_cor

  fold_metrics <- rbind(
    fold_metrics,
    data.frame(
      fold = fold,
      train_n = length(idx_train),
      test_n = length(idx_test),
      train_cor = train_cor,
      test_cor = test_cor,
      stringsAsFactors = FALSE
    )
  )
}

mean_u <- rowMeans(all_u)
mean_beta <- mean(all_beta)

write.csv(fold_metrics, file = fold_metrics_output, row.names = FALSE)
write.csv(
  data.frame(SNP = rownames(all_u), Effect = mean_u, stringsAsFactors = FALSE),
  file = mean_effect_output,
  row.names = FALSE
)
write.csv(
  data.frame(Intercept = mean_beta, stringsAsFactors = FALSE),
  file = mean_intercept_output,
  row.names = FALSE
)

cat("\n10折交叉验证结果汇总:\n")
cat("平均训练集相关系数:", round(mean(all_train_cor, na.rm = TRUE), 4), "\n")
cat("平均测试集相关系数:", round(mean(all_test_cor, na.rm = TRUE), 4), "\n")
cat("平均效应值数量:", length(mean_u), "\n")
cat("平均截距值:", round(mean_beta, 6), "\n")
