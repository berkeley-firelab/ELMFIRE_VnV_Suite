#!/usr/bin/env python3

from __future__ import annotations

import shutil
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

RADIUS = 5

# Float input rasters: (name, initial value)
FLOAT_RASTERS = [
	("ws", 0.0),   # Wind speed, mph
	("wd", 0.0),   # Wind direction, deg
	("m1", 0.0),   # 1-hr dead moisture content, %
	("m10", 0.0),  # 10-hr dead moisture content, %
	("m100", 0.0), # 100-hr dead moisture content, %
	("adj", 1.0),  # Spread rate adjustment factor
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


def write_float_raster(
	output_path: Path,
	nx: int,
	ny: int,
	cell_size: float,
	xmin: float,
	ymin: float,
	data: np.ndarray,
	a_srs: str = "EPSG:32610",
) -> None:
	"""Write a float raster to GeoTIFF using rasterio."""
	transform = from_bounds(xmin, ymin, xmin + nx * cell_size, ymin + ny * cell_size, nx, ny)
	
	with rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		height=ny,
		width=nx,
		count=1,
		dtype=rasterio.float32,
		crs=a_srs,
		transform=transform,
		compress='deflate',
		zlevel=9,
		nodata=-9999,
	) as dst:
		dst.write(data.astype(np.float32), 1)


def write_int_raster(
	output_path: Path,
	nx: int,
	ny: int,
	cell_size: float,
	xmin: float,
	ymin: float,
	data: np.ndarray,
	a_srs: str = "EPSG:32610",
) -> None:
	"""Write an integer raster to GeoTIFF using rasterio."""
	transform = from_bounds(xmin, ymin, xmin + nx * cell_size, ymin + ny * cell_size, nx, ny)
	
	with rasterio.open(
		output_path,
		'w',
		driver='GTiff',
		height=ny,
		width=nx,
		count=1,
		dtype=rasterio.int16,
		crs=a_srs,
		transform=transform,
		compress='deflate',
		zlevel=9,
		nodata=-9999,
	) as dst:
		dst.write(data.astype(np.int16), 1)


def create_circular_phi(
	nx: int,
	ny: int,
	cell_size: float,
	xmin: float,
	ymin: float,
	radius: float,
) -> np.ndarray:
	"""
	Create a circular phi field.
	
	phi = -1.0 inside circle of given radius centered at domain center
	phi = 1.0 outside circle
	"""
	# Create coordinate grids
	x = xmin + (np.arange(nx) + 0.5) * cell_size
	y = ymin + (np.arange(ny) + 0.5) * cell_size
	xx, yy = np.meshgrid(x, y)
	
	# Calculate distance from domain center (0, 0)
	distance = np.sqrt(xx**2 + yy**2)
	
	# Create phi field
	phi = np.where(distance <= radius, -1.0, 1.0)
	return phi


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

	# Calculate grid dimensions
	nx = int(np.round((xmax - xmin) / cell_size))
	ny = int(np.round((ymax - ymin) / cell_size))

	fuel_models_path = inputs_dir / FUEL_MODELS_FILENAME
	download_file(FUEL_MODELS_URL, fuel_models_path)

	# Create float rasters with constant values
	for raster_name, raster_value in FLOAT_RASTERS:
		data = np.full((ny, nx), raster_value, dtype=np.float32)
		write_float_raster(
			inputs_dir / f"{raster_name}.tif",
			nx, ny, cell_size, xmin, ymin, data, a_srs
		)

	# Create integer rasters with constant values
	for raster_name, raster_value in INT_RASTERS:
		data = np.full((ny, nx), raster_value, dtype=np.int16)
		write_int_raster(
			inputs_dir / f"{raster_name}.tif",
			nx, ny, cell_size, xmin, ymin, data, a_srs
		)

	# Create circular phi field
	phi = create_circular_phi(nx, ny, cell_size, xmin, ymin, RADIUS)
	write_float_raster(
		inputs_dir / "phi.tif",
		nx, ny, cell_size, xmin, ymin, phi, a_srs
	)

	print("[OK] Input rasters generated")
	print(f"  scratch: {scratch_dir}")
	print(f"  inputs:  {inputs_dir}")
	print(f"  outputs: {outputs_dir}")
	print(f"  fuel models: {fuel_models_path}")
	print(f"  domain: {nx}x{ny} cells, {cell_size}m resolution")
	print(f"  circular phi radius: {RADIUS}m")


if __name__ == "__main__":
	main()
