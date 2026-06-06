#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(lme4)
  library(lmerTest)
})

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  parsed <- list()
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (!startsWith(key, "--")) {
      stop(sprintf("Unexpected argument: %s", key), call. = FALSE)
    }
    if (i == length(args)) {
      stop(sprintf("Missing value for argument: %s", key), call. = FALSE)
    }
    parsed[[substring(key, 3L)]] <- args[[i + 1L]]
    i <- i + 2L
  }
  required <- c(
    "input-csv",
    "output-csv",
    "genotype-column",
    "environment-column",
    "phenotype-column"
  )
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

component_label <- function(group_name) {
  if (identical(group_name, "genotype")) {
    return("G (Genotype)")
  }
  if (identical(group_name, "environment")) {
    return("E (Environment)")
  }
  if (identical(group_name, "Residual")) {
    return("Residual (incl. G×E)")
  }
  return(group_name)
}

args <- parse_args()
input_csv <- args[["input-csv"]]
output_csv <- args[["output-csv"]]
genotype_column <- args[["genotype-column"]]
environment_column <- args[["environment-column"]]
phenotype_column <- args[["phenotype-column"]]

dat <- read.csv(input_csv, header = TRUE, check.names = FALSE, stringsAsFactors = FALSE)
required_cols <- c(genotype_column, environment_column, phenotype_column)
missing_cols <- setdiff(required_cols, colnames(dat))
if (length(missing_cols) > 0L) {
  stop(sprintf("Input CSV is missing required columns: %s", paste(missing_cols, collapse = ", ")), call. = FALSE)
}

dat <- dat[, required_cols, drop = FALSE]
colnames(dat) <- c("genotype", "environment", "phenotype")
dat$genotype <- as.factor(dat$genotype)
dat$environment <- as.factor(dat$environment)
dat$phenotype <- suppressWarnings(as.numeric(dat$phenotype))
dat <- dat[!is.na(dat$phenotype), , drop = FALSE]

if (nrow(dat) < 4L) {
  stop("Input phenotype table has fewer than 4 non-missing rows.", call. = FALSE)
}
if (nlevels(dat$genotype) < 2L) {
  stop("At least 2 genotype levels are required.", call. = FALSE)
}
if (nlevels(dat$environment) < 2L) {
  stop("At least 2 environment levels are required.", call. = FALSE)
}

model_genetic <- lme4::lmer(
  phenotype ~ (1 | genotype) + (1 | environment),
  data = dat,
  REML = TRUE
)

vc <- as.data.frame(lme4::VarCorr(model_genetic), stringsAsFactors = FALSE)
vc <- vc[, c("grp", "vcov"), drop = FALSE]
vc <- vc[vc$grp %in% c("genotype", "environment", "Residual"), , drop = FALSE]
vc$grp <- factor(vc$grp, levels = c("genotype", "environment", "Residual"))
vc <- vc[order(vc$grp), , drop = FALSE]

total_var <- sum(vc$vcov)
if (!is.finite(total_var) || total_var <= 0) {
  stop("Total variance is not positive; cannot compute percentages.", call. = FALSE)
}

result <- data.frame(
  component = vapply(as.character(vc$grp), component_label, character(1)),
  vcov = vc$vcov,
  percent = vc$vcov / total_var * 100,
  stringsAsFactors = FALSE,
  check.names = FALSE
)

dir.create(dirname(output_csv), recursive = TRUE, showWarnings = FALSE)
write.csv(result, output_csv, row.names = FALSE, quote = FALSE)
print(result)

