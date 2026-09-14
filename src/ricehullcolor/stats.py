"""Material-level association analyses and publication-ready figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def _bh_fdr(values: np.ndarray) -> np.ndarray:
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    adjusted = ranked * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.clip(adjusted, 0, 1)
    return result


def _hedges_g(indica: np.ndarray, japonica: np.ndarray) -> float:
    n1, n2 = len(indica), len(japonica)
    pooled = np.sqrt(((n1 - 1) * np.var(indica, ddof=1) + (n2 - 1) * np.var(japonica, ddof=1)) / (n1 + n2 - 2))
    correction = 1 - 3 / (4 * (n1 + n2) - 9)
    return float(correction * (np.mean(japonica) - np.mean(indica)) / pooled)


def _design(date: pd.Series, group: pd.Series | None = None) -> np.ndarray:
    dates = pd.get_dummies(date.astype(str), drop_first=True, dtype=float).to_numpy()
    columns = [np.ones((len(date), 1)), dates]
    if group is not None:
        columns.append((group.astype(str).str.lower() == "japonica").to_numpy(dtype=float)[:, None])
    return np.column_stack(columns)


def _nested_f_test(y: np.ndarray, date: pd.Series, group: pd.Series) -> tuple[float, float, float, float, float]:
    reduced = _design(date)
    full = _design(date, group)
    beta_r, *_ = np.linalg.lstsq(reduced, y, rcond=None)
    beta_f, *_ = np.linalg.lstsq(full, y, rcond=None)
    rss_r = float(np.sum((y - reduced @ beta_r) ** 2))
    residual_f = y - full @ beta_f
    rss_f = float(np.sum(residual_f**2))
    df1 = full.shape[1] - reduced.shape[1]
    df2 = len(y) - full.shape[1]
    f_value = ((rss_r - rss_f) / df1) / (rss_f / df2)
    p_value = float(scipy_stats.f.sf(f_value, df1, df2))
    partial_r2 = (rss_r - rss_f) / rss_r
    sigma2 = rss_f / df2
    covariance = sigma2 * np.linalg.pinv(full.T @ full)
    effect = float(beta_f[-1])
    se = float(np.sqrt(covariance[-1, -1]))
    tcrit = float(scipy_stats.t.ppf(0.975, df2))
    return effect, effect - tcrit * se, effect + tcrit * se, p_value, partial_r2


def _permanova_partial_r2(data: pd.DataFrame, traits: list[str], permutations: int, seed: int) -> dict[str, float]:
    y = StandardScaler().fit_transform(data[traits].to_numpy(dtype=float))
    reduced = _design(data["Date"])
    full = _design(data["Date"], data["Group"])
    fitted_r = reduced @ np.linalg.lstsq(reduced, y, rcond=None)[0]
    residual_r = y - fitted_r
    residual_f = y - full @ np.linalg.lstsq(full, y, rcond=None)[0]
    rss_r = float(np.sum(residual_r**2))
    rss_f = float(np.sum(residual_f**2))
    df1 = full.shape[1] - reduced.shape[1]
    df2 = len(data) - full.shape[1]
    observed = ((rss_r - rss_f) / df1) / (rss_f / df2)
    rng = np.random.default_rng(seed)
    blocks = [np.asarray(indices) for indices in data.groupby("Date").indices.values()]
    exceed = 0
    for _ in range(permutations):
        permutation = np.arange(len(data))
        for block in blocks:
            permutation[block] = rng.permutation(block)
        permuted = fitted_r + residual_r[permutation]
        rr = permuted - reduced @ np.linalg.lstsq(reduced, permuted, rcond=None)[0]
        rf = permuted - full @ np.linalg.lstsq(full, permuted, rcond=None)[0]
        sr, sf = float(np.sum(rr**2)), float(np.sum(rf**2))
        statistic = ((sr - sf) / df1) / (sf / df2)
        exceed += statistic >= observed
    return {
        "Pseudo_F": observed,
        "Partial_R2": (rss_r - rss_f) / rss_r,
        "Permutation_p": (exceed + 1) / (permutations + 1),
        "Permutations": permutations,
    }


def _normalise_columns(frame: pd.DataFrame, group_col: str, date_col: str) -> tuple[pd.DataFrame, list[str]]:
    aliases = {
        "Lstar": ["Lstar", "L_mean", "L*"],
        "astar": ["astar", "a_mean", "a*"],
        "bstar": ["bstar", "b_mean", "b*"],
        "Gray": ["Gray", "gray", "灰度值"],
    }
    out = frame.rename(columns={group_col: "Group", date_col: "Date"}).copy()
    for target, options in aliases.items():
        found = next((name for name in options if name in out.columns), None)
        if found is not None and found != target:
            out = out.rename(columns={found: target})
    required = ["Group", "Date", "Lstar", "astar", "bstar"]
    missing = [column for column in required if column not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    mapping = {"籼稻": "Indica", "籼型": "Indica", "indica": "Indica", "粳稻": "Japonica", "粳型": "Japonica", "japonica": "Japonica"}
    out["Group"] = out["Group"].astype(str).str.strip().map(lambda value: mapping.get(value.lower(), mapping.get(value, value)))
    out = out[out["Group"].isin(["Indica", "Japonica"])].copy()
    traits = ["Lstar", "astar", "bstar"] + (["Gray"] if "Gray" in out.columns else [])
    for column in traits:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=["Group", "Date", *traits]).reset_index(drop=True)
    return out, traits


def _cross_validated_classifier(data: pd.DataFrame, repeats: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = data[["Lstar", "astar", "bstar"]].to_numpy(dtype=float)
    y = (data["Group"] == "Japonica").to_numpy(dtype=int)
    folds = min(10, int(np.bincount(y).min()))
    if folds < 2:
        raise ValueError("Each group needs at least two materials for cross-validation")
    splitter = RepeatedStratifiedKFold(n_splits=folds, n_repeats=repeats, random_state=seed)
    predictions = {"Raw LAB": np.zeros((len(data), repeats)), "Date-adjusted LAB": np.zeros((len(data), repeats))}
    metrics: list[dict] = []
    for split_index, (train, test) in enumerate(splitter.split(x, y)):
        repeat = split_index // folds
        for label, adjusted in (("Raw LAB", False), ("Date-adjusted LAB", True)):
            train_x, test_x = x[train].copy(), x[test].copy()
            if adjusted:
                encoder = OneHotEncoder(drop="first", handle_unknown="ignore", sparse_output=False)
                d_train = encoder.fit_transform(data.loc[train, ["Date"]].astype(str))
                d_test = encoder.transform(data.loc[test, ["Date"]].astype(str))
                for column in range(train_x.shape[1]):
                    if d_train.shape[1]:
                        model = LinearRegression().fit(d_train, train_x[:, column])
                        train_x[:, column] -= model.predict(d_train)
                        test_x[:, column] -= model.predict(d_test)
                    else:
                        centre = float(train_x[:, column].mean())
                        train_x[:, column] -= centre
                        test_x[:, column] -= centre
            scaler = StandardScaler().fit(train_x)
            model = LogisticRegression(C=1.0, solver="liblinear", max_iter=2000, random_state=seed)
            model.fit(scaler.transform(train_x), y[train])
            score = model.predict_proba(scaler.transform(test_x))[:, 1]
            predictions[label][test, repeat] = score
            called = score >= 0.5
            sensitivity = recall_score(y[test], called, pos_label=1)
            specificity = recall_score(y[test], called, pos_label=0)
            metrics.append(
                {
                    "Model": label,
                    "Repeat": repeat + 1,
                    "Fold": split_index % folds + 1,
                    "AUC": roc_auc_score(y[test], score),
                    "BalancedAccuracy": balanced_accuracy_score(y[test], called),
                    "Sensitivity": sensitivity,
                    "Specificity": specificity,
                }
            )
    detail = data[[column for column in ["Material", "Date", "Group"] if column in data.columns]].copy()
    for label, matrix in predictions.items():
        detail[f"Pred_{label.replace(' ', '_')}"] = matrix.mean(axis=1)
    return pd.DataFrame(metrics), detail


def _stars(q: float) -> str:
    return "****" if q < 0.0001 else "***" if q < 0.001 else "**" if q < 0.01 else "*" if q < 0.05 else "ns"


def _plots(data: pd.DataFrame, univariate: pd.DataFrame, cv_detail: pd.DataFrame, out: Path) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.linewidth": 0.7, "figure.facecolor": "white"})
    colors = {"Indica": "#D55E00", "Japonica": "#0072B2"}
    traits = univariate["Trait"].tolist()
    fig, axes = plt.subplots(1, len(traits), figsize=(7.2, 2.8), constrained_layout=True)
    if len(traits) == 1:
        axes = [axes]
    rng = np.random.default_rng(20260914)
    for ax, trait in zip(axes, traits):
        values = [data.loc[data.Group == group, trait].to_numpy() for group in ["Indica", "Japonica"]]
        boxes = ax.boxplot(values, widths=0.5, patch_artist=True, showfliers=False)
        for patch, group in zip(boxes["boxes"], ["Indica", "Japonica"]):
            patch.set(facecolor=colors[group], alpha=0.25, edgecolor=colors[group])
        for index, (values_group, group) in enumerate(zip(values, ["Indica", "Japonica"]), start=1):
            ax.scatter(index + rng.uniform(-0.11, 0.11, len(values_group)), values_group, s=7, alpha=0.55, color=colors[group], linewidths=0)
        row = univariate.loc[univariate.Trait == trait].iloc[0]
        ymax, ymin = max(map(np.max, values)), min(map(np.min, values))
        span = ymax - ymin or 1
        bracket = ymax + 0.12 * span
        ax.plot([1, 1, 2, 2], [bracket - .02 * span, bracket, bracket, bracket - .02 * span], color="black", lw=.7)
        ax.text(1.5, bracket + .02 * span, _stars(row.BH_FDR_q), ha="center", fontweight="bold")
        ax.set_ylim(ymin - .05 * span, ymax + .28 * span)
        ax.set_xticks([1, 2], ["Indica", "Japonica"])
        ax.set_ylabel(trait.replace("star", "*"))
        ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "01_Lab_gray_boxplots.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out / "01_Lab_gray_boxplots.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    scaled_lab = StandardScaler().fit_transform(data[["Lstar", "astar", "bstar"]])
    pca = PCA(n_components=2).fit(scaled_lab)
    scores = pca.transform(scaled_lab)
    fig, ax = plt.subplots(figsize=(3.8, 3.2), constrained_layout=True)
    for group, marker in (("Indica", "o"), ("Japonica", "^")):
        subset = data.Group == group
        ax.scatter(scores[subset, 0], scores[subset, 1], s=20, marker=marker, color=colors[group], label=group, alpha=.8, edgecolors="none")
    ax.set(xlabel=f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)", ylabel=f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "02_PCA_LAB.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out / "02_PCA_LAB.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    y = (data.Group == "Japonica").to_numpy(dtype=int)
    fig, ax = plt.subplots(figsize=(3.8, 3.2), constrained_layout=True)
    for label, color in (("Raw LAB", colors["Indica"]), ("Date-adjusted LAB", colors["Japonica"])):
        score = cv_detail[f"Pred_{label.replace(' ', '_')}"]
        fpr, tpr, _ = roc_curve(y, score)
        ax.plot(fpr, tpr, color=color, lw=1.5, label=f"{label} AUC={roc_auc_score(y, score):.3f}")
    ax.plot([0, 1], [0, 1], "--", color="#999999", lw=.7)
    ax.set(xlabel="False-positive rate", ylabel="True-positive rate", xlim=(0, 1), ylim=(0, 1))
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "03_ROC.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(out / "03_ROC.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run_statistics(
    input_csv: str | Path,
    output_dir: str | Path,
    group_col: str = "Group",
    date_col: str = "Date",
    permutations: int = 999,
    repeats: int = 20,
    seed: int = 20260914,
) -> dict[str, Path | int]:
    """Run the recommended material-level association analysis."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_csv, encoding="utf-8-sig")
    data, traits = _normalise_columns(raw, group_col, date_col)
    rows = []
    for trait in traits:
        indica = data.loc[data.Group == "Indica", trait].to_numpy()
        japonica = data.loc[data.Group == "Japonica", trait].to_numpy()
        effect, low, high, p_value, partial_r2 = _nested_f_test(data[trait].to_numpy(), data.Date, data.Group)
        welch = scipy_stats.ttest_ind(japonica, indica, equal_var=False)
        rows.append(
            {
                "Trait": trait,
                "Indica_N": len(indica),
                "Indica_Mean": np.mean(indica),
                "Japonica_N": len(japonica),
                "Japonica_Mean": np.mean(japonica),
                "Raw_Difference_JminusI": np.mean(japonica) - np.mean(indica),
                "Welch_p": welch.pvalue,
                "Hedges_g_JminusI": _hedges_g(indica, japonica),
                "Date_Adjusted_Difference_JminusI": effect,
                "Adjusted_CI95_Low": low,
                "Adjusted_CI95_High": high,
                "Date_Adjusted_p": p_value,
                "Partial_R2": partial_r2,
            }
        )
    univariate = pd.DataFrame(rows)
    univariate["BH_FDR_q"] = _bh_fdr(univariate.Date_Adjusted_p.to_numpy())
    univariate["Significance"] = univariate.BH_FDR_q.map(_stars)
    multivariate = pd.DataFrame([_permanova_partial_r2(data, ["Lstar", "astar", "bstar"], permutations, seed)])
    cv_folds, cv_detail = _cross_validated_classifier(data, repeats, seed)
    cv_summary = cv_folds.groupby("Model", as_index=False).agg(
        AUC=("AUC", "mean"),
        AUC_SD=("AUC", "std"),
        BalancedAccuracy=("BalancedAccuracy", "mean"),
        Sensitivity=("Sensitivity", "mean"),
        Specificity=("Specificity", "mean"),
    )
    data.to_csv(out / "analysis_data.csv", index=False, encoding="utf-8-sig")
    univariate.to_csv(out / "univariate_date_adjusted.csv", index=False, encoding="utf-8-sig")
    multivariate.to_csv(out / "permanova.csv", index=False, encoding="utf-8-sig")
    cv_folds.to_csv(out / "classification_cv_folds.csv", index=False, encoding="utf-8-sig")
    cv_summary.to_csv(out / "classification_summary.csv", index=False, encoding="utf-8-sig")
    cv_detail.to_csv(out / "classification_predictions.csv", index=False, encoding="utf-8-sig")
    _plots(data, univariate, cv_detail, out)
    with pd.ExcelWriter(out / "RiceHullColor_statistics.xlsx", engine="openpyxl") as writer:
        univariate.to_excel(writer, sheet_name="单变量日期校正", index=False)
        multivariate.to_excel(writer, sheet_name="PERMANOVA", index=False)
        cv_summary.to_excel(writer, sheet_name="分类性能", index=False)
        cv_detail.to_excel(writer, sheet_name="交叉验证预测", index=False)
        data.to_excel(writer, sheet_name="分析数据", index=False)
    return {"output_dir": out, "rows": len(data), "indica": int((data.Group == "Indica").sum()), "japonica": int((data.Group == "Japonica").sum())}
