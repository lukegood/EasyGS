#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(clusterProfiler)
  library(dplyr)
  library(ggplot2)
})

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  parsed <- list()
  index <- 1L
  while (index <= length(args)) {
    key <- args[[index]]
    if (!startsWith(key, "--") || index == length(args)) {
      stop(sprintf("Invalid argument near: %s", key), call. = FALSE)
    }
    parsed[[substring(key, 3L)]] <- args[[index + 1L]]
    index <- index + 2L
  }
  required <- c(
    "genelist-txt", "gene2ko-tsv", "kegg-annotation-tsv", "all-output",
    "significant-output", "mapped-output", "plot-output"
  )
  missing <- required[!vapply(required, function(name) {
    !is.null(parsed[[name]]) && nzchar(parsed[[name]])
  }, logical(1))]
  if (length(missing)) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

trim_text <- function(values) {
  trimws(sub("^\ufeff", "", as.character(values)))
}

read_gene_list <- function(path) {
  values <- trim_text(readLines(path, warn = FALSE, encoding = "UTF-8"))
  values <- sub("\t.*$", "", values)
  unique(values[nzchar(values)])
}

empty_enrichment <- function() {
  data.frame(
    ID = character(), Description = character(), GeneRatio = character(),
    BgRatio = character(), RichFactor = numeric(), FoldEnrichment = numeric(),
    zScore = numeric(), pvalue = numeric(), p.adjust = numeric(), qvalue = numeric(),
    geneID = character(), Count = integer(), stringsAsFactors = FALSE
  )
}

write_tsv <- function(data, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write.table(data, path, sep = "\t", quote = FALSE, row.names = FALSE, na = "")
}

write_empty_plot <- function(path, message) {
  plot_data <- data.frame(x = 1, y = 1)
  plot_object <- ggplot(plot_data, aes(x, y)) +
    annotate("text", x = 1, y = 1.15, label = "KEGG Pathway Enrichment", size = 6,
             fontface = "bold") +
    annotate("text", x = 1, y = 0.9, label = message, size = 4.5) +
    xlim(0.5, 1.5) + ylim(0.5, 1.5) + theme_void()
  ggsave(path, plot_object, width = 8, height = 6, dpi = 300, device = "png")
}

args <- parse_args()
genes <- read_gene_list(args[["genelist-txt"]])
if (!length(genes)) {
  stop(sprintf("Gene list TXT is empty: %s", args[["genelist-txt"]]), call. = FALSE)
}

gene2ko <- read.delim(
  args[["gene2ko-tsv"]], stringsAsFactors = FALSE, check.names = FALSE,
  colClasses = "character"
)
annotation <- read.delim(
  args[["kegg-annotation-tsv"]], stringsAsFactors = FALSE, check.names = FALSE,
  colClasses = "character"
)
names(gene2ko) <- trim_text(names(gene2ko))
names(annotation) <- trim_text(names(annotation))

required_gene2ko <- c("locusName", "KO")
required_annotation <- c("KO", "Pathway_ID", "Pathway_Name")
if (!all(required_gene2ko %in% names(gene2ko))) {
  stop("gene2ko TSV must contain locusName and KO columns.", call. = FALSE)
}
if (!all(required_annotation %in% names(annotation))) {
  stop("KEGG annotation TSV must contain KO, Pathway_ID, and Pathway_Name columns.", call. = FALSE)
}

gene2ko <- gene2ko |>
  transmute(locusName = trim_text(locusName), KO = trim_text(KO)) |>
  filter(locusName != "", KO != "") |>
  distinct()
annotation_terms <- annotation |>
  transmute(
    KO = trim_text(KO),
    Pathway_ID = trim_text(Pathway_ID),
    Pathway_Name = trim_text(Pathway_Name)
  ) |>
  filter(KO != "", Pathway_ID != "", Pathway_Name != "") |>
  distinct()

