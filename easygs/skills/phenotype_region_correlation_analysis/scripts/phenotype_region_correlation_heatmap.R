args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(values) {
  parsed <- list()
  i <- 1
  while (i <= length(values)) {
    key <- values[[i]]
    if (!startsWith(key, "--")) {
      stop(paste("Unknown argument:", key), call. = FALSE)
    }
    if (i == length(values)) {
      stop(paste("Missing value for argument:", key), call. = FALSE)
    }
    parsed[[substring(key, 3)]] <- values[[i + 1]]
    i <- i + 2
  }
  parsed
}

required_arg <- function(parsed, name) {
  value <- parsed[[name]]
  if (is.null(value) || identical(value, "")) {
    stop(paste("Missing required argument --", name, sep = ""), call. = FALSE)
  }
  value
}

parsed <- parse_args(args)
input_csv <- required_arg(parsed, "input-csv")
cor_output <- required_arg(parsed, "cor-output")
pdf_output <- required_arg(parsed, "pdf-output")

suppressPackageStartupMessages(library(corrplot))

df <- read.csv(input_csv, header = TRUE, check.names = FALSE)
if (ncol(df) < 3) {
  stop("Input CSV must contain one ID column and at least two phenotype columns.", call. = FALSE)
}

id_col <- if ("ID" %in% names(df)) "ID" else names(df)[1]
phenotype_df <- df[, names(df) != id_col, drop = FALSE]
if (ncol(phenotype_df) < 2) {
  stop("At least two phenotype columns are required to compute cross-region correlations.", call. = FALSE)
}
phenotype_df[] <- lapply(phenotype_df, as.numeric)

cor_matrix <- cor(phenotype_df, use = "pairwise.complete.obs")
write.csv(as.data.frame(cor_matrix), cor_output, quote = FALSE)

pdf(file = pdf_output, width = 8, height = 8)
on.exit(dev.off(), add = TRUE)

corrplot(
  cor_matrix,
  tl.col = "black",
  tl.pos = "lt",
  tl.cex = 1,
  type = "upper",
  tl.srt = 60,
  col = colorRampPalette(c("#D65190", "white", "#87CEFA"))(50),
  method = "circle"
)

corrplot(
  cor_matrix,
  type = "lower",
  add = TRUE,
  method = "number",
  tl.pos = "n",
  cl.pos = "n",
  diag = FALSE,
  col = colorRampPalette(c("#B0C4DE", "#808080"))(50),
  number.cex = 0.9
)
