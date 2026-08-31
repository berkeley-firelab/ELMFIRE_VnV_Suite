#!/usr/bin/env python3
"""Postprocess the merged structural-resolution WUI verification suite.

The script reads real ELMFIRE GeoTIFF outputs when present, aggregates raster
cells by physical structure, computes declared pass/fail metrics, and always
writes a complete metrics table and a report-ready vector figure.
"""

from osgeo import gdal
from spatial_evidence import generate_spatial_evidence
import numpy as np
from pathlib import Path
import json
import math
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Customizable postprocessing and numerical-reference parameters.
FINAL_EMBER_GLOB = "ember_flux_[0-9]*.tif"
FINAL_TOA_GLOB = "time_of_arrival_[0-9]*.tif"
INVALID_OUTPUT_MIN = -1000.0
ANALYTICAL_DT_S = 5.0
AIR_DENSITY_KG_M3 = 1.1
AIR_HEAT_CAPACITY_KJ_KG_K = 1.0
AMBIENT_TEMPERATURE_K = 300.0
GRAVITY_M_S2 = 9.81
STRUCTURE_LENGTH_M = 10.0
FIREBRAND_DENSITY_KG_M3 = 100.0
FIREBRAND_DIAMETER_M = 5.0e-3
EXPECTED_THRESHOLD_TIME_S = 2496.9
EXPECTED_FULL_IGNITION_TIME_S = 2858.8
EXPECTED_BASELINE_ROS_M_S = 0.006
EXPECTED_FINE_ROS_M_S = 0.001
METRIC_DISPLAY_DIGITS = 4
FIGURE_DPI = 180

COLORS = {
    "baseline": "#1f77b4",
    "native_fine": "#d62728",
    "native_coarse": "#ff7f0e",
    "integrated_aligned": "#2ca02c",
    "integrated_misaligned": "#9467bd",
}


def read_band(path):
    """Read one raster band as float and retain NoData as NaN."""
    ds = gdal.Open(str(path))
    if ds is None:
        raise RuntimeError(f"Could not open {path}")
    band = ds.GetRasterBand(1)
    array = band.ReadAsArray().astype(float)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        array[np.isclose(array, nodata)] = np.nan
    return array


def final_output(directory, pattern):
    """Choose the latest lexically sorted final raster, excluding transients."""
    paths = [p for p in directory.glob(pattern) if "_transient_" not in p.name]
    return sorted(paths)[-1] if paths else None


def terminal_time_s(path):
    """Read integer terminal seconds from an ELMFIRE final-raster filename."""
    match = re.search(r"_(\d+)\.tif$", path.name)
    return float(match.group(1)) if match else math.nan


