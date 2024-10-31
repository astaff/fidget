
from fidget.ops import (
    add_hole,
    add_holes,
    align_gear,
    align_gears_vertically,
    apply_shape,
    arrange_meshes,
    build_core,
    build_gear,
    build_pin,
    build_shape,
    rotate_gear,
)
from fidget.types import (
    GearConfig,
    PinConfig,
    PrintLayoutConfig,
    ShapeConfig,
    ShapeType,
)


def test_fidget_gear_cube() -> None:
    rotation_angles = [27, 17, 7, -3, -3, 7, 17, 27]
    core_diameter = 35.0

    core = build_core(diameter=core_diameter)
    gear_config = GearConfig(profile="./assets/gear.svg", base_diameter=24.0, height=500.0, angle=5.7)

    def process_gear(gear_config, face, angle):
        gear = build_gear(gear_config)
        aligned_gear = align_gear(gear, face, 0)
        return rotate_gear(aligned_gear, face, angle)

    gears = [process_gear(gear_config, face, angle) 
            for angle, face in zip(rotation_angles, core.faces)]


    shape_config = ShapeConfig(shape_type=ShapeType.CUBE, size=[40.0, 40.0, 40.0])
    shape = build_shape(shape_config)

    cut_gears = apply_shape(shape, gears)

    pin = build_pin(PinConfig(diameter=6.0, length=12.0))
    core_with_holes = add_holes(core, pin, 1.05)

    cut_gears_with_holes = [add_hole(gear, face, pin, 1.05) for gear, face in zip(cut_gears, core.faces)]
    arranged_gears = arrange_meshes(align_gears_vertically(cut_gears_with_holes, core.faces), PrintLayoutConfig(row_spacing=35, col_spacing=35, rows=3, cols=3))
    pins = arrange_meshes([pin.pin_mesh.copy() for _ in range(8)], PrintLayoutConfig(row_spacing=23, col_spacing=10, rows=3, cols=3))

    assert all(gear.is_watertight for gear in arranged_gears)
    assert all(gear.volume > 0 for gear in arranged_gears)

    assert all(pin.is_watertight for pin in pins)
    assert all(pin.volume > 0 for pin in pins)

    assert core_with_holes.mesh.is_watertight
    assert core_with_holes.mesh.volume > 0
