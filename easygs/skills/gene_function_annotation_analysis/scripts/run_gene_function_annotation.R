#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(AnnotationHub)
  library(clusterProfiler)
  library(ggplot2)
  library(dplyr)
})

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
    "genelist-txt",
    "entrez-map-csv",
    "gene-column",
    "entrez-column",
    "annotationhub-id",
    "kegg-organism",
    "go-ontology",
    "kegg-pvalue-threshold",
    "go-pvalue-threshold",
    "kegg-txt-output",
    "kegg-png-output",
    "go-txt-output",
    "go-png-output",
    "mapping-summary-output"
  )
  missing <- required[
    !vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))
  ]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

write_empty_plot <- function(output_path, title_text, body_text) {
  plot_df <- data.frame(x = 1, y = 1)
  plot_obj <- ggplot(plot_df, aes(x, y)) +
    annotate("text", x = 1, y = 1.15, label = title_text, size = 6, fontface = "bold") +
    annotate("text", x = 1, y = 0.9, label = body_text, size = 4.5) +
    xlim(0.5, 1.5) +
    ylim(0.5, 1.5) +
    theme_void()
  ggsave(output_path, plot_obj, width = 9, height = 6, dpi = 300)
}

empty_kegg_df <- function() {
  data.frame(
    ID = character(),
    Description = character(),
    GeneRatio = character(),
    BgRatio = character(),
    pvalue = numeric(),
    p.adjust = numeric(),
    qvalue = numeric(),
    geneID = character(),
    Count = integer(),
    stringsAsFactors = FALSE
  )
}

empty_go_df <- function() {
  data.frame(
    ONTOLOGY = character(),
    ID = character(),
    Description = character(),
    GeneRatio = character(),
    BgRatio = character(),
    pvalue = numeric(),
    p.adjust = numeric(),
    qvalue = numeric(),
    geneID = character(),
    Count = integer(),
    stringsAsFactors = FALSE
  )
}

write_result_table <- function(df, output_path) {
  dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
  write.table(
    df,
    file = output_path,
    sep = "\t",
    quote = FALSE,
    row.names = FALSE,
    na = ""
  )
}

build_kegg_plot <- function(df, output_path) {
  plot_obj <- ggplot(df, aes(x = reorder(Description, Count), y = Count, fill = -log10(pvalue))) +
    geom_col() +
    geom_point(aes(size = Count), shape = 21, colour = "black", fill = "white", stroke = 1) +
    scale_size_continuous(name = "Gene Count", range = c(2, 6)) +
    scale_fill_gradient(low = "lightblue", high = "darkblue", name = "-log10(p-value)") +
    labs(x = NULL, y = NULL, title = "KEGG Pathway Enrichment") +
    coord_flip() +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      axis.text.x = element_blank(),
      axis.text.y = element_text(colour = "black", size = 11),
      legend.title = element_text(face = "bold", size = 11),
      legend.text = element_text(size = 10),
      panel.background = element_rect(fill = "white", colour = "white"),
      plot.background = element_rect(fill = "white", colour = "white")
    )
  ggsave(output_path, plot_obj, width = 9, height = 6, dpi = 300)
}

build_go_plot <- function(df, output_path) {
  plot_obj <- ggplot(df, aes(x = reorder(Description, Count), y = Count)) +
    geom_point(aes(size = Count, fill = -log10(pvalue)), shape = 21, stroke = 1) +
    scale_size_continuous(name = "Gene Count", range = c(2, 6)) +
    scale_fill_gradient(low = "lightblue", high = "darkblue", name = "-log10(p-value)") +
    labs(x = NULL, y = NULL, title = "GO Pathway Enrichment") +
    coord_flip() +
    facet_grid(~ONTOLOGY) +
    theme_minimal() +
    theme(
      plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      axis.text.x = element_blank(),
      axis.text.y = element_text(colour = "black", size = 11),
      legend.title = element_text(face = "bold", size = 11),
      legend.text = element_text(size = 10),
      panel.background = element_rect(fill = "white", colour = "white"),
      plot.background = element_rect(fill = "white", colour = "white")
    )
  ggsave(output_path, plot_obj, width = 10, height = 7, dpi = 300)
}

safe_annotationhub_orgdb <- function(annotationhub_id) {
  tryCatch(
    {
      cache_candidates <- c(
        file.path(path.expand("~"), ".cache", "R", "AnnotationHub"),
        file.path(tempdir(), "AnnotationHub-cache")
      )
      cache_dir <- NULL
      for (candidate in cache_candidates) {
        suppressWarnings(dir.create(candidate, recursive = TRUE, showWarnings = FALSE))
        if (dir.exists(candidate)) {
          cache_dir <- candidate
          break
        }
      }
      if (is.null(cache_dir)) {
        stop("Unable to create a writable AnnotationHub cache directory.", call. = FALSE)
      }
      hub <- AnnotationHub::AnnotationHub(cache = cache_dir)
      hub[[annotationhub_id]]
    },
    error = function(err) {
      structure(list(message = conditionMessage(err)), class = "easygs_annotationhub_error")
    }
  )
}