def structure_profiles(case_dir, case, item):
    """Return per-cell and per-structure values from one completed variant."""
    variant_dir = case_dir / item["working_directory"]
    fingerprint_file = variant_dir / "logs" / "completed_input_fingerprint.txt"
    if not fingerprint_file.exists():
        return None
    if fingerprint_file.read_text(
            encoding="utf-8").strip() != item.get("input_fingerprint"):
        return None
    output_dir = variant_dir / "outputs"
    ember_path = final_output(output_dir, FINAL_EMBER_GLOB)
    toa_path = final_output(output_dir, FINAL_TOA_GLOB)
    if ember_path is None or toa_path is None:
        return None
    # Input fingerprints alone cannot detect a changed TSTOP.  Reject otherwise
    # compatible rasters unless both terminal filenames match this manifest.
    expected_tstop = float(item["tstop_s"])
    if (
        not np.isclose(terminal_time_s(ember_path), expected_tstop, atol=1.0)
        or not np.isclose(terminal_time_s(toa_path), expected_tstop, atol=1.0)
    ):
        return None

    ids = read_band(variant_dir / "data/inputs/structure_id.tif")
    ember = read_band(ember_path)
    toa = read_band(toa_path)
    row = int(item["center_row"])
    buffer_cells = int(item["buffer_cells"])
    stop = ids.shape[1] - buffer_cells
    raw_ids = np.nan_to_num(
        ids[row, buffer_cells:stop], nan=0.0
    ).astype(int)
    n_structures_x = int(item["n_structures_x"])
    raw_x_index = np.where(
        raw_ids > 0, (raw_ids - 1) % n_structures_x, -1
    )
    present_x = sorted(set(raw_x_index[raw_x_index >= 0]))
    ids_row = np.zeros(raw_ids.shape, dtype=int)
    for sequential_id, x_index in enumerate(present_x, start=1):
        ids_row[raw_x_index == x_index] = sequential_id
    ember_count = ember[row, buffer_cells:stop]
    toa_row = toa[row, buffer_cells:stop]
    dx = float(item["dx_m"])
    cell_density = ember_count / (dx * dx)

    profile = {
        "name": item["name"],
        "role": item["role"],
        "ids": [],
        "x_m": [],
        "load_pcs_m2": [],
        "ignition_s": [],
        "within_relative_range": [],
        "cell_x_m": (np.arange(ids_row.size) + 0.5) * dx,
        "cell_density_pcs_m2": cell_density,
        "cell_structure_ids": ids_row,
        "ember_file": ember_path.name,
        "toa_file": toa_path.name,
    }
    for structure_id in sorted(set(ids_row[ids_row > 0])):
        mask = ids_row == structure_id
        valid_load = np.isfinite(ember_count[mask])
        total_count = float(
            np.nansum(
                ember_count[mask])) if valid_load.any() else math.nan
        valid_toa = toa_row[mask]
        valid_toa = valid_toa[np.isfinite(valid_toa) & (valid_toa > INVALID_OUTPUT_MIN)]
        densities = cell_density[mask]
        densities = densities[np.isfinite(densities)]
        relative_range = math.nan
        if densities.size > 1 and np.mean(densities) > 0.0:
            relative_range = float(
                (np.max(densities) - np.min(densities)) / np.mean(densities))
        profile["ids"].append(int(structure_id))
        cell_centres = (np.flatnonzero(mask) + 0.5) * dx
        represented_area = np.count_nonzero(mask) * dx * dx
        profile["x_m"].append(float(np.mean(cell_centres)))
        profile["load_pcs_m2"].append(total_count / represented_area)
        profile["ignition_s"].append(
            float(np.min(valid_toa)) if valid_toa.size else math.nan)
        profile["within_relative_range"].append(relative_range)
    for key in ("x_m", "load_pcs_m2", "ignition_s", "within_relative_range"):
        profile[key] = np.asarray(profile[key], dtype=float)
    profile["ids"] = np.asarray(profile["ids"], dtype=int)
    return profile


def design_hrr_kw(case, elapsed_s):
    """Piecewise structural design fire curve for one 10 m by 10 m structure."""
    if elapsed_s <= 0.0 or elapsed_s >= case["hrr_decay_end_s"]:
        return 0.0
    peak = case["hrrpua_peak_kw_m2"] * \
        case["structure_width_m"] * case["cross_grid_width_m"]
    if elapsed_s < case["hrr_growth_end_s"]:
        return peak * elapsed_s / case["hrr_growth_end_s"]
    if elapsed_s <= case["hrr_steady_end_s"]:
        return peak
    return peak * (
        case["hrr_decay_end_s"] - elapsed_s
    ) / (case["hrr_decay_end_s"] - case["hrr_steady_end_s"])


def lognormal_cdf(distance, mu_log, sigma_log):
    """Lognormal CDF matching EMPIRICAL_PDF_PARAMETERS in elmfire_spotting.f90."""
    if distance <= 0.0:
        return 0.0
    z = (math.log(max(distance, 1.0e-6)) - mu_log) / (math.sqrt(2.0) * sigma_log)
    return 0.5 * (1.0 + math.erf(z))


