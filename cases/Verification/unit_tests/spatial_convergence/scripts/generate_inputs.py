#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
import numpy as np
from osgeo import gdal


# Float input rasters: (name, initial value)
FLOAT_RASTERS = [
	("ws", 0.0),   # Wind speed, mph
	("wd", 0.0),   # Wind direction, deg
	("m1", 0.0),   # 1-hr dead moisture content, %
	("m10", 0.0),  # 10-hr dead moisture content, %
	("m100", 0.0), # 100-hr dead moisture content, %
	("adj", 1.0),  # Spread rate adjustment factor
	# note: `phi` handled specially to create circular ignition (-1 inside)
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

RESOLUTIONS = [1024, 512, 256, 128]
PHI_RADIUS = 5

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
	src_data = case_dir / "elmfire.data.in"

	# Ensure parent data folder exists for all generated subfolders.
	data_dir.mkdir(parents=True, exist_ok=True)

	dst_config = data_dir / "elmfire.data"
	shutil.copy2(src_data, dst_config)
	config_path = dst_config
	config = parse_elmfire_data_config(config_path)

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

	fuel_models_global = data_dir / FUEL_MODELS_FILENAME
	download_file(FUEL_MODELS_URL, fuel_models_global)

	dummy_xyz_base = data_dir / "scratch_dummy.xyz"
	dummy_xyz_base.write_text(
		"x,y,z\n"
		"-100000,-100000,0\n"
		"100000,-100000,0\n"
		"-100000,100000,0\n"
		"100000,100000,0\n",
		encoding="utf-8",
	)

	# We'll iterate over target resolutions and create separate data/<res> folders
	for res in RESOLUTIONS:
		res_dir = data_dir / str(res)
		scratch_dir = res_dir / "scratch"
		inputs_dir = res_dir / "inputs"
		outputs_dir = res_dir / "outputs"

		for d in (scratch_dir, inputs_dir, outputs_dir):
			if d.exists():
				shutil.rmtree(d)
			d.mkdir(parents=True, exist_ok=True)

		# copy elmfire.data.in into inputs for this resolution and update cell size
		dst_data = inputs_dir / "elmfire.data"
		shutil.copy2(src_data, dst_data)

		# compute and write per-resolution cell size (cell_size = domain_size / nodes)
		cell_size = domain_size / float(res)
		text = dst_data.read_text(encoding="utf-8")
		def replace_kv(text: str, key: str, value: str) -> str:
			lines = text.splitlines()
			for i, line in enumerate(lines):
				if line.strip().upper().startswith(key.upper()):
					parts = line.split("=", 1)
					if len(parts) == 2:
						lines[i] = f"{parts[0].rstrip()} = {value}"
						break
			return "\n".join(lines) + "\n"

		text = replace_kv(text, "COMPUTATIONAL_DOMAIN_CELLSIZE", f"{cell_size:.6f}")
		# adjust directory paths so ELMFIRE can be run inside the resolution folder
		text = replace_kv(text, "FUELS_AND_TOPOGRAPHY_DIRECTORY", "'./inputs'")
		text = replace_kv(text, "WEATHER_DIRECTORY", "'./inputs'")
		text = replace_kv(text, "OUTPUTS_DIRECTORY", "'./outputs'")
		text = replace_kv(text, "SCRATCH", "'./scratch'")
		dst_data.write_text(text, encoding="utf-8")

		# per-resolution fuel models
		fuel_models_path = inputs_dir / FUEL_MODELS_FILENAME
		shutil.copy2(fuel_models_global, fuel_models_path)

		# compute pixel size for this resolution
		tr = [str(domain_size / res), str(domain_size / res)]
		te = [str(xmin), str(ymin), str(xmax), str(ymax)]

		dummy_tif = scratch_dir / "dummy.tif"
		float_base_tif = scratch_dir / "float.tif"
		int_base_tif = scratch_dir / "int.tif"

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

		# create float rasters (excluding phi)
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

		# create integer rasters
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

		# create phi raster with circular region of radius PHI_RADIUS set to -1, else +1
		def create_phi(base_tif: Path, out_tif: Path, radius: float) -> None:
			ds = gdal.Open(str(base_tif))
			if ds is None:
				raise RuntimeError(f"Failed to open base tif: {base_tif}")
			gt = ds.GetGeoTransform()
			proj = ds.GetProjection()
			band = ds.GetRasterBand(1)
			arr = band.ReadAsArray()
			ny, nx = arr.shape

			# compute coordinates of pixel centers
			xs = gt[0] + (np.arange(nx) + 0.5) * gt[1] + (np.arange(ny) + 0.5) * gt[2]
			ys = gt[3] + (np.arange(ny) + 0.5) * gt[5] + (np.arange(nx) + 0.5) * gt[4]

			# But gt[2] and gt[4] usually zero; use meshgrid safer
			x_coords = gt[0] + (np.arange(nx) + 0.5) * gt[1]
			y_coords = gt[3] + (np.arange(ny) + 0.5) * gt[5]
			xv, yv = np.meshgrid(x_coords, y_coords)

			# center at (0,0)
			dist2 = (xv - 0.0) ** 2 + (yv - 0.0) ** 2
			mask = dist2 <= (radius ** 2)

			phi = np.ones_like(arr, dtype=np.float32)
			phi[mask] = -1.0

			# write out
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

		create_phi(float_base_tif, inputs_dir / "phi.tif", PHI_RADIUS)

	print("[OK] Input rasters generated")
	print(f"  scratch: {scratch_dir}")
	print(f"  inputs:  {inputs_dir}")
	print(f"  outputs: {outputs_dir}")
	print(f"  fuel models: {fuel_models_path}")


if __name__ == "__main__":
	main()
