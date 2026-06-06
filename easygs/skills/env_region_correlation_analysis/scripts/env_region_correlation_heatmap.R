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
  stop("Input CSV must contain at least region, date, and one environmental-factor column.", call. = FALSE)
}

region_col <- if ("env_code" %in% names(df)) "env_code" else names(df)[1]
regions <- unique(df[[region_col]])
if (length(regions) < 2) {
  stop("At least two regions are required to compute cross-region correlations.", call. = FALSE)
}

factor_df <- df[, -(1:2), drop = FALSE]
if (ncol(factor_df) == 0) {
  stop("No environmental-factor columns remain after removing the first two metadata columns.", call. = FALSE)
}
factor_df[] <- lapply(factor_df, as.numeric)

region_vectors <- lapply(regions, function(region_name) {
  subset_df <- factor_df[df[[region_col]] == region_name, , drop = FALSE]
  as.vector(as.matrix(subset_df))
})

max_length <- max(vapply(region_vectors, length, integer(1)))
region_matrix <- do.call(
  cbind,
  lapply(region_vectors, function(values) {
    length(values) <- max_length
    values
  })
)
colnames(region_matrix) <- regions

cor_matrix <- cor(region_matrix, use = "pairwise.complete.obs")
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