def himoto_parameters(case, hrr_kw):
    """Return log-space Himoto parameters from reference Eqs. 6.3--6.4."""
    wind = 0.447 * case["wind_speed_mph"] / 0.87
    length = STRUCTURE_LENGTH_M
    b_star = (
        wind / math.sqrt(GRAVITY_M_S2 * length)
        * (FIREBRAND_DENSITY_KG_M3 / AIR_DENSITY_KG_M3) ** (-0.75)
        * (FIREBRAND_DIAMETER_M / length) ** (-0.75)
        * (
            hrr_kw
            / (
                AIR_DENSITY_KG_M3 * AIR_HEAT_CAPACITY_KJ_KG_K
                * AMBIENT_TEMPERATURE_K * math.sqrt(GRAVITY_M_S2)
                * length ** 2.5
            )
        ) ** 0.5
    )
    mean_x = max(0.47 * b_star ** (2.0 / 3.0) * length, 1.0e-5)
    sigma_x = max(0.88 * b_star ** (1.0 / 3.0) * length, 1.0e-5)
    mu_log = math.log(mean_x / math.sqrt((sigma_x / mean_x) ** 2 + 1.0))
    sigma_log = math.sqrt(math.log(1.0 + (sigma_x / mean_x) ** 2))
    return mu_log, sigma_log


def analytical_load(case, profile, tstop_s):
    """Integrate analytical deposited load using simulated source ignition times."""
    values = np.zeros(profile["ids"].size, dtype=float)
    width = float(case["structure_width_m"])
    area = width * float(case["cross_grid_width_m"])
    generation = float(case["ember_generation_building_pcs_mw_s"])
    for target in range(profile["ids"].size):
        target_center = profile["x_m"][target]
        for source in range(target):
            ignition = profile["ignition_s"][source]
            if not np.isfinite(ignition):
                continue
            elapsed_max = min(case["hrr_decay_end_s"], tstop_s - ignition)
            if elapsed_max <= 0.0:
                continue
            for elapsed in np.arange(
                    0.5 * ANALYTICAL_DT_S,
                    elapsed_max,
                    ANALYTICAL_DT_S):
                hrr_kw = design_hrr_kw(case, elapsed)
                if hrr_kw <= 0.0:
                    continue
                mu_log, sigma_log = himoto_parameters(case, hrr_kw)
                relative_center = target_center - profile["x_m"][source]
                probability = (lognormal_cdf(relative_center + 0.5 * width,
                                             mu_log,
                                             sigma_log) - lognormal_cdf(max(0.0,
                                                                            relative_center - 0.5 * width),
                               mu_log,
                               sigma_log))
                values[target] += generation * \
                    (hrr_kw / 1000.0) * probability * ANALYTICAL_DT_S
    return values / area


def mean_ros(profile):
    """Fit ignition time against structure centre and invert the slope."""
    mask = np.isfinite(profile["ignition_s"]) & (profile["ids"] >= 2)
    if np.count_nonzero(mask) < 2:
        return math.nan
    slope = np.polyfit(profile["x_m"][mask], profile["ignition_s"][mask], 1)[0]
    return float(1.0 / slope) if slope > 0.0 else math.nan


def relative_errors(a, b):
    """Return finite absolute relative errors using b as the reference."""
    mask = np.isfinite(a) & np.isfinite(b) & (np.abs(b) > 1.0e-12)
    return np.abs(a[mask] - b[mask]) / np.abs(b[mask])


def matched_errors(candidate, baseline, field):
    """Compare profiles at common physical structure IDs."""
    common = sorted(set(candidate["ids"]).intersection(set(baseline["ids"])))
    left, right = [], []
    for sid in common:
        left.append(candidate[field][np.where(candidate["ids"] == sid)[0][0]])
        right.append(baseline[field][np.where(baseline["ids"] == sid)[0][0]])
    return relative_errors(np.asarray(left), np.asarray(right))


def metric(name, limit, calculated=None, passed=None, note=""):
    """Create a complete metric row; unavailable calculations never leave blanks."""
    if calculated is None:
        calculated_text = "N/A"
        status = "NOT EVALUATED"
    elif isinstance(calculated, (int, float, np.floating)) and not np.isfinite(calculated):
        calculated_text = "N/A"
        status = "NOT EVALUATED"
        note = note or "The required finite comparison value was unavailable."
    else:
        calculated_text = (
            f"{calculated:.{METRIC_DISPLAY_DIGITS}g}"
            if isinstance(calculated, (int, float, np.floating)) else str(calculated)
        )
        status = "PASS" if passed else "FAIL"
    return {
        "metric": name, "limit": limit, "calculated": calculated_text,
        "status": status, "note": note,
    }


