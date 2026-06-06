#!/usr/bin/env Rscript

trim_scalar <- function(value) {
  trimws(sub("^\ufeff", "", as.character(value)))
}

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
    "protlist-txt",
    "source-annotation-tsv",
    "annotation-source",
    "min-count-in-candidates",
    "p-adjust-method",
    "fdr-cutoff",
    "all-enrichment-csv-output",
    "sig-enrichment-csv-output"
  )
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

empty_result_df <- function() {
  data.frame(
    pfam = character(),
    K = integer(),
    k = integer(),
    p_hyper = numeric(),
    p_fisher = numeric(),
    FoldEnrich = numeric(),
    p = numeric(),
    p_adj = numeric(),
    negLog10p = numeric(),
    negLog10p_adj = numeric(),
    stringsAsFactors = FALSE
  )
}

safe_fisher_p <- function(k, n, K, M) {
  matrix_values <- matrix(c(k, n - k, K - k, M - K - (n - k)), nrow = 2)
  if (any(matrix_values < 0)) {
    return(NA_real_)
  }
  stats::fisher.test(matrix_values)$p.value
}

args <- parse_args()
protlist_txt <- args[["protlist-txt"]]
source_annotation_tsv <- args[["source-annotation-tsv"]]
background_protein_txt <- if (!is.null(args[["background-protein-txt"]])) args[["background-protein-txt"]] else ""
annotation_source <- trim_scalar(args[["annotation-source"]])
min_count_in_candidates <- as.integer(args[["min-count-in-candidates"]])
p_adjust_method <- trim_scalar(args[["p-adjust-method"]])
fdr_cutoff <- as.numeric(args[["fdr-cutoff"]])
all_enrichment_csv_output <- args[["all-enrichment-csv-output"]]
sig_enrichment_csv_output <- args[["sig-enrichment-csv-output"]]

if (annotation_source == "") {
  stop("annotation-source must not be empty.", call. = FALSE)
}
if (is.na(min_count_in_candidates) || min_count_in_candidates < 1L) {
  stop("min-count-in-candidates must be >= 1.", call. = FALSE)
}
if (is.na(fdr_cutoff) || fdr_cutoff < 0 || fdr_cutoff > 1) {
  stop("fdr-cutoff must be between 0 and 1.", call. = FALSE)
}

