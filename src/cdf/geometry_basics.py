"""
Geometry basics -- reusable Rhino.Geometry functions for Grasshopper.

Adding a new function with Copilot
-----------------------------------
1. Open this file and select this chat model, then ask Copilot something like:
   "Add a function here, all in Rhino geometry, that builds a <your shape/idea>.
   Follow the same style as create_cone / create_fractal_tree (defaults for
   optional inputs, a docstring listing params, return a Rhino.Geometry object)."
2. Once the function is added, ask Copilot:
   "Give me the Python code to use this function in a Grasshopper GHPython 3
   component, importing it from computational_design_and_fabrication."
3. Copy the snippet Copilot gives you into a GHPython component, wire up the
   inputs as sliders/panels, and set the output variable (e.g. `a`).
"""

import math
import Rhino.Geometry as rg

def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
    """
    Build a cone as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cone's base circle
    height     : float -- cone height along the base plane's normal (Z by default)
    radius     : float -- base circle radius
    cap_bottom : bool  -- whether to cap the base circle (closed vs open cone)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

def create_sphere(center_point=None, radius=5.0):
    """
    Build a sphere as a Brep.

    center_point : Rhino.Geometry.Point3d -- center of the sphere (origin by default)
    radius       : float -- sphere radius

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    if radius <= 0:
        raise ValueError("radius must be positive.")

    sphere = rg.Sphere(center_point, radius)
    return sphere.ToBrep()

def boolean_difference(brep_a, brep_b):
    """
    Subtract one or more Breps from a base Brep.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep or list[Rhino.Geometry.Brep] -- Brep(s) to subtract

    Returns a list of Rhino.Geometry.Brep resulting from the difference.
    """
    if brep_a is None or brep_b is None:
        raise ValueError("brep_a and at least one brep_b must be provided.")

    breps_b = [brep_b] if isinstance(brep_b, rg.Brep) else list(brep_b)
    if not breps_b or any(brep is None for brep in breps_b):
        raise ValueError("brep_b must contain at least one valid Brep.")

    result = rg.Brep.CreateBooleanDifference([brep_a], breps_b, 0.001)
    return result


def boolean_union(breps, tolerance=0.001):
    """
    Join overlapping or touching Breps into their Boolean union.

    breps     : Rhino.Geometry.Brep or list[Rhino.Geometry.Brep] -- Breps to union
    tolerance : float -- Rhino model tolerance for the Boolean operation

    Returns a list of Rhino.Geometry.Brep results.
    """
    if breps is None:
        raise ValueError("At least two Breps must be provided.")

    brep_list = [breps] if isinstance(breps, rg.Brep) else list(breps)
    if len(brep_list) < 2 or any(brep is None for brep in brep_list):
        raise ValueError("At least two valid Breps must be provided.")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive.")

    result = rg.Brep.CreateBooleanUnion(brep_list, tolerance)
    if not result:
        raise RuntimeError("Could not create the Boolean union.")
    return result


