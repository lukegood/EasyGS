#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(Fast3VmrMLM)
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
    "bfile-prefix",
    "phenotype-csv",
    "structure-csv",
    "output-prefix",
    "trait-count",
    "n-en",
    "phenotype-id-column",
    "structure-id-column",
    "geno-type",
    "svrad",
    "svpal",
    "svmlod",
    "n-threads",
    "draw-plot",
    "plot-format"
  )
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

parse_bool <- function(value) {
  normalized <- toupper(trimws(as.character(value)))
  normalized %in% c("TRUE", "T", "1", "YES", "Y")
}

args <- parse_args()
bfile_prefix <- args[["bfile-prefix"]]
phenotype_csv <- args[["phenotype-csv"]]
structure_csv <- args[["structure-csv"]]
output_prefix <- args[["output-prefix"]]
trait_count <- as.integer(args[["trait-count"]])
n_en_values <- as.integer(strsplit(args[["n-en"]], ",", fixed = TRUE)[[1L]])
phenotype_id_column <- trimws(args[["phenotype-id-column"]])
structure_id_column <- trimws(args[["structure-id-column"]])
geno_type <- trimws(args[["geno-type"]])
svrad <- as.numeric(args[["svrad"]])
svpal <- as.numeric(args[["svpal"]])
svmlod <- as.numeric(args[["svmlod"]])
n_threads <- as.integer(args[["n-threads"]])
draw_plot <- parse_bool(args[["draw-plot"]])
plot_format <- trimws(args[["plot-format"]])

if (is.na(trait_count) || trait_count < 1L) {
  stop("trait_count must be a positive integer.", call. = FALSE)
}
if (length(n_en_values) != trait_count || any(is.na(n_en_values)) || any(n_en_values < 1L)) {
  stop("n_en must be a comma-separated list of positive integers whose length matches trait_count.", call. = FALSE)
}

phe_header <- colnames(read.csv(phenotype_csv, header = TRUE, check.names = FALSE, nrows = 5L))
ps_header <- colnames(read.csv(structure_csv, header = TRUE, check.names = FALSE, nrows = 5L))
if (length(phe_header) < 2L || phe_header[[1L]] != phenotype_id_column) {
  stop(sprintf("Phenotype CSV first column must be %s.", phenotype_id_column), call. = FALSE)
}
if (length(ps_header) < 2L || ps_header[[1L]] != structure_id_column) {
  stop(sprintf("Structure CSV first column must be %s.", structure_id_column), call. = FALSE)
}

dir.create(dirname(output_prefix), recursive = TRUE, showWarnings = FALSE)

Fast3VmrMLM::Fast3VmrMLM_MEJA(
  fileGen = bfile_prefix,
  filePhe = phenotype_csv,
  fileKin = NULL,
  filePS = structure_csv,
  fileOut = output_prefix,
  genoType = geno_type,
  trait = trait_count,
  n_en = n_en_values,
  svrad = svrad,
  svpal = svpal,
  svmlod = svmlod,
  nThreads = n_threads,
  DrawPlot = draw_plot,
  Plotformat = plot_format
)

cat(sprintf("QEI detection completed with output prefix: %s\n", output_prefix))
