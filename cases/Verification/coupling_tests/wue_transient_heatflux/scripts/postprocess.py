#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------- Imports & paths -----------------------
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# External functions you already have
from wue_functions import hrr_transient, ellipse_ucb, heat_flux_calc
from raster_functions import load_stack

# Resolve case directory assuming this file is .../cases/<case>/scripts/postprocess.py
CASE_DIR = Path(__file__).resolve().parents[1]
FIG_DIR = CASE_DIR / "figures"
REP_DIR = CASE_DIR / "report"
OUT_DIR = CASE_DIR / "outputs"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REP_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------- Add customized postprocessing code below -----------------------
def savefig(fig, name: str):
    """Save a figure into the case-local figures/ folder as PDF and close it."""
    out = FIG_DIR / f"{name}.pdf"
    fig.savefig(out, format="pdf")  # no bbox_inches
    plt.close(fig)
    return out

# ----------------------- Config -----------------------
NONBURNABLE_FRAC = 0.0
ABSORPTIVITY = 0.89
RAD_DIST = 100.0                  # Radiation cut-off distance [m]
ANALYSIS_CELLSIZE = 20.0          # Computation cell size [m]
WD20_NOW = 0.0                    # Wind direction in degree (meteorological: from)

WS20_NOW = 15.0                   # Wind speed in mph
HAMADA_A = 10.0                   # Avg structure footprint dimension
HAMADA_D = 10.0                   # Avg structure separation distance
WIND_PROP = 1.0

# Design fire curve
EARLY_TIME = 300.0                # developing phase time scale [s]
DEVELOPED_TIME = 3900.0           # steady phase time scale [s]
DECAY_TIME = 4200.0               # decay time scale [s]
HRR_PEAK = 400.0                  # kW/m^2

# Area of interest: indices in a 11×11 neighborhood centered at (0,0)
idxs = np.arange(-5, 6, 1)
idys = np.arange(-5, 6, 1)
idxs_grid, idys_grid = np.meshgrid(idxs, idys, indexing="xy")

# Time history
dt = 1.0
t = np.arange(0.0, 5000.0 + dt, dt)  # inclusive end to mirror MATLAB 0:dt:5000

# ----------------------- Analytical results -----------------------
nT = t.size
nRows, nCols = idxs_grid.shape

HRR_TRANSIENT_HIST = np.zeros(nT)
ELLIPSE_MAJOR_HIST = np.zeros(nT)
ELLIPSE_MINOR_HIST = np.zeros(nT)
ELLIPSE_ECCENTRICITY_HIST = np.zeros(nT)
DIST_DOWNWIND_HIST = np.zeros(nT)

DFC_HEAT_RECEIVED_MAT = np.zeros((nT, nRows, nCols))
RAD_HEAT_RECEIVED_MAT = np.zeros((nT, nRows, nCols))

for it in range(nT):
    BURNING_TIME = t[it] - t[0]

    HRR_TRANSIENT = hrr_transient(
        BURNING_TIME, EARLY_TIME, DEVELOPED_TIME, DECAY_TIME, HRR_PEAK
    )
    HRR_TRANSIENT_HIST[it] = HRR_TRANSIENT

    ellipse_dimensions = ellipse_ucb(WS20_NOW, HAMADA_A, HAMADA_D, WIND_PROP)
    ELLIPSE_MAJOR_HIST[it] = ellipse_dimensions[0]
    ELLIPSE_MINOR_HIST[it] = ellipse_dimensions[1]
    ELLIPSE_ECCENTRICITY_HIST[it] = ellipse_dimensions[2]
    DIST_DOWNWIND_HIST[it] = ellipse_dimensions[3]

    # loop over grid cells
    for r in range(nRows):
        for c in range(nCols):
            idx = float(idxs_grid[r, c])
            idy = float(idys_grid[r, c])
            if idx == 0.0 and idy == 0.0:
                continue
            dfc, rad = heat_flux_calc(
                HRR_TRANSIENT,
                NONBURNABLE_FRAC,
                ABSORPTIVITY,
                RAD_DIST,
                ellipse_dimensions,
                idx, idy, ANALYSIS_CELLSIZE,
                WD20_NOW
            )
            DFC_HEAT_RECEIVED_MAT[it, r, c] = dfc
            RAD_HEAT_RECEIVED_MAT[it, r, c] = rad

