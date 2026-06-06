#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(tidyr)
  library(dplyr)
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
  required <- c("input-csv", "long-output", "slope-output", "trait-label")
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

args <- parse_args()
input_csv <- args[["input-csv"]]
long_output <- args[["long-output"]]
slope_output <- args[["slope-output"]]
trait_label <- args[["trait-label"]]

da <- read.csv(input_csv, header = TRUE, check.names = FALSE, stringsAsFactors = FALSE)
if (ncol(da) < 2L) {
  stop("Input phenotype CSV must contain LINE_ID and at least one environment column.", call. = FALSE)
}
colnames(da)[1L] <- "LINE_ID"

f2 <- tidyr::pivot_longer(
  data = da,
  cols = -LINE_ID,
  names_to = "location",
  values_to = trait_label
)
colnames(f2)[1L] <- "LINE"
f2[[trait_label]] <- suppressWarnings(as.numeric(f2[[trait_label]]))
f2 <- f2[!is.na(f2[[trait_label]]), , drop = FALSE]
if (nrow(f2) < 4L) {
  stop("Long-format phenotype table has fewer than 4 non-missing observations.", call. = FALSE)
}

dir.create(dirname(long_output), recursive = TRUE, showWarnings = FALSE)
write.csv(f2, long_output, row.names = FALSE, quote = FALSE)

f2$LINE <- as.factor(f2$LINE)
f2$location <- as.factor(f2$location)

env_index_df <- f2 %>%
  group_by(location) %>%
  summarise(env_index = mean(.data[[trait_label]], na.rm = TRUE), .groups = "drop")

f2_idx <- f2 %>%
  left_join(env_index_df, by = "location")

line_levels <- levels(f2_idx$LINE)
result_rows <- lapply(line_levels, function(line_name) {
  sub_df <- f2_idx %>%
    filter(LINE == line_name) %>%
    select(all_of(trait_label), env_index)

  sub_df[[trait_label]] <- suppressWarnings(as.numeric(sub_df[[trait_label]]))
  sub_df$env_index <- suppressWarnings(as.numeric(sub_df$env_index))
  sub_df <- sub_df[stats::complete.cases(sub_df), , drop = FALSE]

  intercept <- NA_real_
  slope <- NA_real_
  if (nrow(sub_df) >= 2L && length(unique(sub_df$env_index)) >= 2L) {
    fit <- tryCatch(
      stats::lm(stats::as.formula(sprintf("`%s` ~ env_index", trait_label)), data = sub_df),
      error = function(e) NULL
    )
    if (!is.null(fit)) {
      coeffs <- stats::coef(fit)
      intercept <- suppressWarnings(as.numeric(coeffs[[1L]]))
      slope <- suppressWarnings(as.numeric(coeffs[["env_index"]]))
    }
  }

  data.frame(
    LINE = as.character(line_name),
    intercept = intercept,
    slope = slope,
    stringsAsFactors = FALSE
  )
})

clean_df <- dplyr::bind_rows(result_rows) %>%
  arrange(desc(slope))

dir.create(dirname(slope_output), recursive = TRUE, showWarnings = FALSE)
write.csv(clean_df, slope_output, row.names = FALSE, quote = FALSE)
cat(sprintf("Saved %d reaction-norm rows to: %s\n", nrow(clean_df), slope_output))