dir.create(dirname(all_enrichment_csv_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(sig_enrichment_csv_output), recursive = TRUE, showWarnings = FALSE)

candidate_proteins <- trim_scalar(readLines(protlist_txt, warn = FALSE, encoding = "UTF-8"))
candidate_proteins <- unique(candidate_proteins[nzchar(candidate_proteins)])

if (!length(candidate_proteins)) {
  all_df <- empty_result_df()
  sig_df <- empty_result_df()
  utils::write.csv(all_df, all_enrichment_csv_output, row.names = FALSE, quote = TRUE)
  utils::write.csv(sig_df, sig_enrichment_csv_output, row.names = FALSE, quote = TRUE)
  cat("No candidate proteins found in protlist.txt.\n")
  quit(save = "no", status = 0)
}

ip <- utils::read.delim(
  source_annotation_tsv,
  header = FALSE,
  sep = "\t",
  quote = "",
  comment.char = "",
  fill = TRUE,
  stringsAsFactors = FALSE,
  check.names = FALSE
)

if (ncol(ip) < 5L) {
  stop("source-annotation-tsv must contain at least 5 tab-separated columns.", call. = FALSE)
}

protein_ids <- trim_scalar(ip[[1L]])
pfam_values <- trim_scalar(ip[[5L]])

keep <- nzchar(protein_ids) & nzchar(pfam_values) & pfam_values != "-"

protein_pfam <- data.frame(
  gene = protein_ids[keep],
  pfam = pfam_values[keep],
  stringsAsFactors = FALSE
)
protein_pfam <- unique(protein_pfam)

if (nzchar(background_protein_txt)) {
  background <- trim_scalar(readLines(background_protein_txt, warn = FALSE, encoding = "UTF-8"))
  background <- unique(background[nzchar(background)])
} else {
  background <- unique(protein_pfam$gene)
}

protein_pfam_bg <- protein_pfam[protein_pfam$gene %in% background, , drop = FALSE]
M <- length(unique(background))
cands_in_bg <- intersect(candidate_proteins, background)
n <- length(unique(cands_in_bg))

if (M == 0L || n == 0L || nrow(protein_pfam_bg) == 0L) {
  all_df <- empty_result_df()
  sig_df <- empty_result_df()
  utils::write.csv(all_df, all_enrichment_csv_output, row.names = FALSE, quote = TRUE)
  utils::write.csv(sig_df, sig_enrichment_csv_output, row.names = FALSE, quote = TRUE)
  cat(sprintf("No analyzable proteins after filtering. Background=%d, candidates=%d.\n", M, n))
  quit(save = "no", status = 0)
}

K_df <- stats::aggregate(gene ~ pfam, protein_pfam_bg, function(x) length(unique(x)))
names(K_df)[names(K_df) == "gene"] <- "K"
k_source <- protein_pfam_bg[protein_pfam_bg$gene %in% cands_in_bg, , drop = FALSE]
k_df <- if (nrow(k_source) > 0L) {
  stats::aggregate(gene ~ pfam, k_source, function(x) length(unique(x)))
} else {
  data.frame(pfam = character(), gene = integer(), stringsAsFactors = FALSE)
}
if (nrow(k_df) > 0L) {
  names(k_df)[names(k_df) == "gene"] <- "k"
}

pfam_stats <- merge(K_df, k_df, by = "pfam", all.x = TRUE, sort = FALSE)
pfam_stats$k[is.na(pfam_stats$k)] <- 0L
pfam_stats <- pfam_stats[pfam_stats$k >= 1L, , drop = FALSE]

if (!nrow(pfam_stats)) {
  all_df <- empty_result_df()
  sig_df <- empty_result_df()
  utils::write.csv(all_df, all_enrichment_csv_output, row.names = FALSE, quote = TRUE)
  utils::write.csv(sig_df, sig_enrichment_csv_output, row.names = FALSE, quote = TRUE)
  cat("No domains were observed in candidate proteins.\n")
  quit(save = "no", status = 0)
}

pfam_stats$p_hyper <- stats::phyper(pfam_stats$k - 1L, pfam_stats$K, M - pfam_stats$K, n, lower.tail = FALSE)
pfam_stats$p_fisher <- mapply(safe_fisher_p, pfam_stats$k, MoreArgs = list(n = n, M = M), K = pfam_stats$K)
pfam_stats$FoldEnrich <- (pfam_stats$k / n) / (pfam_stats$K / M)
pfam_stats$p <- pfam_stats$p_hyper
pfam_stats$p_adj <- stats::p.adjust(pfam_stats$p, method = p_adjust_method)
pfam_stats$negLog10p <- -log10(pfam_stats$p)
pfam_stats$negLog10p_adj <- -log10(pfam_stats$p_adj)
pfam_stats <- pfam_stats[order(pfam_stats$p_adj, pfam_stats$p, decreasing = FALSE), , drop = FALSE]

sig <- pfam_stats[pfam_stats$p_adj <= fdr_cutoff & pfam_stats$k >= min_count_in_candidates, , drop = FALSE]

utils::write.csv(pfam_stats, all_enrichment_csv_output, row.names = FALSE, quote = TRUE)
utils::write.csv(sig, sig_enrichment_csv_output, row.names = FALSE, quote = TRUE)

cat(sprintf("Background proteins (M) = %d\n", M))
cat(sprintf("Candidates in background (n) = %d\n", n))
cat(sprintf("All enrichment rows = %d\n", nrow(pfam_stats)))
cat(sprintf("Significant enrichment rows = %d\n", nrow(sig)))
