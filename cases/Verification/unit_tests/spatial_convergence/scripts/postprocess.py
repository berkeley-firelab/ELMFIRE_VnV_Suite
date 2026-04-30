#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from glob import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


CASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = CASE_DIR / "data"
FIG_DIR = CASE_DIR / "figures"
REP_DIR = CASE_DIR / "report"
OUT_DIR = CASE_DIR / "outputs"

FIG_DIR.mkdir(parents=True, exist_ok=True)
REP_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE_RESOLUTION = 1024
ANALYTICAL_REFERENCE_RESOLUTION = 4096  # Finer grid for analytical solution evaluation
DEFAULT_ROS = 0.0116332
DEFAULT_R0 = 5.0
TIMESTEP = -1


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


def get_float(config: dict[str, str], key: str, default: float | None = None) -> float:
    value = config.get(key)
    if value is None:
        if default is None:
            raise KeyError(f"Missing required key in elmfire.data: {key}")
        return float(default)
    return float(value)


def read_tif_as_array(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.asarray(img)


def extract_time_seconds(path: Path) -> float:
    m = re.search(r"_(\d+)\.tif$", path.name)
    if not m:
        raise ValueError(f"Could not infer time from filename: {path.name}")
    return float(int(m.group(1)))


def resolution_dirs() -> list[Path]:
    dirs: list[Path] = []
    for candidate in sorted(DATA_DIR.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 10**9):
        if not candidate.is_dir() or not candidate.name.isdigit():
            continue
        if not (candidate / "inputs" / "elmfire.data").exists():
            continue
        if not (candidate / "outputs").exists():
            continue
        dirs.append(candidate)
    return dirs


def load_time_series(output_dir: Path, prefix: str) -> tuple[np.ndarray, np.ndarray]:
    files = sorted(Path(p) for p in glob(str(output_dir / f"{prefix}_*.tif")))
    if not files:
        return np.array([], dtype=float), np.empty((0, 0, 0), dtype=np.float32)

    times = np.array([extract_time_seconds(p) for p in files], dtype=float)
    arrays = [read_tif_as_array(p).astype(np.float32, copy=False) for p in files]
    return times, np.stack(arrays, axis=0)


def select_timestep(times: np.ndarray, series: np.ndarray, timestep: int) -> tuple[float, np.ndarray]:
    if series.size == 0 or times.size == 0:
        raise FileNotFoundError("No time series data available")
    if series.shape[0] != times.shape[0]:
        raise ValueError(
            f"Time axis mismatch: {times.shape[0]} timestamps for {series.shape[0]} frames"
        )
    if not -series.shape[0] <= timestep < series.shape[0]:
        raise IndexError(
            f"TIMESTEP={timestep} is out of range for series with {series.shape[0]} frames"
        )
    return float(times[timestep]), series[timestep]


def build_domain_vectors(config: dict[str, str], nx: int, ny: int) -> tuple[np.ndarray, np.ndarray]:
    cell_size = get_float(config, "COMPUTATIONAL_DOMAIN_CELLSIZE")
    xllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
    yllcorner = get_float(config, "COMPUTATIONAL_DOMAIN_YLLCORNER")
    x = xllcorner + (np.arange(nx, dtype=float) + 0.5) * cell_size
    y = yllcorner + (np.arange(ny, dtype=float) + 0.5) * cell_size
    return x, y


def analytical_solution(
    x: np.ndarray,
    y: np.ndarray,
    t: float,
    *,
    ros: float = DEFAULT_ROS,
    R0: float = DEFAULT_R0,
) -> np.ndarray:
    x_grid, y_grid = np.meshgrid(x, y)
    radius = np.sqrt(x_grid**2 + y_grid**2)
    target_radius = R0 + ros * float(t)
    return np.where(radius <= target_radius, -1.0, 1.0).astype(np.float32)


def infer_initial_radius(phi0: np.ndarray, x: np.ndarray, y: np.ndarray) -> float:
    mask = np.asarray(phi0) < 0
    if not np.any(mask):
        return 1.0
    x_grid, y_grid = np.meshgrid(x, y)
    radius = np.sqrt(x_grid**2 + y_grid**2)
    return float(np.max(radius[mask]))


def plot_field(
    x: np.ndarray,
    y: np.ndarray,
    field: np.ndarray,
    title: str,
    out_path: Path,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
    cmap: str = "bwr",
) -> None:
    arr = np.asarray(field)
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
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def save_convergence_plot(results: list[dict[str, object]], l2_curve: bool = True, linf_curve: bool = False) -> None:
    dx = np.array([float(r["dx"]) for r in results], dtype=float)
    linf = np.array([float(r["linf_rel"]) for r in results], dtype=float)
    l2 = np.array([float(r["l2_rel"]) for r in results], dtype=float)
    resolutions = np.array([int(r["resolution"]) for r in results], dtype=int)

    # order = np.argsort(dx)
    # dx = dx[order]
    # linf = linf[order]
    # resolutions = resolutions[order]

    order2_ref = l2[0] * (dx / dx[0]) ** 2

    plt.figure(figsize=(8, 6))
    plt.xscale("log", base=2)
    plt.yscale("log")
    if l2_curve:
        plt.plot(dx, l2, marker="o", label=r"$L_2$")
    if linf_curve:
        plt.plot(dx, linf, marker="s", label=r"$L_\infty$")
    plt.plot(dx, order2_ref, linestyle="--", color="black", label=r"$O(\Delta x^2)$ reference")
    # for x_val, y_val, res in zip(dx, linf, resolutions, strict=False):
    #     plt.annotate(f"{res}", (x_val, y_val), textcoords="offset points", xytext=(5, 5), fontsize=8)
    plt.xlabel(r"$\Delta x = \Delta y$")
    plt.ylabel("Error")
    plt.title("Spatial convergence against analytical solution")
    plt.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "phi_convergence_error.png", dpi=300)
    plt.close()


