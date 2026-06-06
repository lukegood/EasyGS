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

parse_bool_arg <- function(value, name) {
  normalized <- tolower(trimws(as.character(value)))
  if (normalized %in% c("1", "true", "yes", "y")) {
    return(TRUE)
  }
  if (normalized %in% c("0", "false", "no", "n")) {
    return(FALSE)
  }
  stop(paste("Invalid boolean value for --", name, ": ", value, sep = ""), call. = FALSE)
}

load_required_packages <- function() {
  packages <- c("dplyr", "tidyr", "corrgram", "colorspace")
  missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) {
    stop(
      paste("Missing required R packages:", paste(missing, collapse = ", ")),
      call. = FALSE
    )
  }

  suppressPackageStartupMessages(library(dplyr))
  suppressPackageStartupMessages(library(corrgram))
  suppressPackageStartupMessages(library(colorspace))
}

normalize_dir <- function(path_value) {
  path_value <- normalizePath(path_value, winslash = "/", mustWork = FALSE)
  if (!endsWith(path_value, "/")) {
    path_value <- paste0(path_value, "/")
  }
  path_value
}

parsed <- parse_args(args)
env_meta_path <- required_arg(parsed, "env-meta")
trait_records_path <- required_arg(parsed, "trait-records")
env_paras_path <- required_arg(parsed, "env-paras")
output_dir <- required_arg(parsed, "output-dir")
trait_label <- required_arg(parsed, "trait-label")
trait_column <- required_arg(parsed, "trait-column")
searching_daps <- as.integer(required_arg(parsed, "searching-daps"))
max_window_start <- as.integer(required_arg(parsed, "max-window-start"))
max_window_end <- as.integer(required_arg(parsed, "max-window-end"))
key_parameter <- required_arg(parsed, "key-parameter")
run_downstream <- parse_bool_arg(required_arg(parsed, "run-downstream"), "run-downstream")
env_meta_encoding <- required_arg(parsed, "env-meta-encoding")
subfunctions_script <- required_arg(parsed, "subfunctions-script")

if (is.na(searching_daps) || searching_daps < 7) {
  stop("searching_daps must be an integer >= 7", call. = FALSE)
}
if (is.na(max_window_start) || max_window_start < 1) {
  stop("max_window_start must be an integer >= 1", call. = FALSE)
}
if (is.na(max_window_end) || max_window_end < max_window_start) {
  stop("max_window_end must be an integer >= max_window_start", call. = FALSE)
}

