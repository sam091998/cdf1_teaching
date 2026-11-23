"""RhinoCommon geometry helpers for the Assignment 2 ripple floor."""

from math import ceil, sqrt
from typing import Dict, List, Tuple

import Rhino.Geometry as rg

from cdf.ripple_core import Params, RippleField, generate_ripple_field


def build_height_mesh(params: Params, result: RippleField) -> rg.Mesh:
    """Build a sampled height-field mesh from the normalised ripple values."""
    if params.amplitude <= 0.0:
        raise ValueError("amplitude must be positive.")

    row_count = len(result.ys)
    column_count = len(result.xs)

    if row_count < 2 or column_count < 2:
        raise ValueError("The floor mesh needs at least two rows and columns.")

    mesh = rg.Mesh()

    # Create one vertex for every sampled field value.
    for row_index, y in enumerate(result.ys):
        for column_index, x in enumerate(result.xs):
            height = result.field[row_index][column_index] * params.amplitude
            mesh.Vertices.Add(x, y, height)

    # Connect each group of four neighbouring samples into a quad.
    for row_index in range(row_count - 1):
        for column_index in range(column_count - 1):
            lower_left = row_index * column_count + column_index
            lower_right = lower_left + 1
            upper_left = lower_left + column_count
            upper_right = upper_left + 1

            mesh.Faces.AddFace(
                lower_left,
                lower_right,
                upper_right,
                upper_left,
            )

    mesh.Normals.ComputeNormals()
    mesh.Compact()

    if not mesh.IsValid:
        raise RuntimeError("Rhino could not create a valid ripple height mesh.")

    return mesh


def extract_threshold_contours(
    mesh: rg.Mesh,
    params: Params,
) -> Tuple[List[rg.Curve], List[str]]:
    """Extract contours at the negative and positive class thresholds."""
    if params.contour_tolerance <= 0.0:
        raise ValueError("contour_tolerance must be positive.")
    if params.amplitude <= 0.0:
        raise ValueError("amplitude must be positive.")

    contour_levels = (
        (-params.threshold, "dark-mid boundary"),
        (params.threshold, "mid-light boundary"),
    )
    contours = []
    contour_labels = []

    for field_level, label in contour_levels:
        z_level = field_level * params.amplitude
        section_plane = rg.Plane(
            rg.Point3d(0.0, 0.0, z_level),
            rg.Vector3d.ZAxis,
        )

        # RhinoCommon 7.13+ overload verified in the official API reference:
        # Mesh.CreateContourCurves(Mesh, Plane, double tolerance).
        level_curves = rg.Mesh.CreateContourCurves(
            mesh,
            section_plane,
            params.contour_tolerance,
        )

        if level_curves is None:
            raise RuntimeError(
                "Rhino failed to extract contours at field value {}.".format(
                    field_level
                )
            )

        for curve in level_curves:
            contours.append(curve)
            contour_labels.append(label)

    return contours, contour_labels


