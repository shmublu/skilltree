import math
import random
import json
import matplotlib
import matplotlib.pyplot as plt

# Disable interactive mode and set backend for consistency.
plt.ioff()
matplotlib.use("Agg", force=True)

##############################################################################
# Unique ID Generator
##############################################################################
class UniqueIDGenerator:
    counters = {}

    @staticmethod
    def get_unique_id(alias):
        if alias not in UniqueIDGenerator.counters:
            UniqueIDGenerator.counters[alias] = 0
        this_id = UniqueIDGenerator.counters[alias]
        UniqueIDGenerator.counters[alias] += 1
        return this_id

    @staticmethod
    def reset_counters():
        UniqueIDGenerator.counters.clear()

##############################################################################
# Base PlotObject with transformation and bounding-box support
##############################################################################
class PlotObject:
    ALIAS = "PlotObject"

    def __init__(self):
        self.obj_id = UniqueIDGenerator.get_unique_id(self.ALIAS)
        self.sub_references = []

    def assign_geometry(self):
        for child in self.sub_references:
            child.assign_geometry()

    def perform_skills(self, verbose=False):
        # Default: simply collect child skills trees.
        children = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        tree = {"action": "Base", "object": f"{self.ALIAS}#{self.obj_id}", "children": children}
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        for child in self.sub_references:
            child.render(ax)

    def __repr__(self):
        return f"{self.ALIAS}#{self.obj_id}"

    def set_bottom_left(self, x, y, angle=0, **kwargs):
        # To be overridden by subclasses.
        pass

    # Export object structure as a JSON–serializable dict.
    def to_dict(self):
        def make_serializable(value):
            if isinstance(value, (int, float, str, bool)) or value is None:
                return value
            elif isinstance(value, (list, tuple)):
                return [make_serializable(v) for v in value]
            elif isinstance(value, dict):
                return {k: make_serializable(v) for k, v in value.items()}
            elif isinstance(value, PlotObject):
                return value.to_dict()
            else:
                return str(value)
        data = {"type": self.ALIAS, "obj_id": self.obj_id, "attributes": {}}
        for key, value in self.__dict__.items():
            if key.startswith("_") or key == "sub_references":
                continue
            data["attributes"][key] = make_serializable(value)
        if self.sub_references:
            data["children"] = [child.to_dict() for child in self.sub_references]
        return data

    # Recursively apply an affine transformation function to all coordinate attributes.
    def apply_transformation(self, func):
        for attr in ['p1', 'p2', 'center', 'base_position']:
            if hasattr(self, attr):
                value = getattr(self, attr)
                if value is not None and isinstance(value, tuple) and len(value) == 2:
                    setattr(self, attr, func(value))
        if hasattr(self, 'vertices') and self.vertices is not None:
            self.vertices = [func(v) if v is not None else None for v in self.vertices]
        for child in self.sub_references:
            child.apply_transformation(func)

    # Return a bounding box (min_x, min_y, max_x, max_y).
    def get_bbox(self):
        if hasattr(self, 'p1') and hasattr(self, 'p2'):
            return (min(self.p1[0], self.p2[0]),
                    min(self.p1[1], self.p2[1]),
                    max(self.p1[0], self.p2[0]),
                    max(self.p1[1], self.p2[1]))
        if hasattr(self, 'center') and hasattr(self, 'width') and hasattr(self, 'height'):
            return (self.center[0] - self.width/2, self.center[1] - self.height/2,
                    self.center[0] + self.width/2, self.center[1] + self.height/2)
        if hasattr(self, 'vertices') and self.vertices:
            xs = [v[0] for v in self.vertices if v is not None]
            ys = [v[1] for v in self.vertices if v is not None]
            return (min(xs), min(ys), max(xs), max(ys))
        bboxes = [child.get_bbox() for child in self.sub_references if hasattr(child, "get_bbox")]
        if bboxes:
            return (min(b[0] for b in bboxes),
                    min(b[1] for b in bboxes),
                    max(b[2] for b in bboxes),
                    max(b[3] for b in bboxes))
        return (0, 0, 0, 0)

##############################################################################
# Helper functions for angle comparisons and checks
##############################################################################
def angle_difference(a, b):
    diff = abs(a - b) % 360
    if diff > 180:
        diff = 360 - diff
    return diff

def is_arrow_pointing_direction(arrow, target_direction, tol=5):
    direction_angles = {"upward": 90, "downward": 270, "leftward": 180, "rightward": 0}
    target_angle = direction_angles[target_direction]
    return angle_difference(arrow.angle, target_angle) <= tol

def are_lines_parallel(line1, line2, tol=5):
    from .utilities import get_line_length_and_angle
    _, a1 = get_line_length_and_angle(line1.p1, line1.p2)
    _, a2 = get_line_length_and_angle(line2.p1, line2.p2)
    return angle_difference(a1, a2) <= tol

def are_lines_perpendicular(line1, line2, tol=5):
    from .utilities import get_line_length_and_angle
    _, a1 = get_line_length_and_angle(line1.p1, line1.p2)
    _, a2 = get_line_length_and_angle(line2.p1, line2.p2)
    return abs(angle_difference(a1, a2) - 90) <= tol


def skills_tree_to_text(tree, indent=0):
    """
    Recursively convert a skills tree (a dict) into a list of text lines.
    Each node should have keys:
      - "action": the skill action (e.g. "RecognizeInstanceLine")
      - "object": the object ID (e.g. "Line#3")
      - "details": optional extra details (e.g. "(Endpoints: (x,y), (x2,y2))")
      - "children": a list of child nodes
    """
    lines = []
    prefix = " " * indent
    line = prefix + tree.get("action", "")
    if "object" in tree:
        line += " => " + tree["object"]
    if "details" in tree:
        line += " " + tree["details"]
    lines.append(line)
    for child in tree.get("children", []):
        lines.extend(skills_tree_to_text(child, indent=indent+2))
    return lines