safe_enrich_kegg <- function(entrez_ids, organism_code) {
  tryCatch(
    {
      clusterProfiler::enrichKEGG(
        gene = entrez_ids,
        organism = organism_code,
        pvalueCutoff = 1,
        qvalueCutoff = 1
      )
    },
    error = function(err) structure(list(message = conditionMessage(err)), class = "easygs_enrich_error")
  )
}

safe_enrich_go <- function(entrez_ids, orgdb, ontology_code) {
  tryCatch(
    {
      clusterProfiler::enrichGO(
        gene = entrez_ids,
        keyType = "ENTREZID",
        OrgDb = orgdb,
        ont = ontology_code,
        pvalueCutoff = 1,
        qvalueCutoff = 1,
        readable = TRUE
      )
    },
    error = function(err) structure(list(message = conditionMessage(err)), class = "easygs_enrich_error")
  )
}

args <- parse_args()
genelist_txt <- args[["genelist-txt"]]
entrez_map_csv <- args[["entrez-map-csv"]]
gene_column <- trim_scalar(args[["gene-column"]])
entrez_column <- trim_scalar(args[["entrez-column"]])
annotationhub_id <- trim_scalar(args[["annotationhub-id"]])
kegg_organism <- trim_scalar(args[["kegg-organism"]])
go_ontology <- toupper(trim_scalar(args[["go-ontology"]]))
kegg_pvalue_threshold <- as.numeric(args[["kegg-pvalue-threshold"]])
go_pvalue_threshold <- as.numeric(args[["go-pvalue-threshold"]])
kegg_txt_output <- args[["kegg-txt-output"]]
kegg_png_output <- args[["kegg-png-output"]]
go_txt_output <- args[["go-txt-output"]]
go_png_output <- args[["go-png-output"]]
mapping_summary_output <- args[["mapping-summary-output"]]

if (is.na(kegg_pvalue_threshold) || kegg_pvalue_threshold < 0 || kegg_pvalue_threshold > 1) {
  stop("kegg-pvalue-threshold must be between 0 and 1.", call. = FALSE)
}
if (is.na(go_pvalue_threshold) || go_pvalue_threshold < 0 || go_pvalue_threshold > 1) {
  stop("go-pvalue-threshold must be between 0 and 1.", call. = FALSE)
}
if (!(go_ontology %in% c("BP", "CC", "MF", "ALL"))) {
  stop("go-ontology must be one of: BP, CC, MF, ALL.", call. = FALSE)
}