def _add_contour_tube(
    mesh: rg.Mesh,
    curve: rg.Curve,
    params: Params,
    contour_index: int,
) -> None:
    """Add one capped, rectangular-section tube around a planar contour."""
    curve_length = curve.GetLength()
    if curve_length <= params.contour_tolerance:
        raise ValueError(
            "Contour {} is too short to create a mesh.".format(contour_index)
        )

    sample_spacing = max(params.resolution, params.contour_mesh_width)
    segment_count = max(3, int(ceil(curve_length / sample_spacing)))
    is_closed = curve.IsClosed
    point_count = segment_count if is_closed else segment_count + 1
    points = []

    for point_index in range(point_count):
        fraction = point_index / float(segment_count)
        point = curve.PointAtNormalizedLength(fraction)
        if not point.IsValid:
            raise RuntimeError(
                "Could not sample contour {} for its mesh.".format(contour_index)
            )
        points.append(point)

    first_vertex = mesh.Vertices.Count
    half_width = params.contour_mesh_width * 0.5
    half_height = params.contour_mesh_height * 0.5

    for point_index, point in enumerate(points):
        if is_closed:
            previous_point = points[(point_index - 1) % point_count]
            next_point = points[(point_index + 1) % point_count]
        elif point_index == 0:
            previous_point = points[0]
            next_point = points[1]
        elif point_index == point_count - 1:
            previous_point = points[point_count - 2]
            next_point = points[point_count - 1]
        else:
            previous_point = points[point_index - 1]
            next_point = points[point_index + 1]

        tangent_x = next_point.X - previous_point.X
        tangent_y = next_point.Y - previous_point.Y
        tangent_length = sqrt(
            tangent_x * tangent_x + tangent_y * tangent_y
        )
        if tangent_length <= params.contour_tolerance:
            raise RuntimeError(
                "Contour {} has a degenerate tangent at sample {}.".format(
                    contour_index,
                    point_index,
                )
            )

        tangent_x = tangent_x / tangent_length
        tangent_y = tangent_y / tangent_length
        normal_x = -tangent_y
        normal_y = tangent_x

        # Four points form a small rectangular tube section in XY and Z.
        mesh.Vertices.Add(
            point.X + normal_x * half_width,
            point.Y + normal_y * half_width,
            point.Z + half_height,
        )
        mesh.Vertices.Add(
            point.X - normal_x * half_width,
            point.Y - normal_y * half_width,
            point.Z + half_height,
        )
        mesh.Vertices.Add(
            point.X - normal_x * half_width,
            point.Y - normal_y * half_width,
            point.Z - half_height,
        )
        mesh.Vertices.Add(
            point.X + normal_x * half_width,
            point.Y + normal_y * half_width,
            point.Z - half_height,
        )

    ring_count = point_count
    connection_count = ring_count if is_closed else ring_count - 1

    for ring_index in range(connection_count):
        next_ring = (ring_index + 1) % ring_count
        current_start = first_vertex + ring_index * 4
        next_start = first_vertex + next_ring * 4

        for side_index in range(4):
            next_side = (side_index + 1) % 4
            mesh.Faces.AddFace(
                current_start + side_index,
                current_start + next_side,
                next_start + next_side,
                next_start + side_index,
            )

    if not is_closed:
        start_center = mesh.Vertices.Count
        start_point = points[0]
        mesh.Vertices.Add(start_point.X, start_point.Y, start_point.Z)

        end_center = mesh.Vertices.Count
        end_point = points[-1]
        mesh.Vertices.Add(end_point.X, end_point.Y, end_point.Z)

        start_ring = first_vertex
        end_ring = first_vertex + (ring_count - 1) * 4
        for side_index in range(4):
            next_side = (side_index + 1) % 4
            mesh.Faces.AddFace(
                start_center,
                start_ring + next_side,
                start_ring + side_index,
            )
            mesh.Faces.AddFace(
                end_center,
                end_ring + side_index,
                end_ring + next_side,
            )


def build_contour_mesh(
    contours: List[rg.Curve],
    params: Params,
) -> rg.Mesh:
    """Turn threshold contours into narrow rectangular tube meshes."""
    if params.contour_mesh_width <= 0.0:
        raise ValueError("contour_mesh_width must be positive.")
    if params.contour_mesh_height <= 0.0:
        raise ValueError("contour_mesh_height must be positive.")

    mesh = rg.Mesh()

    for contour_index, curve in enumerate(contours):
        _add_contour_tube(mesh, curve, params, contour_index)

    mesh.Normals.ComputeNormals()
    mesh.Compact()

    if contours and not mesh.IsValid:
        raise RuntimeError("Rhino could not create a valid contour tube mesh.")

    return mesh


def create_rhino_ripple_geometry(params: Params) -> Dict[str, object]:
    """Generate the field, height mesh, contours, and contour tube mesh."""
    result = generate_ripple_field(params)
    mesh = build_height_mesh(params, result)
    contours, contour_labels = extract_threshold_contours(mesh, params)
    contour_mesh = build_contour_mesh(contours, params)

    drop_points = []
    for drop in result.drops:
        drop_points.append(rg.Point3d(drop.x, drop.y, 0.0))

    report_lines = [
        "Drops placed: {} of {}".format(len(result.drops), params.n_drops),
        "Height mesh: {} vertices, {} faces".format(
            mesh.Vertices.Count,
            mesh.Faces.Count,
        ),
        "Threshold contours: {}".format(len(contours)),
        "Contour mesh: {} vertices, {} faces".format(
            contour_mesh.Vertices.Count,
            contour_mesh.Faces.Count,
        ),
        "Field hash: {}".format(result.hash),
        "Class surfaces are not built yet (Milestone 4).",
        "Grout gap is not applied yet (Milestone 4).",
    ]

    if len(result.drops) < params.n_drops:
        report_lines.append(
            "Warning: drop placement stopped before all requested drops fit."
        )

    return {
        "mesh": mesh,
        "contour_mesh": contour_mesh,
        "drops": drop_points,
        "contours": contours,
        "contour_labels": contour_labels,
        "field": result,
        "report": "\n".join(report_lines),
    }
