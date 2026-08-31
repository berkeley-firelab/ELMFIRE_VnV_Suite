#!/usr/bin/env python3
"""Generate the paired ELMFIRE inputs for surface-dominated and mixed-mode variants.

The two variants share the same flat grassland, line ignition, wind, firebrand
source, transport model, and grid. Only ignition-model parameters required by
the reference experiment differ. This script prepares inputs; it never launches
ELMFIRE and never invents simulation results.
"""

from pathlib import Path
import json
import math
import re
import shutil

import numpy as np
from osgeo import gdal, osr


# -----------------------------------------------------------------------------
# Customizable preprocessing parameters
# Change values here to design a sensitivity study. A value of None delegates
# to case.json. Distances use metres, times seconds, and rates SI units unless
# the variable name explicitly states otherwise.
# -----------------------------------------------------------------------------
CASE_CONFIG_FILENAME = "case.json"
BASE_NAMELIST_FILENAME = "elmfire.data.in"
CELL_SIZE_M = None
PHYSICAL_LENGTH_M = None
PHYSICAL_WIDTH_M = None
BUFFER_CELLS = None
PROJECTION_EPSG = 32610
NODATA = -9999.0

FUEL_MODEL = 102
WIND_SPEED_MPH = None
WIND_DIRECTION_DEG = 270.0
DEAD_FUEL_MOISTURE_PERCENT = 0.0
INITIAL_PHI = -1.0

TARGET_CFL = 0.5
WIND_SPEED_MPS = None
OUTPUT_INTERVAL_S = 10.0
EMBER_GENERATION_PER_MW = 33.3
IGNITION_PROBABILITY_PERCENT = 90.0
P_EPS = 0.01
MONTE_CARLO_SEED = 55400


def load_case(case_dir):
    """Read the case contract that defines the two reference variants."""
    return json.loads((case_dir / CASE_CONFIG_FILENAME).read_text(encoding="utf-8"))


def resolve(value, fallback):
    """Return the explicit script override when one is configured."""
    return fallback if value is None else value


def write_tif(path, array, dx, buffer_cells, dtype=gdal.GDT_Float32):
    """Write a north-up, single-band, co-registered verification raster."""
    path = Path(path)
    dataset = gdal.GetDriverByName("GTiff").Create(
        str(path), array.shape[1], array.shape[0], 1, dtype
    )
    if dataset is None:
        raise RuntimeError(f"Could not create {path}")
    dataset.SetGeoTransform(
        (-buffer_cells * dx, dx, 0.0,
         (array.shape[0] - buffer_cells) * dx, 0.0, -dx)
    )
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(PROJECTION_EPSG)
    dataset.SetProjection(spatial_ref.ExportToWkt())
    band = dataset.GetRasterBand(1)
    band.WriteArray(array)
    band.SetNoDataValue(NODATA)
    band.FlushCache()
    dataset = None


def replace_assignment(text, key, value):
    """Replace one existing Fortran namelist assignment and require a match."""
    pattern = re.compile(rf"(?im)^\s*{re.escape(key)}\s*=.*$")
    replaced, count = pattern.subn(f"{key}={value}", text)
    if count != 1:
        raise ValueError(f"Expected exactly one {key} assignment; found {count}")
    return replaced


def write_input_stack(input_dir, nx, ny, dx, buffer_cells, wind_mph):
    """Create the common flat-grassland raster stack with a crosswind fireline."""
    input_dir.mkdir(parents=True, exist_ok=True)
    zeros = np.zeros((ny, nx), dtype=np.float32)
    ones = np.ones((ny, nx), dtype=np.float32)
    phi = np.ones((ny, nx), dtype=np.float32)
    fbfm = np.full((ny, nx), FUEL_MODEL, dtype=np.int16)

    # A line ignition across all physical rows makes the centre-row solution
    # one-dimensional, matching the reference MATLAB setup.
    phi[buffer_cells:ny - buffer_cells, buffer_cells] = INITIAL_PHI

    rasters = (
        ("asp", zeros, gdal.GDT_Float32),
        ("cbd", zeros, gdal.GDT_Float32),
        ("cbh", zeros, gdal.GDT_Float32),
        ("cc", zeros, gdal.GDT_Float32),
        ("ch", zeros, gdal.GDT_Float32),
        ("dem", zeros, gdal.GDT_Float32),
        ("slp", zeros, gdal.GDT_Float32),
        ("adj", ones, gdal.GDT_Float32),
        ("new_phi", phi, gdal.GDT_Float32),
        ("new_fbfm40", fbfm, gdal.GDT_Int16),
        ("ws", np.full((ny, nx), wind_mph, dtype=np.float32), gdal.GDT_Float32),
        ("wd", np.full((ny, nx), WIND_DIRECTION_DEG, dtype=np.float32), gdal.GDT_Float32),
        ("m1", np.full((ny, nx), DEAD_FUEL_MOISTURE_PERCENT, dtype=np.float32), gdal.GDT_Float32),
        ("m10", np.full((ny, nx), DEAD_FUEL_MOISTURE_PERCENT, dtype=np.float32), gdal.GDT_Float32),
        ("m100", np.full((ny, nx), DEAD_FUEL_MOISTURE_PERCENT, dtype=np.float32), gdal.GDT_Float32),
    )
    for name, array, dtype in rasters:
        write_tif(input_dir / f"{name}.tif", array, dx, buffer_cells, dtype)


