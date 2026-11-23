# Grasshopper Rhino 8 Python 3 Script component.
#
# Inputs:
#   show (Boolean Toggle)
#   base_chain_stitch_count (integer slider, default 16)
#   single_crochet (integer slider, minimum 1; controls rows, width, and seams)
#   increase (integer slider, default 2)
#   stitch_width, stitch_height (positive number sliders)
#   turns (integer slider, default 5; geometric setting, not in crochet pseudocode)
#   stitches_per_wave (integer slider, default 16; geometric setting)
#   curve_amount (number slider, 0.0 .. 0.5, default 0.15; controls S-bend strength)
#   m_ratio (optional number slider, 0.0 .. 1.0; triangular orientation/spiral)
#   ripple (optional number slider, 0.0 .. 0.5; wind-chime ruffle)
#   inner_diameter_ratio (optional slider, 0.0 .. 0.95; default 0.60)
#   base_point (optional Rhino point; translates all geometry outputs)
# Outputs:
#   surface (legacy only; empty in cone mode), wind_chime, spiral, row_curves,
#   axis, info, double_crochet_length,
#   triple_crochet_length, crochet_stitch_lengths,
#   crochet_stitch_patterns, row_path_lengths, vertical_stitch_pattern,
#   across_stitch_pattern, spiral_stitch_pattern, stitch_seams,
#   stitch_seam_labels

import Rhino
import Rhino.Geometry as rg
import Grasshopper.Kernel as gh
from cdf.hyperbolic_spiral import create_hyperbolic_wind_spinner
from cdf.hyperbolic_spiral import create_triangular_crochet_spiral

surface = rg.Mesh()
wind_chime = rg.Mesh()
spiral = None
row_curves = []
axis = None
info = ""
double_crochet_length = None
triple_crochet_length = None
crochet_stitch_lengths = []
crochet_stitch_patterns = []
row_path_lengths = []
vertical_stitch_pattern = []
across_stitch_pattern = []
spiral_stitch_pattern = []
stitch_seams = []
stitch_seam_labels = []

single_crochet_input = float(single_crochet)
try:
    m_ratio_input = m_ratio
except NameError:
    m_ratio_input = None
try:
    ripple_input = ripple
except NameError:
    ripple_input = 0.10
try:
    inner_diameter_ratio_input = inner_diameter_ratio
except NameError:
    inner_diameter_ratio_input = 0.60
try:
    base_point_input = base_point
except NameError:
    base_point_input = rg.Point3d.Origin


def find_self_intersection(mesh, tolerance):
    face_meshes = []
    for face_index in range(mesh.Faces.Count):
        face = mesh.Faces[face_index]
        vertex_indices = [face.A, face.B, face.C]
        if not face.IsTriangle:
            vertex_indices.append(face.D)

        vertices = []
        for index in vertex_indices:
            point = mesh.Vertices[index]
            if not any(point.DistanceTo(existing) <= tolerance for existing in vertices):
                vertices.append(point)
        if len(vertices) < 3:
            continue

        face_mesh = rg.Mesh()
        for point in vertices:
            face_mesh.Vertices.Add(point)
        if len(vertices) == 3:
            face_mesh.Faces.AddFace(0, 1, 2)
        else:
            face_mesh.Faces.AddFace(0, 1, 2, 3)

        face_meshes.append((
            face_index,
            set(vertex_indices),
            face_mesh,
            face_mesh.GetBoundingBox(True),
        ))

    face_meshes.sort(key=lambda item: item[3].Min.X)

    for i, first in enumerate(face_meshes):
        first_index, first_vertices, first_mesh, first_box = first
        for second in face_meshes[i + 1:]:
            second_index, second_vertices, second_mesh, second_box = second
            if second_box.Min.X > first_box.Max.X + tolerance:
                break
            if not first_vertices.isdisjoint(second_vertices):
                continue
            if (
                first_box.Max.Y + tolerance < second_box.Min.Y
                or second_box.Max.Y + tolerance < first_box.Min.Y
                or first_box.Max.Z + tolerance < second_box.Min.Z
                or second_box.Max.Z + tolerance < first_box.Min.Z
            ):
                continue

            curves = rg.Intersect.Intersection.MeshMeshAccurate(
                first_mesh, second_mesh, tolerance
            )
            if curves and any(curve.Length > tolerance for curve in curves):
                return first_index, second_index

    return None


