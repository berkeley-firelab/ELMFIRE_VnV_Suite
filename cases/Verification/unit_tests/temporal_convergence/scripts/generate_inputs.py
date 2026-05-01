#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from osgeo import gdal


FLOAT_RASTERS = [
	("ws", 0.0),
	("wd", 0.0),
	("m1", 0.0),
	("m10", 0.0),
	("m100", 0.0),
	("adj", 1.0),
]

INT_RASTERS = [
	("slp", 0),
	("asp", 0),
	("dem", 0),
	("fbfm40", 102),
	("cc", 0),
	("ch", 0),
	("cbh", 0),
	("cbd", 0),
]

TIME_GRIDS = [180, 360, 720, 1440]
FIXED_RESOLUTION = 1024
PHI_RADIUS = 5

FUEL_MODELS_URL = "https://raw.githubusercontent.com/lautenberger/elmfire/refs/heads/main/build/source/fuel_models.csv"
FUEL_MODELS_FILENAME = "fuel_models.csv"


def run_cmd(cmd: list[str]) -> None:
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


def replace_kv(text: str, key: str, value: str) -> str:
	lines = text.splitlines()
	for index, line in enumerate(lines):
		if line.strip().upper().startswith(key.upper()):
			parts = line.split("=", 1)
			if len(parts) == 2:
				lines[index] = f"{parts[0].rstrip()} = {value}"
				break
	return "\n".join(lines) + "\n"


def write_simulation_config(base_text: str, out_path: Path, time_grid: int) -> None:
	dt_value = 360.0 / time_grid
	text = replace_kv(base_text, "SIMULATION_DT", f"{dt_value:.6f}")
	text = replace_kv(text, "SIMULATION_DTMAX", f"{dt_value:.6f}")
	text = replace_kv(text, "OUTPUTS_DIRECTORY", f"'./data/outputs/{time_grid}'")
	text = replace_kv(text, "SCRATCH", f"'./data/scratch/{time_grid}'")
	out_path.write_text(text, encoding="utf-8")


def create_phi(base_tif: Path, out_tif: Path, radius: float) -> None:
	ds = gdal.Open(str(base_tif))
	if ds is None:
		raise RuntimeError(f"Failed to open base tif: {base_tif}")
	gt = ds.GetGeoTransform()
	proj = ds.GetProjection()
	band = ds.GetRasterBand(1)
	arr = band.ReadAsArray()
	ny, nx = arr.shape

	x_coords = gt[0] + (np.arange(nx) + 0.5) * gt[1]
	y_coords = gt[3] + (np.arange(ny) + 0.5) * gt[5]
	xv, yv = np.meshgrid(x_coords, y_coords)
	mask = (xv**2 + yv**2) <= (radius**2)

	phi = np.ones_like(arr, dtype=np.float32)
	phi[mask] = -1.0

	driver = gdal.GetDriverByName("GTiff")
	out_ds = driver.Create(
		str(out_tif), nx, ny, 1, gdal.GDT_Float32,
		options=["COMPRESS=DEFLATE", "ZLEVEL=9"],
	)
	out_ds.SetGeoTransform(gt)
	out_ds.SetProjection(proj)
	out_band = out_ds.GetRasterBand(1)
	out_band.WriteArray(phi)
	out_band.SetNoDataValue(-9999)
	out_band.FlushCache()
	out_ds = None


def main() -> None:
	case_dir = Path(__file__).resolve().parents[1]
	data_dir = case_dir / "data"
	inputs_dir = data_dir / "inputs"
	outputs_root = data_dir / "outputs"
	scratch_root = data_dir / "scratch"
	source_config = case_dir / "elmfire.data.in"

	for directory in (data_dir, inputs_dir, outputs_root, scratch_root):
		directory.mkdir(parents=True, exist_ok=True)

	base_config_path = inputs_dir / "elmfire.data"
	shutil.copy2(source_config, base_config_path)
	base_text = base_config_path.read_text(encoding="utf-8")
	config = parse_elmfire_data_config(base_config_path)

	xllcorner = get_float_value(config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
	if xllcorner >= 0:
		raise RuntimeError(
			"Cannot infer domain size from elmfire.data when "
			"COMPUTATIONAL_DOMAIN_XLLCORNER is non-negative."
		)
	domain_size = -2.0 * xllcorner
	a_srs = config.get("A_SRS", "EPSG:32610")

	xmin = -0.5 * domain_size
	xmax = 0.5 * domain_size
	ymin = xmin
	ymax = xmax

	fuel_models_path = inputs_dir / FUEL_MODELS_FILENAME
	download_file(FUEL_MODELS_URL, fuel_models_path)

	dummy_xyz_base = scratch_root / "scratch_dummy.xyz"
	dummy_xyz_base.write_text(
		"x,y,z\n"
		"-100000,-100000,0\n"
		"100000,-100000,0\n"
		"-100000,100000,0\n"
		"100000,100000,0\n",
		encoding="utf-8",
	)

	cell_size = domain_size / float(FIXED_RESOLUTION)
	tr = [str(cell_size), str(cell_size)]
	te = [str(xmin), str(ymin), str(xmax), str(ymax)]

	dummy_tif = scratch_root / "dummy.tif"
	float_base_tif = scratch_root / "float.tif"
	int_base_tif = scratch_root / "int.tif"

	run_cmd([
		"gdalwarp",
		"-tr", "200000", "200000",
		"-te", "-100000", "-100000", "100000", "100000",
		"-s_srs", a_srs,
		"-t_srs", a_srs,
		str(dummy_xyz_base),
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

	create_phi(float_base_tif, inputs_dir / "phi.tif", PHI_RADIUS)

	for time_grid in TIME_GRIDS:
		write_simulation_config(base_text, inputs_dir / f"elmfire_{time_grid}.data", time_grid)
		(outputs_root / str(time_grid)).mkdir(parents=True, exist_ok=True)
		(scratch_root / str(time_grid)).mkdir(parents=True, exist_ok=True)

	print("[OK] Input rasters generated")
	print(f"  inputs:  {inputs_dir}")
	print(f"  outputs: {outputs_root}")
	print(f"  scratch: {scratch_root}")
	print(f"  fuel models: {fuel_models_path}")
	print(f"  time grids: {', '.join(str(grid) for grid in TIME_GRIDS)}")


if __name__ == "__main__":
	main()