def main() -> None:
    res_dirs = resolution_dirs()
    if not res_dirs:
        raise FileNotFoundError(f"No resolution directories found under {DATA_DIR}")

    reference_dir = next((d for d in res_dirs if d.name == str(REFERENCE_RESOLUTION)), res_dirs[0])
    ref_config = parse_elmfire_data_config(reference_dir / "inputs" / "elmfire.data")
    ref_output_dir = reference_dir / "outputs"

    ref_times, ref_phi_series = load_time_series(ref_output_dir, "phi")
    if ref_phi_series.size == 0:
        raise FileNotFoundError(f"No phi outputs found in {ref_output_dir}")

    ref_phi0 = read_tif_as_array(reference_dir / "inputs" / "phi.tif").astype(np.float32, copy=False)
    ref_ny, ref_nx = int(ref_phi_series.shape[-2]), int(ref_phi_series.shape[-1])
    ref_x, ref_y = build_domain_vectors(ref_config, nx=ref_nx, ny=ref_ny)

    t_reference, ref_phi_timestep = select_timestep(ref_times, ref_phi_series, TIMESTEP)
    
    # Build analytical reference on finer grid (independent of ELMFIRE resolutions)
    analytical_nx, analytical_ny = ANALYTICAL_REFERENCE_RESOLUTION, ANALYTICAL_REFERENCE_RESOLUTION
    
    # Compute domain bounds and cell size for analytical grid
    xllcorner = get_float(ref_config, "COMPUTATIONAL_DOMAIN_XLLCORNER")
    yllcorner = get_float(ref_config, "COMPUTATIONAL_DOMAIN_YLLCORNER")
    domain_size = -2.0 * xllcorner  # Infer domain size from xllcorner (assuming symmetric domain)
    analytical_cell_size = domain_size / analytical_nx
    
    # Build analytical coordinate vectors at finer resolution
    analytical_x = xllcorner + (np.arange(analytical_nx, dtype=float) + 0.5) * analytical_cell_size
    analytical_y = yllcorner + (np.arange(analytical_ny, dtype=float) + 0.5) * analytical_cell_size
    
    phi_analytical_ref = analytical_solution(analytical_x, analytical_y, t_reference, ros=DEFAULT_ROS, R0=DEFAULT_R0)
    
    plot_field(
        analytical_x,
        analytical_y,
        phi_analytical_ref,
        rf"Analytical $\phi$ on {ANALYTICAL_REFERENCE_RESOLUTION}$\times${ANALYTICAL_REFERENCE_RESOLUTION} grid",
        FIG_DIR / "phi_analytical_reference.png",
        vmin=-1.0,
        vmax=1.0,
    )

    results: list[dict[str, object]] = []

    for res_dir in res_dirs:
        config = parse_elmfire_data_config(res_dir / "inputs" / "elmfire.data")
        output_dir = res_dir / "outputs"
        times, phi_series = load_time_series(output_dir, "phi")
        if phi_series.size == 0:
            continue

        latest_time, phi_final = select_timestep(times, phi_series, TIMESTEP)
        phi_final = phi_final.astype(np.float32, copy=False)
        ny, nx = phi_final.shape
        x, y = build_domain_vectors(config, nx=nx, ny=ny)
        dx = get_float(config, "COMPUTATIONAL_DOMAIN_CELLSIZE")

        # Stride from finer analytical reference (4096x4096) to current resolution
        # stride_x = max(1, analytical_nx // nx)
        # stride_y = max(1, analytical_ny // ny)
        # phi_analytical = phi_analytical_ref[::stride_y, ::stride_x]
        # if phi_analytical.shape != phi_final.shape:
        #     phi_analytical = phi_analytical_ref[: ny * stride_y : stride_y, : nx * stride_x : stride_x]
        # if phi_analytical.shape != phi_final.shape:
        #     raise ValueError(
        #         f"Analytical grid shape {phi_analytical.shape} does not match output shape {phi_final.shape} for {res_dir.name}"
        #     )
        phi_analytical = analytical_solution(x, y, latest_time, ros=DEFAULT_ROS, R0=DEFAULT_R0)

        diff = phi_final - phi_analytical
        rmse = float(np.sqrt(np.mean(diff**2)))
        linf = float(np.max(np.abs(diff)))
        l2 = float(np.linalg.norm(diff.flatten(), ord=2))
        error = np.abs(diff)
        linf_rel = linf / np.max(np.abs(phi_analytical.flatten()))
        l2_rel = l2 / np.linalg.norm(phi_analytical.flatten(), ord=2)
        
        print(f"[{res_dir.name}x{res_dir.name}], dx: {dx:.6f}, dy: {dx:.6f}, Time: {latest_time:.2f}s, RMSE: {rmse:.6f}, L_inf: {linf:.6f}, L2: {l2:.6f}, L_inf_rel: {linf_rel:.6f}, L2_rel: {l2_rel:.6f}")

        plot_field(
            x,
            y,
            phi_final,
            f"Final $\\phi$, {res_dir.name}x{res_dir.name}",
            FIG_DIR / f"phi_final_{res_dir.name}.png",
            vmin=-1.0,
            vmax=1.0,
        )
        plot_field(
            x,
            y,
            error,
            f"Error $\\phi - \\phi_{{analytical}}$, {res_dir.name}x{res_dir.name}",
            FIG_DIR / f"phi_error_{res_dir.name}.png",
            cmap="coolwarm",
        )

        results.append(
            {
                "resolution": int(res_dir.name),
                "dx": dx,
                "dy": dx,
                "time": latest_time,
                "rmse": rmse,
                "linf": linf,
                "l2": l2,
                "linf_rel": float(linf_rel),
                "l2_rel": float(l2_rel),
                "phi_min": float(np.min(phi_final)),
                "phi_max": float(np.max(phi_final)),
            }
        )

    if not results:
        raise FileNotFoundError("No usable resolution outputs were found")

    save_convergence_plot(results)

    metrics = {
        "reference_resolution": REFERENCE_RESOLUTION,
        "analytical_reference_resolution": ANALYTICAL_REFERENCE_RESOLUTION,
        "reference_time": t_reference,
        "reference_timestep": TIMESTEP,
        "analytical_ros": DEFAULT_ROS,
        "analytical_initial_radius": DEFAULT_R0,
        "resolutions": results,
        "error_summary": {
            "rmse_min": float(np.min([r["rmse"] for r in results])),
            "rmse_max": float(np.max([r["rmse"] for r in results])),
            "linf_min": float(np.min([r["linf"] for r in results])),
            "linf_max": float(np.max([r["linf"] for r in results])),
            "l2_min": float(np.min([r["l2"] for r in results])),
            "l2_max": float(np.max([r["l2"] for r in results])),
        },
    }
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    np.savez_compressed(
        OUT_DIR / "convergence_results.npz",
        resolution=np.array([r["resolution"] for r in results], dtype=float),
        dx=np.array([r["dx"] for r in results], dtype=float),
        dy=np.array([r["dy"] for r in results], dtype=float),
        time=np.array([r["time"] for r in results], dtype=float),
        rmse=np.array([r["rmse"] for r in results], dtype=float),
        linf=np.array([r["linf"] for r in results], dtype=float),
        l2=np.array([r["l2"] for r in results], dtype=float),
        linf_rel=np.array([r["linf_rel"] for r in results], dtype=float),
        l2_rel=np.array([r["l2_rel"] for r in results], dtype=float),
    )

    print("[OK] Postprocess complete.")
    print(f"  - ELMFIRE reference grid: {REFERENCE_RESOLUTION}x{REFERENCE_RESOLUTION}")
    print(f"  - Analytical reference grid: {ANALYTICAL_REFERENCE_RESOLUTION}x{ANALYTICAL_REFERENCE_RESOLUTION}")
    print(f"  - Reference time: {t_reference}")
    print(f"  - Reference timestep: {TIMESTEP}")
    print(f"  - Figures: {FIG_DIR}")
    print(f"  - Metrics JSON: {OUT_DIR / 'metrics.json'}")


if __name__ == "__main__":
    main()
