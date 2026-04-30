#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ----------------------- Imports & paths -----------------------
from pathlib import Path
from glob import glob
import json
import re
from typing import Literal
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


def load_initial_phi_from_file(nx: int, ny: int) -> np.ndarray | None:
    phi_path = ELMFIRE_INPUT / "phi.tif"
    if not phi_path.exists():
        return None

    phi0 = read_tif_as_array(phi_path).astype(np.float32, copy=False)
    if phi0.ndim != 2:
        return None
    if phi0.shape != (ny, nx):
        return None
    return phi0

def analytical_solution(
    x: np.ndarray,
    y: np.ndarray,
    t: np.ndarray,
    ros: float = 2.29,
    R0: float = 0.0,
    mode: str = "binary",
) -> np.ndarray:
    # Support two useful analytical forms:
    # - "binary": phi = -1 inside the disk r <= R0 + ROS*t, +1 outside (binary indicator used by tests)
    # - "signed_distance": d = r - (R0 + ROS*t) (continuous signed distance)
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)  # shape (ny, nx)
    t_arr = np.atleast_1d(t).astype(float)
    radii = R0 + ros * t_arr  # shape (nt,)

    if mode == "binary":
        mask = r[None, :, :] <= radii[:, None, None]  # shape (nt, ny, nx)
        phi = np.where(mask, -1.0, 1.0).astype(np.float32)
        return phi
    elif mode == "signed_distance":
        d = r[None, :, :] - radii[:, None, None]
        return d.astype(np.float32)
    else:
        raise ValueError(f"Unknown mode for analytical_solution: {mode}")


def build_initial_phi_from_ignition(config: dict, nx: int, ny: int) -> np.ndarray:
    cell_size = get_float(config, "COMPUTATIONAL_DOMAIN_CELLSIZE")
    xllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
    yllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_YLLCORNER")

    # ELMFIRE convention in this case: unburned ~ +1 and ignited cells = -1.
    phi0 = np.ones((ny, nx), dtype=np.float32)

    x_centers = xllcorner + (np.arange(nx, dtype=float) + 0.5) * cell_size
    y_centers = yllcorner + (np.arange(ny, dtype=float) + 0.5) * cell_size

    num_ignitions = int(round(get_float(config, "NUM_IGNITIONS", default=0.0)))
    for i in range(1, num_ignitions + 1):
        x_key = f"X_IGN({i})"
        y_key = f"Y_IGN({i})"
        t_key = f"T_IGN({i})"
        if x_key not in config or y_key not in config:
            continue

        t_ign = get_float(config, t_key, default=0.0)
        if t_ign > 0.0:
            continue

        x_ign = get_float(config, x_key)
        y_ign = get_float(config, y_key)

        # Map ignition coordinates to the nearest cell centers.
        ix = int(np.argmin(np.abs(x_centers - x_ign)))
        iy = int(np.argmin(np.abs(y_centers - y_ign)))

        # Raster row index is top-origin, y-centers are bottom-origin.
        row = ny - 1 - iy
        col = ix
        phi0[row, col] = -1.0

    return phi0