dir.create(dirname(kegg_txt_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(kegg_png_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(go_txt_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(go_png_output), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(mapping_summary_output), recursive = TRUE, showWarnings = FALSE)

gene_lines <- trim_scalar(readLines(genelist_txt, warn = FALSE, encoding = "UTF-8"))
gene_lines <- gene_lines[nzchar(gene_lines)]
if (!length(gene_lines)) {
  stop(sprintf("Gene list TXT is empty: %s", genelist_txt), call. = FALSE)
}
genelist_df <- data.frame(gene_value = gene_lines, stringsAsFactors = FALSE)
names(genelist_df) <- gene_column

entrez_map <- read.csv(
  entrez_map_csv,
  stringsAsFactors = FALSE,
  check.names = FALSE
)
names(entrez_map) <- trim_scalar(names(entrez_map))
required_cols <- c(gene_column, entrez_column)
missing_cols <- required_cols[!(required_cols %in% names(entrez_map))]
if (length(missing_cols) > 0L) {
  stop(
    sprintf(
      "ENTREZ mapping CSV is missing required columns: %s",
      paste(missing_cols, collapse = ", ")
    ),
    call. = FALSE
  )
}
entrez_map[[gene_column]] <- trim_scalar(entrez_map[[gene_column]])
entrez_map[[entrez_column]] <- trim_scalar(entrez_map[[entrez_column]])
entrez_map <- entrez_map |>
  dplyr::filter(.data[[gene_column]] != "") |>
  dplyr::distinct(.data[[gene_column]], .keep_all = TRUE)

merged <- dplyr::left_join(genelist_df, entrez_map[, required_cols, drop = FALSE], by = gene_column)
mapped_mask <- !is.na(merged[[entrez_column]]) & nzchar(trim_scalar(merged[[entrez_column]]))
mapped_entrez_ids <- unique(trim_scalar(merged[[entrez_column]][mapped_mask]))
mapped_entrez_ids <- mapped_entrez_ids[nzchar(mapped_entrez_ids)]

orgdb <- safe_annotationhub_orgdb(annotationhub_id)
orgdb_status <- "ok"
if (inherits(orgdb, "easygs_annotationhub_error")) {
  orgdb_status <- paste("error:", orgdb$message)
  orgdb <- NULL
}

kegg_status <- "not_run"
kegg_df <- empty_kegg_df()
if (length(mapped_entrez_ids) == 0L) {
  kegg_status <- "empty: no mapped ENTREZ IDs"
} else {
  kegg_result <- safe_enrich_kegg(mapped_entrez_ids, kegg_organism)
  if (inherits(kegg_result, "easygs_enrich_error")) {
    kegg_status <- paste("error:", kegg_result$message)
  } else {
    kegg_df <- as.data.frame(kegg_result)
    if (!nrow(kegg_df)) {
      kegg_df <- empty_kegg_df()
      kegg_status <- "empty: no KEGG enrichment terms returned"
    } else {
      kegg_df <- kegg_df[kegg_df$pvalue < kegg_pvalue_threshold, , drop = FALSE]
      if (!nrow(kegg_df)) {
        kegg_df <- kegg_df[0, , drop = FALSE]
        kegg_status <- sprintf("empty: no KEGG terms passed pvalue < %s", format(kegg_pvalue_threshold))
      } else {
        kegg_status <- "ok"
      }
    }
  }
}

go_status <- "not_run"
go_df <- empty_go_df()
if (length(mapped_entrez_ids) == 0L) {
  go_status <- "empty: no mapped ENTREZ IDs"
} else if (is.null(orgdb)) {
  go_status <- paste("error: failed to load AnnotationHub OrgDb", orgdb_status)
} else {
  go_result <- safe_enrich_go(mapped_entrez_ids, orgdb, go_ontology)
  if (inherits(go_result, "easygs_enrich_error")) {
    go_status <- paste("error:", go_result$message)
  } else {
    go_df <- as.data.frame(go_result)
    if (!nrow(go_df)) {
      go_df <- empty_go_df()
      go_status <- "empty: no GO enrichment terms returned"
    } else {
      go_df <- go_df[go_df$pvalue < go_pvalue_threshold, , drop = FALSE]
      if (!nrow(go_df)) {
        go_df <- go_df[0, , drop = FALSE]
        go_status <- sprintf("empty: no GO terms passed pvalue < %s", format(go_pvalue_threshold))
      } else {
        go_status <- "ok"
      }
    }
  }
}

write_result_table(kegg_df, kegg_txt_output)
write_result_table(go_df, go_txt_output)

if (nrow(kegg_df) > 0L) {
  build_kegg_plot(kegg_df, kegg_png_output)
} else {
  write_empty_plot(kegg_png_output, "KEGG Pathway Enrichment", kegg_status)
}

if (nrow(go_df) > 0L) {
  build_go_plot(go_df, go_png_output)
} else {
  write_empty_plot(go_png_output, "GO Pathway Enrichment", go_status)
}

mapping_summary <- data.frame(
  metric = c(
    "annotationhub_id",
    "gene_column",
    "entrez_column",
    "input_gene_rows",
    "unique_input_genes",
    "mapping_rows",
    "unique_mapping_genes",
    "mapped_input_genes",
    "mapped_entrez_ids",
    "unmapped_input_genes",
    "orgdb_status",
    "kegg_status",
    "go_status",
    "kegg_terms",
    "go_terms"
  ),
  value = c(
    annotationhub_id,
    gene_column,
    entrez_column,
    as.character(length(gene_lines)),
    as.character(length(unique(gene_lines))),
    as.character(nrow(entrez_map)),
    as.character(length(unique(entrez_map[[gene_column]]))),
    as.character(sum(mapped_mask)),
    as.character(length(mapped_entrez_ids)),
    as.character(sum(!mapped_mask)),
    orgdb_status,
    kegg_status,
    go_status,
    as.character(nrow(kegg_df)),
    as.character(nrow(go_df))
  ),
  stringsAsFactors = FALSE
)

write.table(
  mapping_summary,
  file = mapping_summary_output,
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

cat(sprintf("Mapped %d of %d input genes to %d unique ENTREZ IDs.\n", sum(mapped_mask), length(gene_lines), length(mapped_entrez_ids)))
cat(sprintf("KEGG terms written: %d -> %s\n", nrow(kegg_df), kegg_txt_output))
cat(sprintf("GO terms written: %d -> %s\n", nrow(go_df), go_txt_output))
