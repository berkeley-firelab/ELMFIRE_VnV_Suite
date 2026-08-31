#!/usr/bin/env python3
"""Prepare the paired fine-grid no-surface reference and surface-coupled variant WUI variants.

Both variants use identical deterministic inputs and numerical resolution. The
only controlled difference is NO_SURFACE_FIRE, allowing the postprocessor to
attribute changes in ignition chronology to surface-fire coupling.
"""

from pathlib import Path
import hashlib
import json
import math
import shutil

import numpy as np
from osgeo import gdal, osr

# Customizable preprocessing parameters (SI units unless noted).
CASE_FILENAME = "case.json"
NAMELIST_TEMPLATE = "elmfire.data.in"
VARIANTS_DIRECTORY = "variants"
BUFFER_CELLS = 2
DEFAULT_PHYSICAL_WIDTH_M = 100.0
MIN_RASTER_DIMENSION = 10
EPSG = 32610
NODATA_FLOAT = -9999.0
NODATA_INT = -9999
BACKGROUND_FUEL_MODEL = 93
SURFACE_FUEL_MODEL = 102
STRUCTURE_FUEL_MODEL = 91
BUILDING_FUEL_MODEL_ID = 14
WIND_DIRECTION_DEG = 270.0
MOISTURE_PERCENT = 0.0
BUILDING_HEIGHT_M = 8.0
BUILDING_PLAN_DIMENSION_M = 10.0
BUILDING_NONBURNABLE_FRACTION = 0.5
BUILDING_FOOTPRINT_FRACTION = 1.0
BUILDING_SEPARATION_M = 10.0
BUILDING_FUEL_LOAD_KG_M2 = 1560.0
BUILDING_CRITICAL_FLUX_W_M2 = 10500.0
BUILDING_CRITICAL_TEMPERATURE = 9.0
BUILDING_ABSORPTIVITY = 0.89
BUILDING_IGNITION_PROBABILITY_PERCENT = 90.0


