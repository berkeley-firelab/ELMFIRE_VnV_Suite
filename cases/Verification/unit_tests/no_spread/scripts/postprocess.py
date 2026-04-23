#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------- Imports & paths -----------------------
from pathlib import Path
from glob import glob
import json
import re
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# Resolve case directory assuming this file is .../cases/<case>/scripts/postprocess.py
CASE_DIR = Path(__file__).resolve().parents[1]
# To read
DATA_DIR = CASE_DIR / "data"
ELMFIRE_INPUT = DATA_DIR / "inputs"
ELMFIRE_OUTPUT = DATA_DIR / "outputs"
# To write
FIG_DIR = CASE_DIR / "figures"
REP_DIR = CASE_DIR / "report"
OUT_DIR = CASE_DIR / "outputs"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REP_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------- Add customized postprocessing code below -----------------------
def parse_elmfire_data_config(file_path: Path) -> dict:
    config = {}
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


def get_float(config: dict, key: str, default: float | None = None) -> float:
    value = config.get(key)
    if value is None:
        if default is None:
            raise KeyError(f"Missing required key in elmfire.data: {key}")
        return float(default)
    return float(value)


def read_tif_as_array(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        arr = np.array(img)
    return np.asarray(arr)


def extract_time_seconds(path: Path) -> float:
    # ELMFIRE output examples: phi_0000001_0003600.tif, time_of_arrival_0000001_0003601.tif
    m = re.search(r"_(\d+)\.tif$", path.name)
    if not m:
        raise ValueError(f"Could not infer time from filename: {path.name}")
    return float(int(m.group(1)))


def load_time_series(prefix: str) -> tuple[np.ndarray, np.ndarray]:
    files = sorted(Path(p) for p in glob(str(ELMFIRE_OUTPUT / f"{prefix}_*.tif")))
    if not files:
        return np.array([], dtype=float), np.empty((0, 0, 0), dtype=np.float32)

    times = np.array([extract_time_seconds(p) for p in files], dtype=float)
    arrays = [read_tif_as_array(p).astype(np.float32, copy=False) for p in files]
    stack = np.stack(arrays, axis=0)
    return times, stack


def load_latest_frame(prefix: str) -> np.ndarray:
    files = sorted(Path(p) for p in glob(str(ELMFIRE_OUTPUT / f"{prefix}_*.tif")))
    if not files:
        return np.empty((0, 0), dtype=np.float32)
    return read_tif_as_array(files[-1]).astype(np.float32, copy=False)


def build_domain_vectors(config: dict, nx: int, ny: int, t: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cell_size = get_float(config, "COMPUTATIONAL_DOMAIN_CELLSIZE")
    xllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
    yllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_YLLCORNER")

    x = xllcorner + (np.arange(nx, dtype=float) + 0.5) * cell_size
    y = yllcorner + (np.arange(ny, dtype=float) + 0.5) * cell_size

    if t.size > 0:
        tvec = t
    else:
        dt_dump = get_float(config, "DTDUMP", default=1.0)
        t_stop = get_float(config, "SIMULATION_TSTOP", default=0.0)
        if dt_dump <= 0:
            tvec = np.array([0.0], dtype=float)
        else:
            tvec = np.arange(dt_dump, t_stop + 0.5 * dt_dump, dt_dump, dtype=float)
    return x, y, tvec


def load_elmfire_arrays() -> dict:
    config_path = CASE_DIR / "elmfire.data.in"
    if not config_path.exists():
        config_path = ELMFIRE_INPUT / "elmfire.data"
    if not config_path.exists():
        raise FileNotFoundError("Could not find elmfire.data.in or data/inputs/elmfire.data")

    config = parse_elmfire_data_config(config_path)

    t_phi, phi = load_time_series("phi")
    t_sf, surface_fire = load_time_series("surface_fire")
    time_of_arrival = load_latest_frame("time_of_arrival")
    vs = load_latest_frame("vs")

    # Use the first available raster to determine nx, ny.
    sample = None
    for candidate in (phi, surface_fire, time_of_arrival[None, ...], vs[None, ...]):
        if candidate.size > 0:
            sample = candidate
            break
    if sample is None:
        raise FileNotFoundError(f"No ELMFIRE output GeoTIFFs found in {ELMFIRE_OUTPUT}")

    ny, nx = int(sample.shape[-2]), int(sample.shape[-1])
    t = t_phi if t_phi.size > 0 else t_sf
    x, y, t = build_domain_vectors(config, nx=nx, ny=ny, t=t)

    return {
        "x": x,
        "y": y,
        "t": t,
        "t_phi": t_phi,
        "t_surface_fire": t_sf,
        "phi": phi,
        "surface_fire": surface_fire,
        "time_of_arrival": time_of_arrival,
        "vs": vs,
    }
    
def field_stats(field: np.ndarray, *, nonnegative_only: bool = False) -> dict:
    values = np.asarray(field).ravel()
    values = values[np.isfinite(values)]
    if nonnegative_only:
        values = values[values >= 0]

    if values.size == 0:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
        }

    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }
    
def analytical_solution_comparison(phi_n: np.ndarray) -> np.ndarray:
    # Since ros is 0, the analytical solution should be the initial condition for all time steps.
    difference = phi_n - phi_n[0]  # Shape: (nt, ny, nx)
    norm = np.linalg.norm(difference, axis=(1, 2))  # L2 norm over spatial dimensions for each time step shape: (nt,)
    return difference, norm