# ----------------------- Load simulation rasters -----------------------
# TODO: adjust these three globs to your actual outputs (or parametrize via YAML)
glob_hrr = CASE_DIR / "outputs" / "hrr_transient_0000001_*.tif"
glob_rad = CASE_DIR / "outputs" / "hf_rad_transient_0000001_*.tif"
glob_dfc = CASE_DIR / "outputs" / "hf_dfc_transient_0000001_*.tif"

stack_hrr, times_hrr, *_ = load_stack(str(glob_hrr))
stack_rad, times_rad, *_ = load_stack(str(glob_rad))
stack_dfc, times_dfc, *_ = load_stack(str(glob_dfc))

# Slice regions to match the analytic window & orientation
dfc_sliced = np.flip(stack_dfc[:, 5:16, 5:16], axis=1)
rad_sliced = np.flip(stack_rad[:, 5:16, 5:16], axis=1)

# ----------------------- Figures -----------------------
mpl.rcParams.update({"figure.dpi": 200})

# 1) HRR history at center
hrr_simu = stack_hrr[:, 10, 10]
fig = plt.figure(figsize=(6, 4))
plt.plot(t, HRR_TRANSIENT_HIST, linewidth=1.2, label="Analytic")
plt.plot(times_hrr, hrr_simu, ":o", linewidth=1.2, markersize=4, label="Simulation")
plt.grid(True)
plt.xlabel("Time (s)")
plt.ylabel(r"HRRPUA (kW/m$^2$)")
plt.legend()
plt.tight_layout()
savefig(fig, "hrr_history")

# helper to draw selected frames
def draw_frames(data, t_list, t_sel, raster_extent, draw_extent, clabel, flip=False, vmin=None, vmax=None):
    idx_sel = [int(np.argmin(np.abs(t_list - ts))) for ts in t_sel]
    cmap = mpl.colormaps["hot"].copy()
    cmap.set_bad(color=(0, 0, 0, 0))
    ncols = len(idx_sel)
    fig, axes = plt.subplots(1, ncols, figsize=(3.2*ncols, 2.8), constrained_layout=True)
    if ncols == 1:
        axes = [axes]
    for k, it in enumerate(idx_sel):
        ax = axes[k]
        imD = data[it, :, :]
        imD_masked = np.ma.masked_less_equal(np.flipud(imD) if flip else imD, 0)
        img = ax.imshow(
            imD_masked, extent=raster_extent, origin="lower", aspect="equal",
            cmap=cmap, vmin=vmin, vmax=vmax
        )
        ax.set_title(f"t = {t_list[it]:.0f} s")
        ax.set_xlim([draw_extent[0], draw_extent[1]])
        ax.set_ylim([draw_extent[2], draw_extent[3]])
        if k == 0:
            ax.set_ylabel("y (m)")
        ax.set_xlabel("x (m)")
    cbar = fig.colorbar(img, ax=axes, location="right", shrink=0.9)
    cbar.set_label(clabel)
    return fig

t_sel = np.array([100, 200, 300, 4100], dtype=float)
draw_extent = [-100, 100, -100, 100]
# analytic extents
xlims = (np.array([idxs.min() - 0.5, idxs.max() + 0.5]) * ANALYSIS_CELLSIZE).astype(float)
ylims = (np.array([idys.min() - 0.5, idys.max() + 0.5]) * ANALYSIS_CELLSIZE).astype(float)
extent_analytic = [xlims[0], xlims[1], ylims[0], ylims[1]]
# sim extents (adjust to match your rasters; these came from your snippet)
extent_sim = [-210, 190, -190, 210]

# 2) DFC comparison (analytic vs sim)
fig = draw_frames(
    DFC_HEAT_RECEIVED_MAT, t, t_sel, extent_analytic, draw_extent,
    r"$\dot{q}''_{\mathrm{DFC}}$ (kW/m$^2$)", vmin=0.0, vmax=100.0
)
savefig(fig, "dfc_analytic_frames")