if show:
    if single_crochet_input < 1:
        raise ValueError("single_crochet must be at least 1.")
    rows_input = int(round(single_crochet_input))
    max_width_input = single_crochet_input * float(stitch_width)
    crochet_length_input = float(stitch_width)

    if m_ratio_input is not None:
        result = create_triangular_crochet_spiral(
            max_width=float(max_width_input),
            m_ratio=float(m_ratio_input),
            base_chain_stitch_count=int(base_chain_stitch_count),
            rows=rows_input,
            increase=int(increase),
            stitch_width=float(stitch_width),
            stitch_height=float(stitch_height),
            turns=int(turns),
            single_crochet_length=(
                float(crochet_length_input)
                if crochet_length_input is not None else None
            ),
            stitches_per_wave=int(stitches_per_wave),
            ripple=float(ripple_input),
            inner_diameter_ratio=float(inner_diameter_ratio_input),
            step_seam_count=rows_input,
        )
        vertical_stitch_pattern = result["vertical_stitch_pattern"]
        across_stitch_pattern = result["across_stitch_pattern"]
    else:
        result = create_hyperbolic_wind_spinner(
            base_chain_stitch_count=int(base_chain_stitch_count),
            rows=rows_input,
            increase=int(increase),
            stitch_width=float(stitch_width),
            stitch_height=float(stitch_height),
            turns=int(turns),
            stitches_per_wave=int(stitches_per_wave),
            curve_amount=float(curve_amount),
            single_crochet_length=(
                float(crochet_length_input)
                if crochet_length_input is not None else None
            ),
        )
    double_crochet_length = result["double_crochet_length"]
    triple_crochet_length = result["triple_crochet_length"]
    crochet_stitch_lengths = result["crochet_stitch_lengths"]
    crochet_stitch_patterns = result["crochet_stitch_patterns"]
    row_path_lengths = result["row_path_lengths"]
    if "spiral_points" in result:
        spiral = rg.PolylineCurve([
            rg.Point3d(x, y, z) for x, y, z in result["spiral_points"]
        ])
        spiral_stitch_pattern = result["spiral_stitch_pattern"]
    if "wind_chime_points" in result:
        for x, y, z in result["wind_chime_points"]:
            wind_chime.Vertices.Add(x, y, z)
        for face in result["wind_chime_faces"]:
            if len(face) == 3:
                wind_chime.Faces.AddFace(face[0], face[1], face[2])
            else:
                wind_chime.Faces.AddFace(
                    face[0], face[1], face[2], face[3]
                )
        wind_chime.Normals.ComputeNormals()
        wind_chime.Compact()
    stitch_seams = [
        rg.PolylineCurve([
            rg.Point3d(x, y, z) for x, y, z in seam_points
        ])
        for seam_points in result.get("stitch_seams", [])
    ]
    stitch_seam_labels = result.get("stitch_seam_labels", [])

    mesh_points = []
    for x, y, z in result["smooth_points"]:
        point = rg.Point3d(x, y, z)
        mesh_points.append(point)
        surface.Vertices.Add(point)

    display_rows = result.get(
        "wind_chime_row_indices",
        result.get("display_row_indices", result["smooth_row_indices"]),
    )
    for indices in display_rows:
        if "m_ratio" in result:
            row_points = [
                rg.Point3d(
                    result["wind_chime_points"][index][0],
                    result["wind_chime_points"][index][1],
                    result["wind_chime_points"][index][2],
                )
                for index in indices
            ]
        else:
            row_points = [mesh_points[index] for index in indices]
        if len(row_points) > 1:
            row_curves.append(rg.PolylineCurve(row_points))

    if "axis_points" in result:
        axis = rg.PolylineCurve([
            rg.Point3d(x, y, z) for x, y, z in result["axis_points"]
        ])
    elif row_curves:
        axis = row_curves[0]

    for face in result["smooth_faces"]:
        if len(face) == 3:
            surface.Faces.AddFace(face[0], face[1], face[2])
        else:
            surface.Faces.AddFace(face[0], face[1], face[2], face[3])

    surface.Normals.ComputeNormals()
    surface.Compact()
    intersection = None
    if "m_ratio" not in result:
        tolerance = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
        intersection = find_self_intersection(surface, tolerance)
    if intersection:
        message = "Surface self-intersection detected between mesh faces {} and {}.".format(
            intersection[0], intersection[1]
        )
        ghenv.Component.AddRuntimeMessage(
            gh.GH_RuntimeMessageLevel.Error, message
        )
        info = message
    else:
        info = (
            "stitches per row: {}\nturns: {}\nsurface samples per row: "
            "{}\nvisible surface faces: {}\nwind-chime faces: {}\n"
            "crochet stitch lengths: {}\ncrochet stitch patterns: {}"
            "\nrow path lengths: {}\nM ratio: {}\nmaximum width: {}"
        ).format(
            result["counts"], result["turns"],
            len(display_rows[0]) if display_rows else 0,
            surface.Faces.Count,
            wind_chime.Faces.Count,
            result["crochet_stitch_lengths"],
            result["crochet_stitch_patterns"], result["row_path_lengths"],
            result.get("m_ratio", "legacy"),
            result.get("max_width", "legacy")
        )

if not isinstance(base_point_input, rg.Point3d):
    raise TypeError("base_point must be a Rhino Point3d.")

translation = rg.Transform.Translation(
    base_point_input - rg.Point3d.Origin
)
geometries_to_translate = [
    ("surface", surface),
    ("wind_chime", wind_chime),
    ("spiral", spiral),
    ("axis", axis),
]
geometries_to_translate.extend(
    ("row_curve_{}".format(index), geometry)
    for index, geometry in enumerate(row_curves)
)
geometries_to_translate.extend(
    ("stitch_seam_{}".format(index), geometry)
    for index, geometry in enumerate(stitch_seams)
)
for name, geometry in geometries_to_translate:
    if geometry is None:
        continue
    if isinstance(geometry, rg.Mesh) and geometry.Vertices.Count == 0:
        continue
    if not geometry.Transform(translation):
        raise RuntimeError(
            "Could not translate {} to the requested base_point.".format(name)
        )