def create_box(center_point=None, width=10.0, depth=10.0, height=10.0):
    """
    Build a box as a Brep.

    center_point : Rhino.Geometry.Point3d -- center of the box (origin by default)
    width        : float -- box width along the X axis
    depth        : float -- box depth along the Y axis
    height       : float -- box height along the Z axis

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    if width <= 0 or depth <= 0 or height <= 0:
        raise ValueError("width, depth, and height must be positive.")

    corner1 = rg.Point3d(center_point.X - width / 2, center_point.Y - depth / 2, center_point.Z - height / 2)
    corner2 = rg.Point3d(center_point.X + width / 2, center_point.Y + depth / 2, center_point.Z + height / 2)
    box = rg.Box(rg.BoundingBox(corner1, corner2))
    return box.ToBrep()


def create_staircase(base_point=None, step_count=5, width=5.0, step_depth=1.0, step_height=0.5):
    """
    Create a staircase from separate box-shaped steps rising along +Y and +Z.

    base_point : Rhino.Geometry.Point3d -- center of the first, lowest step
    step_count : int -- number of box steps
    width      : float -- width of each step along X
    step_depth : float -- depth of each step along Y
    step_height: float -- height of each step along Z

    Returns a list of Rhino.Geometry.Brep steps.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if step_count is None:
        step_count = 5
    if width is None:
        width = 5.0
    if step_depth is None:
        step_depth = 1.0
    if step_height is None:
        step_height = 0.5

    step_count = int(step_count)
    if step_count < 1:
        raise ValueError("step_count must be at least one.")
    if width <= 0 or step_depth <= 0 or step_height <= 0:
        raise ValueError("width, step_depth, and step_height must be positive.")

    first_step = create_box(
        center_point=base_point,
        width=width,
        depth=step_depth,
        height=step_height,
    )
    steps = [first_step]
    for index in range(1, step_count):
        step = first_step.DuplicateBrep()
        moved = step.Transform(
            rg.Transform.Translation(
                rg.Vector3d(0, step_depth * index, step_height * index)
            )
        )
        if not moved:
            raise RuntimeError("Could not move a copied staircase step.")
        steps.append(step)
    return steps


def create_solid_staircase(base_point=None, step_count=5, width=5.0, step_depth=1.0, step_height=0.5):
    """
    Create one solid staircase by extruding a closed stepped profile.

    base_point : Rhino.Geometry.Point3d -- front-left corner at the bottom of the stairs
    step_count : int -- number of steps
    width      : float -- staircase width along X
    step_depth : float -- depth of each tread along +Y
    step_height: float -- rise of each step along +Z

    Returns one capped Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if step_count is None:
        step_count = 5
    if width is None:
        width = 5.0
    if step_depth is None:
        step_depth = 1.0
    if step_height is None:
        step_height = 0.5

    step_count = int(step_count)
    if step_count < 1:
        raise ValueError("step_count must be at least one.")
    if width <= 0 or step_depth <= 0 or step_height <= 0:
        raise ValueError("width, step_depth, and step_height must be positive.")

    front_y = base_point.Y
    bottom_z = base_point.Z
    back_y = front_y + step_count * step_depth
    top_z = bottom_z + step_count * step_height
    profile_points_yz = [(front_y, bottom_z), (back_y, bottom_z), (back_y, top_z)]

    for level in range(step_count - 1, -1, -1):
        profile_points_yz.append((front_y + level * step_depth, bottom_z + (level + 1) * step_height))
        if level > 0:
            profile_points_yz.append((front_y + level * step_depth, bottom_z + level * step_height))
    profile_points_yz.append((front_y, bottom_z))

    profile_points = [
        rg.Point3d(base_point.X - width / 2, y, z)
        for y, z in profile_points_yz
    ]
    segments = [
        rg.LineCurve(profile_points[index], profile_points[index + 1])
        for index in range(len(profile_points) - 1)
    ]
    tolerance = 0.001
    joined_profile = rg.Curve.JoinCurves(segments, tolerance)
    if not joined_profile or len(joined_profile) != 1 or not joined_profile[0].IsClosed:
        raise RuntimeError("Could not create a closed staircase profile.")

    extruded_surface = rg.Surface.CreateExtrusion(
        joined_profile[0],
        rg.Vector3d(width, 0, 0),
    )
    if extruded_surface is None:
        raise RuntimeError("Could not extrude the staircase profile.")
    staircase = extruded_surface.ToBrep().CapPlanarHoles(tolerance)
    if staircase is None:
        raise RuntimeError("Could not cap the solid staircase.")
    return staircase


def create_helix(base_point=None, radius=2.0, height=10.0, turns=3.0, points_per_turn=24):
    """
    Create a smooth helical curve rising around the Z axis.

    base_point      : Rhino.Geometry.Point3d -- center of the helix at its base
    radius          : float -- distance from the helix to its central axis
    height          : float -- vertical rise from start to end
    turns           : float -- number of complete rotations
    points_per_turn : int -- sampling density used to create the smooth curve

    Returns a Rhino.Geometry.Curve.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if radius is None:
        radius = 2.0
    if height is None:
        height = 10.0
    if turns is None:
        turns = 3.0
    if points_per_turn is None:
        points_per_turn = 24

    if radius <= 0 or height <= 0 or turns <= 0:
        raise ValueError("radius, height, and turns must be positive.")
    points_per_turn = int(points_per_turn)
    if points_per_turn < 4:
        raise ValueError("points_per_turn must be at least 4.")

    sample_count = max(4, int(math.ceil(turns * points_per_turn)))
    points = []
    for index in range(sample_count + 1):
        fraction = float(index) / sample_count
        angle = 2 * math.pi * turns * fraction
        points.append(
            rg.Point3d(
                base_point.X + radius * math.cos(angle),
                base_point.Y + radius * math.sin(angle),
                base_point.Z + height * fraction,
            )
        )

    helix = rg.Curve.CreateInterpolatedCurve(points, 3)
    if helix is None:
        raise RuntimeError("Could not create the interpolated helix curve.")
    return helix