def calculate_metrics(case, manifest, profiles):
    """Apply the case-specific decision contract to available profiles."""
    limits = case["metrics"]
    rows = []
    baseline = profiles.get("baseline")
    fine = profiles.get("native_fine")
    coarse = profiles.get("native_coarse")

    if baseline is None:
        rows.extend([metric("exact-grid baseline load mean relative error",
                            f"<= {limits['baseline_load_mean_relative_error_max']}"),
                     metric("exact-grid baseline ignition-time relative error",
                            f"<= {limits['baseline_ignition_relative_error_max']}"),
                     ])
    else:
        reference = analytical_load(case, baseline, next(
            item["tstop_s"] for item in manifest if item["role"] == "baseline"
        ))
        errors = relative_errors(baseline["load_pcs_m2"][1:], reference[1:])
        load_mre = float(np.mean(errors)) if errors.size else math.nan
        second = np.where(baseline["ids"] == 2)[0]
        ignition = baseline["ignition_s"][second[0]] if second.size else math.nan
        ignition_error = abs(ignition - EXPECTED_FULL_IGNITION_TIME_S) / \
            EXPECTED_FULL_IGNITION_TIME_S
        rows.extend([
            metric("exact-grid baseline load mean relative error",
                   f"<= {limits['baseline_load_mean_relative_error_max']}", load_mre,
                   np.isfinite(load_mre) and load_mre <= limits["baseline_load_mean_relative_error_max"]),
            metric("exact-grid baseline ignition-time relative error",
                   f"<= {limits['baseline_ignition_relative_error_max']}", ignition_error,
                   np.isfinite(ignition_error) and ignition_error <= limits["baseline_ignition_relative_error_max"]),
        ])
        baseline["analytical_load_pcs_m2"] = reference

    if fine is None or baseline is None:
        rows.extend([
            metric("native fine-grid variant within-structure load range",
                   f">= {limits['fine_within_structure_relative_range_min']}"),
            metric("native fine-grid variant ROS ratio to baseline",
                   f"<= {limits['fine_ros_ratio_to_baseline_max']}"),
        ])
    else:
        ranges = fine["within_relative_range"]
        ranges = ranges[np.isfinite(ranges)]
        range_value = float(np.median(ranges)) if ranges.size else math.nan
        ros_base, ros_fine = mean_ros(baseline), mean_ros(fine)
        ratio = ros_fine / ros_base if ros_base > 0.0 else math.nan
        rows.extend([
            metric("native fine-grid variant within-structure load range",
                   f">= {limits['fine_within_structure_relative_range_min']}", range_value,
                   np.isfinite(range_value) and range_value >= limits["fine_within_structure_relative_range_min"]),
            metric("native fine-grid variant ROS ratio to baseline",
                   f"<= {limits['fine_ros_ratio_to_baseline_max']}", ratio,
                   np.isfinite(ratio) and ratio <= limits["fine_ros_ratio_to_baseline_max"]),
        ])

    if coarse is None or baseline is None:
        rows.append(
            metric(
                "native coarse-grid variant baseline/coarse load ratio",
                f"{limits['coarse_load_ratio_reference']} +/- {100*limits['coarse_load_ratio_relative_error_max']:.0f}%"))
    else:
        baseline_sid = 4  # 60--70 m native structure
        coarse_sid = 2    # 60--90 m mode-resampled structure
        bi = np.where(baseline["ids"] == baseline_sid)[0]
        ci = np.where(coarse["ids"] == coarse_sid)[0]
        ratio = (
            baseline["load_pcs_m2"][bi[0]] / coarse["load_pcs_m2"][ci[0]]
            if bi.size and ci.size and coarse["load_pcs_m2"][ci[0]] != 0 else math.nan
        )
        ref = limits["coarse_load_ratio_reference"]
        ratio_error = abs(ratio - ref) / ref
        rows.append(
            metric(
                "native coarse-grid variant baseline/coarse load ratio",
                f"{ref} +/- {100*limits['coarse_load_ratio_relative_error_max']:.0f}%",
                ratio,
                np.isfinite(ratio_error) and ratio_error <= limits["coarse_load_ratio_relative_error_max"]))

    for role, test, load_key, ignition_key, reducer in (
        ("integrated_aligned", "integrated aligned variant", "aligned_load_mean_relative_error_max",
         "aligned_ignition_mean_relative_error_max", np.mean),
        ("integrated_misaligned", "integrated misaligned variant", "misaligned_load_max_relative_error_max",
         "misaligned_ignition_max_relative_error_max", np.max),
    ):
        candidate = profiles.get(role)
        item = next(entry for entry in manifest if entry["role"] == role)
        if not item["runnable"] or candidate is None or baseline is None:
            note = item["capability_status"]
            rows.extend([
                metric(f"{test} structure-load relative error", f"<= {limits[load_key]}", note=note),
                metric(f"{test} ignition-time relative error", f"<= {limits[ignition_key]}", note=note),
            ])
        else:
            load_errors = matched_errors(candidate, baseline, "load_pcs_m2")
            ignition_errors = matched_errors(candidate, baseline, "ignition_s")
            load_value = float(reducer(load_errors)) if load_errors.size else math.nan
            ignition_value = float(
                reducer(ignition_errors)) if ignition_errors.size else math.nan
            rows.extend([
                metric(f"{test} structure-load relative error", f"<= {limits[load_key]}",
                       load_value, np.isfinite(load_value) and load_value <= limits[load_key]),
                metric(f"{test} ignition-time relative error", f"<= {limits[ignition_key]}",
                       ignition_value, np.isfinite(ignition_value) and ignition_value <= limits[ignition_key]),
            ])
    evaluated_native = [row for row in rows[:5] if row["status"] != "NOT EVALUATED"]
    native_status = (
        "NOT RUN" if not evaluated_native else
        ("PASS" if all(row["status"] == "PASS" for row in evaluated_native) else "FAIL")
    )
    missing_capability = any(not item["runnable"] for item in manifest)
    overall = (
        "NOT EVALUATED (capability missing)" if missing_capability else
        ("PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL")
    )
    return rows, native_status, overall


