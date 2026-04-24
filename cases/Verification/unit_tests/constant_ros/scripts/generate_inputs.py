#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


# Float input rasters: (name, initial value)
FLOAT_RASTERS = [
	("ws", 0.0),   # Wind speed, mph
	("wd", 0.0),   # Wind direction, deg
	("m1", 0.0),   # 1-hr dead moisture content, %
	("m10", 0.0),  # 10-hr dead moisture content, %
	("m100", 0.0), # 100-hr dead moisture content, %
	("adj", 1.0),  # Spread rate adjustment factor
	("phi", 1.0),  # Initial value of phi field
]

# Integer input rasters: (name, initial value)
INT_RASTERS = [
	("slp", 0),     # Topographical slope (deg)
	("asp", 0),     # Topographical aspect (deg)
	("dem", 0),     # Elevation (m)
	("fbfm40", 102),# Fire behavior fuel model code
	("cc", 0),      # Canopy cover (percent)
	("ch", 0),      # Canopy height (10*meters)
	("cbh", 0),     # Canopy base height (10*meters)
	("cbd", 0),     # Canopy bulk density (100*kg/m3)
]

FUEL_MODELS_URL = "https://raw.githubusercontent.com/lautenberger/elmfire/refs/heads/main/build/source/fuel_models.csv"
FUEL_MODELS_FILENAME = "fuel_models.csv"


def run_cmd(cmd: list[str]) -> None:
	"""Run a command and fail fast if it exits non-zero."""
	subprocess.run(cmd, check=True)


def parse_elmfire_data_config(file_path: Path) -> dict[str, str]:
	config: dict[str, str] = {}
	for raw_line in file_path.read_text(encoding="utf-8").splitlines():
		line = raw_line.strip()
		if not line or line.startswith("&") or line == "/":
			continue
		if "=" not in line:
			continue
		key, value = line.split("=", 1)
		key = key.strip().upper()
		value = value.strip()
		if "!" in value:
			value = value.split("!", 1)[0].strip()
		if value.startswith("'") and value.endswith("'") and len(value) >= 2:
			value = value[1:-1]
		if value.startswith('"') and value.endswith('"') and len(value) >= 2:
			value = value[1:-1]
		config[key] = value
	return config


def get_float_value(config: dict[str, str], key: str) -> float:
	if key not in config:
		raise RuntimeError(f"Missing key in elmfire.data.in: {key}")
	try:
		return float(config[key])
	except ValueError as exc:
		raise RuntimeError(f"Invalid numeric value for {key}: {config[key]}") from exc


def download_file(url: str, destination: Path) -> None:
	try:
		with urllib.request.urlopen(url) as response:
			content = response.read()
	except urllib.error.URLError as exc:
		raise RuntimeError(f"Failed to download {url}: {exc}") from exc
	destination.write_bytes(content)


def main() -> None:
	case_dir = Path(__file__).resolve().parents[1]
	data_dir = case_dir / "data"
	scratch_dir = data_dir / "scratch"
	inputs_dir = data_dir / "inputs"
	outputs_dir = data_dir / "outputs"
	src_data = case_dir / "elmfire.data.in"

	# Ensure parent data folder exists for all generated subfolders.
	data_dir.mkdir(parents=True, exist_ok=True)

	for d in (scratch_dir, inputs_dir, outputs_dir):
		if d.exists():
			shutil.rmtree(d)
		d.mkdir(parents=True, exist_ok=True)

	dst_data = inputs_dir / "elmfire.data"
	shutil.copy2(src_data, dst_data)
	config_path = dst_data
	config = parse_elmfire_data_config(config_path)
 
	xllcorner = get_float_value(config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
	if xllcorner >= 0:
		raise RuntimeError(
			"Cannot infer domain size from elmfire.data when "
			"COMPUTATIONAL_DOMAIN_XLLCORNER is non-negative."
		)
	domain_size = -2.0 * xllcorner

	cell_size = get_float_value(config, "COMPUTATIONAL_DOMAIN_CELLSIZE")
	a_srs = config.get("A_SRS", "EPSG:32610")

	xmin = -0.5 * domain_size
	xmax = 0.5 * domain_size
	ymin = xmin
	ymax = xmax

	tr = [str(cell_size), str(cell_size)]
	te = [str(xmin), str(ymin), str(xmax), str(ymax)]

	fuel_models_path = inputs_dir / FUEL_MODELS_FILENAME
	download_file(FUEL_MODELS_URL, fuel_models_path)

	dummy_xyz = scratch_dir / "dummy.xyz"
	dummy_xyz.write_text(
		"x,y,z\n"
		"-100000,-100000,0\n"
		"100000,-100000,0\n"
		"-100000,100000,0\n"
		"100000,100000,0\n",
		encoding="utf-8",
	)

	dummy_tif = scratch_dir / "dummy.tif"
	float_base_tif = scratch_dir / "float.tif"
	int_base_tif = scratch_dir / "int.tif"

	run_cmd([
		"gdalwarp",
		"-tr", "200000", "200000",
		"-te", "-100000", "-100000", "100000", "100000",
		"-s_srs", a_srs,
		"-t_srs", a_srs,
		str(dummy_xyz),
		str(dummy_tif),
	])

	run_cmd([
		"gdalwarp",
		"-dstnodata", "-9999",
		"-ot", "Float32",
		"-tr", *tr,
		"-te", *te,
		str(dummy_tif),
		str(float_base_tif),
	])

	run_cmd([
		"gdalwarp",
		"-dstnodata", "-9999",
		"-ot", "Int16",
		"-tr", *tr,
		"-te", *te,
		str(dummy_tif),
		str(int_base_tif),
	])

	for raster_name, raster_value in FLOAT_RASTERS:
		run_cmd([
			"gdal_calc.py",
			"-A", str(float_base_tif),
			"--co=COMPRESS=DEFLATE",
			"--co=ZLEVEL=9",
			"--NoDataValue=-9999",
			f"--outfile={inputs_dir / f'{raster_name}.tif'}",
			f"--calc=A + {raster_value}",
		])

	for raster_name, raster_value in INT_RASTERS:
		run_cmd([
			"gdal_calc.py",
			"-A", str(int_base_tif),
			"--co=COMPRESS=DEFLATE",
			"--co=ZLEVEL=9",
			"--NoDataValue=-9999",
			f"--outfile={inputs_dir / f'{raster_name}.tif'}",
			f"--calc=A + {raster_value}",
		])

	print("[OK] Input rasters generated")
	print(f"  scratch: {scratch_dir}")
	print(f"  inputs:  {inputs_dir}")
	print(f"  outputs: {outputs_dir}")
	print(f"  fuel models: {fuel_models_path}")


if __name__ == "__main__":
	main()