def create_double_helix_surface(
    base_point=None,
    radius=2.0,
    height=10.0,
    turns=3.0,
    min_width=0.3,
    max_width=1.0,
    points_per_turn=24,
):
    """
    Create two lofted ribbon surfaces winding around the Z axis.

    The ribbons are offset by half a turn. Their width varies smoothly from
    min_width to max_width and back once per turn.

    base_point      : Rhino.Geometry.Point3d -- center of the helix at its base
    radius          : float -- distance from the helix axis to each ribbon center
    height          : float -- vertical rise from start to end
    turns           : float -- number of complete rotations
    min_width       : float -- narrowest ribbon width
    max_width       : float -- widest ribbon width
    points_per_turn : int -- number of loft sections per turn

    Returns a tuple of two Rhino.Geometry.Brep ribbon surfaces.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if radius is None:
        radius = 2.0
    if height is None:
        height = 10.0
    if turns is None:
        turns = 3.0
    if min_width is None:
        min_width = 0.3
    if max_width is None:
        max_width = 1.0
    if points_per_turn is None:
        points_per_turn = 24

    if radius <= 0 or height <= 0 or turns <= 0:
        raise ValueError("radius, height, and turns must be positive.")
    if min_width <= 0 or max_width < min_width:
        raise ValueError("widths must be positive and max_width must be at least min_width.")
    points_per_turn = int(points_per_turn)
    if points_per_turn < 4:
        raise ValueError("points_per_turn must be at least 4.")

    sample_count = max(4, int(math.ceil(turns * points_per_turn)))
    angular_speed = 2 * math.pi * turns
    vertical_speed = height / angular_speed
    surfaces = []

    for phase in (0.0, math.pi):
        sections = []
        for index in range(sample_count + 1):
            fraction = float(index) / sample_count
            angle = angular_speed * fraction + phase
            radial = rg.Vector3d(math.cos(angle), math.sin(angle), 0.0)
            center = rg.Point3d(
                base_point.X + radius * radial.X,
                base_point.Y + radius * radial.Y,
                base_point.Z + height * fraction,
            )
            tangent = rg.Vector3d(
                -radius * angular_speed * math.sin(angle),
                radius * angular_speed * math.cos(angle),
                vertical_speed,
            )
            width_direction = rg.Vector3d.CrossProduct(tangent, radial)
            if not width_direction.Unitize():
                raise RuntimeError("Could not calculate the ribbon width direction.")

            width_factor = 0.5 - 0.5 * math.cos(2 * math.pi * turns * fraction)
            ribbon_width = min_width + (max_width - min_width) * width_factor
            half_width = width_direction * (ribbon_width / 2)
            edge_a = center - half_width
            edge_b = center + half_width
            sections.append(rg.LineCurve(edge_a, edge_b))

        lofts = rg.Brep.CreateFromLoft(
            sections,
            rg.Point3d.Unset,
            rg.Point3d.Unset,
            rg.LoftType.Normal,
            False,
        )
        if not lofts or len(lofts) != 1 or lofts[0] is None:
            raise RuntimeError("Could not loft one of the double-helix ribbons.")
        surfaces.append(lofts[0])

    return surfaces[0], surfaces[1]


def create_cylinder(center_point=None, radius=5.0, height=10.0):
    """
    Build a capped cylinder as a Brep, aligned with the Z axis.

    center_point : Rhino.Geometry.Point3d -- center of the cylinder (origin by default)
    radius       : float -- cylinder radius
    height       : float -- cylinder height along the Z axis

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    if radius <= 0 or height <= 0:
        raise ValueError("radius and height must be positive.")

    base_point = center_point - rg.Vector3d(0, 0, height / 2)
    base_plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cylinder = rg.Cylinder(rg.Circle(base_plane, radius), height)
    return cylinder.ToBrep(True, True)




