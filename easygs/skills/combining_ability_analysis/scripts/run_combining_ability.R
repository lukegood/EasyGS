#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(sommer)
  library(lme4)
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
    "female-gca-output",
    "male-gca-output",
    "sca-output",
    "hybrid-column",
    "female-column",
    "male-column",
    "phenotype-column"
  )
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

extract_effect_df <- function(mod, effect_name, id_column, value_column) {
  available <- names(mod$U)
  candidates <- c(effect_name, paste0("u:", effect_name))
  match_name <- candidates[candidates %in% available][1L]
  if (is.na(match_name) || is.null(match_name)) {
    grep_match <- grep(effect_name, available, fixed = TRUE, value = TRUE)
    if (length(grep_match) == 0L) {
      stop(sprintf("Could not find random-effect block for %s. Available blocks: %s", effect_name, paste(available, collapse = ", ")), call. = FALSE)
    }
    match_name <- grep_match[[1L]]
  }

  effect_block <- mod$U[[match_name]]
  if (is.list(effect_block) && !is.data.frame(effect_block) && !is.matrix(effect_block)) {
    sub_names <- names(effect_block)
    if (length(sub_names) > 0L) {
      if ("Phenotype" %in% sub_names) {
        effect_block <- effect_block[["Phenotype"]]
      } else {
        effect_block <- effect_block[[sub_names[[1L]]]]
      }
    }
  }

  effect_df <- as.data.frame(effect_block, stringsAsFactors = FALSE)
  if (ncol(effect_df) == 0L) {
    stop(sprintf("Random-effect block for %s is empty.", effect_name), call. = FALSE)
  }
  row_id <- rownames(effect_df)
  if (is.null(row_id) || !length(row_id)) {
    row_id <- seq_len(nrow(effect_df))
  }
  prefix_pattern <- paste0("^", effect_name)
  row_id <- sub(prefix_pattern, "", row_id)
  value <- suppressWarnings(as.numeric(effect_df[[1L]]))
  out <- data.frame(row_id, value, stringsAsFactors = FALSE, check.names = FALSE)
  colnames(out) <- c(id_column, value_column)
  out
}

args <- parse_args()
input_csv <- args[["input-csv"]]
female_gca_output <- args[["female-gca-output"]]
male_gca_output <- args[["male-gca-output"]]
sca_output <- args[["sca-output"]]
hybrid_column <- args[["hybrid-column"]]
female_column <- args[["female-column"]]
male_column <- args[["male-column"]]
phenotype_column <- args[["phenotype-column"]]

dat <- read.csv(input_csv, header = TRUE, check.names = FALSE, stringsAsFactors = FALSE)
required_cols <- c(hybrid_column, female_column, male_column, phenotype_column)
missing_cols <- setdiff(required_cols, colnames(dat))
if (length(missing_cols) > 0L) {
  stop(sprintf("Input CSV is missing required columns: %s", paste(missing_cols, collapse = ", ")), call. = FALSE)
}

dat[[female_column]] <- as.factor(dat[[female_column]])
dat[[male_column]] <- as.factor(dat[[male_column]])
dat[[hybrid_column]] <- as.factor(dat[[hybrid_column]])
dat[[phenotype_column]] <- suppressWarnings(as.numeric(dat[[phenotype_column]]))
dat <- dat[!is.na(dat[[phenotype_column]]), , drop = FALSE]
if (nrow(dat) < 4L) {
  stop("Input phenotype table has fewer than 4 non-missing rows.", call. = FALSE)
}

model_formula <- stats::as.formula(sprintf("%s ~ 1", phenotype_column))
random_formula <- stats::as.formula(
  sprintf("~ %s + %s + %s", female_column, male_column, hybrid_column)
)
mod <- sommer::mmer(
  fixed = model_formula,
  random = random_formula,
  data = dat
)

female_gca <- extract_effect_df(mod, female_column, female_column, "GCA")
male_gca <- extract_effect_df(mod, male_column, male_column, "GCA")
sca_df <- extract_effect_df(mod, hybrid_column, hybrid_column, "SCA")

female_gca <- female_gca[order(-female_gca$GCA), , drop = FALSE]
male_gca <- male_gca[order(-male_gca$GCA), , drop = FALSE]
sca_df <- sca_df[order(-sca_df$SCA), , drop = FALSE]

dir.create(dirname(female_gca_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(male_gca_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(sca_output), recursive = TRUE, showWarnings = FALSE)

write.csv(female_gca, female_gca_output, row.names = FALSE, quote = FALSE)
write.csv(male_gca, male_gca_output, row.names = FALSE, quote = FALSE)
write.csv(sca_df, sca_output, row.names = FALSE, quote = FALSE)

cat(sprintf("Saved %d female GCA rows to: %s\n", nrow(female_gca), female_gca_output))
cat(sprintf("Saved %d male GCA rows to: %s\n", nrow(male_gca), male_gca_output))
cat(sprintf("Saved %d SCA rows to: %s\n", nrow(sca_df), sca_output))
