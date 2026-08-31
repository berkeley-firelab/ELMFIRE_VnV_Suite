#!/usr/bin/env python3
"""
Stack transient heat-flux rasters and plot maps/time series.

Requirements:
  pip install rasterio matplotlib numpy
"""

import glob
import re
from typing import List
import numpy as np
import rasterio

FNAME_TIME_RE = re.compile(r"_(\d{7})\.tif$", re.IGNORECASE)

def find_rasters(pattern: str) -> List[str]:
    files = glob.glob(f"{pattern}")

    if not files:
        raise FileNotFoundError("No files matched the pattern")

    # sort by the numeric time suffix
    def time_key(p: str) -> int:
        m = FNAME_TIME_RE.search(p)
        if not m:
            raise ValueError(f"Filename does not end with _XXXXXXX.tif: {p}")
        return int(m.group(1))
    files.sort(key=time_key)
    return files

def load_stack(pattern: str):
    files = find_rasters(pattern)
    with rasterio.open(files[0]) as src0:
        height, width = src0.height, src0.width
        transform = src0.transform
        crs = src0.crs
        nodata = src0.nodata
        bounds = src0.bounds

    t_list = []
    arr_stack = np.ma.empty((len(files), height, width), dtype=np.float32)

    for i, f in enumerate(files):
        with rasterio.open(f) as src:
            data = src.read(1).astype(np.float32)
            if nodata is not None:
                data = np.ma.masked_equal(data, nodata)
            else:
                data = np.ma.masked_invalid(data)
        t = int(FNAME_TIME_RE.search(f).group(1))  # seconds
        t_list.append(t)
        arr_stack[i] = data

    times = np.array(t_list, dtype=int)
    return arr_stack, times, transform, crs, bounds