fig = draw_frames(
    stack_dfc, times_dfc, t_sel, extent_sim, draw_extent,
    r"$\dot{q}''_{\mathrm{DFC}}$ (kW/m$^2$)", flip=True, vmin=0.0, vmax=100.0
)
savefig(fig, "dfc_sim_frames")

# 3) RAD comparison (analytic vs sim)
fig = draw_frames(
    RAD_HEAT_RECEIVED_MAT, t, t_sel, extent_analytic, draw_extent,
    r"$\dot{q}''_{\mathrm{rad}}$ (kW/m$^2$)", vmin=0.0, vmax=4.0
)
savefig(fig, "rad_analytic_frames")

fig = draw_frames(
    stack_rad, times_rad, t_sel, extent_sim, draw_extent,
    r"$\dot{q}''_{\mathrm{rad}}$ (kW/m$^2$)", flip=True, vmin=0.0, vmax=4.0
)
savefig(fig, "rad_sim_frames")

# 4) Point histories (fix: use times_dfc for DFC)
fig = plt.figure(figsize=(6, 4))
plt.plot(t, RAD_HEAT_RECEIVED_MAT[:, 3, 5], linewidth=1.2, label="Analytic")
plt.plot(times_rad, rad_sliced[:, 3, 5], ":o", linewidth=1.2, markersize=4, label="Simulation")
plt.grid(True)
plt.xlabel("Time (s)")
plt.ylabel(r"$\dot{q}''_{\mathrm{rad}}$ (kW/m$^2$)")
plt.title("Radiative heat at x=0 m, y=-30 m")
plt.legend()
plt.tight_layout()
savefig(fig, "rad_history_xy0_m30")

fig = plt.figure(figsize=(6, 4))
plt.plot(t, DFC_HEAT_RECEIVED_MAT[:, 4, 5], linewidth=1.2, label="Analytic")
plt.plot(times_dfc, dfc_sliced[:, 4, 5], ":o", linewidth=1.2, markersize=4, label="Simulation")
plt.grid(True)
plt.xlabel("Time (s)")
plt.ylabel(r"$\dot{q}''_{\mathrm{DFC}}$ (kW/m$^2$)")
plt.title("DFC heat at x=0 m, y=-20 m")
plt.legend()
plt.tight_layout()
savefig(fig, "dfc_history_xy0_m20")

# ----------------------- Metrics (relative errors) -----------------------
def nearest_indices(tref, times):
    tref = np.asarray(tref, dtype=float)
    times = np.asarray(times, dtype=float)
    return np.array([int(np.argmin(np.abs(tref - ts))) for ts in times], dtype=int)

idt_hrr = nearest_indices(t, times_hrr)
idt_dfc = nearest_indices(t, times_dfc)
idt_rad = nearest_indices(t, times_rad)

hrr_ref = HRR_TRANSIENT_HIST[idt_hrr]
hrr_cmp = stack_hrr[:, 10, 10]
error_hrr = float(np.mean(np.abs(hrr_ref - hrr_cmp) / np.maximum(hrr_ref, 1e-9)))

dfc_ref = DFC_HEAT_RECEIVED_MAT[idt_dfc, :, :]
dfc_cmp = dfc_sliced
error_dfc = float(np.nanmean(np.abs(dfc_ref - dfc_cmp) / np.maximum(dfc_ref, 1e-9)))

rad_ref = RAD_HEAT_RECEIVED_MAT[idt_rad, :, :]
rad_cmp = rad_sliced
error_rad = float(np.nanmean(np.abs(rad_ref - rad_cmp) / np.maximum(rad_ref, 1e-9)))

# ----------------------- Output Metrics for report -----------------------
# Modify the following name-value pairs, that prepares metric values to be used for report

metrics = {
    "error_hrr_mean_rel": round(error_hrr, 6),
    "error_dfc_mean_rel": round(error_dfc, 6),
    "error_rad_mean_rel": round(error_rad, 6),
}
(OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

print("[OK] Postprocess complete.")
print(f"  - Figures: {FIG_DIR}")
print(f"  - Report snippets: {REP_DIR/'figures.tex'}, {REP_DIR/'metrics.tex'}")
print(f"  - Metrics JSON: {OUT_DIR/'metrics.json'}")
