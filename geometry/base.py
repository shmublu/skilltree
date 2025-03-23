import math
import random
import json
import matplotlib
import matplotlib.pyplot as plt
import re
from decimal import Decimal, ROUND_HALF_UP
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

def format_sig(x, sig):
    """
    Rounds the number x to 'sig' significant figures using ROUND_HALF_UP,
    and returns it as a string in fixed-point (non-exponential) notation.
    Trailing zeros and an unnecessary decimal point are removed.
    """
    if x == 0:
        return "0"
    exponent = int(math.floor(math.log10(abs(x))))
    digits = sig - exponent - 1
    quantize_str = "1." + "0" * max(digits, 0)
    rounded = Decimal(str(x)).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
    s = format(rounded, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def skills_tree_to_text(tree, indent=0, sigfigs=1):
    """
    Recursively converts a skills tree (a dict) into a list of text lines.
    Each node in the tree should have:
      - "action": e.g. "RecognizeInstanceLine"
      - "object": e.g. "Line#3"
      - "details": optional details (e.g. "(Endpoints: (x,y), (x2,y2))")
      - "children": a list of child nodes.
    This function replaces any number in 'details' with its rounded version using
    the specified number of significant figures.
    """
    lines = []
    prefix = " " * indent
    line = prefix + tree.get("action", "")
    if "object" in tree:
        line += " => " + tree["object"]
    if "details" in tree:
        details = tree["details"]
        def replace_number(match):
            try:
                num = float(match.group(0))
                return format_sig(num, sigfigs)
            except Exception:
                return match.group(0)
        details = re.sub(r"[-+]?\d*\.\d+|\d+", replace_number, details)
        line += " " + details
    lines.append(line)
    for child in tree.get("children", []):
        lines.extend(skills_tree_to_text(child, indent=indent+2, sigfigs=sigfigs))
    return lines

def count_low_level_nodes(tree, string):
    """
    Recursively count nodes whose action is either "RecognizeInstanceLine" or "RecognizeInstanceOval".
    """
    low_level_actions = {string}
    count = 0
    if tree.get("action", "") in low_level_actions:
        count += 1
    for child in tree.get("children", []):
        count += count_low_level_nodes(child, string)
    return count
def collapse_skills_tree_single_line(tree, sigfigs=1):
    """
    Consolidates a skills tree into one or more consolidated lines.
    
    For a given node:
      - Its header is derived from the "object" field (e.g. "Line#0" becomes "Line 0:")
      - If the node has children and its own details are empty, then it is considered “simple”
        and the details from its children are merged into one comma‑separated string.
        In this case, if a grouping detail (one that starts with "from") is found among the children,
        it is not appended to the header but later merged.
      - If the node’s own details are non‑empty (i.e. for composite objects such as an Arrow),
        then first the children’s consolidated lines are output (each on its own),
        and then the parent's consolidated line is appended.
    Numbers in details are formatted to the specified number of significant figures.
    The overall ordering is preserved: for composite objects the children appear first.
    """
    # Derive header from the node's "object" field.
    obj_field = tree.get("object", "").strip()
    if obj_field:
        if "#" in obj_field:
            obj_type, obj_num = obj_field.split("#", 1)
            header = f"{obj_type.strip()} {obj_num.strip()}:"
        else:
            header = f"{obj_field}:"
    else:
        header = ""
        
    # Function to format numbers in a details string.
    def format_details(text):
        def replace_number(match):
            try:
                num = float(match.group(0))
                return format_sig(num, sigfigs)
            except Exception:
                return match.group(0)
        return re.sub(r"[-+]?\d*\.\d+|\d+", replace_number, text)
    
    parent_details = tree.get("details", "").strip()
    parent_details = format_details(parent_details)
    
    # Recursively collapse children.
    child_lines = []
    for child in tree.get("children", []):
        child_lines.extend(collapse_skills_tree_single_line(child, sigfigs))
    
    # Helper to remove outer parentheses, if present.
    def strip_parentheses(detail):
        detail = detail.strip()
        if detail.startswith("(") and detail.endswith(")"):
            return detail[1:-1].strip()
        return detail

    if child_lines and not parent_details:
        grouping_detail = None
        other_details = []
        for line in child_lines:
            # Expect each line to be in "Header: (detail)" format.
            parts = line.split(":", 1)
            detail = parts[1].strip() if len(parts) == 2 else ""
            if detail.startswith("(") and detail.endswith(")"):
                detail = detail[1:-1].strip()
            if detail.lower().startswith("from"):
                grouping_detail = detail
            elif detail:
                stripped = strip_parentheses(detail)
                if stripped:
                    other_details.append(stripped)
        new_header = header.rstrip(":")
        # Build consolidated details: grouping (if any) comes first.
        details_list = []
        if grouping_detail:
            details_list.append(grouping_detail)
        details_list.extend(other_details)
        if details_list:
            consolidated = f"{new_header}: (" + ", ".join(details_list) + ")"
        else:
            consolidated = new_header + ":"
        return [consolidated]
    else:
        lines = []
        if child_lines:
            lines.extend(child_lines)
        # Changed here: always format parent's line as "Header: (details)" if details exist.
        if header or parent_details:
            if parent_details:
                lines.append(f"{header} ({parent_details})".strip())
            else:
                lines.append(header)
        return lines


def demo_question_count_objects(target_counts=None, outdir="demo_output/question_count_objects", canvas_size=(100,100), sigfigs=3, json_skill_graph=False):
    width, height = canvas_size
    canvas = (0, width, 0, height)
    
    # Decide whether to count one type or two types (ensuring two distinct types if chosen)
    if random.random() < 0.5:
        count_types = [random.choice(["Line", "Oval", "Rectangle", "Triangle", "Arrow"])]
    else:
        count_types = random.sample(["Line", "Oval", "Rectangle", "Triangle", "Arrow"], 2)
    
    # If no target_counts are provided, choose a random count (0 to 5) for each type.
    # target_counts is a dict mapping object type to count.
    if target_counts is None:
        target_counts = {}
        for t in count_types:
            target_counts[t] = random.randint(0, 5)
    
    # Build the plan so that create_scene is asked to create exactly the specified counts for each type.
    plan = {}
    for t in count_types:
        plan[t] = target_counts[t]
    
    scene, skill_output, skill_trees = create_scene(plan, canvas=canvas, avoid_types=[], sigfigs=sigfigs)
    
    # After scene creation, verify the scene contains the correct number of each object type.
    # Instead of raising an exception, update the target count if it differs.
    def count_objects(scene, obj_type):
        count = 0
        for obj in scene:
            if hasattr(obj, "ALIAS") and obj.ALIAS == obj_type:
                count += 1
            if hasattr(obj, "sub_references"):
                stack = list(obj.sub_references)
                while stack:
                    sub = stack.pop()
                    if hasattr(sub, "ALIAS") and sub.ALIAS == obj_type:
                        count += 1
                    if hasattr(sub, "sub_references"):
                        stack.extend(sub.sub_references)
        return count

    for t in count_types:
        actual_count = count_objects(scene, t)
        if actual_count != target_counts[t]:
            target_counts[t] = actual_count  # update to the actual count
    
    # Compose the question text and compute the final answer.
    if len(count_types) == 1:
        question_text = f"How many {count_types[0]}s are in the image?"
        final_answer = str(target_counts[count_types[0]])
    else:
        question_text = f"How many {count_types[0]}s and {count_types[1]}s are in the image?"
        final_answer = str(target_counts[count_types[0]] + target_counts[count_types[1]])
    
    display_and_save_scene(scene, outdir=outdir, question=question_text, reasoning=skill_output, final_answer=final_answer, canvas=canvas)
    if json_skill_graph:
        print("Skill Graph JSON:")
        print(json.dumps(skill_trees, indent=2))