def configure_namelist(base_text, variant, dx, dt, generation_rate):
    """Make all tested model selectors explicit in one variant namelist."""
    values = {
        "SIMULATION_DT": f"{dt:.8g}",
        "SIMULATION_DTMAX": f"{dt:.8g}",
        "TARGET_CFL": f"{TARGET_CFL:.8g}",
        "SIMULATION_TSTOP": f"{float(variant['tstop_s']):.8g}",
        "DTDUMP": f"{OUTPUT_INTERVAL_S:.8g}",
        "SEED": str(MONTE_CARLO_SEED),
        "GENERATION_MODEL": "'PER-MW'",
        "SPOTTING_DISTANCE_MODEL": "'EMPIRICAL'",
        "ACCUMULATION_MODEL": "'EULERIAN'",
        "IGNITION_MODEL": f"'{variant['ignition_model']}'",
        "EMBER_GR_PER_MW_VEGE": f"{generation_rate:.8g}",
        "PIGN": f"{IGNITION_PROBABILITY_PERCENT:.8g}",
        "P_EPS": f"{P_EPS:.8g}",
        "LOCAL_IGNITION_TIME": f"{float(variant['local_ignition_time_s']):.8g}",
        "CELL_IGNITION_DELAY": f"{float(variant['cell_ignition_delay_s']):.8g}",
        "DIFF_WILDLAND_IGNITION": ".FALSE.",
        "NO_SURFACE_FIRE": ".FALSE.",
        "USE_PHYSICAL_SPOTTING_DURATION": ".TRUE.",
    }
    text = base_text
    for key, value in values.items():
        text = replace_assignment(text, key, value)
    return text


def preprocess(case_dir):
    """Prepare independent directories for surface-dominated variant and mixed-mode variant."""
    case_dir = Path(case_dir)
    case = load_case(case_dir)
    dx = float(resolve(CELL_SIZE_M, case["dx_m"]))
    length = float(resolve(PHYSICAL_LENGTH_M, case["physical_length_m"]))
    width = float(resolve(PHYSICAL_WIDTH_M, case["physical_width_m"]))
    buffer_cells = int(resolve(BUFFER_CELLS, case["buffer_cells"]))
    wind_mps = float(resolve(WIND_SPEED_MPS, case["wind_speed_mps"]))
    wind_mph = float(resolve(WIND_SPEED_MPH, case["wind_speed_mph"]))

    physical_nx = int(round(length / dx))
    physical_ny = int(round(width / dx))
    if not math.isclose(
            physical_nx * dx,
            length) or not math.isclose(
            physical_ny * dx,
            width):
        raise ValueError(
            "Physical dimensions must be integral multiples of CELL_SIZE_M")
    nx = physical_nx + 2 * buffer_cells
    ny = physical_ny + 2 * buffer_cells
    dt = TARGET_CFL * dx / wind_mps

    # ELMFIRE multiplies this normalized rate by FLIN*cell_size/1000, which is
    # the cell heat-release rate in MW. The normalized 33.3 value therefore
    # remains constant with resolution; cell-size scaling occurs in the model.
    generation_rate = EMBER_GENERATION_PER_MW
    base_text = (case_dir / BASE_NAMELIST_FILENAME).read_text(encoding="utf-8")
    reference_misc_dir = case_dir / "data" / "misc"
    manifest = {
        "case_id": case["id"],
        "generated_by": "scripts/preprocess.py",
        "dx_m": dx,
        "dt_s": dt,
        "target_cfl": TARGET_CFL,
        "physical_length_m": length,
        "physical_width_m": width,
        "nx_with_halo": nx,
        "ny_with_halo": ny,
        "buffer_cells": buffer_cells,
        "wind_speed_mps": wind_mps,
        "surface_ros_reference_mps": case["surface_ros_reference_mps"],
        "maximum_spotting_distance_m": case["maximum_spotting_distance_m"],
        "generation_rate_per_mw_cell": generation_rate,
        "variants": [],
    }

    for variant in case["variants"]:
        variant_dir = case_dir / "variants" / variant["name"]
        for subdir in (
            "data/inputs",
            "data/misc",
            "outputs",
            "figures",
                "logs/scratch"):
            (variant_dir / subdir).mkdir(parents=True, exist_ok=True)
        write_input_stack(
            variant_dir /
            "data/inputs",
            nx,
            ny,
            dx,
            buffer_cells,
            wind_mph)
        for filename in ("fuel_models.csv", "building_fuel_models.csv"):
            source = reference_misc_dir / filename
            if not source.is_file():
                raise FileNotFoundError(f"Required model table is missing: {source}")
            shutil.copyfile(source, variant_dir / "data/misc" / filename)
        namelist = configure_namelist(base_text, variant, dx, dt, generation_rate)
        (variant_dir / "elmfire.data.in").write_text(namelist, encoding="utf-8")
        manifest["variants"].append({
            **variant,
            "directory": str(Path("variants") / variant["name"]),
            "namelist": "elmfire.data.in",
            "outputs": "outputs",
        })

    manifest_path = case_dir / "variants" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"[OK] prepared {len(manifest['variants'])} reference variants at dx={dx:g} m")


if __name__ == "__main__":
    preprocess(Path(__file__).resolve().parents[1])
