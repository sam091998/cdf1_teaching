"""Geometry algorithms for the crochet pseudosphere and wind-spinner examples."""
import math
import random
import bisect


def stitch_counts(first_round, rounds, increase):
    """Stitches per ring. counts[0] is the first round (into the ring centre),
    counts[r] = first_round * increase ** r."""
    counts = [first_round]
    for _ in range(rounds):
        counts.append(counts[-1] * increase)
    return counts



def build_topology(counts, increase, stitch_width, stitch_height):
    """Returns (offsets, ring_of, edges).
    offsets[r]  : index of the first stitch of ring r in one flat list
    ring_of[i]  : ring number of stitch i
    edges       : list of (i, j, rest_length, kind) with kind 'ring' or 'radial'
    """
    offsets, ring_of = [], []
    total = 0
    for r, n in enumerate(counts):
        offsets.append(total)
        ring_of.extend([r] * n)
        total += n

    edges = []
    for r, n in enumerate(counts):
        o = offsets[r]
        for k in range(n):
            # neighbour inside the same round (wraps around -> closed ring)
            edges.append((o + k, o + (k + 1) % n, stitch_width, "ring"))
            # link to the parent stitch of the previous round
            if r > 0:
                parent = offsets[r - 1] + k // increase
                edges.append((o + k, parent, stitch_height, "radial"))
    return offsets, ring_of, edges




def _ring_length(radius, amplitude, waves, samples=360):
    length, prev = 0.0, None
    for s in range(samples + 1):
        t = 2 * math.pi * s / samples
        p = (radius * math.cos(t), radius * math.sin(t), amplitude * math.sin(waves * t))
        if prev is not None:
            length += math.dist(p, prev)
        prev = p
    return length


def _solve_amplitude(radius, waves, target_length):
    """Bisection: find the wave height that makes the wavy ring exactly target_length long."""
    if _ring_length(radius, 0.0, waves) >= target_length:
        return 0.0
    low, high = 0.0, target_length
    for _ in range(30):
        mid = (low + high) / 2
        if _ring_length(radius, mid, waves) < target_length:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def initial_positions(counts, stitch_width, stitch_height, stitches_per_wave, noise, seed):
    rnd = random.Random(seed)                       # same seed -> same result
    r0 = counts[0] * stitch_width / (2 * math.pi)   # ring 0 has exactly the right length
    pts = []
    for r, n in enumerate(counts):
        radius = r0 + r * stitch_height * 0.6       # rings move outwards AND up/down
        waves = max(3, int(round(n / stitches_per_wave)))
        amp = _solve_amplitude(radius, waves, n * stitch_width)
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            z = amp * math.sin(waves * a) + rnd.uniform(-noise, noise)
            pts.append([radius * math.cos(a), radius * math.sin(a), z])
    return pts



