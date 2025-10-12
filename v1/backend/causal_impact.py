#!/usr/bin/env python3
"""
causal_impact.py - Production-grade causal inference for health campaigns.

This script computes the causal impact of a health campaign using robust methods
including AIPW/DR with K-fold cross-fitting, propensity scoring, and various
robustness checks. It produces manager-ready outputs with diagnostics.

Usage:
    python causal_impact.py --data PATH.csv --outdir outputs --kfold 5 --min-per-arm 60 --seed 42 --plots
"""
import os
import traceback
from pathlib import Path
from typing import Tuple
import pandas as pd
from huggingface_hub import InferenceClient, HfFolder

def generate_llm_report(
    outdir: Path,
    ate_aipw: float,
    ci_aipw: Tuple[float, float],
    top_segments_df: pd.DataFrame
) -> None:
    """
    Generate a natural language summary of the results using the Hugging Face Inference API.
    This step requires an HF_TOKEN environment variable.
    """
    print("\nGenerating LLM-powered summary using Hugging Face...")

    try:
        # --- Hugging Face API Configuration ---
        # Load Hugging Face token securely from an environment variable.
        hf_token = os.environ.get("HF_TOKEN","REDACTED_HF_TOKEN")
        if not hf_token:
            print("\n" + "="*60)
            print("     WARNING: HF_TOKEN environment variable not found.")
            print("     Skipping LLM report generation. Please set the HF_TOKEN.")
            print("="*60 + "\n")
            return

        HfFolder.save_token(hf_token)

        # --- Model and Client Initialization ---
        MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"
        client = InferenceClient()

        # --- Data Preparation for Prompt ---
        # Create a simplified text version of the top segments for the prompt.
        top_segments_text = ""
        if not top_segments_df.empty:
            for _, row in top_segments_df.head(3).iterrows():
                # Filter for relevant columns and ensure they are not NaN
                segment_cols = ['district', 'age_band', 'locale', 'send_time']
                segment_desc = ' & '.join([
                    f"{col}={row[col]}"
                    for col in row.index
                    if col in segment_cols and pd.notna(row[col])
                ])
                # FIX: Corrected the column name from 'estimated_ uplift_pp' to 'estimated_uplift_pp'
                uplift = row['estimated_uplift_pp']
                top_segments_text += f"- Segment: '{segment_desc}', Estimated Uplift: {uplift:.2f} percentage points\n"
        else:
            top_segments_text = "No specific high-impact segments were identified for targeting."

        # --- Prompt Construction ---
        # This prompt is structured for a chat-based model.
        prompt = f"""
        You are a senior data analyst reporting to a non-technical marketing manager.
        Your task is to summarize the results of a causal impact analysis for a recent health campaign.
        Write a clear, concise, and business-focused executive summary. Avoid overly technical jargon.

        *Key Causal Impact Results:*
        - *Primary Finding (Average Treatment Effect):* The campaign caused a {ate_aipw*100:.2f} percentage point increase in the 7-day booking rate.
        - *95% Confidence Interval:* We are 95% confident that the true effect is between {ci_aipw[0]*100:.2f}pp and {ci_aipw[1]*100:.2f}pp.
        - *Top Performing Segments for Next Wave:*
        {top_segments_text}

        *Instructions:*
        1.  Start with a clear "Executive Summary" section.
        2.  Explain what the main finding means in simple business terms (is the result positive and statistically significant?).
        3.  Create a "Key Findings" section using bullet points.
        4.  Create a "Recommendations" section, translating the top segments into actionable advice for the next campaign.
        5.  Keep the tone confident and data-driven.
        """

        # --- API Call to Hugging Face ---
        response = client.chat_completion(
            messages=[
                {"role": "user", "content": prompt},
            ],
            model=MODEL_ID,
            max_tokens=1024,  # Increased token limit for a detailed report
        )

        report_content = response.choices[0].message.content

        # --- Save the Report ---
        report_path = outdir / 'report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"     Saved LLM summary -> {report_path}")

    except Exception as e:
        print("\n" + "!"*60)
        print("     ERROR: Hugging Face report generation failed.")
        print("     This could be an invalid token, network issue, or file permission error.")
        print("!"*60 + "\n")
        print("     Detailed Exception:")
        # Print the full traceback for easier debugging
        traceback.print_exc()


import argparse
import os
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import OneHotEncoder