for (path_value in c(env_meta_path, trait_records_path, env_paras_path, subfunctions_script)) {
  if (!file.exists(path_value)) {
    stop(paste("Required input file not found:", path_value), call. = FALSE)
  }
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
setwd(output_dir)
load_required_packages()

col_wdw <- 25
col_palette <- diverge_hcl(col_wdw + 1, h = c(260, 0), c = 100, l = c(50, 90), power = 1)
t_base <- 50
t_max1 <- 100
t_max2 <- 1000
Haun_threshold <- 0
p <- 1

Top_dir <- normalize_dir(output_dir)
source(subfunctions_script)

trait <- trait_label

env_meta_info_0 <- read.table(
  env_meta_path,
  header = TRUE,
  sep = "\t",
  check.names = TRUE,
  stringsAsFactors = FALSE,
  fileEncoding = env_meta_encoding
)

PTT_PTR <- read.table(
  env_paras_path,
  header = TRUE,
  sep = "\t",
  check.names = TRUE,
  stringsAsFactors = FALSE
)

Paras <- c(
  "DL", "GDD", "PTT", "PTR", "dGDD", "DTR", "PTD1", "PTD2", "TSR", "MMR",
  "PR", "RH", "PRDTR", "dPTT", "PS", "WS", "WD", "APAR", "CPAR", "UVA",
  "UVB", "SW", "SM", "TMAX", "TMIN"
)
Paras <- intersect(Paras, colnames(PTT_PTR))

if (!("env_code" %in% colnames(env_meta_info_0))) {
  stop("Env_meta_table.txt must contain env_code column", call. = FALSE)
}
if (!all(c("env_code", "Date") %in% colnames(PTT_PTR))) {
  stop("Environment parameter file must contain env_code and Date columns", call. = FALSE)
}

exp_traits <- read.table(
  trait_records_path,
  sep = "\t",
  header = TRUE,
  stringsAsFactors = FALSE,
  na.strings = "NA",
  check.names = TRUE
)

required_trait_columns <- c("line_code", "env_code", trait_column)
missing_trait_columns <- setdiff(required_trait_columns, colnames(exp_traits))
if (length(missing_trait_columns) > 0) {
  stop(
    paste(
      "Trait_records.txt is missing required columns:",
      paste(missing_trait_columns, collapse = ", ")
    ),
    call. = FALSE
  )
}

if (run_downstream && !(key_parameter %in% colnames(PTT_PTR))) {
  stop(
    paste("key_parameter not found in environment parameter file:", key_parameter),
    call. = FALSE
  )
}

all_env_codes <- unique(exp_traits$env_code)
env_cols <- rainbow_hcl(length(all_env_codes), c = 80, l = 60, start = 0, end = 300, fixup = TRUE, alpha = 0.75)

exp_trait_dir <- paste(Top_dir, trait, "/", sep = "")
if (!dir.exists(exp_trait_dir)) {
  dir.create(exp_trait_dir, recursive = TRUE)
}

exp_trait <- exp_traits[, c("line_code", "env_code", trait_column)]
colnames(exp_trait)[3] <- "Yobs"
exp_trait <- aggregate(Yobs ~ line_code + env_code, data = exp_trait, mean)
exp_trait <- exp_trait[!is.na(exp_trait$Yobs), ]

line_codes <- unique(exp_trait$line_code)
env_mean_trait_0 <- na.omit(aggregate(x = exp_trait$Yobs, by = list(env_code = exp_trait$env_code), mean, na.rm = TRUE))
colnames(env_mean_trait_0)[2] <- "meanY"
env_mean_trait <- env_mean_trait_0[order(env_mean_trait_0$meanY), ]

try(Pairwise_trait_env_distribution_plot(exp_trait, exp_trait_dir, trait, all_env_codes, env_meta_info_0))

pop_cor_file <- paste(exp_trait_dir, trait, "_", nrow(env_mean_trait), "Envs_PTTPTR_", 0, "LOO_cor.txt", sep = "")
Exhaustive_search(
  env_mean_trait,
  PTT_PTR,
  searching_daps,
  exp_trait_dir,
  exp_traits[[trait_column]],
  trait,
  p,
  searching_daps,
  searching_daps,
  0,
  Paras,
  pop_cor_file
)

search.results <- read.table(pop_cor_file, header = TRUE) %>%
  tidyr::gather(key = "Parameter", value = "Corr", -Day_x, -Day_y, -window, -pop_code) %>%
  arrange(-Corr)
search.results <- search.results %>%
  group_by(Parameter) %>%
  top_n(5, Corr)
write.csv(search.results, file = file.path(output_dir, "allwinds_EF_cor.csv"), quote = FALSE, row.names = FALSE)

first_occurrences <- search.results %>%
  group_by(Parameter) %>%
  filter(row_number() == 1)
write.csv(first_occurrences, file = file.path(output_dir, "highest_EF.csv"), quote = FALSE, row.names = FALSE)

if (!run_downstream) {
  quit(save = "no", status = 0)
}

PTT_PTR_ind <- which(colnames(PTT_PTR) == key_parameter)
Plot_Trait_mean_envParas(env_mean_trait, PTT_PTR, max_window_start, max_window_end, trait, exp_trait_dir, env_cols, Paras)
Slope_Intercept(max_window_start, max_window_end, env_mean_trait, PTT_PTR, exp_trait, line_codes, exp_trait_dir)

obs_prd_file <- paste(
  exp_trait_dir,
  trait,
  "_",
  nrow(env_mean_trait),
  "Env_LOO_by_Lines_",
  key_parameter,
  "D",
  max_window_start,
  "_",
  max_window_end,
  ".txt",
  sep = ""
)
LOO_pdf_file <- paste(
  exp_trait_dir,
  trait,
  "_",
  nrow(env_mean_trait),
  "Env_LOO_by_Lines_",
  key_parameter,
  "D",
  max_window_start,
  "_",
  max_window_end,
  ".png",
  sep = ""
)
if (!file.exists(obs_prd_file)) {
  prdM <- LOOCV(max_window_start, max_window_end, env_mean_trait, PTT_PTR, PTT_PTR_ind, exp_trait, obs_prd_file, p)
  Plot_prediction_result(obs_prd_file, all_env_codes, prdM, key_parameter, LOO_pdf_file, env_cols)
}