def copy_brep_along_z(brep, distance, copy_count):
    """
    Create copies of a Brep, each offset in the +Z direction.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by distance * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies

def create_arch(base_point=None, span=10.0, thickness=1.0, depth=2.0, leg_height=5.0):
    """
    Build a solid semicircular arch with vertical legs as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the arch's bottom edge
    span       : float -- overall width of the arch
    thickness  : float -- thickness of the arch ring and legs
    depth      : float -- extrusion depth along the +Y axis
    leg_height : float -- height of the vertical legs up to the spring line

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if span <= 0 or depth <= 0 or leg_height <= 0:
        raise ValueError("span, depth, and leg_height must be positive.")
    if thickness <= 0 or thickness >= span / 2:
        raise ValueError("thickness must be positive and less than half the span.")

    outer_radius = span / 2
    inner_radius = outer_radius - thickness
    y = base_point.Y
    base_z = base_point.Z
    spring_z = base_z + leg_height

    boundary = [
        rg.LineCurve(
            rg.Point3d(base_point.X - outer_radius, y, base_z),
            rg.Point3d(base_point.X - outer_radius, y, spring_z),
        ),
        rg.Arc(
            rg.Point3d(base_point.X - outer_radius, y, spring_z),
            rg.Point3d(base_point.X, y, spring_z + outer_radius),
            rg.Point3d(base_point.X + outer_radius, y, spring_z),
        ).ToNurbsCurve(),
        rg.LineCurve(
            rg.Point3d(base_point.X + outer_radius, y, spring_z),
            rg.Point3d(base_point.X + outer_radius, y, base_z),
        ),
        rg.LineCurve(
            rg.Point3d(base_point.X + outer_radius, y, base_z),
            rg.Point3d(base_point.X + inner_radius, y, base_z),
        ),
        rg.LineCurve(
            rg.Point3d(base_point.X + inner_radius, y, base_z),
            rg.Point3d(base_point.X + inner_radius, y, spring_z),
        ),
        rg.Arc(
            rg.Point3d(base_point.X + inner_radius, y, spring_z),
            rg.Point3d(base_point.X, y, spring_z + inner_radius),
            rg.Point3d(base_point.X - inner_radius, y, spring_z),
        ).ToNurbsCurve(),
        rg.LineCurve(
            rg.Point3d(base_point.X - inner_radius, y, spring_z),
            rg.Point3d(base_point.X - inner_radius, y, base_z),
        ),
        rg.LineCurve(
            rg.Point3d(base_point.X - inner_radius, y, base_z),
            rg.Point3d(base_point.X - outer_radius, y, base_z),
        ),
    ]
    tolerance = 0.001
    joined_boundary = rg.Curve.JoinCurves(boundary, tolerance)
    if not joined_boundary or len(joined_boundary) != 1 or not joined_boundary[0].IsClosed:
        raise RuntimeError("Could not create a closed arch profile.")

    extruded_surface = rg.Surface.CreateExtrusion(
        joined_boundary[0],
        rg.Vector3d(0, depth, 0),
    )
    if extruded_surface is None:
        raise RuntimeError("Could not extrude the arch profile.")
    arch = extruded_surface.ToBrep().CapPlanarHoles(tolerance)
    if arch is None:
        raise RuntimeError("Could not cap the extruded arch.")
    return arch


