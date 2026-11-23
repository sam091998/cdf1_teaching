import importlib.util
from pathlib import Path


CORE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "cdf"
    / "ripple_core.py"
)
CORE_SPEC = importlib.util.spec_from_file_location("ripple_core_test", CORE_PATH)
CORE_MODULE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE_MODULE)

Params = CORE_MODULE.Params
count_class_pixels = CORE_MODULE.count_class_pixels
generate_ripple_field = CORE_MODULE.generate_ripple_field
get_tile_size = CORE_MODULE.get_tile_size
merge_small_islands = CORE_MODULE.merge_small_islands
place_drops = CORE_MODULE.place_drops


def test_drop_spacing():
    params = Params(seed=7)
    drops = place_drops(params)

    assert len(drops) <= params.n_drops
    for index, first in enumerate(drops):
        for second in drops[index + 1 :]:
            dx = first.x - second.x
            dy = first.y - second.y
            distance = (dx * dx + dy * dy) ** 0.5
            assert distance >= params.d_min


def test_field_range_and_threshold_classes():
    result = generate_ripple_field(Params(seed=11))

    for row in result.field:
        for value in row:
            assert -1.0 <= value <= 1.0

    for row in result.classes:
        for class_value in row:
            assert class_value in (0, 1, 2)


def test_seed_determinism():
    params = Params(seed=123)
    first = generate_ripple_field(params)
    second = generate_ripple_field(params)

    assert first.hash == second.hash
    assert first.drops == second.drops
    assert first.field == second.field
    assert first.classes == second.classes


def test_class_counts_cover_the_grid():
    result = generate_ripple_field(Params(seed=19))
    dark, mid, light = count_class_pixels(result.classes)

    grid_count = len(result.xs) * len(result.ys)
    assert dark + mid + light == grid_count


def test_default_floor_has_ten_by_ten_tiles():
    params = Params()
    tile_width, tile_height = get_tile_size(params)

    assert params.tile_columns == 10
    assert params.tile_rows == 10
    assert tile_width == 600.0
    assert tile_height == 400.0


def test_small_island_merges_into_class_with_most_shared_edges():
    params = Params(resolution=20.0, min_area=0.0008)
    classes = (
        (0, 0, 0),
        (0, 2, 1),
        (0, 0, 1),
    )

    merged = merge_small_islands(classes, params)

    assert merged[1][1] == 0


def test_small_island_tie_uses_lower_class_value():
    params = Params(resolution=20.0, min_area=0.0008)
    classes = (
        (0, 0, 0, 0, 0),
        (0, 0, 0, 1, 1),
        (0, 0, 2, 1, 1),
        (0, 0, 1, 1, 1),
        (0, 0, 1, 1, 1),
    )

    merged = merge_small_islands(classes, params)

    assert merged[2][2] == 0


def test_island_merge_removes_all_regions_below_minimum_area():
    params = Params(resolution=20.0, min_area=0.0008)
    classes = (
        (0, 0, 0, 0),
        (0, 2, 1, 1),
        (0, 0, 1, 1),
        (0, 0, 0, 0),
    )

    merged = merge_small_islands(classes, params)
    regions = CORE_MODULE._find_class_regions(merged)
    minimum_sample_count = params.min_area * 1000000.0 / (
        params.resolution * params.resolution
    )

    for region in regions:
        assert len(region) >= minimum_sample_count