def plot_reference_figures(case_dir, case, profiles):
    """Write one reference-aligned physical-state figure per native grid regime."""
    labels = {
        "baseline": "exact-grid baseline",
        "native_fine": "native fine grid",
        "native_coarse": "native coarse grid",
    }
    expected_ros = {
        "baseline": EXPECTED_BASELINE_ROS_M_S,
        "native_fine": EXPECTED_FINE_ROS_M_S,
        "native_coarse": EXPECTED_BASELINE_ROS_M_S,
    }
    for role in ("baseline", "native_fine", "native_coarse"):
        profile = profiles.get(role)
        fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.2), constrained_layout=True)
        if profile is None:
            for axis in axes.flat:
                axis.text(0.5, 0.5, "Current matching output not available",
                          ha="center", va="center", transform=axis.transAxes)
        else:
            if role == "native_fine":
                mask = profile["cell_structure_ids"] > 0
                axes[0, 0].plot(profile["cell_x_m"][mask],
                                profile["cell_density_pcs_m2"][mask],
                                color=COLORS[role], marker="o", markersize=2.2,
                                linewidth=1.0, label="ELMFIRE cell load")
            else:
                axes[0, 0].plot(profile["x_m"], profile["load_pcs_m2"],
                                color=COLORS[role], marker="o", markersize=3,
                                linewidth=1.1, label="ELMFIRE structure load")
            if role == "baseline" and "analytical_load_pcs_m2" in profile:
                axes[0, 0].plot(profile["x_m"], profile["analytical_load_pcs_m2"],
                                "k--", linewidth=1.4,
                                label="analytical deposited-load reference")
            axes[0, 0].axhline(case["critical_load_pcs_m2"], color="0.25",
                               linestyle=":", label="critical ignition load")
            finite = np.isfinite(profile["ignition_s"])
            axes[0, 1].plot(profile["x_m"][finite], profile["ignition_s"][finite],
                            color=COLORS[role], marker="o", markersize=3,
                            linewidth=1.1, label="ELMFIRE")
            if role == "baseline":
                axes[0, 1].scatter([25.0], [EXPECTED_FULL_IGNITION_TIME_S],
                                   color="black", marker="x", s=45,
                                   label="second-structure reference")
            if np.count_nonzero(finite) >= 2:
                order = np.argsort(profile["ignition_s"][finite])
                time = profile["ignition_s"][finite][order]
                edge = profile["x_m"][finite][order]
                axes[1, 0].step(time, edge, where="post", color=COLORS[role],
                                label="ELMFIRE leading edge")
                ros = np.diff(edge) / np.diff(time)
                axes[1, 1].plot(time[1:], ros, color=COLORS[role], marker="o",
                                markersize=2.5, linewidth=1.0,
                                label="ELMFIRE instantaneous")
            axes[1, 1].axhline(expected_ros[role], color="black", linestyle="--",
                               label="reference mean ROS")
        axes[0, 0].set(xlabel="Downwind distance [m]",
                       ylabel=r"Accumulated firebrands [pcs/m$^2$]",
                       ylim=(0.0, None))
        axes[0, 1].set(xlabel="Downwind distance [m]", ylabel="Ignition time [s]",
                       ylim=(0.0, None))
        axes[1, 0].set(xlabel="Time [s]", ylabel="Leading-edge position [m]",
                       ylim=(0.0, None))
        axes[1, 1].set(xlabel="Time [s]", ylabel="Leading-edge ROS [m/s]",
                       ylim=(0.0, None))
        for panel, axis in zip(("(a)", "(b)", "(c)", "(d)"), axes.flat):
            axis.text(0.01, 0.98, panel, transform=axis.transAxes,
                      ha="left", va="top", fontweight="bold")
            axis.grid(alpha=0.2)
            handles, _ = axis.get_legend_handles_labels()
            if handles:
                axis.legend(fontsize=7)
        fig.suptitle(labels[role])
        fig.savefig(case_dir / "figures" / f"{role}_reference.pdf", dpi=FIGURE_DPI)
        plt.close(fig)