def create_arch_module(base_point=None, span=10.0, thickness=1.0, depth=2.0, leg_height=5.0, lintel_height=1.0):
    """
    Build a rectangular wall module with a semicircular opening and flat top.

    base_point : Rhino.Geometry.Point3d -- center of the module's bottom edge
    span       : float -- overall width of the wall module
    thickness  : float -- thickness of the side walls around the opening
    depth      : float -- extrusion depth along the +Y axis
    leg_height : float -- height of the straight sides of the opening
    lintel_height : float -- wall height above the outer arch crown

    Returns a Rhino.Geometry.Brep.

    To control the lintel with a Grasshopper input named ``lintel_height``,
    call ``create_arch_module(lintel_height=lintel_height)`` in the component.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if lintel_height is None:
        lintel_height = 1.0
    if span <= 0 or depth <= 0 or leg_height <= 0 or lintel_height <= 0:
        raise ValueError("span, depth, leg_height, and lintel_height must be positive.")
    if thickness <= 0 or thickness >= span / 2:
        raise ValueError("thickness must be positive and less than half the span.")

    opening_radius = span / 2 - thickness
    tolerance = 0.001
    y = base_point.Y - tolerance
    base_z = base_point.Z
    spring_z = base_z + leg_height
    opening_left = rg.Point3d(base_point.X - opening_radius, y, base_z - tolerance)
    opening_spring_left = rg.Point3d(base_point.X - opening_radius, y, spring_z)
    opening_crown = rg.Point3d(base_point.X, y, spring_z + opening_radius)
    opening_spring_right = rg.Point3d(base_point.X + opening_radius, y, spring_z)
    opening_right = rg.Point3d(base_point.X + opening_radius, y, base_z - tolerance)

    boundary = [
        rg.LineCurve(opening_left, opening_spring_left),
        rg.Arc(opening_spring_left, opening_crown, opening_spring_right).ToNurbsCurve(),
        rg.LineCurve(opening_spring_right, opening_right),
        rg.LineCurve(opening_right, opening_left),
    ]
    joined_boundary = rg.Curve.JoinCurves(boundary, tolerance)
    if not joined_boundary or len(joined_boundary) != 1 or not joined_boundary[0].IsClosed:
        raise RuntimeError("Could not create a closed arch opening profile.")

    opening_surface = rg.Surface.CreateExtrusion(
        joined_boundary[0],
        rg.Vector3d(0, depth + 2 * tolerance, 0),
    )
    if opening_surface is None:
        raise RuntimeError("Could not extrude the arch opening profile.")
    opening = opening_surface.ToBrep().CapPlanarHoles(tolerance)
    if opening is None:
        raise RuntimeError("Could not cap the arch opening cutter.")

    module_height = leg_height + span / 2 + lintel_height
    module_center = rg.Point3d(
        base_point.X,
        base_point.Y + depth / 2,
        base_z + module_height / 2,
    )
    module = create_box(module_center, width=span, depth=depth, height=module_height)
    result = rg.Brep.CreateBooleanDifference([module], [opening], tolerance)
    if not result or len(result) != 1:
        raise RuntimeError("Could not cut the semicircular opening from the wall module.")
    return result[0]


def create_arch_boolean_parts(
    base_point=None,
    opening_span=6.0,
    thickness=1.0,
    depth=2.0,
    leg_height=5.0,
    lintel_height=2.0,
):
    """
    Create a rectangular block and a separate arched opening cutter.

    Connect the returned block to Boolean Difference A and the cutter to B.
    The opening cutter extends slightly beyond the block to ensure a through-cut.

    base_point    : Rhino.Geometry.Point3d -- center of the block's bottom face
    opening_span  : float -- clear width of the arched opening
    thickness     : float -- block material width on each side of the opening
    depth         : float -- block depth along the +Y axis
    leg_height    : float -- height of the straight sides of the opening
    lintel_height : float -- block material above the opening crown

    Returns (block, opening_cutter), both Rhino.Geometry.Brep objects.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if opening_span is None:
        opening_span = 6.0
    if thickness is None:
        thickness = 1.0
    if depth is None:
        depth = 2.0
    if leg_height is None:
        leg_height = 5.0
    if lintel_height is None:
        lintel_height = 2.0
    if opening_span <= 0 or thickness <= 0 or depth <= 0:
        raise ValueError("opening_span, thickness, and depth must be positive.")
    if leg_height <= 0 or lintel_height <= 0:
        raise ValueError("leg_height and lintel_height must be positive.")

    tolerance = 0.001
    radius = opening_span / 2
    block_width = opening_span + 2 * thickness
    block_height = leg_height + radius + lintel_height
    block_center = rg.Point3d(
        base_point.X,
        base_point.Y + depth / 2,
        base_point.Z + block_height / 2,
    )
    block_corner1 = rg.Point3d(
        block_center.X - block_width / 2,
        block_center.Y - depth / 2,
        block_center.Z - block_height / 2,
    )
    block_corner2 = rg.Point3d(
        block_center.X + block_width / 2,
        block_center.Y + depth / 2,
        block_center.Z + block_height / 2,
    )
    block = rg.Box(rg.BoundingBox(block_corner1, block_corner2)).ToBrep()

    front_y = base_point.Y - tolerance
    bottom_z = base_point.Z - tolerance
    spring_z = base_point.Z + leg_height
    left = rg.Point3d(base_point.X - radius, front_y, bottom_z)
    spring_left = rg.Point3d(base_point.X - radius, front_y, spring_z)
    crown = rg.Point3d(base_point.X, front_y, spring_z + radius)
    spring_right = rg.Point3d(base_point.X + radius, front_y, spring_z)
    right = rg.Point3d(base_point.X + radius, front_y, bottom_z)

    profile = [
        rg.LineCurve(left, spring_left),
        rg.Arc(spring_left, crown, spring_right).ToNurbsCurve(),
        rg.LineCurve(spring_right, right),
        rg.LineCurve(right, left),
    ]
    joined_profile = rg.Curve.JoinCurves(profile, tolerance)
    if not joined_profile or len(joined_profile) != 1 or not joined_profile[0].IsClosed:
        raise RuntimeError("Could not create a closed arch opening profile.")

    cutter_surface = rg.Surface.CreateExtrusion(
        joined_profile[0],
        rg.Vector3d(0, depth + 2 * tolerance, 0),
    )
    if cutter_surface is None:
        raise RuntimeError("Could not extrude the arch opening profile.")
    opening_cutter = cutter_surface.ToBrep().CapPlanarHoles(tolerance)
    if opening_cutter is None:
        raise RuntimeError("Could not cap the arch opening cutter.")

    return block, opening_cutter