def build_domain_vectors(config: dict, nx: int, ny: int, t: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cell_size = get_float(config, "COMPUTATIONAL_DOMAIN_CELLSIZE")
    xllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
    yllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_YLLCORNER")

    x = xllcorner + (np.arange(nx, dtype=float) + 0.5) * cell_size
    y = yllcorner + (np.arange(ny, dtype=float) + 0.5) * cell_size

    if t.size > 0:
        tvec = t if np.isclose(t[0], 0.0) else np.concatenate(([0.0], t))
    else:
        dt_dump = get_float(config, "DTDUMP", default=1.0)
        t_stop = get_float(config, "SIMULATION_TSTOP", default=0.0)
        if dt_dump <= 0:
            tvec = np.array([0.0], dtype=float)
        else:
            tvec = np.arange(0.0, t_stop + 0.5 * dt_dump, dt_dump, dtype=float)
    return x, y, tvec


def load_elmfire_arrays() -> dict:
    # config_path = CASE_DIR / "elmfire.data"
    # if not config_path.exists():
    config_path = ELMFIRE_INPUT / "elmfire.data"
    if not config_path.exists():
        raise FileNotFoundError("Could not find the configuration file.")

    config = parse_elmfire_data_config(config_path)

    t_phi, phi = load_time_series("phi")
    if phi.size > 0:
        ny_phi, nx_phi = int(phi.shape[-2]), int(phi.shape[-1])
    else:
        sample = None
        for candidate in (load_latest_frame("surface_fire"), load_latest_frame("time_of_arrival"), load_latest_frame("vs")):
            if candidate.size > 0:
                sample = candidate
                break
        if sample is None:
            raise FileNotFoundError(f"No ELMFIRE output GeoTIFFs found in {ELMFIRE_OUTPUT}")
        ny_phi, nx_phi = int(sample.shape[-2]), int(sample.shape[-1])

    # Prefer an explicit initial-condition raster when available.
    # Keep ignition-based construction as a fallback.
    # phi0 = load_initial_phi_from_file(nx=nx_phi, ny=ny_phi)
    # if phi0 is None:
    # Kind of analytical solution construction based on ignition points, since ros=0 means phi should not evolve over time. This also allows us to have an initial condition even when no phi_*.tif files are output by ELMFIRE.
    phi0 = build_initial_phi_from_ignition(config, nx=nx_phi, ny=ny_phi)

    if phi.size == 0:
        t_phi = np.array([0.0], dtype=float)
        phi = phi0[None, ...]
    elif np.isclose(t_phi[0], 0.0):
        phi = phi.copy()
        phi[0] = phi0
    else:
        t_phi = np.concatenate(([0.0], t_phi))
        phi = np.concatenate((phi0[None, ...], phi), axis=0)

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

# NormOrder = int | float | Literal["fro", "nuc"] | None
def analytical_solution_comparison(
    phi_n: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    t: np.ndarray,
    norm: int | float | Literal["fro", "nuc"] | None = 2,
    ros: float = 2.29,
    R0: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    phi_analytical = analytical_solution(x=x, y=y, t=t, ros=ros, R0=R0)
    difference = phi_n - phi_analytical  # Shape: (nt, ny, nx)
    norms = np.linalg.norm(difference, axis=(1, 2), ord=norm)  # Supports numeric orders, +/-inf, and matrix norms like 'fro'.
    return difference, norms

def plot_field(
    x: np.ndarray,
    y: np.ndarray,
    field: np.ndarray,
    title: str,
    out_path: Path,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: str | None = None,
):
    arr = np.asarray(field)
    if cmap is None:
        unique = np.unique(np.nan_to_num(arr))
        if unique.size <= 2 and np.all(np.isin(unique, [-1.0, 1.0])):
            cmap = "bwr"
            if vmin is None:
                vmin = -1.0
            if vmax is None:
                vmax = 1.0
        else:
            cmap = "bwr"

    if vmin is None:
        vmin = float(np.nanmin(arr))
    if vmax is None:
        vmax = float(np.nanmax(arr))

    plt.figure(figsize=(8, 6))
    plt.contourf(x, y, arr, levels=50, cmap=cmap, vmin=vmin, vmax=vmax)
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
# Evaluate analytical solution on a denser grid for smoother contour plots
t_final = arrays["t"][-1] if arrays["t"].size > 0 else 10.0
num_dense = 800
ros_analytical = 0.0116332  # Use the same ROS as in the analytical solution for consistency
r0_analytical = 0.7071  # Assuming ignition starts at the origin
x_dense = np.linspace(arrays["x"][0], arrays["x"][-1], num_dense)
y_dense = np.linspace(arrays["y"][0], arrays["y"][-1], num_dense)
t_dense = np.linspace(0.0, t_final, num_dense)
# x_dense = arrays["x"]
# y_dense = arrays["y"]
# t_dense = arrays["t"] if arrays["t"].size > 0 else np.array([0.0], dtype=float)
phi_analytical = analytical_solution(
    x=x_dense, y=y_dense, t=t_dense, ros=ros_analytical, R0=r0_analytical, mode="binary"
)
plot_field(x_dense, y_dense, phi_analytical[0], r"Analytical $\phi(x,y,0)$", FIG_DIR / "phi_analytical_initial.png")
plot_field(x_dense, y_dense, phi_analytical[-1], r"Analytical $\phi(x,y,t_{\text{final}})$", FIG_DIR / "phi_analytical_final.png")
plot_field(arrays["x"], arrays["y"], arrays["phi"][0], r"$\phi(x,y,0)$", FIG_DIR / "phi_initial.png")
plot_field(arrays["x"], arrays["y"], arrays["phi"][-1], r"$\phi(x,y,t_{\text{final}})$", FIG_DIR / "phi_final.png")
plot_field(arrays["x"], arrays["y"], arrays["surface_fire"][0], r"$\text{Surface Fire}(x,y,0)$", FIG_DIR / "surface_fire_initial.png")
plot_field(arrays["x"], arrays["y"], arrays["surface_fire"][-1], r"$\text{Surface Fire}(x,y,t_{\text{final}})$", FIG_DIR / "surface_fire_final.png")
plot_field(arrays["x"], arrays["y"], arrays["time_of_arrival"], r"$\text{Time of Arrival}(x,y)$", FIG_DIR / "time_of_arrival.png")
plot_field(arrays["x"], arrays["y"], arrays["vs"], r"$\text{Rate of Spread}(x,y)$", FIG_DIR / "vs.png")

# ----------------------- Output Metrics for report -----------------------
# Name-value pairs prepared for report usage.
phi_stats = field_stats(arrays["phi"])
surface_fire_stats = field_stats(arrays["surface_fire"])
time_of_arrival_stats = field_stats(arrays["time_of_arrival"])
vs_stats = field_stats(arrays["vs"], nonnegative_only=True)
# Get analytical solution comparison metrics (error norms) if possible.
norm = np.inf  # Use max norm for error comparison, can be changed to 2 for L2 norm or other supported norms.
norm_label = r"\infty" if norm == np.inf else str(norm)
if arrays["phi"].shape[0] > 1:
    difference, error_norm = analytical_solution_comparison(
        arrays["phi"],
        x=arrays["x"],
        y=arrays["y"],
        t=arrays["t"],
        norm=norm,
        ros=ros_analytical,
        R0=r0_analytical,
    )
    plot_field(arrays["x"], arrays["y"], np.abs(difference[-1]), r"$|\phi(x,y,t_{\text{final}}) - \phi(x,y,0)|$", FIG_DIR / "phi_error_final.png")
    # Plot error curves over time
    plt.figure(figsize=(8, 6))
    plt.plot(arrays["t"], error_norm, marker="o")
    plt.xlabel("Time (s)")
    ylabel = r"$\|\phi(x,y,t_{\text{final}}) - \phi(x,y,0)\|_{" + norm_label + "}$"
    plt.ylabel(ylabel)
    plt.title(r"Error Over Time")
    plt.grid()
    plt.savefig(FIG_DIR / "phi_error_over_time.png", dpi=300)
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
    "phi_error_norm_avg": float(np.mean(error_norm)) if error_norm is not None else None,
}
(OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


print("[OK] Postprocess complete.")
print(f"  - Domain: nx={metrics['nx']}, ny={metrics['ny']}, nt_phi={metrics['nt']}")
print(f"  - x range: [{metrics['x_min']}, {metrics['x_max']}], y range: [{metrics['y_min']}, {metrics['y_max']}], t range: [{metrics['t_min']}, {metrics['t_max']}]")
print(f"  - Arrays NPZ: {OUT_DIR/'elmfire_arrays.npz'}")
print(f"  - Figures: {FIG_DIR}")
print(f"  - Report snippets: {REP_DIR/'figures.tex'}, {REP_DIR/'metrics.tex'}")
print(f"  - Metrics JSON: {OUT_DIR/'metrics.json'}")