def plot_field(x: np.ndarray, y: np.ndarray, field: np.ndarray, title: str, out_path: Path):
    plt.figure(figsize=(8, 6))
    plt.contourf(x, y, field, levels=50, cmap="inferno", vmin=np.nanmin(field), vmax=np.nanmax(field))
    plt.colorbar(label=title)
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title(title)
    plt.savefig(out_path, dpi=300)
    plt.close()
    return None


arrays = load_elmfire_arrays()

# Optional convenience export for downstream analysis notebooks/scripts.
np.savez_compressed(OUT_DIR / "elmfire_arrays.npz", **arrays)

# Create plots
plot_field(arrays["x"], arrays["y"], arrays["phi"][0], r"$\phi(x,y,0)$", FIG_DIR / "phi_initial.png")
plot_field(arrays["x"], arrays["y"], arrays["phi"][-1], r"$\phi(x,y,t_{\text{final}})$", FIG_DIR / "phi_final.png")
plot_field(arrays["x"], arrays["y"], arrays["surface_fire"][0], r"$\text{Surface Fire}(x,y,0)$", FIG_DIR / "surface_fire_initial.png")
plot_field(arrays["x"], arrays["y"], arrays["surface_fire"][-1], r"$\text{Surface Fire}(x,y,T)$", FIG_DIR / "surface_fire_final.png")
plot_field(arrays["x"], arrays["y"], arrays["time_of_arrival"], r"$\text{Time of Arrival}(x,y)$", FIG_DIR / "time_of_arrival.png")
plot_field(arrays["x"], arrays["y"], arrays["vs"], r"$\text{Rate of Spread}(x,y)$", FIG_DIR / "vs.png")

# ----------------------- Output Metrics for report -----------------------
# Name-value pairs prepared for report usage.
phi_stats = field_stats(arrays["phi"])
surface_fire_stats = field_stats(arrays["surface_fire"])
time_of_arrival_stats = field_stats(arrays["time_of_arrival"])
vs_stats = field_stats(arrays["vs"], nonnegative_only=True)
# Get analytical solution comparison metrics (error norms) if possible.
if arrays["phi"].shape[0] > 1:
    difference, error_norm = analytical_solution_comparison(arrays["phi"])
    plot_field(arrays["x"], arrays["y"], np.abs(difference[-1]), r"$\|\phi(x,y,t_{\text{final}}) - \phi(x,y,0)\|_2$", FIG_DIR / "phi_error_final.png")
    # Plot error curves over time
    plt.figure(figsize=(8, 6))
    plt.plot(arrays["t"], error_norm, marker="o")
    plt.xlabel("Time (s)")
    plt.ylabel(r"$\|\phi(x,y,t_{\text{final}}) - \phi(x,y,0)\|_2$")
    plt.title(r"Error Over Time")
    plt.grid()
    plt.savefig(FIG_DIR / "phi_error_norm_over_time.png", dpi=300)
    plt.close()
else:
    error_norm = None

metrics = {
    "nx": int(arrays["x"].size),
    "ny": int(arrays["y"].size),
    "nt": int(arrays["t"].size),
    "x_min": float(arrays["x"][0]),
    "x_max": float(arrays["x"][-1]),
    "y_min": float(arrays["y"][0]),
    "y_max": float(arrays["y"][-1]),
    "t_min": float(arrays["t"][0]) if arrays["t"].size > 0 else None,
    "t_max": float(arrays["t"][-1]) if arrays["t"].size > 0 else None,
    # "nt_surface_fire": int(arrays["surface_fire"].shape[0]) if arrays["surface_fire"].ndim == 3 else 0,
    "phi_min": phi_stats["min"],
    "phi_max": phi_stats["max"],
    "phi_mean": phi_stats["mean"],
    "phi_std": phi_stats["std"],
    "surface_fire_min": surface_fire_stats["min"],
    "surface_fire_max": surface_fire_stats["max"],
    "surface_fire_mean": surface_fire_stats["mean"],
    "surface_fire_std": surface_fire_stats["std"],
    "time_of_arrival_min": time_of_arrival_stats["min"],
    "time_of_arrival_max": time_of_arrival_stats["max"],
    "time_of_arrival_mean": time_of_arrival_stats["mean"],
    "time_of_arrival_std": time_of_arrival_stats["std"],
    "vs_min": vs_stats["min"],
    "vs_max": vs_stats["max"],
    "vs_mean": vs_stats["mean"],
    "vs_std": vs_stats["std"],
    "phi_error_norm_avg": float(np.mean(error_norm)),
}
(OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


print("[OK] Postprocess complete.")
print(f"  - Domain: nx={metrics['nx']}, ny={metrics['ny']}, nt_phi={metrics['nt']}")
print(f"  - x range: [{metrics['x_min']}, {metrics['x_max']}], y range: [{metrics['y_min']}, {metrics['y_max']}], t range: [{metrics['t_min']}, {metrics['t_max']}]")
print(f"  - Arrays NPZ: {OUT_DIR/'elmfire_arrays.npz'}")
print(f"  - Figures: {FIG_DIR}")
print(f"  - Report snippets: {REP_DIR/'figures.tex'}, {REP_DIR/'metrics.tex'}")
print(f"  - Metrics JSON: {OUT_DIR/'metrics.json'}")
