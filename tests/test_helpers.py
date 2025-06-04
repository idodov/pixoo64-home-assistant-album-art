import ast
import os
import pathlib
import sys
from typing import List, Optional, Tuple

import pytest

# Load only the relevant helper functions from the source file without executing
# the entire module (which requires Home Assistant and Pillow dependencies).
MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "pixoo64_album_art" / "helpers.py"
source = MODULE_PATH.read_text()
module_ast = ast.parse(source)

globals_dict = {
    "logging": __import__("logging"),
    "Optional": Optional,
    "List": List,
    "Tuple": Tuple,
    "_LOGGER": __import__("logging").getLogger("test"),
}

for node in module_ast.body:
    if isinstance(node, ast.FunctionDef) and node.name in {"hex_to_rgb_list", "rgb_to_hex"}:
        code = ast.Module(body=[node], type_ignores=[])
        exec(compile(code, filename=str(MODULE_PATH), mode="exec"), globals_dict)

hex_to_rgb_list = globals_dict["hex_to_rgb_list"]
rgb_to_hex = globals_dict["rgb_to_hex"]


# Tests for hex_to_rgb_list
@pytest.mark.parametrize(
    "hex_str,expected",
    [
        ("#FFFFFF", [255, 255, 255]),
        ("#000000", [0, 0, 0]),
        ("#123456", [18, 52, 86]),
        ("#abc", [170, 187, 204]),
    ],
)
def test_hex_to_rgb_list_valid(hex_str, expected):
    assert hex_to_rgb_list(hex_str) == expected

@pytest.mark.parametrize(
    "hex_str",
    [None, "", "123456", "#12", "#1234", "#ZZZZZZ"]
)
def test_hex_to_rgb_list_invalid(hex_str):
    assert hex_to_rgb_list(hex_str) == [0, 0, 0]

# Tests for rgb_to_hex
@pytest.mark.parametrize(
    "rgb,expected",
    [
        ((255, 255, 255), "#ffffff"),
        ((0, 0, 0), "#000000"),
        ((256, -1, 1000), "#ff00ff"),
    ],
)
def test_rgb_to_hex_valid(rgb, expected):
    assert rgb_to_hex(rgb) == expected

@pytest.mark.parametrize(
    "rgb",
    [[255, 0, 0], (255, 0), "not a tuple", ("a", 0, 0)]
)
def test_rgb_to_hex_invalid(rgb):
    assert rgb_to_hex(rgb) == "#000000"
