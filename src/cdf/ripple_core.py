"""Pure-Python core for the Assignment 2 floor-pattern algorithm."""

from dataclasses import dataclass
from hashlib import sha256
from math import cos, exp, pi, sqrt
import random
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class Params:
    """All user-editable parameters for the rain-wave floor pattern."""

    width: float = 6000.0
    height: float = 4000.0
    tile_columns: int = 10
    tile_rows: int = 10
    resolution: float = 20.0
    n_drops: int = 9
    d_min: float = 1100.0
    wavelength: float = 520.0
    decay: float = 1500.0
    threshold: float = 0.22
    min_area: float = 0.06
    min_width: float = 25.0
    seed: int = 42
    gap: float = 0.0
    amplitude: float = 100.0
    contour_tolerance: float = 0.0000001
    contour_mesh_width: float = 12.0
    contour_mesh_height: float = 3.0
    placement_attempt_limit: int = 5000


@dataclass(frozen=True)
class Drop:
    """One rain drop used as the source of a circular wave."""

    x: float
    y: float
    strength: float
    phase: float


@dataclass(frozen=True)
class RippleField:
    """Grid values and material classes before and after island cleanup."""

    xs: Tuple[float, ...]
    ys: Tuple[float, ...]
    field: Tuple[Tuple[float, ...], ...]
    raw_classes: Tuple[Tuple[int, ...], ...]
    classes: Tuple[Tuple[int, ...], ...]
    drops: Tuple[Drop, ...]
    hash: str


def _clamped_position(value: float, maximum: float) -> float:
    """Keep a sampled grid position inside the rectangular floor."""
    if value < 0.0:
        return 0.0
    if value > maximum:
        return maximum
    return value


def place_drops(params: Params) -> Tuple[Drop, ...]:
    """Place drops sequentially while keeping them at least d_min apart.

    A candidate is rejected if it is too close to any accepted drop.
    The search stops after 5000 consecutive candidate attempts in total.
    If fewer drops are found, the function returns those accepted drops.
    """
    if params.width <= 0.0 or params.height <= 0.0:
        raise ValueError("width and height must be positive.")
    if params.n_drops < 0:
        raise ValueError("n_drops cannot be negative.")
    if params.d_min < 0.0:
        raise ValueError("d_min cannot be negative.")
    if params.placement_attempt_limit < 1:
        raise ValueError("placement_attempt_limit must be at least 1.")

    rng = random.Random(params.seed)
    accepted: List[Drop] = []

    for drop_index in range(params.n_drops):
        candidate_attempts = 0

        while candidate_attempts < params.placement_attempt_limit:
            candidate_attempts += 1

            x = rng.uniform(0.0, params.width)
            y = rng.uniform(0.0, params.height)
            strength = rng.uniform(0.6, 1.0)
            phase = rng.uniform(0.0, 2.0 * pi)

            too_close = False
            for existing_drop in accepted:
                dx = x - existing_drop.x
                dy = y - existing_drop.y
                distance = sqrt(dx * dx + dy * dy)
                if distance < params.d_min:
                    too_close = True
                    break

            if not too_close:
                accepted.append(Drop(x, y, strength, phase))
                break

        if candidate_attempts >= params.placement_attempt_limit:
            break

    return tuple(accepted)


def make_regular_grid(params: Params) -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    """Return regular x and y coordinates inside the rectangular floor."""
    if params.resolution <= 0.0:
        raise ValueError("resolution must be positive.")

    xs_list: List[float] = []
    x = 0.0
    while x < params.width:
        xs_list.append(_clamped_position(x, params.width))
        x += params.resolution
    if not xs_list or xs_list[-1] != params.width:
        xs_list.append(params.width)

    ys_list: List[float] = []
    y = 0.0
    while y < params.height:
        ys_list.append(_clamped_position(y, params.height))
        y += params.resolution
    if not ys_list or ys_list[-1] != params.height:
        ys_list.append(params.height)

    return tuple(xs_list), tuple(ys_list)


def evaluate_drop_wave(drop: Drop, x: float, y: float, params: Params) -> float:
    """Evaluate R2 for one drop at one point."""
    dx = x - drop.x
    dy = y - drop.y
    radius = sqrt(dx * dx + dy * dy)

    cosine_part = cos(2.0 * pi * radius / params.wavelength + drop.phase)
    decay_part = exp(-radius / params.decay)
    return drop.strength * cosine_part * decay_part