def create_multi_arch_module(
    base_point=None,
    width=12.0,
    depth=8.0,
    opening_span=3.0,
    thickness=1.0,
    leg_height=5.0,
    lintel_height=1.0,
    front_openings=2,
    side_openings=1,
):
    """
    Build a rectangular module with repeated arched openings on front and side faces.

    base_point     : Rhino.Geometry.Point3d -- center of the module's bottom face
    width          : float -- module width along X
    depth          : float -- module depth along Y
    opening_span   : float -- clear width of each semicircular opening
    thickness      : float -- minimum pier and side-wall spacing between openings
    leg_height     : float -- straight height of each opening
    lintel_height  : float -- solid wall height above each opening crown
    front_openings : int -- number of openings across the front face
    side_openings  : int -- number of openings across each side face

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)
    if width is None:
        width = 12.0
    if depth is None:
        depth = 8.0
    if opening_span is None:
        opening_span = 3.0
    if thickness is None:
        thickness = 1.0
    if leg_height is None:
        leg_height = 5.0
    if lintel_height is None:
        lintel_height = 1.0
    if front_openings is None:
        front_openings = 2
    if side_openings is None:
        side_openings = 1
    if width <= 0 or depth <= 0 or opening_span <= 0:
        raise ValueError("width, depth, and opening_span must be positive.")
    if thickness <= 0 or leg_height <= 0 or lintel_height <= 0:
        raise ValueError("thickness, leg_height, and lintel_height must be positive.")
    if front_openings < 0 or side_openings < 0:
        raise ValueError("front_openings and side_openings must not be negative.")
    if front_openings == 0 and side_openings == 0:
        raise ValueError("At least one opening must be requested.")

    front_openings = int(front_openings)
    side_openings = int(side_openings)
    if front_openings * opening_span + (front_openings + 1) * thickness > width:
        raise ValueError("Front openings and piers do not fit within the module width.")
    if side_openings * opening_span + (side_openings + 1) * thickness > depth:
        raise ValueError("Side openings and piers do not fit within the module depth.")

    tolerance = 0.001
    radius = opening_span / 2
    base_z = base_point.Z
    spring_z = base_z + leg_height
    module_height = leg_height + radius + lintel_height
    module_center = rg.Point3d(
        base_point.X,
        base_point.Y + depth / 2,
        base_z + module_height / 2,
    )
    module = create_box(module_center, width=width, depth=depth, height=module_height)
    cutters = []

    def make_cutter(center, plane_axis):
        x, y = center
        if plane_axis == "front":
            left = rg.Point3d(x - radius, y, base_z - tolerance)
            spring_left = rg.Point3d(x - radius, y, spring_z)
            crown = rg.Point3d(x, y, spring_z + radius)
            spring_right = rg.Point3d(x + radius, y, spring_z)
            right = rg.Point3d(x + radius, y, base_z - tolerance)
            extrusion = rg.Vector3d(0, depth + 2 * tolerance, 0)
        else:
            left = rg.Point3d(x, y - radius, base_z - tolerance)
            spring_left = rg.Point3d(x, y - radius, spring_z)
            crown = rg.Point3d(x, y, spring_z + radius)
            spring_right = rg.Point3d(x, y + radius, spring_z)
            right = rg.Point3d(x, y + radius, base_z - tolerance)
            extrusion = rg.Vector3d(width + 2 * tolerance, 0, 0)

        profile = [
            rg.LineCurve(left, spring_left),
            rg.Arc(spring_left, crown, spring_right).ToNurbsCurve(),
            rg.LineCurve(spring_right, right),
            rg.LineCurve(right, left),
        ]
        joined = rg.Curve.JoinCurves(profile, tolerance)
        if not joined or len(joined) != 1 or not joined[0].IsClosed:
            raise RuntimeError("Could not create an arched opening profile.")
        surface = rg.Surface.CreateExtrusion(joined[0], extrusion)
        if surface is None:
            raise RuntimeError("Could not extrude an arched opening cutter.")
        cutter = surface.ToBrep().CapPlanarHoles(tolerance)
        if cutter is None:
            raise RuntimeError("Could not cap an arched opening cutter.")
        return cutter

    if front_openings:
        spacing = width / front_openings
        for index in range(front_openings):
            x = base_point.X - width / 2 + spacing * (index + 0.5)
            cutters.append(make_cutter((x, base_point.Y - tolerance), "front"))

    if side_openings:
        spacing = depth / side_openings
        side_x = base_point.X - width / 2 - tolerance
        for index in range(side_openings):
            y = base_point.Y + spacing * (index + 0.5)
            cutters.append(make_cutter((side_x, y), "side"))

    result = rg.Brep.CreateBooleanDifference([module], cutters, tolerance)
    if not result or len(result) != 1:
        raise RuntimeError("Could not cut the arched openings from the module.")
    return result[0]