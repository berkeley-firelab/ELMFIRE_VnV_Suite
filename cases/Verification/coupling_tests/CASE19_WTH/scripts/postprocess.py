#!/usr/bin/env python3
"""Compare WUI transient heat-flux outputs with a case-local reference algorithm."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from raster_functions import load_stack
from wue_functions import ellipse_ucb, heat_flux_calc, hrr_transient

CASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = CASE_DIR / "outputs"
FIG_DIR = CASE_DIR / "figures"
METRICS_PATH = OUT_DIR / "metrics.json"

NONBURNABLE_FRAC = 0.0
ABSORPTIVITY = 0.89
RADIATION_CUTOFF_M = 100.0
CELL_SIZE_M = 20.0
WIND_DIRECTION_DEG = 0.0
WIND_SPEED_MPH = 15.0
BUILDING_AREA_M = 10.0
BUILDING_SEPARATION_M = 10.0
WIND_PROPORTIONALITY = 1.0
EARLY_TIME_S = 300.0
DEVELOPED_TIME_S = 3900.0
DECAY_TIME_S = 4200.0
PEAK_HRRPUA_KW_M2 = 400.0
RELATIVE_L1_TOLERANCE = 0.005


def write_metrics(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] CASE19_WTH: {payload['overall_status']}")


def reference_fields(times: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate the documented WUI reference algorithm on the 11-by-11 audit window."""
    times = np.asarray(times, dtype=float)
    hrr = np.array([
        hrr_transient(t, EARLY_TIME_S, DEVELOPED_TIME_S, DECAY_TIME_S, PEAK_HRRPUA_KW_M2)
        for t in times
    ])
    dfc = np.zeros((len(times), 11, 11), dtype=float)
    rad = np.zeros_like(dfc)
    ellipse = ellipse_ucb(
        WIND_SPEED_MPH, BUILDING_AREA_M, BUILDING_SEPARATION_M, WIND_PROPORTIONALITY
    )
    offsets = range(-5, 6)
    for it, heat_release in enumerate(hrr):
        for row, idy in enumerate(offsets):
            for column, idx in enumerate(offsets):
                if idx == 0 and idy == 0:
                    continue
                dfc[it, row, column], rad[it, row, column] = heat_flux_calc(
                    heat_release,
                    NONBURNABLE_FRAC,
                    ABSORPTIVITY,
                    RADIATION_CUTOFF_M,
                    ellipse,
                    float(idx),
                    float(idy),
                    CELL_SIZE_M,
                    WIND_DIRECTION_DEG,
                )
    return hrr, dfc, rad


def normalized_l1(reference: np.ndarray, calculated: np.ndarray) -> float:
    """Return sum(abs(error))/sum(abs(reference)) over mutually finite values."""
    ref = np.ma.asarray(reference)
    calc = np.ma.asarray(calculated)
    if ref.shape != calc.shape:
        raise ValueError(f"shape mismatch: reference {ref.shape}, output {calc.shape}")
    mask = (
        ~np.ma.getmaskarray(ref)
        & ~np.ma.getmaskarray(calc)
        & np.isfinite(np.ma.filled(ref, np.nan))
        & np.isfinite(np.ma.filled(calc, np.nan))
    )
    if not np.any(mask):
        raise ValueError("no mutually finite comparison values")
    ref_values = np.asarray(ref)[mask]
    calc_values = np.asarray(calc)[mask]
    denominator = float(np.sum(np.abs(ref_values)))
    numerator = float(np.sum(np.abs(calc_values - ref_values)))
    if denominator <= 1.0e-12:
        return 0.0 if numerator <= 1.0e-12 else float("inf")
    return numerator / denominator


def audit_window(stack: np.ndarray) -> np.ndarray:
    """Extract the documented 11-by-11 window and restore mathematical y orientation."""
    if stack.ndim != 3 or stack.shape[1] < 16 or stack.shape[2] < 16:
        raise ValueError(f"output stack is too small for audit window: {stack.shape}")
    return np.flip(stack[:, 5:16, 5:16], axis=1)