def evaluate_field(
    params: Params,
    xs: Sequence[float],
    ys: Sequence[float],
    drops: Sequence[Drop],
) -> Tuple[Tuple[float, ...], ...]:
    """Evaluate R2 for every drop, sum R3, and normalise R3 to [-1, 1]."""
    if params.decay <= 0.0:
        raise ValueError("decay must be positive.")
    if params.wavelength <= 0.0:
        raise ValueError("wavelength must be positive.")

    raw_rows: List[Tuple[float, ...]] = []
    maximum_absolute = 0.0

    for y in ys:
        raw_row: List[float] = []
        for x in xs:
            field_value = 0.0
            for drop in drops:
                field_value += evaluate_drop_wave(drop, x, y, params)
            raw_row.append(field_value)

            if abs(field_value) > maximum_absolute:
                maximum_absolute = abs(field_value)
        raw_rows.append(tuple(raw_row))

    if maximum_absolute == 0.0:
        maximum_absolute = 1.0

    normalised_rows: List[Tuple[float, ...]] = []
    for raw_row in raw_rows:
        normalised_row = tuple(value / maximum_absolute for value in raw_row)
        normalised_rows.append(normalised_row)

    return tuple(normalised_rows)


def classify_field(
    field: Sequence[Sequence[float]],
    threshold: float,
) -> Tuple[Tuple[int, ...], ...]:
    """Apply R4: 2 = light, 0 = dark, 1 = mid."""
    if threshold < 0.0:
        raise ValueError("threshold cannot be negative.")

    class_rows: List[Tuple[int, ...]] = []
    for field_row in field:
        class_row: List[int] = []
        for field_value in field_row:
            if field_value > threshold:
                class_row.append(2)
            elif field_value < -threshold:
                class_row.append(0)
            else:
                class_row.append(1)
        class_rows.append(tuple(class_row))
    return tuple(class_rows)


def field_hash(field: Sequence[Sequence[float]]) -> str:
    """Create a stable SHA-256 hash of rounded field values."""
    digest = sha256()
    for row in field:
        for value in row:
            digest.update(format(round(value, 12), ".12f").encode("ascii"))
            digest.update(b",")
    return digest.hexdigest()


def generate_ripple_field(params: Params) -> RippleField:
    """Generate R1-R5 for one floor and seed."""
    xs, ys = make_regular_grid(params)
    drops = place_drops(params)
    field = evaluate_field(params, xs, ys, drops)
    raw_classes = classify_field(field, params.threshold)
    classes = merge_small_islands(raw_classes, params)
    return RippleField(
        xs=xs,
        ys=ys,
        field=field,
        raw_classes=raw_classes,
        classes=classes,
        drops=drops,
        hash=field_hash(field),
    )


def get_tile_size(params: Params) -> Tuple[float, float]:
    """Return one tile's width and height in millimetres."""
    if params.tile_columns < 1:
        raise ValueError("tile_columns must be at least 1.")
    if params.tile_rows < 1:
        raise ValueError("tile_rows must be at least 1.")
    return (
        params.width / params.tile_columns,
        params.height / params.tile_rows,
    )


def _find_class_regions(
    classes: Sequence[Sequence[int]],
) -> List[List[Tuple[int, int]]]:
    """Find same-class regions using horizontal and vertical neighbours."""
    if not classes:
        return []

    row_count = len(classes)
    column_count = len(classes[0])
    for row in classes:
        if len(row) != column_count:
            raise ValueError("Every class-grid row must have the same length.")

    visited = set()
    regions: List[List[Tuple[int, int]]] = []

    for row_index in range(row_count):
        for column_index in range(column_count):
            start = (row_index, column_index)
            if start in visited:
                continue

            class_value = classes[row_index][column_index]
            region = []
            cells_to_check = [start]
            visited.add(start)

            while cells_to_check:
                current_row, current_column = cells_to_check.pop()
                region.append((current_row, current_column))

                neighbours = [
                    (current_row - 1, current_column),
                    (current_row + 1, current_column),
                    (current_row, current_column - 1),
                    (current_row, current_column + 1),
                ]

                for neighbour_row, neighbour_column in neighbours:
                    if (
                        neighbour_row < 0
                        or neighbour_row >= row_count
                        or neighbour_column < 0
                        or neighbour_column >= column_count
                    ):
                        continue

                    neighbour = (neighbour_row, neighbour_column)
                    if neighbour in visited:
                        continue
                    if classes[neighbour_row][neighbour_column] != class_value:
                        continue

                    visited.add(neighbour)
                    cells_to_check.append(neighbour)

            regions.append(region)

    return regions