term2gene <- gene2ko |>
  inner_join(annotation_terms, by = "KO", relationship = "many-to-many") |>
  transmute(term = Pathway_ID, gene = locusName) |>
  distinct()
term2name <- annotation_terms |>
  transmute(term = Pathway_ID, name = Pathway_Name) |>
  distinct()

background_genes <- unique(gene2ko$locusName)
mapped_genes <- intersect(genes, background_genes)
pathway_mapped_genes <- intersect(mapped_genes, unique(term2gene$gene))

all_results <- empty_enrichment()
status_message <- "No genes mapped to KEGG pathways."
if (length(pathway_mapped_genes) && nrow(term2gene)) {
  enrichment <- suppressMessages(enricher(
    gene = mapped_genes,
    universe = background_genes,
    TERM2GENE = term2gene,
    TERM2NAME = term2name,
    pvalueCutoff = 1,
    qvalueCutoff = 1,
    pAdjustMethod = "BH",
    minGSSize = 5,
    maxGSSize = 500
  ))
  if (!is.null(enrichment)) {
    result_frame <- as.data.frame(enrichment)
    if (nrow(result_frame)) {
      all_results <- result_frame
      status_message <- "ok"
    } else {
      status_message <- "No KEGG pathways passed the gene-set size filters."
    }
  }
}

significant_results <- all_results[0, , drop = FALSE]
if (nrow(all_results)) {
  keep <- !is.na(all_results$pvalue) & all_results$pvalue < 0.1
  if ("qvalue" %in% names(all_results)) {
    keep <- keep & !is.na(all_results$qvalue) & all_results$qvalue < 0.2
  }
  significant_results <- all_results[keep, , drop = FALSE]
}

write_tsv(all_results, args[["all-output"]])
write_tsv(significant_results, args[["significant-output"]])
dir.create(dirname(args[["mapped-output"]]), recursive = TRUE, showWarnings = FALSE)
write.table(
  mapped_genes, args[["mapped-output"]], quote = FALSE, row.names = FALSE,
  col.names = FALSE
)

dir.create(dirname(args[["plot-output"]]), recursive = TRUE, showWarnings = FALSE)
if (nrow(all_results)) {
  plot_data <- all_results |>
    arrange(pvalue) |>
    slice_head(n = 20)
  plot_object <- ggplot(
    plot_data,
    aes(x = reorder(Description, -Count), y = Count, fill = -log10(pvalue))
  ) +
    geom_col() +
    geom_point(aes(size = Count), shape = 21, color = "black", fill = "white", stroke = 1) +
    scale_size_continuous(name = "Gene Count", range = c(2, 6)) +
    scale_fill_gradient(low = "lightblue", high = "darkblue", name = "-log10(p-value)") +
    labs(x = NULL, y = NULL, title = "KEGG Pathway Enrichment") +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 20, face = "bold", hjust = 0.5),
      panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
      axis.text.x = element_blank(), axis.text.y = element_text(color = "black", size = 12),
      legend.title = element_text(face = "bold", size = 12),
      legend.text = element_text(size = 10),
      panel.background = element_rect(fill = "white", color = "white"),
      plot.background = element_rect(fill = "white", color = "white")
    ) +
    coord_flip()
  ggsave(
    args[["plot-output"]], plot_object, width = 8,
    height = max(6, 0.45 * nrow(plot_data)), dpi = 300, device = "png"
  )
} else {
  write_empty_plot(args[["plot-output"]], status_message)
}

cat(sprintf("Input genes: %d\n", length(genes)))
cat(sprintf("Gene-to-KO mapped genes: %d\n", length(mapped_genes)))
cat(sprintf("KEGG pathway mapped genes: %d\n", length(pathway_mapped_genes)))
cat(sprintf("All KEGG pathways: %d\n", nrow(all_results)))
cat(sprintf("Significant KEGG pathways (p < 0.1 and q < 0.2): %d\n", nrow(significant_results)))
