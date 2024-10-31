
import fidget as F
from fidget.types import Core, Gear, GearConfig


def test_build_core() -> None:
    core = F.build_core(diameter=1000.0)
    assert core is not None

    # Basic assertions
    assert isinstance(core, Core)
    assert core.mesh.is_watertight
    assert core.mesh.volume > 0


def test_build_gear() -> None:
    config = GearConfig(profile="./assets/gear.svg", base_diameter=100, height=50, angle=135)
    gear = F.build_gear(config)
    assert gear is not None

    assert isinstance(gear, Gear)
    assert gear.is_watertight
    assert gear.volume > 0