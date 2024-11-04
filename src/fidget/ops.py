from typing import List

import numpy as np
import trimesh

from fidget.types import (
    Core,
    Face,
    Gear,
    GearConfig,
    Pin,
    PinConfig,
    PrintLayoutConfig,
    Shape,
    ShapeConfig,
    ShapeType,
)


def build_core(diameter: float) -> Core:
    cube = trimesh.creation.box(extents=[diameter, diameter, diameter])
    cube.apply_translation(-cube.centroid)

    octahedron_radius = np.sqrt(2) * (diameter / 2.0)

    # Create vertices of the octahedron
    vertices = np.array([
        [octahedron_radius, 0, 0], [-octahedron_radius, 0, 0],
        [0, octahedron_radius, 0], [0, -octahedron_radius, 0],
        [0, 0, octahedron_radius], [0, 0, -octahedron_radius]
    ])
    
    # Define faces of the octahedron
    octahedron_faces = np.array([
        [0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2],
        [1, 4, 2], [1, 3, 4], [1, 5, 3], [1, 2, 5]
    ])
    
    # Create the mesh
    octahedron = trimesh.Trimesh(vertices=vertices, faces=octahedron_faces)
    octahedron.apply_translation(-octahedron.centroid)

    def calculate_face_origin(vertices):
        return tuple(np.mean(vertices, axis=0))

    face_origins = [calculate_face_origin(octahedron.vertices[face]) for face in octahedron.faces]
    faces = [Face(normal=normal, origin=origin) for normal, origin in zip(octahedron.face_normals, face_origins)]
    
    return Core(mesh=trimesh.boolean.intersection([octahedron, cube]), faces=faces)


def build_pin(config: PinConfig) -> Pin:
    def get_profile(is_outer: bool) -> list[tuple[float, float]]:
        profiles = {
            True: [
                (2.5, 0), (2.5, 1.25), (5, 2.5), (10, 3.5),
                (11, 2.75), (11+config.center_length, 2.75), (12+config.center_length, 3.5), (17+config.center_length, 2.5),
                (19.5+config.center_length, 1.25), (19.5+config.center_length, 0)
            ],
            False: [
                (4, 0), (6, 1), (16+config.center_length, 1), (18+config.center_length, 0),
                (16+config.center_length, -1), (6, -1), (4, 0)
            ]
        }
        return [(y, x) for x, y in profiles[is_outer]]

    def create_mesh(path: list[tuple[float, float]], revolve: bool = True) -> trimesh.Trimesh:
        if revolve:
            return trimesh.creation.revolve(path, sections=256, angle=2*np.pi)
        
        vertices = np.array(path)
        entities = [trimesh.path.entities.Line([i, (i + 1) % len(path)]) 
                   for i in range(len(path))]
        path_2d = trimesh.path.Path2D(vertices=vertices, entities=entities)
        return trimesh.creation.extrude_polygon(path_2d.polygons_full[0], height=1024.0)

    def center_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        mesh.vertices -= mesh.center_mass
        return mesh

    # Create outer pin shape
    pin_outer = create_mesh(get_profile(True))
    cylinder = pin_outer.bounding_cylinder
    
    # Create and align box for flat side
    box = trimesh.creation.box(extents=[
        cylinder.primitive.radius * 2,
        cylinder.primitive.radius,
        cylinder.primitive.height
    ])
    box.vertices -= box.center_mass
    box.apply_transform(cylinder.primitive.transform)
    
    # Create flat pin and center cut
    flat_pin = center_mesh(trimesh.boolean.intersection([box, pin_outer]))
    center_cut = center_mesh(create_mesh(get_profile(False), revolve=False))
    pin_outer = center_mesh(pin_outer)

    # Rotate and cut final pin
    rotation = trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0])
    center_cut.apply_transform(rotation)
    final_pin = trimesh.boolean.difference([flat_pin, center_cut])
    final_pin.apply_transform(rotation)

    return Pin(round_mesh=pin_outer, flat_mesh=flat_pin, pin_mesh=final_pin)