warnings.filterwarnings('ignore', category=FutureWarning)
plt.style.use('default')


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compute causal impact of health campaign with robust methods"
    )
    parser.add_argument(
        '--data',
        type=str,
        required=True,
        help='Path to input CSV with campaign data'
    )
    parser.add_argument(
        '--outdir',
        type=str,
        default='outputs',
        help='Output directory for results (default: outputs)'
    )
    parser.add_argument(
        '--kfold',
        type=int,
        default=5,
        help='Number of folds for cross-fitting (default: 5)'
    )
    parser.add_argument(
        '--min-per-arm',
        type=int,
        default=60,
        help='Minimum treated and control counts for actionable segments (default: 60)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--plots',
        action='store_true',
        help='Generate diagnostic plots'
    )
    return parser.parse_args()


def validate_schema(df: pd.DataFrame) -> None:
    """
    Validate that required columns exist in the dataframe.

    Args:
        df: Input dataframe

    Raises:
        ValueError: If required columns are missing
    """
    required_cols = [
        'treatment', 'outcome_booking_7d',
        'district', 'locale', 'age_band',
        'prior_engagement', 'send_time', 'chronic_diabetes'
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise ValueError(
            f"Missing required columns: {missing_cols}\n"
            f"Please ensure your CSV contains all required columns:\n"
            f"{required_cols}"
        )

    # Create stratum if missing
    if 'stratum' not in df.columns:
        df['stratum'] = df['district'] + "" + df['age_band'] + "" + df['locale']
        print(f"Created 'stratum' column from district_age_band_locale")


def build_covariates(
    df: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str], OneHotEncoder]:
    """
    Build covariate matrix X, outcome Y, and treatment T from dataframe.
    Only uses pre-treatment covariates.

    Args:
        df: Input dataframe

    Returns:
        X: Covariate matrix (one-hot encoded)
        Y: Outcome vector
        T: Treatment vector
        feature_names: List of feature names after encoding
        encoder: Fitted OneHotEncoder for future use
    """
    # Pre-treatment covariates only
    categorical_cols = ['district', 'locale', 'age_band', 'prior_engagement', 'send_time']
    numeric_cols = ['chronic_diabetes']

    # Prepare categorical features
    X_cat = df[categorical_cols].astype(str)

    # One-hot encode categorical variables
    encoder = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore')
    X_cat_encoded = encoder.fit_transform(X_cat)

    # Get feature names
    cat_feature_names = encoder.get_feature_names_out(categorical_cols).tolist()

    # Combine with numeric features
    X_num = df[numeric_cols].values
    X = np.hstack([X_cat_encoded, X_num])

    feature_names = cat_feature_names + numeric_cols

    # Extract outcome and treatment
    Y = df['outcome_booking_7d'].values.astype(float)
    T = df['treatment'].values.astype(float)

    return X, Y, T, feature_names, encoder


def fit_propensity_crossfit(
    X: np.ndarray,
    T: np.ndarray,
    n_splits: int = 5,
    seed: int = 42
) -> Tuple[np.ndarray, float]:
    """
    Fit propensity score model with K-fold cross-fitting.

    Args:
        X: Covariate matrix
        T: Treatment vector
        n_splits: Number of folds
        seed: Random seed

    Returns:
        ps_hat: Out-of-fold propensity scores
        auc: Average AUC across folds
    """
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    ps_hat = np.zeros(len(T))
    aucs = []

    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        T_train, T_val = T[train_idx], T[val_idx]

        # Fit propensity model
        ps_model = LogisticRegression(max_iter=500, random_state=seed)
        ps_model.fit(X_train, T_train)

        # Predict on validation fold
        ps_val = ps_model.predict_proba(X_val)[:, 1]
        ps_hat[val_idx] = ps_val

        # Calculate AUC for this fold
        if len(np.unique(T_val)) > 1:
            aucs.append(roc_auc_score(T_val, ps_val))

    # Clip propensity scores
    ps_hat = np.clip(ps_hat, 1e-3, 1 - 1e-3)

    avg_auc = np.mean(aucs) if aucs else 0.5

    return ps_hat, avg_auc


