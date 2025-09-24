#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------- Imports & paths -----------------------
from pathlib import Path
from typing import List,Optional
import matplotlib.pyplot as plt
import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np
import json

# External functions you already have
from landscape_validation_helpers import (
        plot_fuel_map, plot_wx_hist, load_viirs_points, add_viirs_obstime, 
        viirs_concave_hulls_by_halfday, viirs_burn_area_history_from_hulls, 
        load_toa_stack, burn_area_history_from_toa, reproject_to, array_extent, 
        plot_burnt_map_from_toa, plot_viirs_points, calc_cohen_kappa_for_case
    )

# Resolve case directory assuming this file is .../cases/<case>/scripts/postprocess.py
CASE_DIR = Path(__file__).resolve().parents[1]
FIG_DIR = CASE_DIR / "figures"
REP_DIR = CASE_DIR / "report"
OUT_DIR = CASE_DIR / "outputs"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REP_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

def savefig(fig, name: str):
    """Save a figure into the case-local figures/ folder as PDF and close it."""
    out = FIG_DIR / f"{name}.pdf"
    fig.savefig(out, format="pdf")  # no bbox_inches
    plt.close(fig)
    return out

# ----------------------- Config -----------------------
# Inputs
FUELMAP_PATH   = CASE_DIR / "data/fuels_and_topography/fbfm40b.tif"
WX_WS_PATH     = CASE_DIR / "data/weather/ws.tif"
WX_WD_PATH     = CASE_DIR / "data/weather/wd.tif"
WX_M1_PATH     = CASE_DIR / "data/weather/m1.tif"
WX_M10_PATH    = CASE_DIR / "data/weather/m10.tif"
WX_M100_PATH   = CASE_DIR / "data/weather/m100.tif"
VIIRS_DIR      = CASE_DIR / "data/viirs_observation"                      # expects viirs_*.shp

# Outputs
TOA_GLOB       = str(OUT_DIR / "time_of_arrival_*.tif")

OUT_CRS = "EPSG:4326"   # Plotting in lon/lat for base map
MAP_EXTENT_OVERRIDE = [-122.8, -122.6, 38.45, 38.625] # in MAP_CRS
start_time="2017-10-08, 21:45 PST" # Real fire start time

# ----------------------- Post Processing & Figures -----------------------

# ---- 1) Fuel map base layer
fig, ax = plt.subplots(figsize=(11, 10))
_, ax, extent_ll = plot_fuel_map(FUELMAP_PATH, ax=ax, show_colorbar=True, dst_crs=OUT_CRS)
ax.set_xlabel(r'Longitude [$^\circ$]')
ax.set_ylabel(r'Latitude [$^\circ$]')
ax.set_xlim(MAP_EXTENT_OVERRIDE[0], MAP_EXTENT_OVERRIDE[1])
ax.set_ylim(MAP_EXTENT_OVERRIDE[2], MAP_EXTENT_OVERRIDE[3])
ax.set_xticks(np.linspace(MAP_EXTENT_OVERRIDE[0], MAP_EXTENT_OVERRIDE[1],5))
ax.set_yticks(np.linspace(MAP_EXTENT_OVERRIDE[2], MAP_EXTENT_OVERRIDE[3],4))
ax.set_aspect("equal")
out=savefig(fig, "fuelmap_categorical")

# ---- 2) Weather histograms
wx_list = [
    (WX_WS_PATH, "Wind Speed [mph]"),
    (WX_WD_PATH, "Wind Direction [°]"),
    (WX_M1_PATH, "1-hr Dead Fuel Moisture [%]"),
    (WX_M10_PATH, "10-hr Dead Fuel Moisture [%]"),
    (WX_M100_PATH, "100-hr Dead Fuel Moisture [%]"),
]
for path, xlabel in wx_list:
    fig, ax = plt.subplots(figsize=(6,4))
    plot_wx_hist(ax, path, bins=60)
    ax.set_xlabel(xlabel)
    savefig(fig, f"hist_{path.stem}")

# ---- 3) Load TOA + compute pixel area
toa_paths, toa_arrays, toa_times, toa_transform, toa_meta = load_toa_stack(TOA_GLOB)
with rasterio.open(toa_paths[0]) as src0:
    px_area = abs(src0.transform.a * src0.transform.e)  # (m/px)*(m/px) if UTM/proj in meters
toa_times_hist, count, toa_area_hist = burn_area_history_from_toa(toa_arrays, pixel_area_m2=px_area)

# ---- 4) VIIRS: load, timebin (half-day), filter to map extent, build hulls
NEEDED = ["ACQ_DATE", "ACQ_TIME", "LATITUDE", "LONGITUDE", "geometry"]
viirs_gdf = load_viirs_points(VIIRS_DIR, columns=NEEDED).drop_duplicates(subset=["ACQ_DATE","ACQ_TIME","geometry"])
viirs_gdf = add_viirs_obstime(viirs_gdf)

