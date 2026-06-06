#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(lme4)
  library(reshape2)
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
  required <- c("input-csv", "output-csv")
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

args <- parse_args()
input_csv <- args[["input-csv"]]
output_csv <- args[["output-csv"]]

ph <- read.csv(input_csv, header = TRUE, check.names = FALSE, stringsAsFactors = FALSE)
if (ncol(ph) < 2L) {
  stop("Input phenotype CSV must contain LINE_ID and at least one environment column.", call. = FALSE)
}
colnames(ph)[1L] <- "LINE_ID"

ph_long <- reshape2::melt(
  ph,
  id.vars = "LINE_ID",
  variable.name = "Environment",
  value.name = "Phenotype"
)
ph_long$Phenotype <- suppressWarnings(as.numeric(ph_long$Phenotype))
ph_long <- ph_long[!is.na(ph_long$Phenotype), , drop = FALSE]
if (nrow(ph_long) < 4L) {
  stop("Long-format phenotype table has fewer than 4 non-missing observations.", call. = FALSE)
}

model <- lme4::lmer(
  Phenotype ~ (1 | LINE_ID) + Environment,
  data = ph_long,
  REML = TRUE
)

blup_values <- lme4::ranef(model)$LINE_ID
colnames(blup_values) <- "BLUP_Value"
blup_values_df <- blup_values %>%
  as.data.frame() %>%
  mutate(LINE_ID = rownames(blup_values)) %>%
  dplyr::select(LINE_ID, BLUP_Value) %>%
  arrange(desc(BLUP_Value))

dir.create(dirname(output_csv), recursive = TRUE, showWarnings = FALSE)
write.csv(blup_values_df, output_csv, quote = FALSE, row.names = FALSE)
cat(sprintf("Saved %d BLUP rows to: %s\n", nrow(blup_values_df), output_csv))
