#!/usr/bin/env python3
"""Create or refresh one validation case per GOFER fire in this directory.

This is a construction aid, not a runtime dependency: every case it writes is
self-contained (own scripts, report sources, metadata) and runs from its own
root.  Large inputs and simulation results are not copied; each case records
where they are provided in data/data_paths.json.

Usage:
    python tools/build_cases.py [--fires kincade_2019 ...] [--no-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GOFER_DIR = Path(__file__).resolve().parents[1]          # cases/Validation/GOFER
SUITE_DIR = GOFER_DIR.parents[2]                          # ELMFIRE_VnV_Suite
DATA_ROOT = SUITE_DIR.parent                              # fire_data/GOFER
VALIDATION_DIR = DATA_ROOT / "ELMFIRE_GOFER_validation"
TOA_DIR = DATA_ROOT / "toa"
GOFER_SUMMARY = DATA_ROOT / "GOFER_Combined" / "GOFERC_summary.csv"
FIRE_DATA = DATA_ROOT / "fireData.csv"
EXPLORATORY = Path.home() / "Desktop" / "GOFER_val_exploratory"
CASE_FILES = Path(__file__).resolve().parent / "case_files"
ELMFIRE_REVISION = "5ea7460d514b24bf9a1cdda571c16f4f03de603f"
RETRIEVAL_DATE = "2026-10-20"

INPUT_FILES = {
    "landscape.tif": "terrain, surface-fuel and canopy layers (8 bands, 30 m)",
    "adj.tif": "spread-rate adjustment factor", "phi.tif": "initial level set",
    "ws.tif": "hourly 20-ft wind speed", "wd.tif": "hourly wind direction",
    "m1.tif": "hourly 1-h dead-fuel moisture", "m10.tif": "hourly 10-h dead-fuel moisture",
    "m100.tif": "hourly 100-h dead-fuel moisture", "lh.tif": "hourly live herbaceous moisture",
    "lw.tif": "hourly live woody moisture", "ignition_mask.tif": "300-m disk at the first ignition",
    "ignitions.csv": "ignition points used", "metadata.out": "retrieval domain record",
    "fuel_models.csv": "fuel-model parameters", "elmfire.data": "current configuration",
}

CONFIGURATIONS = {
    "baseline": {
        "description": (
            "This result used a single point ignition at the first GOFER ignition point, "
            "firebrand spotting disabled and the ELMFIRE default crown-fire treatment, with the "
            "same inputs, stop time and numerical controls as the current configuration."),
    },
    "reference_spotting": {
        "description": (
            "This result used every GOFER ignition point at its observed time, the ELMFIRE "
            "default crown-fire treatment, and firebrand spotting with the settings of the "
            "landscape-scale reconstructions of the Camp, Thomas and Tubbs fires: firebrands "
            "generated in proportion to fire power from both surface and crown fire, an "
            "empirical transport-distance model, Eulerian accumulation and a physical ignition "
            "model.  Inputs, stop time and numerical controls match the current configuration."),
    },
    "current": {
        "description": (
            "This result used the current case configuration described in the model "
            "configuration section."),
    },
}

NOTE_PRE_FILL = ("This result was produced before offshore cells outside LANDFIRE coverage were "
                 "filled with open-water values; those cells then held a fill value read as data. "
                 "They lie offshore beyond a band of open water that the simulated fire did not "
                 "reach, but the result is not from the corrected inputs.")
NOTE_RECONSTRUCTED = ("The configuration file was not retained with this result; the "
                      "configuration is documented from the case owner's preparation record.")
NOTE_RETAINED = "The configuration file used was retained with this result."

# Simulation results available so far, per fire: (run_id, label, configuration, dir, notes)
SIMULATIONS = {
    "Kincade_2019": [("reference_spotting", "Reference-case spotting configuration", "reference_spotting",
                      EXPLORATORY / "Kincade_2019" / "outputs", [NOTE_RECONSTRUCTED])],
    "CZU_Lightning_Complex_2020": [
        ("baseline", "Single-ignition baseline without spotting", "baseline",
         EXPLORATORY / "CZU_Lightning_Complex_2020" / "outputs_baseline", [NOTE_RECONSTRUCTED, NOTE_PRE_FILL]),
        ("reference_spotting", "Reference-case spotting configuration", "reference_spotting",
         EXPLORATORY / "CZU_Lightning_Complex_2020" / "outputs", [NOTE_RETAINED, NOTE_PRE_FILL])],
    "Glass_2020": [("baseline", "Single-ignition baseline without spotting", "baseline",
                    EXPLORATORY / "Glass_2020" / "outputs", [NOTE_RETAINED])],
    "Caldor_2021": [("baseline", "Single-ignition baseline without spotting", "baseline",
                     EXPLORATORY / "Caldor_2021" / "outputs", [NOTE_RETAINED])],
}
CALIBRATION_FIRES = {"Kincade_2019", "CZU_Lightning_Complex_2020"}
OFFSHORE_FILLED = {"CZU_Lightning_Complex_2020": 283496, "Dolan_2020": 561820,
                   "LNU_Lightning_Complex_2020": 272932}
CASE_NOTES = {
    "Zogg_2020": (
        "LANDFIRE maps between 61 and 75\\% of the area within 2~km of the ignition point as "
        "timber-litter fuel models at about 25\\% canopy cover, whereas the observed fire spread "
        "through grass and oak woodland.  Slow litter spread under the analyzed winds can stall "
        "a simulation started at this point, independently of the weather or spotting settings."),
    "CZU_Lightning_Complex_2020": (
        "The fire burned near the coast, where the marine layer and fog influenced late growth; "
        "the 2.5-km weather analysis may not resolve these effects."),
}


def rel(path: Path, start: Path) -> str:
    return os.path.relpath(path, start)


def tex(text: str) -> str:
    return text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def display_name(fname: str) -> str:
    """Fire name as used in prose: 'Kincade' -> 'Kincade Fire'."""
    if fname.endswith("Complex"):
        return fname
    return fname + (" Fires" if " and " in fname else " Fire")


def utm_name(crs: str) -> str:
    zone = int(crs.split(":")[1]) - 32600
    return f"UTM zone {zone}N (EPSG:{crs.split(':')[1]})"


def namelist_value(text: str, key: str) -> str:
    return re.search(rf"(?m)^{re.escape(key)}\s*=\s*(\S+)", text).group(1)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def gofer_area_series(row: dict, summary: list[dict]) -> dict:
    from datetime import datetime
    start = datetime.strptime(row["t_start_utc"], "%Y-%m-%dT%H:%M:%SZ")
    hours, area = [], []
    for s in summary:
        if s["fname"] == row["fname"] and s["fyear"] == row["fyear"]:
            t = datetime.strptime(s["tUTC"], "%Y-%m-%d %H:%M:%S")
            hours.append((t - start).total_seconds() / 3600.0)
            area.append(float(s["farea"]))
    return {"hours": hours, "area_km2": area}


def human_time(iso: str) -> str:
    from datetime import datetime
    t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    return f"{t.day} {t:%B %Y} at {t:%H:%M}~UTC"


def write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def build_case(row: dict, log: dict, summary: list[dict], official: dict) -> Path:
    fire_id = row["fire_id"]
    case_id = fire_id.lower()
    name = display_name(row["fname"])
    case = GOFER_DIR / case_id
    inputs = VALIDATION_DIR / fire_id / "inputs"
    namelist = (inputs / "elmfire.data").read_text(encoding="utf-8")
    ignitions = [r for r in read_csv(inputs / "ignitions.csv") if r["used"] == "True"]
    crs = log["srs"]
    from datetime import datetime
    t_start = datetime.strptime(row["t_start_utc"], "%Y-%m-%dT%H:%M:%SZ")
    t_wx = datetime.strptime(log["wx_start_utc"], "%Y-%m-%dT%H:%M:%SZ")
    offset_h = (t_wx - t_start).total_seconds() / 3600.0
    tstop_h = float(namelist_value(namelist, "SIMULATION_TSTOP")) / 3600.0
    bands = int(namelist_value(namelist, "NUM_METEOROLOGY_TIMES"))
    sims = SIMULATIONS.get(fire_id, [])

    # Case-specific copies of the analysis scripts and report sources
    for sub in ("scripts", "report"):
        (case / sub).mkdir(parents=True, exist_ok=True)
        for path in (CASE_FILES / sub).iterdir():
            shutil.copy(path, case / sub / path.name)
    shutil.copy(SUITE_DIR / "tools" / "report_language.py", case / "scripts" / "report_language.py")

    # Current configuration, with case-specific output and scratch locations
    config = re.sub(r"(?m)^OUTPUTS_DIRECTORY\s*=.*$", "OUTPUTS_DIRECTORY    = './simulation'", namelist)
    config = re.sub(r"(?m)^SCRATCH\s*=.*$", "SCRATCH                        = './logs/scratch'", config)
    write(case / "elmfire.data.in", config)

    source = {
        "schema_version": 1, "case_id": case_id, "fire_id": fire_id,
        "fire_name": name, "fire_year": int(row["fyear"]),
        "event_start_utc": row["t_start_utc"], "event_end_utc": row["t_end_utc"],
        "official_size_ac": float(official.get(fire_id, "nan")),
        "model_domain": {"crs": crs, "crs_name": utm_name(crs), "cell_size_m": 30.0,
                         "extent": log["domain_te"], "margin_km": 10.0},
        "model_inputs": {
            "provider": "CloudFire fuel, weather and ignition service (worldgen.cloudfire.io)",
            "retrieval_date": RETRIEVAL_DATE,
            "fuel_source": "LANDFIRE", "fuel_version": log["fuel_version"],
            "weather_source": "Real-Time Mesoscale Analysis (RTMA), as stated by the case owner",
            "offshore_cells_filled": OFFSHORE_FILLED.get(fire_id, 0),
            "files": [{"name": n, "role": r, "size": (inputs / n).stat().st_size}
                      for n, r in INPUT_FILES.items() if (inputs / n).is_file()],
        },
        "weather": {"first_time_utc": log["wx_start_utc"], "band_count": bands,
                    "interval_s": 3600, "offset_from_event_start_h": offset_h},
        "simulation": {"planned_stop_h": tstop_h, "elmfire_revision": ELMFIRE_REVISION},
        "ignitions": [{"t_utc": r["t_utc"], "lon": float(r["lon"]), "lat": float(r["lat"]),
                       "x": float(r["x"]), "y": float(r["y"]), "t_ign_s": float(r["t_ign_s"]),
                       "moved_m": float(r["moved_m"])} for r in ignitions],
        "observation": {
            "product": "GOFER-Combined hourly perimeters (Liu et al., 2024; doi:10.5281/zenodo.8327264)",
            "derivation": "cumulative hourly perimeters rasterized to first arrival hour since the GOES ignition hour",
            "hourly_perimeters": int(row["n_timesteps"]),
            "gofer_final_area_km2": float(row["final_area_km2"]),
            "area_series": gofer_area_series(row, summary),
        },
        "configurations": CONFIGURATIONS,
    }
    write(case / "data" / "source_manifest.json", json.dumps(source, indent=2) + "\n")
    paths = {
        "inputs": rel(inputs, case),
        "observation": rel(TOA_DIR / f"{fire_id}_toa.tif", case),
        "simulations": [{"run_id": r, "label": lab, "configuration": c,
                         "results_dir": rel(d, case), "notes": notes}
                        for r, lab, c, d, notes in sims],
    }
    write(case / "data" / "data_paths.json", json.dumps(paths, indent=2) + "\n")

    n_ign = len(ignitions)
    moved = [r for r in ignitions if float(r["moved_m"]) > 0]
    move_note = (f"{len(moved)} of {n_ign} points moved at most "
                 f"{max(float(r['moved_m']) for r in moved):.0f}~m off non-burnable cells"
                 if moved else "no point required moving")
    ign_text = ("a single point ignition" if n_ign == 1 else
                f"{n_ign} point ignitions, each applied at its observed GOFER time")
    configuration_text = (
        f"The domain is the 30-m landscape grid in {utm_name(crs)}.  The simulation starts at "
        f"the first GOFER ignition point and runs {tstop_h:.0f}~h, to the last GOFER perimeter, with "
        f"{ign_text}.  Weather and fuel moisture are read hourly and interpolated in time.  "
        "Surface spread follows the Rothermel model with the Scott and Burgan fuel models.  "
        "Crown fire uses the ELMFIRE default treatment: initiation when surface fireline "
        "intensity exceeds the critical intensity of Van Wagner \\cite{vanwagner1977}, and "
        "active-crown spread rate from Cruz et al. \\cite{cruz2005}, capped at 250~ft~min$^{-1}$, "
        "with a constant foliar moisture of 90\\%.  Firebrand spotting is enabled with every "
        "other spotting setting at its ELMFIRE default, so firebrands are generated only by "
        "crown-fire cells.  The level-set equation is advanced with an adaptive timestep "
        "targeting a Courant--Friedrichs--Lewy (CFL) number of 0.2, starting at 1~s and "
        "limited to 600~s.  The run is a single deterministic member with a fixed random seed; "
        "arrival time, spread rate, fireline intensity and fire-size statistics are recorded "
        "at the stop time.")
    calibration = ("The firebrand-spotting configuration was changed after the case owner "
                   "inspected comparisons of this fire with GOFER, so results for this fire "
                   "are not independent of that choice." if fire_id in CALIBRATION_FIRES else
                   "No model parameter was tuned against the GOFER observation of this fire; the "
                   "spotting configuration was revised after comparisons for the Kincade and CZU "
                   "Lightning Complex fires.")
    offshore = (f"Offshore, {OFFSHORE_FILLED[fire_id]:,} cells outside LANDFIRE coverage were "
                "assigned LANDFIRE open-water values; they are non-burnable."
                if fire_id in OFFSHORE_FILLED else "")
    revision = (f"The simulation results reported here were produced with ELMFIRE~1.1 at source "
                f"revision \\texttt{{{ELMFIRE_REVISION[:12]}}}, as recorded for the CZU Lightning "
                "Complex runs and assumed for the other results produced on the same system."
                if sims else
                f"The case configuration targets ELMFIRE~1.1 at source revision "
                f"\\texttt{{{ELMFIRE_REVISION[:12]}}}.")
    official_txt = (f" and an official size of {source['official_size_ac']:,.0f}~ac"
                    if source["official_size_ac"] == source["official_size_ac"] else "")
    summary_txt = (f"GOFER records the {tex(name)} from {human_time(row['t_start_utc'])} to "
                   f"{human_time(row['t_end_utc'])} with {row['n_timesteps']} hourly perimeters, a final "
                   f"perimeter area of {float(row['final_area_km2']):.0f}~km$^2${official_txt}, "
                   f"and {row['n_ignitions']} ignition point(s).")
    metadata = "\n".join([
        rf"\newcommand{{\CaseID}}{{{tex(case_id)}}}",
        rf"\newcommand{{\CaseTitle}}{{{row['fyear']} {tex(name)} Reconstruction against GOFER Hourly Perimeters}}",
        rf"\newcommand{{\FireName}}{{{tex(name)}}}",
        rf"\newcommand{{\FireYear}}{{{row['fyear']}}}",
        rf"\newcommand{{\EventStart}}{{{human_time(row['t_start_utc'])}}}",
        rf"\newcommand{{\EventEnd}}{{{human_time(row['t_end_utc'])}}}",
        rf"\newcommand{{\DurationHours}}{{{float(row['duration_h']):.0f}}}",
        rf"\newcommand{{\CRSName}}{{{utm_name(crs)}}}",
        rf"\newcommand{{\FuelVersionText}}{{LANDFIRE release {tex(log['fuel_version'])}}}",
        rf"\newcommand{{\FireSummary}}{{{summary_txt}}}",
        rf"\newcommand{{\IgnitionMoveNote}}{{{move_note}}}",
        rf"\newcommand{{\OffshoreNote}}{{{offshore}}}",
        rf"\newcommand{{\CalibrationNote}}{{{calibration}}}",
        rf"\newcommand{{\ConfigurationText}}{{{configuration_text}}}",
        rf"\newcommand{{\WeatherOffsetText}}{{{abs(offset_h):.0f}~h {'after' if offset_h >= 0 else 'before'} "
        r"the GOES ignition hour; all results are reported in hours since the GOES ignition hour.}",
        rf"\newcommand{{\RevisionText}}{{{revision}}}",
        rf"\newcommand{{\CaseInterpretation}}{{{CASE_NOTES.get(fire_id, '')}}}",
        rf"\newcommand{{\ElmfireRevision}}{{{ELMFIRE_REVISION[:12]}}}",
        "",
    ])
    write(case / "report" / "case_metadata.tex", metadata)

    figures = ["observation_summary.pdf", "input_overview.pdf", "input_distributions.pdf",
               "weather_time_series.pdf", "weather_summary.pdf"]
    if sims:
        figures.append("burned_area_growth.pdf")
        for r, *_ in sims:
            figures += [f"comparison_{r}.pdf", f"arrival_{r}.pdf", f"fields_{r}.pdf"]
    yaml_figures = "\n".join(f'    - "figures/{f}"' for f in figures)
    write(case / "case.yaml", f'''case_id: "{case_id}"
case_title: "{row['fyear']} {name} reconstruction against GOFER hourly perimeters"
case_type: "validation"
category: "GOFER"

elmfire:
  bin: "${{ELMFIRE_BIN:-elmfire}}"
  config: "elmfire.data.in"
  mpi_ranks: 1

validation:
  observation: "GOFER-Combined hourly perimeters (arrival-time raster)"
  event_start_utc: "{row['t_start_utc']}"
  event_end_utc: "{row['t_end_utc']}"
  comparison_times_h: [24, 48, 72, "final GOFER arrival"]

postprocess:
  metrics: "outputs/metrics.json"
  figures:
{yaml_figures}

namelist_contract:
  schema_version: 1
  report: "report/case_body.tex"
  files:
    - path: "elmfire.data.in"
      invariants:
        TIME_CONTROL.SIMULATION_TSTOP: {float(namelist_value(namelist, "SIMULATION_TSTOP"))}
        TIME_CONTROL.TARGET_CFL: 0.2
        MONTE_CARLO.NUM_METEOROLOGY_TIMES: {bands}
        SIMULATOR.NUM_IGNITIONS: {n_ign}
        SIMULATOR.CROWN_FIRE_MODEL: 1
        SPOTTING.ENABLE_SPOTTING: true
        OUTPUTS.DUMP_TIME_OF_ARRIVAL: true
''')
    write(case / "run_case.sh", f'''#!/usr/bin/env bash
set -euo pipefail

CASE_DIR=$(cd -- "$(dirname -- "${{BASH_SOURCE[0]}}")" && pwd)
ELMFIRE_BIN=${{ELMFIRE_BIN:-elmfire}}
PYTHON_BIN=${{PYTHON_BIN:-python3}}
export PYTHONNOUSERSITE=1

mkdir -p "$CASE_DIR/outputs" "$CASE_DIR/figures" "$CASE_DIR/logs/scratch" "$CASE_DIR/simulation"
"$PYTHON_BIN" "$CASE_DIR/scripts/preprocess.py"

# The configuration reads ./inputs; point it at the provided input directory.
INPUTS=${{GOFER_INPUTS_DIR:-$("$PYTHON_BIN" -c 'import json,os,sys; d=sys.argv[1]; print(os.path.normpath(os.path.join(d, json.load(open(os.path.join(d,"data","data_paths.json")))["inputs"])))' "$CASE_DIR")}}
ln -sfn "$INPUTS" "$CASE_DIR/inputs"

echo "[INFO] Running {name} ({row['fyear']}) with one ELMFIRE process."
(cd "$CASE_DIR" && GFORTRAN_UNBUFFERED_PRECONNECTED=y "$ELMFIRE_BIN" elmfire.data.in) \\
  >"$CASE_DIR/logs/elmfire.stdout" 2>"$CASE_DIR/logs/elmfire.stderr"

"$PYTHON_BIN" "$CASE_DIR/scripts/postprocess.py"
bash "$CASE_DIR/compile_case.sh"
echo "[OK] {case_id} validation complete."
''', executable=True)
    write(case / "compile_case.sh", '''#!/usr/bin/env bash
set -euo pipefail

CASE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
"$PYTHON_BIN" "$CASE_DIR/scripts/metrics_to_macro.py"
(cd "$CASE_DIR/report" && latexmk -lualatex -interaction=nonstopmode -halt-on-error case_report.tex)
echo "[OK] Built $CASE_DIR/report/case_report.pdf"
''', executable=True)
    return case


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fires", nargs="*", help="case ids (default: fires with simulation results)")
    parser.add_argument("--all", action="store_true", help="build every fire, including those without results")
    parser.add_argument("--no-run", action="store_true", help="only write case files")
    args = parser.parse_args()
    fires = read_csv(VALIDATION_DIR / "fires.csv")
    logs = {r["fire_id"]: r for r in read_csv(VALIDATION_DIR / "inputs_log.csv")}
    summary = read_csv(GOFER_SUMMARY)
    official = {f"{r['fname'].replace(' ', '_').replace('-', '_')}_{r['fyear']}": r["acres_official"]
                for r in read_csv(FIRE_DATA)}
    for row in fires:
        if args.fires and row["fire_id"].lower() not in args.fires:
            continue
        if not args.fires and not args.all and row["fire_id"] not in SIMULATIONS:
            continue
        case = build_case(row, logs[row["fire_id"]], summary, official)
        if args.no_run:
            continue
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for script in ("preprocess.py", "postprocess.py"):
            subprocess.run([sys.executable, str(case / "scripts" / script)], check=True, env=env)
        subprocess.run(["bash", str(case / "compile_case.sh")], check=True,
                       env={**env, "PYTHON_BIN": sys.executable}, stdout=subprocess.DEVNULL)
        print(f"[OK] {case.name}: report built")


if __name__ == "__main__":
    main()
