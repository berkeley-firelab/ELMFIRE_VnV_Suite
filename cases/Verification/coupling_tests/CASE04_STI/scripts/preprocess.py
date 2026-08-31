#!/usr/bin/env python3
"""Generate steady-transport and immediate-ignition variants.

Inputs are the case-local ``case.json`` and ``elmfire.data.in`` template. The
script writes deterministic rasters, local namelists, and ``variants/manifest.json``;
it does not run ELMFIRE. Raster indices include a two-cell numerical halo.
"""
from pathlib import Path
import json
import re
import shutil
import numpy as np
from osgeo import gdal, osr

# -----------------------------------------------------------------------------
# Customizable scientific and numerical parameters (SI unless noted)
# -----------------------------------------------------------------------------
CASE_CONFIG_FILENAME = "case.json"
PHYSICAL_LENGTH_M = None       # None reads case.json.
PHYSICAL_WIDTH_M = None
CELL_SIZE_M = None
BUFFER_CELLS = 2
PROJECTION_EPSG = 32610
NODATA = -9999.0
FUEL_MODEL = 102
WIND_SPEED_MPH = 15.0
WIND_DIRECTION_DEG = 270.0
INITIAL_PHI = -1.0
IGNITION_X_M = 5.0
TRANSPORT_CFL = 0.5
WIND_SPEED_MPS = 6.71
EMBER_GR_PER_MW_1M = 33.3     # pcs s-1 MW-1 for a represented 1 m strip.
DIRECT_IGNITION_PROBABILITY_PERCENT = 100.0
LOCAL_IGNITION_TIME_S = 0.0
CELL_IGNITION_DELAY_S = 0.0
DUMP_INTERVAL_TRANSPORT_S = 10.0
DUMP_INTERVAL_WILDLAND_S = 5.0

CASE_DIR = Path(__file__).resolve().parents[1]
REFERENCE_MISC_DIR = CASE_DIR / "data" / "misc"


def write_tif(path, array, dx, dtype):
    """Write a north-up, single-band raster whose halo lies outside the domain."""
    ds = gdal.GetDriverByName("GTiff").Create(
        str(path), array.shape[1], array.shape[0], 1, dtype)
    # Columns increase eastward; rows increase southward. The usable domain
    # begins at [BUFFER_CELLS, BUFFER_CELLS], at physical coordinate (0, width).
    ds.SetGeoTransform((-BUFFER_CELLS * dx, dx, 0.0,
                        (array.shape[0] - BUFFER_CELLS) * dx, 0.0, -dx))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(PROJECTION_EPSG)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.WriteArray(array)
    band.SetNoDataValue(NODATA)
    band.FlushCache()
    ds = None


def replace_key(text, key, value):
    """Replace one existing scalar namelist assignment and reject omissions."""
    pattern = rf"(?m)^(\s*{re.escape(key)}\s*=\s*).*$"
    updated, count = re.subn(pattern, rf"\g<1>{value}", text)
    if count != 1:
        raise RuntimeError(f"expected one {key} assignment, found {count}")
    return updated


def build_inputs(target, nx, ny, dx):
    """Write a co-registered flat grassland stack with one interior ignition seed."""
    target.mkdir(parents=True, exist_ok=True)
    zeros = np.zeros((ny, nx), np.float32)
    ones = np.ones((ny, nx), np.float32)
    phi = np.ones((ny, nx), np.float32)
    centre_row = BUFFER_CELLS + (ny - 2 * BUFFER_CELLS) // 2
    phi[centre_row, BUFFER_CELLS] = INITIAL_PHI
    rasters = {
        "asp": (zeros, gdal.GDT_Float32), "cbd": (zeros, gdal.GDT_Float32),
        "cbh": (zeros, gdal.GDT_Float32), "cc": (zeros, gdal.GDT_Float32),
        "ch": (zeros, gdal.GDT_Float32), "dem": (zeros, gdal.GDT_Float32),
        "slp": (zeros, gdal.GDT_Float32), "adj": (ones, gdal.GDT_Float32),
        "new_phi": (phi, gdal.GDT_Float32),
        "new_fbfm40": (np.full((ny, nx), FUEL_MODEL, np.int16), gdal.GDT_Int16),
        "ws": (np.full((ny, nx), WIND_SPEED_MPH, np.float32), gdal.GDT_Float32),
        "wd": (np.full((ny, nx), WIND_DIRECTION_DEG, np.float32), gdal.GDT_Float32),
        "m1": (zeros, gdal.GDT_Float32), "m10": (zeros, gdal.GDT_Float32),
        "m100": (zeros, gdal.GDT_Float32),
    }
    for name, (array, dtype) in rasters.items():
        write_tif(target / f"{name}.tif", array, dx, dtype)