def build_gear(config: GearConfig) -> Gear:
    path = trimesh.load_path(config.profile)

    # Create the 3D mesh by extruding the path
    gear = trimesh.creation.extrude_polygon(
        polygon=path.polygons_full[0],
        height=config.height
    )

    bounds = trimesh.bounds.minimum_cylinder(gear)

    bottom_diameter = bounds["radius"] * 2
    top_diameter = bottom_diameter + 2 * config.height * np.tan(np.radians(90 - config.angle))

    for i, vertex in enumerate(gear.vertices):
        _, _, z = vertex
        scale = 1 + z / config.height * (top_diameter / bottom_diameter - 1)
        gear.vertices[i, 0] *= scale
        gear.vertices[i, 1] *= scale

    xy_scale = config.base_diameter / bottom_diameter
    transform = np.array([
        [xy_scale, 0, 0, 0],
        [0, xy_scale, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    gear.apply_transform(transform)
    
    return gear


def build_shape(config: ShapeConfig) -> Shape:
    def create_centered_shape(shape):
        shape.apply_translation(-shape.centroid)
        # Convert polar angles to rotation matrix using Euler angles
        rotation_matrix = trimesh.transformations.euler_matrix(
            config.rotation[0],  # phi (azimuthal)
            config.rotation[1],  # theta (polar) 
            config.rotation[2],  # psi (roll)
            'rxyz'
        )
        shape.apply_transform(rotation_matrix)
        scale_matrix = np.array([
            [config.scale[0], 0, 0, 0],
            [0, config.scale[1], 0, 0],
            [0, 0, config.scale[2], 0],
            [0, 0, 0, 1]
        ])
        shape.apply_transform(scale_matrix)
        shape.apply_translation(config.offset)
        return shape

    if config.shape_type == ShapeType.CUSTOM:
        if config.stl_path is None:
            raise ValueError("STL path is required for custom shape")
        return create_centered_shape(trimesh.load_mesh(str(config.stl_path)))

    if config.shape_type == ShapeType.CUBE:
        return create_centered_shape(trimesh.creation.box(extents=config.size))
    elif config.shape_type == ShapeType.SPHERE:
        return create_centered_shape(trimesh.creation.icosphere(radius=config.radius))
    elif config.shape_type == ShapeType.CYLINDER:
        return create_centered_shape(trimesh.creation.cylinder(radius=config.radius, height=config.height))
    else:
        raise ValueError(f"Unsupported shape type: {config.shape_type}")


def add_holes(core: Core, pin: Pin, scale: float) -> Core:
    mesh = core.mesh.copy()

    for face in core.faces:
        new_pin = pin.flat_mesh.copy()
        rotation_matrix = trimesh.geometry.align_vectors([0, 0, 1], face.normal)
        new_pin.apply_transform(rotation_matrix)
        new_pin.apply_translation(face.origin)
        new_pin.apply_scale(scale)
        mesh = trimesh.boolean.difference([mesh, new_pin])

    return Core(mesh=mesh, faces=core.faces)


def add_hole(gear: Gear, face: Face, pin: Pin, scale: float) -> Gear:
    new_pin = pin.round_mesh.copy()
    rotation_matrix = trimesh.geometry.align_vectors([0, 0, 1], face.normal)
    new_pin.apply_transform(rotation_matrix)
    new_pin.apply_translation(face.origin)
    new_pin.apply_scale(scale)
    return trimesh.boolean.difference([gear, new_pin])


def rotate_gear(gear: Gear, face: Face, angle: float) -> Gear:
    gear = gear.copy()

    rotation_matrix = trimesh.transformations.rotation_matrix(
        angle=np.radians(angle),
        direction=face.normal,
        point=face.origin
    )
    
    gear.apply_transform(rotation_matrix)

    return gear


def align_gear(gear: Gear, face: Face, offset: float) -> Gear:
    gear = gear.copy()

    # Calculate the rotation matrix to align the gear with the face normal
    rotation_matrix = trimesh.geometry.align_vectors([0, 0, 1], face.normal)
    
    # Apply the rotation to the gear
    gear.apply_transform(rotation_matrix)
    
    # Translate the gear to the face origin plus the offset along the normal
    translation = np.array(face.origin) + np.array(face.normal) * offset
    gear.apply_translation(translation)
    
    return gear


def align_gears_vertically(gears: List[Gear], faces: List[Face]) -> List[Gear]:
    return [
        gear.copy().apply_transform(trimesh.geometry.align_vectors(face.normal, [0, 0, 1]))
        for gear, face in zip(gears, faces)
    ]


def arrange_meshes(meshes: List[trimesh.Trimesh], config: PrintLayoutConfig) -> List[trimesh.Trimesh]:
    positions = [
        (col * config.col_spacing, row * config.row_spacing)
        for idx, _ in enumerate(meshes)
        for row, col in [(idx // config.cols, idx % config.cols)]
    ]
    
    return [
        mesh.copy().apply_transform(trimesh.transformations.translation_matrix([x, y, 0]))
        for mesh, (x, y) in zip(meshes, positions)
    ]


def apply_shape(shape: Shape, gears: List[Gear]) -> List[Gear]:
    return [trimesh.boolean.intersection([gear, shape]) for gear in gears]