def plot_figure(case_dir, case, manifest, profiles, rows):
    """Produce a supplemental four-panel cross-variant technical-guide figure."""
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.2), constrained_layout=True)
    ax = axes[0, 0]
    for y, item in enumerate(manifest):
        ids = read_band(
            case_dir /
            item["working_directory"] /
            "data/inputs/structure_id.tif")
        row = ids[int(item["center_row"]), item["buffer_cells"]:-item["buffer_cells"]]
        x = (np.arange(row.size) + 0.5) * item["dx_m"]
        mask = row > 0
        ax.scatter(x[mask], np.full(np.count_nonzero(mask), y), marker="s",
                   s=max(8, 2.5 * item["dx_m"]), color=COLORS[item["role"]],
                   label=item["variant_label"])
    ax.set_yticks(range(len(manifest)), [item["variant_label"] for item in manifest])
    ax.set_xlabel("Downwind distance (m)")
    ax.set_title("(a) Rasterized structure layouts")
    ax.grid(axis="x", alpha=0.25)

    ax = axes[0, 1]
    for role, profile in profiles.items():
        ax.plot(profile["x_m"], profile["load_pcs_m2"], marker="o", ms=3,
                color=COLORS[role], label=role.replace("_", " "))
    if profiles.get(
            "baseline") is not None and "analytical_load_pcs_m2" in profiles["baseline"]:
        base = profiles["baseline"]
        ax.plot(base["x_m"], base["analytical_load_pcs_m2"], "k--", lw=1.5,
                label="Analytical deposited load")
    ax.axhline(
        case["critical_load_pcs_m2"],
        color="0.25",
        ls=":",
        label="critical load")
    ax.set_xlabel("Structure centre x (m)")
    ax.set_ylabel("Accumulated firebrands (pcs/m$^2$)")
    ax.set_title("(b) Structure-integrated deposited load")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)

    ax = axes[1, 0]
    for role, profile in profiles.items():
        ax.plot(profile["x_m"], profile["ignition_s"], marker="o", ms=3,
                color=COLORS[role], label=role.replace("_", " "))
    ax.scatter([25.0], [EXPECTED_FULL_IGNITION_TIME_S], color="k", marker="x",
               s=45, label="reference exact-grid baseline reference")
    ax.set_xlabel("Structure centre x (m)")
    ax.set_ylabel("Full ignition time (s)")
    ax.set_title("(c) Structure ignition chronology")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)

    ax = axes[1, 1]
    labels = [row["metric"].replace("Test ", "T") for row in rows]
    values = [1.0 if row["status"] == "PASS" else (
        1.15 if row["status"] == "FAIL" else 0.0) for row in rows]
    colors = ["#2ca02c" if row["status"] == "PASS" else
              ("#d62728" if row["status"] == "FAIL" else "#bdbdbd") for row in rows]
    positions = np.arange(len(rows))
    ax.barh(positions, values, color=colors)
    ax.axvline(1.0, color="k", ls="--", lw=1)
    ax.set_yticks(positions, labels, fontsize=6)
    ax.set_xlim(0.0, 1.25)
    ax.set_xticks([0, 1], ["not evaluated", "acceptance"])
    ax.set_title("(d) Verification decision summary")
    ax.invert_yaxis()
    fig.savefig(case_dir / "figures" / "wui_structure_resolution.pdf", dpi=FIGURE_DPI)
    plt.close(fig)