hulls_by_half = viirs_concave_hulls_by_halfday(viirs_gdf, ratio=0.2,allow_holes=True)
viirs_times, viirs_areas = viirs_burn_area_history_from_hulls(hulls_by_half, start_time=start_time)  # area in map CRS units (km^2 if UTM)

# ---- 5) VIIRS vs TOA overlays for first 3 half-day bins (if available)
toa_field = toa_arrays[0]

# Reproject fuel map to the TOA CRS for consistent overlay (no colorbar in small multiples)
dst, transform, meta = reproject_to(FUELMAP_PATH, OUT_CRS)
extent = array_extent(transform, meta["width"], meta["height"])

n_show = min(2, len(viirs_times))
fig, axs = plt.subplots(1, n_show, figsize=(6*n_show+2, 6))
if n_show == 1:
    axs = [axs]

half_ids = sorted(viirs_gdf["half_day"].unique())
obs_times = sorted(hulls_by_half.keys())
sub_pts = gpd.GeoDataFrame(columns=viirs_gdf.columns, geometry=[], crs=viirs_gdf.crs)

for i, ax in enumerate(axs):
    time_now_sec = viirs_times[i]
    half_id = half_ids[i]
    # Base fuel map in TOA CRS
    _im, _ax, _ = plot_fuel_map(FUELMAP_PATH, ax=ax, show_colorbar=False, dst_crs=OUT_CRS)

    # Burned map from a single TOA field
    toa_max = plot_burnt_map_from_toa(ax, toa_field, time_now_sec, extent, alpha=1)

    # VIIRS points for this bin → TOA CRS
    # Accumulate VIIRS points (avoid concat on empty to silence FutureWarning)
    new_pts = viirs_gdf[viirs_gdf["half_day"] == half_id]
    if not new_pts.empty:
        new_pts = new_pts.to_crs(OUT_CRS)
        if sub_pts.empty:
            sub_pts = new_pts.reset_index(drop=True)
        else:
            sub_pts = pd.concat([sub_pts, new_pts], ignore_index=True)

    if not sub_pts.empty:
        plot_viirs_points(ax, sub_pts, s=4, marker='s')
        
    hull = hulls_by_half[obs_times[i]]
    if hull and not hull.is_empty:
        hull_gdf = gpd.GeoDataFrame(geometry=[hull], crs="EPSG:4326").to_crs(OUT_CRS)
        hull_gdf.boundary.plot(ax=ax, edgecolor="red", linewidth=2, alpha=0.8)
        
    ax.set_title(f"Simulation: {toa_max/3600:.1f} hours post ignition;\n VIIRS: {time_now_sec/3600:.1f} hours post ignition")
    ax.set_xlabel(r'Longitude [$^\circ$]')
    ax.set_ylabel(r'Latitude [$^\circ$]')
    ax.set_xlim(MAP_EXTENT_OVERRIDE[0], MAP_EXTENT_OVERRIDE[1])
    ax.set_ylim(MAP_EXTENT_OVERRIDE[2], MAP_EXTENT_OVERRIDE[3])
    ax.set_xticks(np.linspace(MAP_EXTENT_OVERRIDE[0], MAP_EXTENT_OVERRIDE[1],5))
    ax.set_yticks(np.linspace(MAP_EXTENT_OVERRIDE[2], MAP_EXTENT_OVERRIDE[3],4))
    ax.set_aspect("equal")

savefig(fig, "simu_vs_viirs_examples")

# ---- 6) Burn area history plot
fig, ax = plt.subplots(figsize=(8,5))
ax.plot(np.array(toa_times_hist)/3600.0, np.array(toa_area_hist)/1e6, label="Simulated (TOA)", lw=2)
ax.plot(np.array(viirs_times)/3600, np.array(viirs_areas), label="Observed (VIIRS hull)", lw=2)
ax.set_xlabel("Time [s]")
ax.set_ylabel("Burned area [km²]")
ax.legend()
savefig(fig, "burn_area_history")

# ----------------------- Metrics  -----------------------
# Cohen's Kappa (per φ slice vs nearest half-day VIIRS hull)
kappas, times_simu, times_viirs = calc_cohen_kappa_for_case(toa_field, 
                                hulls_by_half,
                                start_time,
                                FUELMAP_PATH)

metrics = {
    **{
        f"kappa_{i+1}": (
            None if (i >= len(kappas) or np.isnan(kappas[i]))
            else round(float(kappas[i]), 6)
        )
        for i in range(len(kappas))
    },
    **{
        f"t_simu_{i+1}": (
            None if (i >= len(times_simu) or np.isnan(times_simu[i]))
            else round(float(times_simu[i]), 6)
        )
        for i in range(len(times_simu))
    },
    **{
        f"t_viirs_{i+1}": (
            None if (i >= len(times_viirs) or np.isnan(times_viirs[i]))
            else round(float(times_viirs[i]), 6)
        )
        for i in range(len(times_viirs))
    },
}

(OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print("[OK] Postprocess complete.")
print(f"  - Figures: {FIG_DIR}")
print(f"  - Metrics JSON: {OUT_DIR/'metrics.json'}")