def relax(pts, edges, iterations, strength=0.5, min_dist=0.0, push=0.5):
    """Iterative relaxation (a very simple 'position based' solver).
    1) Edge rule : every edge moves its two end points towards its rest length.
    2) Collision : two stitches closer than `min_dist` push each other apart
                   (yarn cannot pass through yarn). A spatial grid keeps this fast.
    Corrections that land on the same stitch are averaged."""
    n = len(pts)
    for _ in range(iterations):
        shift = [[0.0, 0.0, 0.0] for _ in range(n)]
        hits = [0] * n
        for i, j, rest, _kind in edges:
            pi, pj = pts[i], pts[j]
            dx, dy, dz = pj[0] - pi[0], pj[1] - pi[1], pj[2] - pi[2]
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d < 1e-9:
                continue
            f = strength * (d - rest) / d * 0.5    # half of the error for each end point
            shift[i][0] += f * dx; shift[i][1] += f * dy; shift[i][2] += f * dz
            shift[j][0] -= f * dx; shift[j][1] -= f * dy; shift[j][2] -= f * dz
            hits[i] += 1; hits[j] += 1

        if min_dist > 0:
            grid = {}
            for i, p in enumerate(pts):
                key = (int(p[0] // min_dist), int(p[1] // min_dist), int(p[2] // min_dist))
                grid.setdefault(key, []).append(i)
            for (cx, cy, cz), members in grid.items():
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        for oz in (-1, 0, 1):
                            other = grid.get((cx + ox, cy + oy, cz + oz))
                            if not other:
                                continue
                            for i in members:
                                for j in other:
                                    if j <= i:
                                        continue
                                    pi, pj = pts[i], pts[j]
                                    dx, dy, dz = pj[0] - pi[0], pj[1] - pi[1], pj[2] - pi[2]
                                    d = math.sqrt(dx * dx + dy * dy + dz * dz)
                                    if d >= min_dist or d < 1e-9:
                                        continue
                                    f = push * (d - min_dist) / d * 0.5   # negative -> pushes apart
                                    shift[i][0] += f * dx; shift[i][1] += f * dy; shift[i][2] += f * dz
                                    shift[j][0] -= f * dx; shift[j][1] -= f * dy; shift[j][2] -= f * dz
                                    hits[i] += 1; hits[j] += 1

        for i in range(n):
            if hits[i]:
                pts[i][0] += shift[i][0] / hits[i] * 2
                pts[i][1] += shift[i][1] / hits[i] * 2
                pts[i][2] += shift[i][2] / hits[i] * 2
    return pts


def edge_error(pts, edges):
    """Average relative length error of all edges (0.0 = perfect). Use it to judge the result."""
    tot = 0.0
    for i, j, rest, _k in edges:
        d = math.dist(pts[i], pts[j])
        tot += abs(d - rest) / rest
    return tot / len(edges)



def create_hyperbolic_spiral(first_round=12, rounds=4, increase=2,
                             stitch_width=1.0, stitch_height=1.5,
                             stitches_per_wave=8, iterations=100,
                             noise=0.05, seed=1):
    """iterations=0 -> only the fast analytic ruffles, no relaxation."""
    counts = stitch_counts(first_round, rounds, increase)
    offsets, ring_of, edges = build_topology(counts, increase, stitch_width, stitch_height)
    pts = initial_positions(counts, stitch_width, stitch_height, stitches_per_wave, noise, seed)
    if iterations > 0:
        pts = relax(pts, edges, iterations, min_dist=0.85 * stitch_width)
    return {"counts": counts, "points": pts, "ring_of": ring_of,
            "edges": edges, "error": edge_error(pts, edges)}


def _wind_spinner_axis_frame(t, height, curve_amount):
    """Return the curved centerline point and its local cross-section frame."""
    bend = curve_amount * height
    center_x = bend * math.sin(2.0 * math.pi * t)
    tangent_x = 2.0 * math.pi * bend * math.cos(2.0 * math.pi * t)
    tangent_length = math.sqrt(tangent_x * tangent_x + height * height)
    normal = (height / tangent_length, 0.0, -tangent_x / tangent_length)
    return (center_x, 0.0, height * t), normal


def _wind_spinner_row_length(radius, height, turns, waves, ripple, samples,
                             curve_amount):
    """Approximate the length of one tapered, ruffled helical crochet row."""
    previous = _wind_spinner_point(
        0.0, radius, height, turns, waves, ripple, 0.0, curve_amount
    )
    length = 0.0
    for i in range(1, samples + 1):
        t = i / float(samples)
        point = _wind_spinner_point(
            t, radius, height, turns, waves, ripple, 0.0, curve_amount
        )
        length += math.dist(previous, point)
        previous = point
    return length


def _solve_wind_spinner_radius(target_length, height, turns, waves, ripple,
                               samples, curve_amount):
    """Choose a row radius whose helical path matches its stitch length."""
    axis_length = _wind_spinner_row_length(
        0.0, height, turns, waves, ripple, samples, curve_amount
    )
    if target_length <= axis_length:
        return 0.0

    low, high = 0.0, target_length
    for _ in range(40):
        mid = (low + high) / 2.0
        length = _wind_spinner_row_length(
            mid, height, turns, waves, ripple, samples, curve_amount
        )
        if length < target_length:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def _crochet_stitch_progression(rows, single_crochet_length):
    """Return each expanded row's stitch length and crochet-stitch pattern."""
    single = single_crochet_length
    double = 2.0 * single
    triple = 3.0 * single
    lengths = []
    patterns = []

    for row_index in range(rows):
        if row_index == 0:
            parts = [("single crochet", single)]
        elif row_index == 1:
            parts = [("double crochet", double)]
        elif row_index == 2:
            parts = [("triple crochet", triple)]
        else:
            extra = row_index - 2
            parts = [("triple crochet", triple)]
            while extra >= 3:
                parts.append(("triple crochet", triple))
                extra -= 3
            if extra == 2:
                parts.append(("double crochet", double))
            elif extra == 1:
                parts.append(("single crochet", single))

        lengths.append(sum(length for _name, length in parts))
        patterns.append(" + ".join(name for name, _length in parts))

    return lengths, patterns


def _crochet_path_positions(path_length, single_crochet_length, subdivisions=4):
    """Return refined positions, stitch labels, and stitch-end boundaries."""
    stitch_lengths = (
        single_crochet_length,
        2.0 * single_crochet_length,
        3.0 * single_crochet_length,
    )
    stitch_names = ("single crochet", "double crochet", "triple crochet")
    positions = [0.0]
    pattern = []
    boundaries = []
    distance = 0.0
    stitch_index = 0

    while distance < path_length:
        stitch_length = stitch_lengths[stitch_index % len(stitch_lengths)]
        next_distance = min(distance + stitch_length, path_length)
        stitch_name = stitch_names[stitch_index % len(stitch_names)]
        pattern.append(stitch_name)
        for subdivision in range(1, subdivisions + 1):
            position = distance + (next_distance - distance) * (
                subdivision / float(subdivisions)
            )
            if position > positions[-1]:
                positions.append(position)
        distance = next_distance
        boundaries.append((distance, stitch_name))
        stitch_index += 1

    return positions, pattern, boundaries


def create_triangular_crochet_spiral(max_width, m_ratio,
                                     base_chain_stitch_count=16, rows=3,
                                     increase=2,
                                     stitch_height=1.5, turns=5,
                                     stitch_width=1.0,
                                     single_crochet_length=None,
                                     stitches_per_wave=16, ripple=0.10,
                                     inner_diameter_ratio=0.60,
                                     step_seam_count=None):
    """Create a ruffled, layered wind-chime mesh using a cone profile."""
    if max_width <= 0:
        raise ValueError("max_width must be positive")
    if not 0.0 <= m_ratio <= 1.0:
        raise ValueError("m_ratio must be between 0 and 1")
    if base_chain_stitch_count < 2:
        raise ValueError("base_chain_stitch_count must be at least 2")
    if rows < 1 or turns < 1:
        raise ValueError("rows and turns must be at least 1")
    if increase < 1:
        raise ValueError("increase must be at least 1")
    if stitch_height <= 0 or stitch_width <= 0:
        raise ValueError("stitch_height and stitch_width must be positive")
    if single_crochet_length is not None and single_crochet_length <= 0:
        raise ValueError("single_crochet_length must be positive when provided")
    if stitches_per_wave < 1:
        raise ValueError("stitches_per_wave must be at least 1")
    if not 0.0 <= ripple < 1.0:
        raise ValueError("ripple must be between 0 and 1")
    if not 0.0 <= inner_diameter_ratio < 1.0:
        raise ValueError("inner_diameter_ratio must be in the range [0, 1)")
    if step_seam_count is not None and step_seam_count < 1:
        raise ValueError("step_seam_count must be at least 1")

    single_length = (
        single_crochet_length
        if single_crochet_length is not None else stitch_width
    )
    height = base_chain_stitch_count * stitch_height

    def profile(t):
        inverted_cone = 1.0 - t
        double_cone = 1.0 - abs(2.0 * t - 1.0)
        upright_cone = t
        if m_ratio <= 0.5:
            blend = 2.0 * m_ratio
            return (1.0 - blend) * inverted_cone + blend * double_cone
        blend = 2.0 * (m_ratio - 0.5)
        return (1.0 - blend) * double_cone + blend * upright_cone

    def profile_radius(t):
        return max_width * 0.5 * max(0.0, profile(t))

    def surface_point(t, angle, radius_scale=1.0):
        radius = profile_radius(t) * radius_scale
        return (
            radius * math.cos(angle),
            radius * math.sin(angle),
            height * (t - 0.5),
        )

    vertical_positions, vertical_pattern, _ = (
        _crochet_path_positions(height, single_length)
    )
    across_pattern = _crochet_path_positions(max_width, single_length)[1]
    wave_count = max(
        1,
        int(round(stitch_counts(base_chain_stitch_count, rows, increase)[-1]
                  / float(stitches_per_wave))),
    )
    sample_count = max(128, turns * 32, wave_count * 16)
    mesh_sample_count = max(64, turns * 16, wave_count * 8)
    t_positions = sorted(set(
        [index / float(sample_count) for index in range(sample_count + 1)]
        + [position / height for position in vertical_positions]
    ))
    def spiral_angle(t, phase=rows * 0.08):
        return 2.0 * math.pi * turns * t + phase

    def ruffle_scale(t):
        return 1.0 + ripple * math.cos(2.0 * math.pi * wave_count * t)

    def spiral_point(t):
        return surface_point(t, spiral_angle(t), ruffle_scale(t))

    arc_lengths = [0.0]
    for index in range(1, len(t_positions)):
        arc_lengths.append(
            arc_lengths[-1]
            + math.dist(spiral_point(t_positions[index - 1]),
                        spiral_point(t_positions[index]))
        )

    def parameter_at_distance(distance):
        segment = min(
            bisect.bisect_left(arc_lengths, distance),
            len(arc_lengths) - 1,
        )
        if segment == 0:
            return t_positions[0]
        start_length = arc_lengths[segment - 1]
        end_length = arc_lengths[segment]
        if end_length <= start_length:
            return t_positions[segment]
        factor = (distance - start_length) / (end_length - start_length)
        return (
            t_positions[segment - 1]
            + factor * (t_positions[segment] - t_positions[segment - 1])
        )

    total_spiral_length = arc_lengths[-1]
    spiral_distances = [0.0]
    spiral_pattern = []
    stitch_boundaries = []
    stitch_lengths = (
        single_length, 2.0 * single_length, 3.0 * single_length
    )
    stitch_names = (
        "single crochet", "double crochet", "triple crochet"
    )
    distance = 0.0
    stitch_index = 0
    while distance < total_spiral_length:
        stitch_length = stitch_lengths[stitch_index % 3]
        end_distance = min(distance + stitch_length, total_spiral_length)
        spiral_pattern.append(stitch_names[stitch_index % 3])
        subdivisions = max(1, int(math.ceil(
            (end_distance - distance) / (single_length / 4.0)
        )))
        for subdivision in range(1, subdivisions + 1):
            point_distance = distance + (end_distance - distance) * (
                subdivision / float(subdivisions)
            )
            spiral_distances.append(point_distance)
        stitch_boundaries.append(
            (end_distance, stitch_names[stitch_index % 3])
        )
        distance = end_distance
        stitch_index += 1

    spiral_points = [
        spiral_point(parameter_at_distance(distance))
        for distance in spiral_distances
    ]
    stitch_seams = []
    stitch_seam_labels = []
    for distance, stitch_name in stitch_boundaries:
        t = parameter_at_distance(distance)
        radius = profile_radius(t) * ruffle_scale(t)
        if radius <= 1e-9:
            continue
        angle = spiral_angle(t)
        half_angle = min(math.pi / 12.0, single_length / (2.0 * radius))
        seam = [
            surface_point(
                t,
                angle + half_angle * (2.0 * index / 8.0 - 1.0),
                ruffle_scale(t),
            )
            for index in range(9)
        ]
        stitch_seams.append(seam)
        stitch_seam_labels.append(
            "End of {} at {:.3f}".format(stitch_name, distance)
        )

    if step_seam_count is not None:
        for seam_index in range(1, step_seam_count + 1):
            t = seam_index / float(step_seam_count + 1)
            seam = []
            for row_index in range(rows + 1):
                radial_scale = (
                    inner_diameter_ratio
                    + (1.0 - inner_diameter_ratio)
                    * row_index / float(rows)
                )
                seam.append(surface_point(
                    t,
                    spiral_angle(t, row_index * 0.08),
                    radial_scale * ruffle_scale(t),
                ))
            stitch_seams.append(seam)
            stitch_seam_labels.append(
                "Pattern step {}".format(seam_index)
            )

    wind_chime_points = []
    wind_chime_row_indices = []
    tip_indices = {}
    ribbon_t_positions = [
        index / float(mesh_sample_count)
        for index in range(mesh_sample_count + 1)
    ]
    for row_index in range(rows + 1):
        radial_scale = (
            inner_diameter_ratio
            + (1.0 - inner_diameter_ratio) * row_index / float(rows)
        )
        phase = row_index * 0.08
        indices = []
        for sample_index, t in enumerate(ribbon_t_positions):
            is_collapsed_tip = (
                sample_index in (0, mesh_sample_count)
                and profile_radius(t) <= 1e-12
            )
            if is_collapsed_tip and sample_index in tip_indices:
                indices.append(tip_indices[sample_index])
            else:
                indices.append(len(wind_chime_points))
                wind_chime_points.append(
                    surface_point(
                        t,
                        spiral_angle(t, phase),
                        radial_scale * ruffle_scale(t),
                    )
                )
                if is_collapsed_tip:
                    tip_indices[sample_index] = indices[-1]
        wind_chime_row_indices.append(indices)

    wind_chime_faces = []
    for row_index in range(len(wind_chime_row_indices) - 1):
        lower = wind_chime_row_indices[row_index]
        upper = wind_chime_row_indices[row_index + 1]
        for sample_index in range(mesh_sample_count):
            face = (
                lower[sample_index],
                lower[sample_index + 1],
                upper[sample_index + 1],
                upper[sample_index],
            )
            unique_face = tuple(dict.fromkeys(face))
            if len(unique_face) >= 3:
                wind_chime_faces.append(unique_face)

    axis = [
        (0.0, 0.0, height * (t - 0.5))
        for t in ribbon_t_positions
    ]
    return {
        "counts": stitch_counts(base_chain_stitch_count, rows, increase),
        "smooth_points": [],
        "smooth_row_indices": [],
        "smooth_faces": [],
        "axis_height": height,
        "turns": turns,
        "axis_points": axis,
        "spiral_points": spiral_points,
        "spiral_stitch_pattern": spiral_pattern,
        "wind_chime_points": wind_chime_points,
        "wind_chime_faces": wind_chime_faces,
        "wind_chime_row_indices": wind_chime_row_indices,
        "stitch_seams": stitch_seams,
        "stitch_seam_labels": stitch_seam_labels,
        "max_width": max_width,
        "m_ratio": m_ratio,
        "inner_diameter_ratio": inner_diameter_ratio,
        "single_crochet_length": single_length,
        "double_crochet_length": 2.0 * single_length,
        "triple_crochet_length": 3.0 * single_length,
        "crochet_stitch_lengths": [single_length, 2.0 * single_length,
                                   3.0 * single_length],
        "crochet_stitch_patterns": ["single crochet", "double crochet",
                                    "triple crochet"],
        "vertical_stitch_pattern": vertical_pattern,
        "across_stitch_pattern": across_pattern,
        "row_path_lengths": [height, max_width],
        "stitches_per_wave": stitches_per_wave,
        "ripple": ripple,
    }


def _wind_spinner_point(t, radius, height, turns, waves, ripple, phase,
                       curve_amount):
    """Evaluate one smooth point along a ruffled helical row."""
    angle = 2.0 * math.pi * turns * t + phase
    envelope = math.sin(math.pi * t) ** 0.75
    radial = radius * envelope * (
        1.0 + ripple * math.cos(2.0 * math.pi * waves * t)
    )
    center, normal = _wind_spinner_axis_frame(t, height, curve_amount)
    return (
        center[0] + radial * math.cos(angle) * normal[0],
        center[1] + radial * math.sin(angle),
        center[2] + radial * math.cos(angle) * normal[2],
    )


def create_hyperbolic_wind_spinner(base_chain_stitch_count=16, rows=3,
                                   increase=2, stitch_width=1.0,
                                   stitch_height=1.5, turns=5,
                                   stitches_per_wave=16, ripple=0.10,
                                   curve_amount=0.15,
                                   single_crochet_length=None):
    """Create a tapered, connected helical ribbon from crochet Example 2 rows.

    The base chain follows a curved vertical centerline. Each expanded row is
    mapped to a helix around it; sampled rows form the display mesh.

    If single_crochet_length is provided, expanded rows use a crochet-length
    progression of x, 2x, 3x, 3x+x, 3x+2x, and so on. The resulting per-stitch
    length is multiplied by the row's stitch intervals to set its helical path
    length. When omitted, the legacy stitch_width-based behavior is preserved.
    """
    if base_chain_stitch_count < 2:
        raise ValueError("base_chain_stitch_count must be at least 2")
    if rows < 1:
        raise ValueError("rows must be at least 1")
    if increase < 1:
        raise ValueError("increase must be at least 1")
    if stitch_width <= 0 or stitch_height <= 0:
        raise ValueError("stitch_width and stitch_height must be positive")
    if single_crochet_length is not None and single_crochet_length <= 0:
        raise ValueError("single_crochet_length must be positive when provided")
    if turns < 1 or stitches_per_wave < 1:
        raise ValueError("turns and stitches_per_wave must be at least 1")
    if not 0.0 <= ripple < 1.0:
        raise ValueError("ripple must be between 0 and 1")
    if not 0.0 <= curve_amount <= 0.5:
        raise ValueError("curve_amount must be between 0 and 0.5")

    counts = stitch_counts(base_chain_stitch_count, rows, increase)
    axis_height = base_chain_stitch_count * stitch_height
    row_profiles = [(0.0, 0, 0.0)]
    row_path_lengths = [axis_height]
    crochet_stitch_lengths = []
    crochet_stitch_patterns = []

    if single_crochet_length is not None:
        crochet_stitch_lengths, crochet_stitch_patterns = (
            _crochet_stitch_progression(rows, single_crochet_length)
        )

    for row_index, count in enumerate(counts[1:], start=1):
        waves = max(1, int(round(count / float(stitches_per_wave))))
        samples = max(128, waves * 16)
        if single_crochet_length is None:
            target_length = (count - 1) * stitch_width
        else:
            target_length = (count - 1) * crochet_stitch_lengths[row_index - 1]
        row_path_lengths.append(target_length)
        radius = _solve_wind_spinner_radius(
            target_length, axis_height, turns, waves, ripple, samples,
            curve_amount
        )
        phase = row_index * 0.08
        row_profiles.append((radius, waves, phase))

    smooth_samples = max(128, turns * 32)
    smooth_points = []
    smooth_row_indices = []
    for row_index, (radius, waves, phase) in enumerate(row_profiles):
        indices = []
        for sample in range(smooth_samples + 1):
            t = sample / float(smooth_samples)
            if row_index == 0:
                point, _normal = _wind_spinner_axis_frame(
                    t, axis_height, curve_amount
                )
            else:
                point = _wind_spinner_point(
                    t, radius, axis_height, turns, waves, ripple, phase,
                    curve_amount
                )
            indices.append(len(smooth_points))
            smooth_points.append(point)
        smooth_row_indices.append(indices)

    smooth_faces = []
    for row_index in range(len(smooth_row_indices) - 1):
        lower = smooth_row_indices[row_index]
        upper = smooth_row_indices[row_index + 1]
        for sample in range(smooth_samples):
            smooth_faces.append((
                lower[sample],
                lower[sample + 1],
                upper[sample + 1],
                upper[sample],
            ))

    return {
        "counts": counts,
        "smooth_points": smooth_points,
        "smooth_row_indices": smooth_row_indices,
        "smooth_faces": smooth_faces,
        "axis_height": axis_height,
        "turns": turns,
        "single_crochet_length": single_crochet_length,
        "double_crochet_length": (
            2.0 * single_crochet_length
            if single_crochet_length is not None else None
        ),
        "triple_crochet_length": (
            3.0 * single_crochet_length
            if single_crochet_length is not None else None
        ),
        "crochet_stitch_lengths": crochet_stitch_lengths,
        "crochet_stitch_patterns": crochet_stitch_patterns,
        "row_path_lengths": row_path_lengths,
    }