def fit_outcomes_crossfit(
    X: np.ndarray,
    Y: np.ndarray,
    T: np.ndarray,
    n_splits: int = 5,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit outcome models with K-fold cross-fitting.
    Separate models for treated (m1) and control (m0).

    Args:
        X: Covariate matrix
        Y: Outcome vector
        T: Treatment vector
        n_splits: Number of folds
        seed: Random seed

    Returns:
        m1_hat: Out-of-fold predictions E[Y|T=1,X]
        m0_hat: Out-of-fold predictions E[Y|T=0,X]
    """
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    m1_hat = np.zeros(len(Y))
    m0_hat = np.zeros(len(Y))

    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        Y_train, T_train = Y[train_idx], T[train_idx]

        # Indices for treated and control in training set
        treated_idx = T_train == 1
        control_idx = T_train == 0

        # Fit outcome model for treated
        if treated_idx.sum() > 10:  # Need minimum samples
            m1_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=3,
                random_state=seed
            )
            m1_model.fit(X_train[treated_idx], Y_train[treated_idx])
            m1_hat[val_idx] = m1_model.predict_proba(X_val)[:, 1]


        else:
            m1_hat[val_idx] = Y_train[treated_idx].mean() if treated_idx.sum() > 0 else 0


        # Fit outcome model for control
        if control_idx.sum() > 10:
            m0_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=3,
                random_state=seed
            )
            m0_model.fit(X_train[control_idx], Y_train[control_idx])
            m0_hat[val_idx] = m0_model.predict_proba(X_val)[:, 1]

        else:
            m0_hat[val_idx] = Y_train[control_idx].mean() if control_idx.sum() > 0 else 0

    return m1_hat, m0_hat


def estimate_aipw(
    Y: np.ndarray,
    T: np.ndarray,
    m1: np.ndarray,
    m0: np.ndarray,
    ps: np.ndarray
) -> Tuple[float, float, Tuple[float, float], np.ndarray]:
    """
    Estimate Average Treatment Effect using AIPW/Doubly-Robust estimator.

    Args:
        Y: Outcome vector
        T: Treatment vector
        m1: Predicted outcomes under treatment
        m0: Predicted outcomes under control
        ps: Propensity scores

    Returns:
        ate: Point estimate
        se: Standard error
        ci: 95% confidence interval
        psi: Influence function values
    """
    # Influence function
    psi = (
        T * (Y - m1) / ps -
        (1 - T) * (Y - m0) / (1 - ps) +
        (m1 - m0)
    )

    # Point estimate
    ate = np.mean(psi)

    # Standard error
    n = len(psi)
    se = np.std(psi) / np.sqrt(n)

    # 95% CI
    ci_lower = ate - 1.96 * se
    ci_upper = ate + 1.96 * se

    return ate, se, (ci_lower, ci_upper), psi


def estimate_ipw(
    Y: np.ndarray,
    T: np.ndarray,
    ps: np.ndarray,
    n_bootstrap: int = 500,
    seed: int = 42
) -> Tuple[float, Tuple[float, float]]:
    """
    Estimate ATE using IPW (Hajek stabilized) with bootstrap CI.

    Args:
        Y: Outcome vector
        T: Treatment vector
        ps: Propensity scores
        n_bootstrap: Number of bootstrap samples
        seed: Random seed

    Returns:
        ate: Point estimate
        ci: 95% bootstrap confidence interval
    """
    np.random.seed(seed)

    def ipw_hajek(Y, T, ps):
        """Hajek-stabilized IPW estimator."""
        w1 = T / ps
        w0 = (1 - T) / (1 - ps)

        # Stabilized weights
        w1_sum = w1.sum()
        w0_sum = w0.sum()

        if w1_sum > 0 and w0_sum > 0:
            ate = (Y * w1).sum() / w1_sum - (Y * w0).sum() / w0_sum
        else:
            ate = 0

        return ate

    # Point estimate
    ate = ipw_hajek(Y, T, ps)

    # Bootstrap CI
    n = len(Y)
    bootstrap_ates = []

    for _ in range(n_bootstrap):
        idx = np.random.choice(n, n, replace=True)
        bootstrap_ates.append(ipw_hajek(Y[idx], T[idx], ps[idx]))

    ci_lower = np.percentile(bootstrap_ates, 2.5)
    ci_upper = np.percentile(bootstrap_ates, 97.5)

    return ate, (ci_lower, ci_upper)


def stratified_size_weighted_ate(
    df: pd.DataFrame,
    outcome_col: str = 'outcome_booking_7d',
    treatment_col: str = 'treatment',
    stratum_col: str = 'stratum'
) -> Tuple[float, Tuple[float, float]]:
    """
    Compute stratified size-weighted ATE.

    Args:
        df: Input dataframe
        outcome_col: Name of outcome column
        treatment_col: Name of treatment column
        stratum_col: Name of stratum column

    Returns:
        ate: Size-weighted ATE
        ci: 95% confidence interval
    """
    strata_effects = []
    strata_weights = []
    strata_vars = []

    for stratum in df[stratum_col].unique():
        stratum_df = df[df[stratum_col] == stratum]

        treated = stratum_df[stratum_df[treatment_col] == 1]
        control = stratum_df[stratum_df[treatment_col] == 0]

        if len(treated) > 0 and len(control) > 0:
            # Stratum effect
            effect = treated[outcome_col].mean() - control[outcome_col].mean()

            # Stratum weight (proportion of total sample)
            weight = len(stratum_df) / len(df)

            # Stratum variance
            var_t = treated[outcome_col].var() / len(treated) if len(treated) > 1 else 0
            var_c = control[outcome_col].var() / len(control) if len(control) > 1 else 0
            stratum_var = var_t + var_c

            strata_effects.append(effect)
            strata_weights.append(weight)
            strata_vars.append(stratum_var)

    if not strata_effects:
        return 0, (0, 0)

    # Weighted average
    weights = np.array(strata_weights)
    effects = np.array(strata_effects)
    vars = np.array(strata_vars)

    ate = np.sum(weights * effects)

    # Weighted variance
    weighted_var = np.sum(weights**2 * vars)
    se = np.sqrt(weighted_var)

    ci_lower = ate - 1.96 * se
    ci_upper = ate + 1.96 * se

    return ate, (ci_lower, ci_upper)


def cate_aipw(
    df: pd.DataFrame,
    by_cols: Union[str, List[str]],
    Y: np.ndarray,
    T: np.ndarray,
    m1: np.ndarray,
    m0: np.ndarray,
    ps: np.ndarray,
    min_per_arm: int = 60,
    need_sig: bool = False
) -> pd.DataFrame:
    """
    Compute Conditional Average Treatment Effects (CATEs) using AIPW.

    Args:
        df: Input dataframe
        by_cols: Column(s) to group by
        Y, T, m1, m0, ps: Arrays from main AIPW estimation
        min_per_arm: Minimum samples per arm
        need_sig: Whether to filter for significant effects only

    Returns:
        DataFrame with CATE estimates
    """
    if isinstance(by_cols, str):
        by_cols = [by_cols]

    results = []

    for group_vals, group_df in df.groupby(by_cols):
        if len(by_cols) == 1:
            group_vals = [group_vals]

        indices = group_df.index.values

        # Check minimum samples per arm
        n_treated = (T[indices] == 1).sum()
        n_control = (T[indices] == 0).sum()

        if n_treated >= min_per_arm and n_control >= min_per_arm:
            # AIPW for this segment
            ate_seg, se_seg, ci_seg, _ = estimate_aipw(
                Y[indices], T[indices],
                m1[indices], m0[indices],
                ps[indices]
            )

            # Convert to percentage points
            ate_pp = ate_seg * 100
            ci_lower_pp = ci_seg[0] * 100
            ci_upper_pp = ci_seg[1] * 100

            # Check if significant and positive
            is_significant = ci_lower_pp > 0

            if not need_sig or is_significant:
                result = {col: val for col, val in zip(by_cols, group_vals)}
                result.update({
                    'n': len(indices),
                    'n_B': n_treated,
                    'n_A': n_control,
                    'estimated_uplift_pp': round(ate_pp, 2),
                    'ci95_lower_pp': round(ci_lower_pp, 2),
                    'ci95_upper_pp': round(ci_upper_pp, 2)
                })
                results.append(result)

    return pd.DataFrame(results)


def balance_smd(
    df: pd.DataFrame,
    X_cols: List[str],
    T: np.ndarray,
    weights: Optional[np.ndarray] = None
) -> pd.DataFrame:
    """
    Calculate Standardized Mean Differences (SMD) for covariate balance.

    Args:
        df: Input dataframe
        X_cols: Covariate column names
        T: Treatment vector
        weights: Optional IPW weights

    Returns:
        DataFrame with SMD values
    """
    results = []

    for col in X_cols:
        # For categorical variables, use proportion in each category
        if df[col].dtype == 'object' or col in ['district', 'locale', 'age_band', 'prior_engagement', 'send_time']:
            # Get unique values
            unique_vals = df[col].unique()

            for val in unique_vals:
                indicator = (df[col] == val).astype(float).values

                # Unweighted SMD
                mean_t = indicator[T == 1].mean()
                mean_c = indicator[T == 0].mean()
                var_t = indicator[T == 1].var()
                var_c = indicator[T == 0].var()

                pooled_std = np.sqrt((var_t + var_c) / 2)
                smd_unweighted = (mean_t - mean_c) / pooled_std if pooled_std > 0 else 0

                # Weighted SMD if weights provided
                if weights is not None:
                    w_t = weights[T == 1]
                    w_c = weights[T == 0]

                    mean_t_w = np.average(indicator[T == 1], weights=w_t)
                    mean_c_w = np.average(indicator[T == 0], weights=w_c)

                    var_t_w = np.average((indicator[T == 1] - mean_t_w)**2, weights=w_t)
                    var_c_w = np.average((indicator[T == 0] - mean_c_w)**2, weights=w_c)

                    pooled_std_w = np.sqrt((var_t_w + var_c_w) / 2)
                    smd_weighted = (mean_t_w - mean_c_w) / pooled_std_w if pooled_std_w > 0 else 0
                else:
                    smd_weighted = np.nan

                results.append({
                    'covariate': f"{col}={val}",
                    'smd_unweighted': round(smd_unweighted, 3),
                    'smd_weighted': round(smd_weighted, 3) if not np.isnan(smd_weighted) else np.nan,
                    'balanced': abs(smd_unweighted) <= 0.1
                })

        else:  # Numeric variable
            vals = df[col].values

            # Unweighted SMD
            mean_t = vals[T == 1].mean()
            mean_c = vals[T == 0].mean()
            var_t = vals[T == 1].var()
            var_c = vals[T == 0].var()

            pooled_std = np.sqrt((var_t + var_c) / 2)
            smd_unweighted = (mean_t - mean_c) / pooled_std if pooled_std > 0 else 0

            # Weighted SMD
            if weights is not None:
                w_t = weights[T == 1]
                w_c = weights[T == 0]

                mean_t_w = np.average(vals[T == 1], weights=w_t)
                mean_c_w = np.average(vals[T == 0], weights=w_c)

                var_t_w = np.average((vals[T == 1] - mean_t_w)**2, weights=w_t)
                var_c_w = np.average((vals[T == 0] - mean_c_w)**2, weights=w_c)

                pooled_std_w = np.sqrt((var_t_w + var_c_w) / 2)
                smd_weighted = (mean_t_w - mean_c_w) / pooled_std_w if pooled_std_w > 0 else 0
            else:
                smd_weighted = np.nan

            results.append({
                'covariate': col,
                'smd_unweighted': round(smd_unweighted, 3),
                'smd_weighted': round(smd_weighted, 3) if not np.isnan(smd_weighted) else np.nan,
                'balanced': abs(smd_unweighted) <= 0.1
            })

    return pd.DataFrame(results)


def plot_propensity_overlap(
    ps: np.ndarray,
    T: np.ndarray,
    output_path: str
) -> None:
    """
    Plot propensity score overlap between treatment arms.

    Args:
        ps: Propensity scores
        T: Treatment vector
        output_path: Path to save plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot histograms
    ax.hist(ps[T == 0], bins=30, alpha=0.5, label='Control (A)', color='blue', density=True)
    ax.hist(ps[T == 1], bins=30, alpha=0.5, label='Treated (B)', color='red', density=True)

    ax.set_xlabel('Propensity Score', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Propensity Score Overlap Check', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Add vertical lines for mean propensity scores
    ax.axvline(ps[T == 0].mean(), color='blue', linestyle='--', alpha=0.7, label=f'Control mean: {ps[T == 0].mean():.3f}')
    ax.axvline(ps[T == 1].mean(), color='red', linestyle='--', alpha=0.7, label=f'Treated mean: {ps[T == 1].mean():.3f}')

    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()


def plot_love_plot(
    smd_df: pd.DataFrame,
    output_path: str
) -> None:
    """
    Create Love plot for SMD visualization.

    Args:
        smd_df: DataFrame with SMD values
        output_path: Path to save plot
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Sort by absolute unweighted SMD
    smd_df_sorted = smd_df.sort_values('smd_unweighted', key=lambda x: abs(x))

    y_pos = np.arange(len(smd_df_sorted))

    # Plot unweighted SMD
    ax.scatter(smd_df_sorted['smd_unweighted'], y_pos,
              color='blue', alpha=0.6, s=50, label='Unweighted')

    # Plot weighted SMD if available
    if 'smd_weighted' in smd_df_sorted.columns:
        weighted_vals = smd_df_sorted['smd_weighted'].dropna()
        if len(weighted_vals) > 0:
            ax.scatter(smd_df_sorted['smd_weighted'], y_pos,
                      color='green', alpha=0.6, s=50, label='IPW Weighted')

    # Add reference lines
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax.axvline(x=-0.1, color='red', linestyle='--', alpha=0.5)
    ax.axvline(x=0.1, color='red', linestyle='--', alpha=0.5)

    # Labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(smd_df_sorted['covariate'], fontsize=8)
    ax.set_xlabel('Standardized Mean Difference', fontsize=12)
    ax.set_title('Covariate Balance (Love Plot)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='x')

    # Add text for threshold
    ax.text(0.1, len(smd_df_sorted) - 1, 'Balance threshold',
           color='red', alpha=0.7, fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()


# CHANGE 1: The entire `write_markdown_report` function has been deleted.


def main():
    """Main execution function."""
    # Parse arguments
    # Simulate command-line arguments for notebook execution
    if 'google.colab' in sys.modules:
        sys.argv = ['causal_impact.py', '--data', '/content/causal_campaign_sim_3000.csv', '--plots'] # Added plots flag
        print("Running in Colab, simulating command-line arguments:", sys.argv)
    args = parse_arguments()

    # Set random seed
    np.random.seed(args.seed)

    # Create output directory
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"=" * 60)
    print(f"CAUSAL IMPACT ANALYSIS")
    print(f"=" * 60)
    print(f"Input file: {args.data}")
    print(f"Output directory: {outdir}")
    print(f"Random seed: {args.seed}")
    print(f"K-fold cross-fitting: {args.kfold}")
    print(f"Min per arm: {args.min_per_arm}")
    print(f"Generate plots: {args.plots}")
    print(f"=" * 60)

    # Load data
    print("\n1. Loading and validating data...")
    try:
        df = pd.read_csv(args.data)
        print(f"   Loaded {len(df):,} rows")
    except Exception as e:
        print(f"ERROR: Failed to load data: {e}")
        sys.exit(1)

    # Validate schema
    try:
        validate_schema(df)
        print("   + Schema validation passed")
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Build covariates
    print("\n2. Building covariate matrix...")
    X, Y, T, feature_names, encoder = build_covariates(df)
    print(f"   Features: {len(feature_names)}")
    print(f"   Treated (B): {T.sum():.0f} ({T.mean()*100:.1f}%)")
    print(f"   Control (A): {(1-T).sum():.0f} ({(1-T).mean()*100:.1f}%)")
    print(f"   Outcome rate: {Y.mean()*100:.2f}%")

    # Fit propensity scores with cross-fitting
    print(f"\n3. Fitting propensity model (k={args.kfold} fold cross-fitting)...")
    ps_hat, prop_auc = fit_propensity_crossfit(X, T, n_splits=args.kfold, seed=args.seed)
    print(f"   Propensity AUC: {prop_auc:.3f}")
    print(f"   PS range: [{ps_hat.min():.3f}, {ps_hat.max():.3f}]")

    # Fit outcome models with cross-fitting
    print(f"\n4. Fitting outcome models (k={args.kfold} fold cross-fitting)...")
    m1_hat, m0_hat = fit_outcomes_crossfit(X, Y, T, n_splits=args.kfold, seed=args.seed)
    print(f"   E[Y|T=1,X] mean: {m1_hat.mean()*100:.2f}%")
    print(f"   E[Y|T=0,X] mean: {m0_hat.mean()*100:.2f}%")

    # Calculate IPW weights for balance checking
    ipw_weights = np.where(T == 1, 1/ps_hat, 1/(1-ps_hat))

    # ========== ESTIMATE ATEs ==========
    print("\n5. Computing causal estimates...")

    # 1. Naive difference-in-means
    ate_naive = Y[T == 1].mean() - Y[T == 0].mean()
    se_naive = np.sqrt(Y[T == 1].var()/T.sum() + Y[T == 0].var()/(1-T).sum())
    ci_naive = (ate_naive - 1.96*se_naive, ate_naive + 1.96*se_naive)

    # 2. Stratified size-weighted
    ate_strat, ci_strat = stratified_size_weighted_ate(df)

    # 3. IPW (Hajek)
    ate_ipw, ci_ipw = estimate_ipw(Y, T, ps_hat, n_bootstrap=500, seed=args.seed)

    # 4. AIPW (Double-robust) - PRIMARY
    ate_aipw, se_aipw, ci_aipw, psi = estimate_aipw(Y, T, m1_hat, m0_hat, ps_hat)

    print(f"\n   === PRIMARY RESULT (AIPW) ===")
    print(f"   ATE: {ate_aipw*100:.2f}pp (95% CI: [{ci_aipw[0]*100:.2f}, {ci_aipw[1]*100:.2f}]pp)")
    print(f"   =============================")

    # Create summary dataframe
    summary_data = [
        {
            'Method': 'Naive diff (biased)',
            'ATE_pp': round(ate_naive * 100, 2),
            'CI_lower_pp': round(ci_naive[0] * 100, 2),
            'CI_upper_pp': round(ci_naive[1] * 100, 2),
            'Notes': 'Simple difference, no adjustment'
        },
        {
            'Method': 'Stratified (size-weighted)',
            'ATE_pp': round(ate_strat * 100, 2),
            'CI_lower_pp': round(ci_strat[0] * 100, 2),
            'CI_upper_pp': round(ci_strat[1] * 100, 2),
            'Notes': 'Weighted by stratum size'
        },
        {
            'Method': 'IPW (Hajek)',
            'ATE_pp': round(ate_ipw * 100, 2),
            'CI_lower_pp': round(ci_ipw[0] * 100, 2),
            'CI_upper_pp': round(ci_ipw[1] * 100, 2),
            'Notes': 'Stabilized IPW, bootstrap CI'
        },
        {
            'Method': 'AIPW (cross-fit, double-robust)',
            'ATE_pp': round(ate_aipw * 100, 2),
            'CI_lower_pp': round(ci_aipw[0] * 100, 2),
            'CI_upper_pp': round(ci_aipw[1] * 100, 2),
            'Notes': 'PRIMARY - Doubly robust with cross-fitting'
        }
    ]

    summary_df = pd.DataFrame(summary_data)

    # Save summary
    summary_path = outdir / 'causal_impact_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\n6. Saved causal impact summary  {summary_path}")

    # ========== COMPUTE CATEs ==========
    print("\n7. Computing segment-level effects (CATEs)...")

    # Single dimensions
    cate_results = {}
    for dim in ['age_band', 'district', 'locale', 'send_time']:
        cate_results[dim] = cate_aipw(
            df, dim, Y, T, m1_hat, m0_hat, ps_hat,
            min_per_arm=args.min_per_arm, need_sig=False
        )

    # District × Age combination
    df['district_age'] = df['district'] + '_' + df['age_band']
    cate_district_age = cate_aipw(
        df, 'district_age', Y, T, m1_hat, m0_hat, ps_hat,
        min_per_arm=args.min_per_arm, need_sig=False
    )

    # Split back the combined column for clarity
    if not cate_district_age.empty:
        # Handle potential errors if split doesn't produce 2 parts
        split_cols = cate_district_age['district_age'].str.split('_', n=1, expand=True)
        if split_cols.shape[1] == 2:
            cate_district_age[['district', 'age_band']] = split_cols
            cate_district_age = cate_district_age.drop('district_age', axis=1)
            # Reorder columns
            cols = ['district', 'age_band'] + [c for c in cate_district_age.columns if c not in ['district', 'age_band']]
            cate_district_age = cate_district_age[cols]
        else:
            print("   Warning: Could not split all 'district_age' values into two parts.")
            # Optionally, handle these rows differently or drop them
            # For now, we'll just keep the original 'district_age' column if splitting fails
            pass


    # Save district × age CATEs
    cate_path = outdir / 'cate_aipw_district_age.csv'
    cate_district_age.to_csv(cate_path, index=False)
    print(f"   Saved district × age CATEs  {cate_path}")

    # ========== RECOMMENDATIONS ==========
    print("\n8. Generating next-wave recommendations...")

    # Collect all segments for recommendations
    all_segments = []

    # Add single-dimension segments
    for dim, df_cate in cate_results.items():
        if not df_cate.empty:
            df_cate_copy = df_cate.copy()
            df_cate_copy['segment_type'] = dim
            all_segments.append(df_cate_copy)

    # Add district × age segments
    if not cate_district_age.empty:
        cate_district_age_copy = cate_district_age.copy()
        cate_district_age_copy['segment_type'] = 'district_age'
        all_segments.append(cate_district_age_copy)

    # Combine and filter for recommendations
    if all_segments:
        recommendations = pd.concat(all_segments, ignore_index=True)

        # Filter: CI lower bound > 0 and min samples satisfied
        recommendations = recommendations[
            (recommendations['ci95_lower_pp'] > 0) &
            (recommendations['n_B'] >= args.min_per_arm) &
            (recommendations['n_A'] >= args.min_per_arm)
        ].sort_values('estimated_uplift_pp', ascending=False)

        # Save recommendations
        rec_path = outdir / 'next_wave_recommendations_aipw.csv'
        recommendations.to_csv(rec_path, index=False)
        print(f"   Found {len(recommendations)} actionable segments")
        print(f"   Saved recommendations  {rec_path}")
    else:
        recommendations = pd.DataFrame()
        print("   No segments met criteria for recommendations")

    # ========== DIAGNOSTICS ==========
    print("\n9. Computing balance diagnostics...")

    # Covariate balance
    covariate_cols = ['district', 'locale', 'age_band', 'prior_engagement', 'send_time', 'chronic_diabetes']
    balance_df = balance_smd(df, covariate_cols, T, weights=ipw_weights)

    # Save balance table
    balance_path = outdir / 'balance_smd.csv'
    balance_df.to_csv(balance_path, index=False)
    print(f"   Saved balance table  {balance_path}")

    # Print balance summary
    n_imbalanced = (abs(balance_df['smd_unweighted']) > 0.1).sum()
    if n_imbalanced > 0:
        print(f"    {n_imbalanced} covariates have |SMD| > 0.1 (pre-weighting)")
    else:
        print(f"    All covariates balanced (|SMD| ≤ 0.1)")

    # ========== PLOTS ==========
    if args.plots:
        print("\n10. Generating diagnostic plots...")

        # Propensity overlap plot
        prop_plot_path = outdir / 'propensity_overlap.png'
        plot_propensity_overlap(ps_hat, T, prop_plot_path)
        print(f"   Saved propensity overlap plot  {prop_plot_path}")

        # Love plot
        love_plot_path = outdir / 'love_plot.png'
        plot_love_plot(balance_df, love_plot_path)
        print(f"   Saved love plot  {love_plot_path}")

    # ========== OPTIONAL EXTRAS ==========
    print("\n11. Checking for optional methods...")

    # Try DoWhy if available
    try:
        import dowhy
        from dowhy import CausalModel

        print("   Found DoWhy - adding propensity score matching estimate...")

        # Prepare data for DoWhy
        dowhy_df = df.copy()
        dowhy_df['Y'] = Y
        dowhy_df['T'] = T

        # Build causal model
        model = CausalModel(
            data=dowhy_df,
            treatment='T',
            outcome='Y',
            common_causes=['district', 'locale', 'age_band', 'prior_engagement', 'send_time', 'chronic_diabetes']
        )

        # Identify effect
        identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)

        # Estimate using propensity score matching
        ps_match_estimate = model.estimate_effect(
            identified_estimand,
            method_name="backdoor.propensity_score_matching",
            random_seed=args.seed
        )

        ate_ps_match = ps_match_estimate.value

        # Add to summary
        summary_df = pd.concat([
            summary_df,
            pd.DataFrame([{
                'Method': 'PS Matching (DoWhy)',
                'ATE_pp': round(ate_ps_match * 100, 2),
                'CI_lower_pp': np.nan,
                'CI_upper_pp': np.nan,
                'Notes': 'Propensity score matching via DoWhy'
            }])
        ], ignore_index=True)

        # Re-save summary
        summary_df.to_csv(summary_path, index=False)
        print(f"   Added PS matching estimate: {ate_ps_match*100:.2f}pp")

    except ImportError:
        print("   DoWhy not installed - skipping PS matching")
    except Exception as e:
        print(f"   DoWhy error: {e}")

    # Try EconML if available
    try:
        from econml.metalearners import XLearner
        from lightgbm import LGBMRegressor

        print("   Found EconML + LightGBM - adding X-learner estimate...")

        # X-learner
        x_learner = XLearner(
            models=LGBMRegressor(n_estimators=100, max_depth=3, random_state=args.seed, verbosity=-1),
            propensity_model=LogisticRegression(max_iter=500, random_state=args.seed),
            random_state=args.seed
        )

        x_learner.fit(Y, T, X=X)
        ate_xlearner = x_learner.ate(X)

        print(f"   X-learner ATE: {ate_xlearner*100:.2f}pp")

    except ImportError:
        print("   EconML/LightGBM not installed - skipping X-learner")
    except Exception as e:
        print(f"   EconML error: {e}")

    # ========== LLM REPORT (NOW PRIMARY) ==========
    # CHANGE 2: Updated the print statement and removed the call to the old report writer.
    print("\n12. Generating final LLM summary report...")
    generate_llm_report(outdir, ate_aipw, ci_aipw, recommendations)


    # ========== FINAL OUTPUT ==========
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\n PRIMARY RESULT (AIPW Double-Robust):")
    print(f"   ATE = {ate_aipw*100:.2f}pp")
    print(f"   95% CI = [{ci_aipw[0]*100:.2f}, {ci_aipw[1]*100:.2f}]pp")
    print(f"\n Model Performance:")
    print(f"   Propensity AUC = {prop_auc:.3f}")
    print(f"\n Targeting Recommendations:")
    print(f"   {len(recommendations)} segments identified for next wave")
    print(f"   See: {outdir / 'next_wave_recommendations_aipw.csv'}")

    print(f"\n All outputs saved to: {outdir}/")
    print("=" * 60)


if __name__ == "__main__":

    # Simulate command-line arguments for notebook execution
    if 'google.colab' in sys.modules:
        sys.argv = ['causal_impact.py', '--data', '/content/causal_campaign_sim_3000.csv', '--plots'] # Added plots flag
        print("Running in Colab, simulating command-line arguments:", sys.argv)
    main()