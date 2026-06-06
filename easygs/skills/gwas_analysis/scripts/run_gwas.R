#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(rMVP)
  library(bigmemory)
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
    "bfile-prefix",
    "phenotype-csv",
    "output-dir",
    "line-column",
    "trait-column",
    "methods",
    "threshold",
    "pcs-keep",
    "npc-glm",
    "npc-mlm",
    "npc-farmcpu",
    "ncpus"
  )
  missing <- required[!vapply(required, function(name) !is.null(parsed[[name]]) && nzchar(parsed[[name]]), logical(1))]
  if (length(missing) > 0L) {
    stop(sprintf("Missing required arguments: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  parsed
}

select_pc_covariates <- function(pc_matrix, count, label) {
  count <- as.integer(count)
  if (is.na(count) || count <= 0L) {
    return(NULL)
  }
  available <- ncol(pc_matrix)
  if (available < 1L) {
    return(NULL)
  }
  keep <- min(count, available)
  if (keep < count) {
    message(sprintf("%s=%d exceeds available PCs (%d); using %d columns instead.", label, count, available, keep))
  }
  pc_matrix[, seq_len(keep), drop = FALSE]
}

args <- parse_args()
bfile_prefix <- args[["bfile-prefix"]]
phenotype_csv <- args[["phenotype-csv"]]
output_dir <- args[["output-dir"]]
line_column <- args[["line-column"]]
trait_column <- args[["trait-column"]]
methods <- strsplit(args[["methods"]], ",", fixed = TRUE)[[1L]]
methods <- methods[nzchar(methods)]
threshold <- as.numeric(args[["threshold"]])
pcs_keep <- as.integer(args[["pcs-keep"]])
npc_glm <- as.integer(args[["npc-glm"]])
npc_mlm <- as.integer(args[["npc-mlm"]])
npc_farmcpu <- as.integer(args[["npc-farmcpu"]])
ncpus <- as.integer(args[["ncpus"]])

if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
}

phe_raw <- read.csv(phenotype_csv, header = TRUE, check.names = FALSE, stringsAsFactors = FALSE)
required_cols <- c(line_column, trait_column)
missing_cols <- setdiff(required_cols, colnames(phe_raw))
if (length(missing_cols) > 0L) {
  stop(sprintf("Phenotype CSV is missing required columns: %s", paste(missing_cols, collapse = ", ")), call. = FALSE)
}

phe <- phe_raw[, required_cols, drop = FALSE]
colnames(phe) <- c(line_column, trait_column)
phe[[line_column]] <- trim_scalar(phe[[line_column]])
phe[[trait_column]] <- suppressWarnings(as.numeric(phe[[trait_column]]))
phe <- phe[nzchar(phe[[line_column]]) & !is.na(phe[[trait_column]]), , drop = FALSE]
if (nrow(phe) < 4L) {
  stop("Phenotype CSV has fewer than 4 non-missing rows after filtering.", call. = FALSE)
}

phe_path <- file.path(output_dir, "gwas_input_phenotype.csv")
write.csv(phe, phe_path, row.names = FALSE, quote = FALSE)

mvp_prefix <- file.path(output_dir, "mvp.plink")
kin_prefix <- file.path(output_dir, "mvpKin")
pc_prefix <- file.path(output_dir, "mvpPC")
cpu_count <- max(1L, ncpus)

# MVP.Data handles BFILE conversion together with phenotype cleanup.
rMVP::MVP.Data(
  fileBed = bfile_prefix,
  filePhe = phe_path,
  sep.phe = ",",
  fileKin = FALSE,
  filePC = FALSE,
  out = mvp_prefix
)

rMVP::MVP.Data.Kin(
  TRUE,
  mvp_prefix = mvp_prefix,
  out = kin_prefix,
  cpu = cpu_count
)

rMVP::MVP.Data.PC(
  TRUE,
  mvp_prefix = mvp_prefix,
  pcs.keep = pcs_keep,
  out = pc_prefix,
  cpu = cpu_count
)

genotype <- attach.big.matrix(paste0(mvp_prefix, ".geno.desc"))
phenotype <- read.table(paste0(mvp_prefix, ".phe"), header = TRUE)
map <- read.table(paste0(mvp_prefix, ".geno.map"), header = TRUE)
Kinship <- attach.big.matrix(paste0(kin_prefix, ".kin.desc"))
Covariates_PC <- bigmemory::as.matrix(attach.big.matrix(paste0(pc_prefix, ".pc.desc")))

if (nrow(Covariates_PC) != nrow(phenotype)) {
  stop(
    sprintf(
      "PC matrix row count (%d) does not match phenotype row count (%d).",
      nrow(Covariates_PC),
      nrow(phenotype)
    ),
    call. = FALSE
  )
}

glm_covariates <- select_pc_covariates(Covariates_PC, npc_glm, "npc_glm")
mlm_covariates <- select_pc_covariates(Covariates_PC, npc_mlm, "npc_mlm")
farmcpu_covariates <- select_pc_covariates(Covariates_PC, npc_farmcpu, "npc_farmcpu")

mvp_args <- list(
  phe = phenotype,
  geno = genotype,
  map = map,
  K = Kinship,
  ncpus = cpu_count,
  vc.method = "BRENT",
  method.bin = "static",
  threshold = threshold,
  method = methods,
  memo = trait_column,
  outpath = output_dir,
  file.output = c("pmap", "pmap.signal", "plot", "log")
)

if ("GLM" %in% methods && !is.null(glm_covariates)) {
  mvp_args[["CV.GLM"]] <- glm_covariates
}

if ("MLM" %in% methods && !is.null(mlm_covariates)) {
  mvp_args[["CV.MLM"]] <- mlm_covariates
}

if ("FarmCPU" %in% methods) {
  mvp_args[["nPC.FarmCPU"]] <- 0L
  if (!is.null(farmcpu_covariates)) {
    mvp_args[["CV.FarmCPU"]] <- farmcpu_covariates
  }
}

imMVP <- do.call(rMVP::MVP, mvp_args)

print(imMVP)
