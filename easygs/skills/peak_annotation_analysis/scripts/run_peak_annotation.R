#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ChIPseeker)
  library(GenomicFeatures)
  library(ggplot2)
  library(txdbmaker)
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
  required <- c("gff3", "bed", "output-tsv", "output-png", "tss-upstream", "tss-downstream")
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

args <- parse_args()
gff3_path <- args[["gff3"]]
bed_path <- args[["bed"]]
output_tsv <- args[["output-tsv"]]
output_png <- args[["output-png"]]
tss_upstream <- as.integer(args[["tss-upstream"]])
tss_downstream <- as.integer(args[["tss-downstream"]])

if (is.na(tss_upstream) || tss_upstream < 0L) {
  stop("tss-upstream must be a non-negative integer.", call. = FALSE)
}
if (is.na(tss_downstream) || tss_downstream < 0L) {
  stop("tss-downstream must be a non-negative integer.", call. = FALSE)
}

dir.create(dirname(output_tsv), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(output_png), recursive = TRUE, showWarnings = FALSE)

txdb <- txdbmaker::makeTxDbFromGFF(gff3_path)
peaks <- ChIPseeker::readPeakFile(bed_path)
annot <- ChIPseeker::annotatePeak(
  peaks,
  tssRegion = c(-tss_upstream, tss_downstream),
  TxDb = txdb
)
peak_anno_df <- as.data.frame(annot)

write.table(
  peak_anno_df,
  file = output_tsv,
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)

png(output_png, width = 8, height = 6, units = "in", res = 300)
plot_obj <- ChIPseeker::plotAnnoPie(annot)
print(plot_obj)
dev.off()

cat(sprintf("Saved %d annotation rows to: %s\n", nrow(peak_anno_df), output_tsv))
cat(sprintf("Saved annotation plot to: %s\n", output_png))