def input_fingerprint(variant_dir):
    """Hash every generated file that can affect an ELMFIRE variant run."""
    digest = hashlib.sha256()
    paths = [variant_dir / "elmfire.data.in"]
    paths.extend(sorted((variant_dir / "data" / "inputs").glob("*")))
    paths.extend(sorted((variant_dir / "data" / "misc").glob("*")))
    for path in paths:
        digest.update(str(path.relative_to(variant_dir)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_tif(path, array, dx, dtype):
    """Write a north-up, one-band GeoTIFF aligned with the ELMFIRE domain."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ds = gdal.GetDriverByName("GTiff").Create(
        str(path), array.shape[1], array.shape[0], 1, dtype
    )
    if ds is None:
        raise RuntimeError(f"Could not create {path}")
    ds.SetGeoTransform(
        (-BUFFER_CELLS * dx, dx, 0.0,
         (array.shape[0] - BUFFER_CELLS) * dx, 0.0, -dx)
    )
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(EPSG)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.WriteArray(array)
    nodata = NODATA_INT if np.issubdtype(array.dtype, np.integer) else NODATA_FLOAT
    band.SetNoDataValue(nodata)
    band.FlushCache()
    ds = None


def interval_overlap(left, right, interval_left, interval_right):
    """Return overlap length between two half-open one-dimensional intervals."""
    return max(0.0, min(right, interval_right) - max(left, interval_left))


def physical_structure_fraction(x_left, x_right, width, gap):
    """Fraction of a cell occupied by the repeating structure/firebreak pattern."""
    period = width + gap
    first = math.floor((x_left - width) / period)
    last = math.ceil(x_right / period)
    overlap = 0.0
    for index in range(first, last + 1):
        structure_left = index * period
        overlap += interval_overlap(
            x_left, x_right, structure_left, structure_left + width
        )
    return min(1.0, overlap / (x_right - x_left))


def physical_structure_index(center, width, gap):
    """Map a represented cell centre to a zero-based lattice index."""
    period = width + gap
    return max(0, int(math.floor((center + 0.5 * gap) / period)))


def ignition_coordinates(source_mask, structure_ids, dx):
    """Return one ignition point inside each structure in the upwind column."""
    source_ids = np.unique(structure_ids[source_mask])
    source_ids = source_ids[source_ids > 0]
    if source_ids.size == 0:
        raise RuntimeError("The rasterized domain has no source structures.")
    lines = []
    for index, structure_id in enumerate(source_ids, start=1):
        rows, columns = np.where(source_mask & (structure_ids == structure_id))
        centre = np.argmin(
            (rows - np.mean(rows)) ** 2 + (columns - np.mean(columns)) ** 2
        )
        row, column = int(rows[centre]), int(columns[centre])
        x = (column - BUFFER_CELLS + 0.5) * dx
        y = (source_mask.shape[0] - BUFFER_CELLS - row - 0.5) * dx
        lines.extend((f"X_IGN({index})={x:.8g}", f"Y_IGN({index})={y:.8g}"))
    return int(source_ids.size), "\n".join(lines)


def building_model_row(case):
    """Return structural fuel model 14 for true square-cell 2-D footprints."""
    hrr_peak = case["hrrpua_peak_kw_m2"]
    hardening = 1.0
    values = [
        BUILDING_FUEL_MODEL_ID, "CH6",
        case["hrr_growth_end_s"], case["hrr_growth_end_s"],
        case["hrr_steady_end_s"], case["hrr_decay_end_s"],
        BUILDING_FUEL_LOAD_KG_M2, hrr_peak,
        BUILDING_CRITICAL_FLUX_W_M2, BUILDING_CRITICAL_TEMPERATURE,
        BUILDING_ABSORPTIVITY, BUILDING_HEIGHT_M,
        BUILDING_NONBURNABLE_FRACTION,
        BUILDING_IGNITION_PROBABILITY_PERCENT,
        hardening, case["small_ignition_delay_s"],
    ]
    return ",".join(str(value) for value in values), hrr_peak, hardening


def write_variant(case_dir, template, case, spec, feature_available):
    """Generate one self-contained variant and return its manifest record."""
    name = spec["name"]
    dx = float(spec["dx_m"])
    length = float(spec["physical_length_m"])
    requested_width = float(case.get("physical_width_m", DEFAULT_PHYSICAL_WIDTH_M))
    physical_columns = int(round(length / dx))
    physical_rows = int(math.ceil(requested_width / dx))
    nx = physical_columns + 2 * BUFFER_CELLS
    ny = max(MIN_RASTER_DIMENSION, physical_rows + 2 * BUFFER_CELLS)
    row0 = ny - BUFFER_CELLS - physical_rows
    col0 = BUFFER_CELLS
    region = np.s_[row0:row0 + physical_rows,
                   col0:col0 + physical_columns]

    variant_dir = case_dir / VARIANTS_DIRECTORY / name
    input_dir = variant_dir / "data" / "inputs"
    misc_dir = variant_dir / "data" / "misc"
    for directory in (
        input_dir, misc_dir, variant_dir / "outputs", variant_dir / "logs" / "scratch"
    ):
        directory.mkdir(parents=True, exist_ok=True)

    zeros = np.zeros((ny, nx), dtype=np.float32)
    ones = np.ones((ny, nx), dtype=np.float32)
    fbfm = np.full((ny, nx), BACKGROUND_FUEL_MODEL, dtype=np.int16)
    phi = np.ones((ny, nx), dtype=np.float32)
    fractions = np.zeros((ny, nx), dtype=np.float32)
    structure_ids = np.zeros((ny, nx), dtype=np.int16)

    width = float(case["structure_width_m"])
    gap = float(case["firebreak_width_m"])
    x_fraction = np.asarray([
        physical_structure_fraction(j * dx, (j + 1) * dx, width, gap)
        for j in range(physical_columns)
    ])
    y_fraction = np.asarray([
        physical_structure_fraction(i * dx, (i + 1) * dx, width, gap)
        for i in range(physical_rows)
    ])
    mode_fraction = np.outer(y_fraction[::-1], x_fraction)
    physical_mask = np.outer(y_fraction[::-1] >= 0.5, x_fraction >= 0.5)
    # Structure cells use the Hamada WUI model; all two-dimensional gaps use
    # the burnable surface fuel so the coupled variant has a continuous path.
    fbfm[region] = np.where(
        physical_mask, STRUCTURE_FUEL_MODEL, SURFACE_FUEL_MODEL
    ).astype(np.int16)
    fractions[region] = mode_fraction.astype(np.float32)

    n_structures_x = int(math.ceil((physical_columns * dx) / (width + gap)))
    structure_x_index = np.full((ny, nx), -1, dtype=np.int16)
    for local_row, local_column in zip(*np.where(physical_mask)):
        x_center = (local_column + 0.5) * dx
        y_center = (physical_rows - local_row - 0.5) * dx
        sx = physical_structure_index(x_center, width, gap)
        sy = physical_structure_index(y_center, width, gap)
        row = row0 + local_row
        column = col0 + local_column
        structure_x_index[row, column] = sx
        structure_ids[row, column] = 1 + sx + n_structures_x * sy

    building_mask = structure_ids > 0
    first_structure_column = int(structure_x_index[building_mask].min())
    source_mask = building_mask & (structure_x_index == first_structure_column)
    source_structure_count = int(np.unique(structure_ids[source_mask]).size)
    represented_rows = np.where(physical_mask.any(axis=1))[0]
    if represented_rows.size == 0:
        raise RuntimeError(f"{name}: mode sampling removed every structure")
    center_row = row0 + int(represented_rows[represented_rows.size // 2])
    # ELMFIRE initializes from PHI0 when a PHI raster is supplied. Negative
    # PHI marks burning cells; ignite every footprint in the upwind column.
    phi[source_mask] = -1.0
    num_ignitions, ignition_text = ignition_coordinates(
        source_mask, structure_ids, dx
    )
    wind_speed = np.full((ny, nx), case["wind_speed_mph"], dtype=np.float32)
    wind_direction = np.full((ny, nx), WIND_DIRECTION_DEG, dtype=np.float32)
    rasters = {
        "asp": (zeros, gdal.GDT_Float32),
        "cbd": (zeros, gdal.GDT_Float32),
        "cbh": (zeros, gdal.GDT_Float32),
        "cc": (zeros, gdal.GDT_Float32),
        "ch": (zeros, gdal.GDT_Float32),
        "dem": (zeros, gdal.GDT_Float32),
        "slp": (zeros, gdal.GDT_Float32),
        "adj": (ones, gdal.GDT_Float32),
        "new_phi": (phi, gdal.GDT_Float32),
        "new_fbfm40": (fbfm, gdal.GDT_Int16),
        "ws": (wind_speed, gdal.GDT_Float32),
        "wd": (wind_direction, gdal.GDT_Float32),
        "m1": (np.full((ny, nx), MOISTURE_PERCENT, np.float32), gdal.GDT_Float32),
        "m10": (np.full((ny, nx), MOISTURE_PERCENT, np.float32), gdal.GDT_Float32),
        "m100": (np.full((ny, nx), MOISTURE_PERCENT, np.float32), gdal.GDT_Float32),
    }
    for filename, (array, dtype) in rasters.items():
        write_tif(input_dir / f"{filename}.tif", array, dx, dtype)

    def building_values(value, dtype):
        """Broadcast one physical building property over represented structure cells and nodata elsewhere."""
        return np.where(building_mask, value, NODATA_FLOAT).astype(dtype)

    write_tif(
        input_dir /
        "bldg_area.tif",
        building_values(
            BUILDING_PLAN_DIMENSION_M,
            np.float32),
        dx,
        gdal.GDT_Float32)
    write_tif(input_dir / "bldg_sep.tif",
              building_values(BUILDING_SEPARATION_M, np.float32), dx, gdal.GDT_Float32)
    write_tif(
        input_dir /
        "bldg_nonburnable.tif",
        building_values(
            BUILDING_NONBURNABLE_FRACTION,
            np.float32),
        dx,
        gdal.GDT_Float32)
    write_tif(
        input_dir /
        "bldg_footprint_frac.tif",
        building_values(
            BUILDING_FOOTPRINT_FRACTION,
            np.float32),
        dx,
        gdal.GDT_Float32)
    write_tif(
        input_dir /
        "bldg_fuel_model.tif",
        np.where(
            building_mask,
            BUILDING_FUEL_MODEL_ID,
            NODATA_INT).astype(
            np.int16),
        dx,
        gdal.GDT_Int16)
    # Auxiliary rasters support resolution-independent physical aggregation.
    write_tif(input_dir / "structure_id.tif", structure_ids, dx, gdal.GDT_Int16)
    write_tif(input_dir / "structure_fraction.tif", fractions, dx, gdal.GDT_Float32)

    fuel_models = case_dir / "data" / "misc" / "fuel_models.csv"
    building_models = case_dir / "data" / "misc" / "building_fuel_models.csv"
    if not fuel_models.exists() or not building_models.exists():
        raise FileNotFoundError("Case-local ELMFIRE fuel-model tables are unavailable.")
    shutil.copyfile(fuel_models, misc_dir / "fuel_models.csv")
    row, hrr_peak, hardening = building_model_row(case)
    existing = building_models.read_text(encoding="utf-8").rstrip()
    (misc_dir / "building_fuel_models.csv").write_text(
        existing + "\n" + row + "\n", encoding="utf-8"
    )

    wind_m_s = float(case["wind_speed_mph"]) * 0.44704
    dt = float(spec["cfl"]) * dx / wind_m_s
    config_text = template
    replacements = {
        "@DT@": f"{dt:.8g}",
        "@TSTOP@": f"{float(spec['tstop_s']):.8g}",
        "@NUM_IGNITIONS@": str(num_ignitions),
        "@IGNITION_COORDINATES@": ignition_text,
        "@NO_SURFACE_FIRE@": ".TRUE." if spec["no_surface_fire"] else ".FALSE.",
    }
    for token, value in replacements.items():
        config_text = config_text.replace(token, value)
    if "@" in config_text:
        raise RuntimeError(f"Unresolved namelist token in {name}")
    (variant_dir / "elmfire.data.in").write_text(config_text, encoding="utf-8")
    fingerprint = input_fingerprint(variant_dir)

    requires_feature = bool(spec["requires_feature"])
    runnable = (not requires_feature) or feature_available
    capability = (
        "available; variant may be executed"
        if runnable else
        f"NOT EVALUATED: case metadata does not enable {case['feature_keyword']}"
    )
    return {
        **spec,
        "working_directory": str(variant_dir.relative_to(case_dir)),
        "config": "elmfire.data.in",
        "runnable": runnable,
        "capability_status": capability,
        "nx": nx, "ny": ny, "physical_columns": physical_columns,
        "physical_rows": physical_rows,
        "physical_width_m": physical_rows * dx,
        "requested_physical_width_m": requested_width,
        "n_structures_x": n_structures_x,
        "buffer_cells": BUFFER_CELLS, "center_row": center_row,
        "simulation_dt_s": dt, "num_ignitions": num_ignitions,
        "source_structure_count": source_structure_count,
        "source_cell_count": int(source_mask.sum()),
        "building_cell_count": int(building_mask.sum()),
        "hrrpua_input_kw_m2": hrr_peak,
        "ignition_hardening_factor": hardening,
        "input_fingerprint": fingerprint,
    }


def main():
    """Prepare the paired no-surface reference reference and surface-coupled surface-coupled variant."""
    case_dir = Path(__file__).resolve().parents[1]
    case = json.loads((case_dir / CASE_FILENAME).read_text(encoding="utf-8"))
    template = (case_dir / NAMELIST_TEMPLATE).read_text(encoding="utf-8")
    feature_available = bool(case.get("required_feature_available", False))
    manifest = [
        write_variant(case_dir, template, case, spec, feature_available)
        for spec in case["variants"]
    ]
    manifest_path = case_dir / VARIANTS_DIRECTORY / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    runnable = sum(item["runnable"] for item in manifest)
    print(f"[OK] prepared {len(manifest)} variants ({runnable} runnable)")
    if runnable < len(manifest):
        print(
            f"[INFO] {len(manifest) - runnable} prospective variants are "
            "capability-gated; see variants/manifest.json"
        )


if __name__ == "__main__":
    main()
