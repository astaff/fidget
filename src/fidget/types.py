from enum import Enum
from pathlib import Path
from typing import List, Tuple, Union

import trimesh
from pydantic import BaseModel, Field


class PinConfig(BaseModel):
    length: float
    diameter: float

class PrintLayoutConfig(BaseModel):
    row_spacing: float
    col_spacing: float
    rows: int
    cols: int

class GearConfig(BaseModel):
    profile: Path | str
    base_diameter: float
    height: float
    angle: float

class ShapeType(Enum):
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    CUSTOM = "custom"

class ShapeConfig(BaseModel):
    shape_type: ShapeType
    size: Union[float, Tuple[float, float, float]] = Field(default=1.0, description="Size for cube or cylinder")
    radius: float = Field(default=1.0, description="Radius for sphere or cylinder")
    height: float = Field(default=1.0, description="Height for cylinder")
    stl_path: Union[str, Path, None] = Field(default=None, description="Path to STL file for custom shape")
    offset: Tuple[float, float, float] = Field(default=(0, 0, 0), description="Offset for shape")
    rotation: Tuple[float, float, float] = Field(default=(0, 0, 0), description="Rotation for shape")
    scale: float = Field(default=1.0, description="Scale for shape")

class FidgetConfig(BaseModel):
    core_diameter: float
    gear: GearConfig
    pin: PinConfig
    gear_rotations: List[float]
    hole_scale: float
    shape: ShapeConfig

class Face(BaseModel):
    normal: Tuple[float, float, float]
    origin: Tuple[float, float, float]

class Core(BaseModel):
    mesh: trimesh.Trimesh = Field(description="Core mesh")
    faces: List[Face] = Field(description="Core faces")

    model_config = {
        "arbitrary_types_allowed": True
    }

class Pin(BaseModel):
    round_mesh: trimesh.Trimesh = Field(description="Round mesh")
    flat_mesh: trimesh.Trimesh = Field(description="Flat mesh")
    pin_mesh: trimesh.Trimesh = Field(description="Pin mesh")

    model_config = {
        "arbitrary_types_allowed": True
    }

# Type aliases for geometric primitives
Gear = trimesh.Trimesh
Shape = trimesh.Trimesh