def main():
    """Materialize complete, isolated transport-impulse variant and immediate-ignition variant run directories."""
    config = json.loads((CASE_DIR / CASE_CONFIG_FILENAME).read_text())
    length = float(config["physical_length_m"]
                   if PHYSICAL_LENGTH_M is None else PHYSICAL_LENGTH_M)
    width = float(config["physical_width_m"]
                  if PHYSICAL_WIDTH_M is None else PHYSICAL_WIDTH_M)
    dx = float(config["cell_size_m"] if CELL_SIZE_M is None else CELL_SIZE_M)
    physical_nx = round(length / dx)
    physical_ny = round(width / dx)
    if not np.isclose(
            physical_nx * dx,
            length) or not np.isclose(
            physical_ny * dx,
            width):
        raise ValueError("physical dimensions must be integer multiples of cell size")
    nx = physical_nx + 2 * BUFFER_CELLS
    ny = physical_ny + 2 * BUFFER_CELLS
    dt = TRANSPORT_CFL * dx / WIND_SPEED_MPS
    template = (CASE_DIR / "elmfire.data.in").read_text()
    variants_root = CASE_DIR / "variants"
    variants_root.mkdir(exist_ok=True)
    manifest = {"case_id": config["id"], "required_variants": [], "variants": []}
    for definition in config["variants"]:
        name = definition["name"]
        root = variants_root / name
        inputs = root / "data" / "inputs"
        misc = root / "data" / "misc"
        outputs = root / "outputs"
        scratch = root / "logs" / "scratch"
        for path in (misc, outputs, scratch):
            path.mkdir(parents=True, exist_ok=True)
        build_inputs(inputs, nx, ny, dx)
        for filename in ("fuel_models.csv", "building_fuel_models.csv"):
            shutil.copyfile(REFERENCE_MISC_DIR / filename, misc / filename)
        text = template
        substitutions = {
            "FUELS_AND_TOPOGRAPHY_DIRECTORY": "'./data/inputs'",
            "WEATHER_DIRECTORY": "'./data/inputs'",
            "OUTPUTS_DIRECTORY": "'./outputs'",
            "MISCELLANEOUS_INPUTS_DIRECTORY": "'./data/misc'",
            "SCRATCH": "'./logs/scratch'",
            "SIMULATION_DT": f"{dt:.10g}",
            "SIMULATION_DTMAX": f"{dt:.10g}",
            "TARGET_CFL": f"{TRANSPORT_CFL:.8g}",
            "SIMULATION_TSTOP": f"{definition['tstop_s']:.8g}",
            # "DTDUMP": f"{DUMP_INTERVAL_TRANSPORT_S if name == 'transport_impulse' else DUMP_INTERVAL_WILDLAND_S:.8g}",
            "X_IGN(1)": f"{IGNITION_X_M:.8g}",
            "Y_IGN(1)": f"{0.5 * width:.8g}",
            "GENERATION_MODEL": f"'{definition['generation_model']}'",
            "USE_PHYSICAL_SPOTTING_DURATION": str(
                definition["physical_spotting_duration"]).upper().replace(
                "TRUE",
                ".TRUE.").replace(
                "FALSE",
                ".FALSE."),
            "NO_SURFACE_FIRE": str(
                definition["no_surface_fire"]).upper().replace(
                "TRUE",
                ".TRUE.").replace(
                "FALSE",
                ".FALSE."),
            "PIGN": f"{DIRECT_IGNITION_PROBABILITY_PERCENT:.8g}",
            "LOCAL_IGNITION_TIME": f"{LOCAL_IGNITION_TIME_S:.8g}",
            "CELL_IGNITION_DELAY": f"{CELL_IGNITION_DELAY_S:.8g}",
        }
        for key, value in substitutions.items():
            text = replace_key(text, key, value)
        if name == "transport_impulse":
            text = replace_key(text, "EMBER_GR", f"{definition['ember_gr']:.8g}")
        else:
            # ELMFIRE multiplies PER-MW generation by pixel fire power FLIN*dy;
            # division by dy keeps the represented 1 m strip invariant.
            configured_gr = EMBER_GR_PER_MW_1M / dx
            text = replace_key(text, "EMBER_GR_PER_MW_VEGE", f"{configured_gr:.10g}")
        (root / "elmfire.data.in").write_text(text)
        item = {
            **definition,
            "path": str(
                root.relative_to(CASE_DIR)),
            "namelist": str(
                (root / "elmfire.data.in").relative_to(CASE_DIR)),
            "outputs": str(
                outputs.relative_to(CASE_DIR)),
            "nx": nx,
            "ny": ny,
            "physical_nx": physical_nx,
            "physical_ny": physical_ny,
            "cell_size_m": dx,
            "physical_length_m": length,
            "physical_width_m": width,
            "buffer_cells": BUFFER_CELLS,
            "simulation_dt_s": dt,
            "wind_speed_mps": WIND_SPEED_MPS,
            "effective_ember_gr_per_mw_1m": EMBER_GR_PER_MW_1M if name != "transport_impulse" else None}
        manifest["required_variants"].append(name)
        manifest["variants"].append(item)
    (variants_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[OK] prepared {len(manifest['variants'])} combined verification variants")


if __name__ == "__main__":
    main()