def _most_touching_neighbour_class(
    classes: Sequence[Sequence[int]],
    region: Sequence[Tuple[int, int]],
) -> int:
    """Return the adjacent class sharing the most cell edges.

    If two classes touch equally often, the numerically smaller class wins.
    """
    row_count = len(classes)
    column_count = len(classes[0])
    region_cells = set(region)
    touching_edges = {}

    for row_index, column_index in region:
        neighbours = [
            (row_index - 1, column_index),
            (row_index + 1, column_index),
            (row_index, column_index - 1),
            (row_index, column_index + 1),
        ]
        for neighbour_row, neighbour_column in neighbours:
            if (
                neighbour_row < 0
                or neighbour_row >= row_count
                or neighbour_column < 0
                or neighbour_column >= column_count
            ):
                continue

            if (neighbour_row, neighbour_column) in region_cells:
                continue

            neighbour_class = classes[neighbour_row][neighbour_column]
            touching_edges[neighbour_class] = (
                touching_edges.get(neighbour_class, 0) + 1
            )

    if not touching_edges:
        raise ValueError(
            "A small region has no neighbouring class to merge into."
        )

    greatest_touch_count = max(touching_edges.values())
    tied_classes = []
    for class_value, touch_count in touching_edges.items():
        if touch_count == greatest_touch_count:
            tied_classes.append(class_value)

    return min(tied_classes)


def merge_small_islands(
    classes: Sequence[Sequence[int]],
    params: Params,
) -> Tuple[Tuple[int, ...], ...]:
    """Apply R5 by merging small 4-connected regions into their strongest neighbour.

    The raster approximation treats each grid sample as a square with area
    ``resolution * resolution``. ``min_area`` is specified in square metres.
    Regions smaller than the threshold are merged in simultaneous passes.
    """
    if params.min_area < 0.0:
        raise ValueError("min_area cannot be negative.")
    if params.resolution <= 0.0:
        raise ValueError("resolution must be positive.")
    if not classes:
        return tuple()

    row_count = len(classes)
    column_count = len(classes[0])
    if column_count == 0:
        return tuple(tuple() for _ in classes)

    working_rows: List[List[int]] = []
    for row in classes:
        if len(row) != column_count:
            raise ValueError("Every class-grid row must have the same length.")
        working_rows.append(list(row))

    minimum_area_mm2 = params.min_area * 1000000.0
    sample_area_mm2 = params.resolution * params.resolution
    minimum_sample_count = minimum_area_mm2 / sample_area_mm2

    while True:
        regions = _find_class_regions(working_rows)
        regions_to_merge = []

        # Decide all merges from the same grid state so each cell is scanned
        # once per pass rather than flood-filling each region again.
        for region in regions:
            if len(region) >= minimum_sample_count:
                continue

            target_class = _most_touching_neighbour_class(
                working_rows,
                region,
            )
            regions_to_merge.append((region, target_class))

        if not regions_to_merge:
            break

        for region, target_class in regions_to_merge:
            for row_index, column_index in region:
                working_rows[row_index][column_index] = target_class

    cleaned_rows = []
    for row in working_rows:
        cleaned_rows.append(tuple(row))
    return tuple(cleaned_rows)


def count_class_pixels(
    classes: Sequence[Sequence[int]],
) -> Tuple[int, int, int]:
    """Return pixel counts for dark, mid, and light classes."""
    dark = 0
    mid = 0
    light = 0

    for class_row in classes:
        for class_value in class_row:
            if class_value == 0:
                dark += 1
            elif class_value == 1:
                mid += 1
            elif class_value == 2:
                light += 1
            else:
                raise ValueError("Unknown material class: {}".format(class_value))

    return dark, mid, light
