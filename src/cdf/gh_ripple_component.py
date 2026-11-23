#! python 3
"""Assignment 2.2 Grasshopper Python 3 Script component.

Paste this file into a Grasshopper Python 3 Script component.

Add input pins with these exact names:
    run, width, height, resolution, n_drops, d_min, wavelength, decay,
    T, min_area, seed, gap, amplitude

For interactive preview, set resolution to 60-100 mm. Use 20 mm for
the final detailed mesh. Set run to False while changing several settings,
then set it to True to generate the geometry once.

Add output pins with these exact names:
    mesh, contour_mesh, drops, contours, contour_labels, surfaces_dark,
    surfaces_mid, surfaces_light, field_hash, report

The three surface outputs are reserved for Milestone 4.
"""

import Rhino.Geometry as rg

from cdf.ripple_core import Params
from cdf.ripple_rhino import create_rhino_ripple_geometry


# Use defaults if an optional Grasshopper input pin is not connected.
defaults = Params()

try:
    run_input = bool(run)
except NameError:
    run_input = True

try:
    width_input = float(width)
except NameError:
    width_input = defaults.width

try:
    height_input = float(height)
except NameError:
    height_input = defaults.height

try:
    resolution_input = float(resolution)
except NameError:
    resolution_input = defaults.resolution

try:
    n_drops_input = int(n_drops)
except NameError:
    n_drops_input = defaults.n_drops

try:
    d_min_input = float(d_min)
except NameError:
    d_min_input = defaults.d_min

try:
    wavelength_input = float(wavelength)
except NameError:
    wavelength_input = defaults.wavelength

try:
    decay_input = float(decay)
except NameError:
    decay_input = defaults.decay

try:
    threshold_input = float(T)
except NameError:
    threshold_input = defaults.threshold

try:
    min_area_input = float(min_area)
except NameError:
    min_area_input = defaults.min_area

try:
    seed_input = int(seed)
except NameError:
    seed_input = defaults.seed

try:
    gap_input = float(gap)
except NameError:
    gap_input = defaults.gap

try:
    amplitude_input = float(amplitude)
except NameError:
    amplitude_input = defaults.amplitude


# Initialise outputs so they remain defined when Run is false.
mesh = rg.Mesh()
contour_mesh = rg.Mesh()
drops = []
contours = []
contour_labels = []
surfaces_dark = []
surfaces_mid = []
surfaces_light = []
field_hash = ""
report = "Set run to True to generate the ripple floor."

if run_input:
    params = Params(
        width=width_input,
        height=height_input,
        resolution=resolution_input,
        n_drops=n_drops_input,
        d_min=d_min_input,
        wavelength=wavelength_input,
        decay=decay_input,
        threshold=threshold_input,
        min_area=min_area_input,
        seed=seed_input,
        gap=gap_input,
        amplitude=amplitude_input,
    )

    result = create_rhino_ripple_geometry(params)

    mesh = result["mesh"]
    contour_mesh = result["contour_mesh"]
    drops = result["drops"]
    contours = result["contours"]
    contour_labels = result["contour_labels"]
    field_hash = result["field"].hash
    report = result["report"]