def save_figures(
    times_hrr: np.ndarray,
    hrr_reference: np.ndarray,
    hrr_output: np.ndarray,
    times_dfc: np.ndarray,
    dfc_reference: np.ndarray,
    dfc_output: np.ndarray,
    dfc_whole: np.ndarray,
    times_rad: np.ndarray,
    rad_reference: np.ndarray,
    rad_output: np.ndarray,
) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    axes[0].plot(times_hrr, hrr_reference, label="reference")
    axes[0].plot(times_hrr, hrr_output, "o", ms=3, label="ELMFIRE")
    axes[0].set(xlabel="Time (s)", ylabel=r"HRRPUA (kW m$^{-2}$)", title="Center-cell HRRPUA")
    axes[0].legend()
    axes[1].plot(times_dfc, np.sum(dfc_reference, axis=(1, 2)), label="reference")
    axes[1].plot(times_dfc, np.sum(dfc_output, axis=(1, 2)), "o", ms=3, label="ELMFIRE")
    axes[1].set(xlabel="Time (s)", ylabel=r"Window sum (kW m$^{-2}$)", title="Direct flame contact")
    axes[2].plot(times_rad, np.sum(rad_reference, axis=(1, 2)), label="reference")
    axes[2].plot(times_rad, np.sum(rad_output, axis=(1, 2)), "o", ms=3, label="ELMFIRE")
    axes[2].set(xlabel="Time (s)", ylabel=r"Window sum (kW m$^{-2}$)", title="Radiation")
    for axis in axes:
        axis.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "verification_summary.pdf", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    image = ax.imshow(np.ma.asarray(dfc_whole[-1]), origin="lower", cmap="inferno")
    ax.set(xlabel="Audit-window column", ylabel="Audit-window row",
           title=f"Final ELMFIRE DFC field at t={times_dfc[-1]:g} s")
    fig.colorbar(image, ax=ax, label=r"DFC heat flux (kW m$^{-2}$)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "whole_domain_result.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    patterns = {
        "hrr": OUT_DIR / "hrr_transient_0000001_*.tif",
        "dfc": OUT_DIR / "hf_dfc_transient_0000001_*.tif",
        "rad": OUT_DIR / "hf_rad_transient_0000001_*.tif",
    }
    try:
        hrr_stack, times_hrr, *_ = load_stack(str(patterns["hrr"]))
        dfc_stack, times_dfc, *_ = load_stack(str(patterns["dfc"]))
        rad_stack, times_rad, *_ = load_stack(str(patterns["rad"]))

        hrr_reference, _, _ = reference_fields(times_hrr)
        _, dfc_reference, _ = reference_fields(times_dfc)
        _, _, rad_reference = reference_fields(times_rad)

        hrr_output = np.ma.asarray(hrr_stack)[:, 10, 10]
        dfc_output = audit_window(dfc_stack)
        rad_output = audit_window(rad_stack)

        errors = {
            "HRRPUA normalized L1 error": normalized_l1(hrr_reference, hrr_output),
            "DFC normalized L1 error": normalized_l1(dfc_reference, dfc_output),
            "radiation normalized L1 error": normalized_l1(rad_reference, rad_output),
        }
        metrics = []
        for name, value in errors.items():
            metrics.append({
                "name": name,
                "expected": 0.0,
                "calculated": value,
                "units": "-",
                "tolerance": f"<= {RELATIVE_L1_TOLERANCE:g}",
                "status": "PASS" if value <= RELATIVE_L1_TOLERANCE else "FAIL",
            })
        passed = all(metric["status"] == "PASS" for metric in metrics)
        save_figures(
            times_hrr, hrr_reference, hrr_output,
            times_dfc, dfc_reference, dfc_output, dfc_stack,
            times_rad, rad_reference, rad_output,
        )
        write_metrics({
            "case_id": "CASE19_WTH",
            "overall_status": "PASS" if passed else "FAIL",
            "verification_passed": passed,
            "required_outputs_complete": True,
            "selected_output_patterns": {key: str(value.relative_to(CASE_DIR)) for key, value in patterns.items()},
            "metrics": metrics,
        })
    except (FileNotFoundError, ValueError, IndexError) as error:
        write_metrics({
            "case_id": "CASE19_WTH",
            "overall_status": "NOT EVALUABLE",
            "verification_passed": False,
            "required_outputs_complete": False,
            "reason": str(error),
            "metrics": [],
        })


if __name__ == "__main__":
    main()

