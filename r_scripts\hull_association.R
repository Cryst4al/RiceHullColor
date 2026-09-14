#!/usr/bin/env Rscript

# Independent R implementation of the material-level univariate and
# multivariate association models documented by RiceHullColor.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2L) stop("Usage: Rscript hull_association.R input.csv output_dir")

input <- normalizePath(args[1], mustWork = TRUE)
output <- args[2]
dir.create(output, recursive = TRUE, showWarnings = FALSE)
dat <- read.csv(input, fileEncoding = "UTF-8-BOM", check.names = FALSE)

aliases <- list(Lstar = c("Lstar", "L_mean", "L."),
                astar = c("astar", "a_mean", "a."),
                bstar = c("bstar", "b_mean", "b."),
                Gray = c("Gray", "gray"))
for (target in names(aliases)) {
  source <- aliases[[target]][aliases[[target]] %in% names(dat)][1]
  if (!is.na(source) && source != target) names(dat)[names(dat) == source] <- target
}
required <- c("Date", "Group", "Lstar", "astar", "bstar")
if (!all(required %in% names(dat))) stop("Missing: ", paste(setdiff(required, names(dat)), collapse = ", "))
dat$Date <- factor(dat$Date)
dat$Group <- factor(dat$Group, levels = c("Indica", "Japonica"))
traits <- intersect(c("Lstar", "astar", "bstar", "Gray"), names(dat))
dat <- dat[complete.cases(dat[, c(required, traits)]), ]

hedges_g <- function(indica, japonica) {
  n1 <- length(indica); n2 <- length(japonica)
  pooled <- sqrt(((n1 - 1) * var(indica) + (n2 - 1) * var(japonica)) / (n1 + n2 - 2))
  (1 - 3 / (4 * (n1 + n2) - 9)) * (mean(japonica) - mean(indica)) / pooled
}

rows <- lapply(traits, function(trait) {
  full <- lm(reformulate(c("Date", "Group"), trait), data = dat)
  reduced <- lm(reformulate("Date", trait), data = dat)
  comparison <- anova(reduced, full)
  indica <- dat[dat$Group == "Indica", trait]
  japonica <- dat[dat$Group == "Japonica", trait]
  estimate <- unname(coef(full)["GroupJaponica"])
  interval <- unname(confint(full, "GroupJaponica"))
  data.frame(Trait = trait,
             Indica_N = length(indica), Indica_Mean = mean(indica),
             Japonica_N = length(japonica), Japonica_Mean = mean(japonica),
             Adjusted_Difference_JminusI = estimate,
             CI95_Low = interval[1], CI95_High = interval[2],
             Adjusted_p = comparison$`Pr(>F)`[2],
             Partial_R2 = (deviance(reduced) - deviance(full)) / deviance(reduced),
             Hedges_g_JminusI = hedges_g(indica, japonica))
})
univariate <- do.call(rbind, rows)
univariate$BH_FDR_q <- p.adjust(univariate$Adjusted_p, method = "BH")
write.csv(univariate, file.path(output, "R_univariate_date_adjusted.csv"), row.names = FALSE, fileEncoding = "UTF-8")

manova_fit <- manova(cbind(Lstar, astar, bstar) ~ Date + Group, data = dat)
capture.output(summary(manova_fit, test = "Pillai"), file = file.path(output, "R_MANOVA_Pillai.txt"))

if (requireNamespace("vegan", quietly = TRUE)) {
  set.seed(20260914)
  permanova <- vegan::adonis2(scale(dat[, c("Lstar", "astar", "bstar")]) ~ Date + Group,
                              data = dat, permutations = 4999, by = "margin")
  capture.output(permanova, file = file.path(output, "R_PERMANOVA_adonis2.txt"))
} else {
  writeLines("Install the CRAN package 'vegan' to run adonis2 PERMANOVA.",
             file.path(output, "R_PERMANOVA_adonis2.txt"))
}

cat("Rows:", nrow(dat), "\nOutput:", normalizePath(output, mustWork = TRUE), "\n")

