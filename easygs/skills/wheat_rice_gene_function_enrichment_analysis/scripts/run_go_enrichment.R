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
    "genelist-txt", "gene2go-tsv", "go-term-tsv", "all-output",
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
    geneID = character(), Count = integer(), ONTOLOGY = character(),
    stringsAsFactors = FALSE
  )
}

write_tsv <- function(data, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  write.table(data, path, sep = "\t", quote = FALSE, row.names = FALSE, na = "")
}

write_empty_plot <- function(path, message) {
  plot_data <- data.frame(x = 1, y = 1)
  plot_object <- ggplot(plot_data, aes(x, y)) +
    annotate("text", x = 1, y = 1.15, label = "GO Enrichment", size = 6,
             fontface = "bold") +
    annotate("text", x = 1, y = 0.9, label = message, size = 4.5) +
    xlim(0.5, 1.5) + ylim(0.5, 1.5) + theme_void()
  ggsave(path, plot_object, width = 12, height = 5, dpi = 300)
}

args <- parse_args()
genes <- read_gene_list(args[["genelist-txt"]])
if (!length(genes)) {
  stop(sprintf("Gene list TXT is empty: %s", args[["genelist-txt"]]), call. = FALSE)
}

gene2go <- read.delim(
  args[["gene2go-tsv"]], stringsAsFactors = FALSE, check.names = FALSE,
  colClasses = "character"
)
go_terms <- read.delim(
  args[["go-term-tsv"]], stringsAsFactors = FALSE, check.names = FALSE,
  colClasses = "character"
)
names(gene2go) <- trim_text(names(gene2go))
names(go_terms) <- trim_text(names(go_terms))

if (!all(c("locusName", "GO") %in% names(gene2go))) {
  stop("gene2go TSV must contain locusName and GO columns.", call. = FALSE)
}
if (!all(c("GOID", "TERM", "ONTOLOGY") %in% names(go_terms))) {
  stop("GO term TSV must contain GOID, TERM, and ONTOLOGY columns.", call. = FALSE)
}

gene2go <- gene2go |>
  transmute(locusName = trim_text(locusName), GO = trim_text(GO)) |>
  filter(locusName != "", GO != "") |>
  distinct()
go_terms <- go_terms |>
  transmute(
    GOID = trim_text(GOID), TERM = trim_text(TERM), ONTOLOGY = trim_text(ONTOLOGY)
  ) |>
  filter(GOID != "", TERM != "", ONTOLOGY != "") |>
  distinct(GOID, .keep_all = TRUE)

term2gene <- gene2go |>
  inner_join(go_terms, by = c("GO" = "GOID")) |>
  transmute(term = GO, gene = locusName) |>
  distinct()
term2name <- go_terms |>
  transmute(term = GOID, name = TERM) |>
  distinct()

background_genes <- unique(gene2go$locusName)
mapped_genes <- intersect(genes, background_genes)
term_mapped_genes <- intersect(mapped_genes, unique(term2gene$gene))

all_results <- empty_enrichment()
status_message <- "No genes mapped to GO terms."
if (length(term_mapped_genes) && nrow(term2gene)) {
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
      all_results <- result_frame |>
        left_join(go_terms |> select(GOID, ONTOLOGY), by = c("ID" = "GOID")) |>
        arrange(p.adjust)
      status_message <- "ok"
    } else {
      status_message <- "No GO terms passed the gene-set size filters."
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
  plot_object <- ggplot(plot_data, aes(x = reorder(Description, -Count), y = Count)) +
    geom_point(aes(size = Count, fill = -log10(pvalue)), shape = 21, stroke = 1) +
    scale_size_continuous(name = "Gene Count", range = c(2, 6)) +
    scale_fill_gradient(low = "lightblue", high = "darkblue", name = "-log10(p-value)") +
    labs(x = NULL, y = NULL, title = "GO Enrichment") +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 20, face = "bold", hjust = 0.5),
      panel.grid.major = element_blank(), panel.grid.minor = element_blank(),
      axis.text.x = element_blank(), axis.text.y = element_text(color = "black", size = 12),
      legend.title = element_text(face = "bold", size = 12),
      legend.text = element_text(size = 10), strip.text = element_text(face = "bold", size = 13),
      strip.background = element_rect(colour = "black", fill = "#2072A8"),
      strip.text.x = element_text(colour = "white"),
      panel.background = element_rect(fill = "white", colour = "white"),
      plot.background = element_rect(fill = "white", colour = "white")
    ) +
    coord_flip() +
    facet_grid(~ONTOLOGY)
  ggsave(
    args[["plot-output"]], plot_object, width = 12,
    height = max(5, 0.45 * nrow(plot_data)), dpi = 300
  )
} else {
  write_empty_plot(args[["plot-output"]], status_message)
}

cat(sprintf("Input genes: %d\n", length(genes)))
cat(sprintf("Gene-to-GO mapped genes: %d\n", length(mapped_genes)))
cat(sprintf("GO term mapped genes: %d\n", length(term_mapped_genes)))
cat(sprintf("All GO terms: %d\n", nrow(all_results)))
cat(sprintf("Significant GO terms (p < 0.1 and q < 0.2): %d\n", nrow(significant_results)))