def latex_escape(value):
    """Escape dynamic text used in generated table rows."""
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}", "_": r"\_", "%": r"\%",
        "&": r"\&", "#": r"\#", "<=": r"$\leq$",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def write_artifacts(case_dir, case, manifest, profiles, rows, native_status, overall):
    """Write JSON evidence and LaTeX macros with no empty calculated cells."""
    output = {
        "case_id": case["id"],
        "overall_status": overall,
        "native_tests_status": native_status,
        "completed_variants": sorted(profiles),
        "unrun_variants": [
            {"name": item["name"], "reason": item["capability_status"]}
            for item in manifest if item["role"] not in profiles
        ],
        "metrics": rows,
        "normalization": "ember count divided by physical structure area (10 m times cross-grid width)",
        "reference_times_s": {
            "critical_load_crossing": EXPECTED_THRESHOLD_TIME_S,
            "full_ignition": EXPECTED_FULL_IGNITION_TIME_S,
        },
    }
    (case_dir / "outputs").mkdir(exist_ok=True)
    (case_dir / "outputs" / "metrics.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    table_rows = []
    for row in rows:
        table_rows.append(
            "{} & {} & {} & {} \\\\".format(
                latex_escape(row["metric"]), latex_escape(row["limit"]),
                latex_escape(row["calculated"]), latex_escape(row["status"])
            )
        )
    macros = [
        rf"\def\OverallStatus{{{latex_escape(overall)}}}",
        rf"\def\NativeStatus{{{latex_escape(native_status)}}}",
        rf"\def\CompletedVariantCount{{{len(profiles)}}}",
        rf"\def\RequestedVariantCount{{{len(manifest)}}}",
        r"\def\MetricRows{",
        *table_rows,
        "}",
    ]
    (case_dir / "report" / "metrics_macros.tex").write_text(
        "\n".join(macros) + "\n", encoding="utf-8"
    )


def main():
    """Load the manifest, process available runs, and refresh report evidence."""
    case_dir = Path(__file__).resolve().parents[1]
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (case_dir / "variants" / "manifest.json").read_text(encoding="utf-8")
    )
    profiles = {}
    for item in manifest:
        profile = structure_profiles(case_dir, case, item) if item["runnable"] else None
        if profile is not None:
            profiles[item["role"]] = profile
    rows, native_status, overall = calculate_metrics(case, manifest, profiles)
    (case_dir / "figures").mkdir(exist_ok=True)
    plot_reference_figures(case_dir, case, profiles)
    plot_figure(case_dir, case, manifest, profiles, rows)
    write_artifacts(
        case_dir, case, manifest, profiles, rows, native_status, overall
    )
    print(
        f"[OK] postprocessed {len(profiles)}/{len(manifest)} variants; "
        f"overall status: {overall}"
    )


if __name__ == "__main__":
    main()
    generate_spatial_evidence(
        Path(__file__).resolve().parents[1],
        output_preference=("time_of_arrival", "ember_flux"),
        preferred_variant="baseline_dx10",
    )
