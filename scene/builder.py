import random
import math
from geometry import UniqueIDGenerator
from geometry.shapes import LineLow, OvalLow, RectangleObj, BarsObj, AxisObj, BarGraphObj, TriangleObj, PolygonObj, ArrowObj
from geometry.base import skills_tree_to_text, collapse_skills_tree_single_line, count_low_level_nodes


OBJECT_TYPES = {
    "Line": LineLow,
    "Oval": OvalLow,
    "Rectangle": RectangleObj,
    "Bars": BarsObj,
    "Axis": AxisObj,
    "BarGraph": BarGraphObj,
    "Triangle": TriangleObj,
    "Polygon": PolygonObj,
    "Arrow": ArrowObj,
}
import random
import math
from geometry import UniqueIDGenerator
from geometry.shapes import LineLow, OvalLow, RectangleObj, BarsObj, AxisObj, BarGraphObj, TriangleObj, PolygonObj, ArrowObj

def build_scene_from_plan(high_level_objects):
    scene = []
    for alias, spec in high_level_objects.items():
        cls_ = OBJECT_TYPES.get(alias, None)
        if cls_ is None:
            continue
        if isinstance(spec, int):
            for _ in range(spec):
                scene.append(cls_())
        elif isinstance(spec, list):
            for params in spec:
                scene.append(cls_(**params))
    return scene

def adjust_scene(scene, canvas=(0, 100, 0, 100)):
    all_bboxes = [obj.get_bbox() for obj in scene]
    if not all_bboxes:
        return
    global_min_x = min(b[0] for b in all_bboxes)
    global_min_y = min(b[1] for b in all_bboxes)
    global_max_x = max(b[2] for b in all_bboxes)
    global_max_y = max(b[3] for b in all_bboxes)
    scene_width = global_max_x - global_min_x
    scene_height = global_max_y - global_min_y
    canvas_x_min, canvas_x_max, canvas_y_min, canvas_y_max = canvas
    canvas_width = canvas_x_max - canvas_x_min
    canvas_height = canvas_y_max - canvas_y_min
    scale = min(canvas_width / scene_width, canvas_height / scene_height, 1)
    new_scene_width = scale * scene_width
    new_scene_height = scale * scene_height
    desired_x_min = canvas_x_min + (canvas_width - new_scene_width) / 2
    desired_y_min = canvas_y_min + (canvas_height - new_scene_height) / 2

    def transform(pt):
        x, y = pt
        new_x = desired_x_min + scale * (x - global_min_x)
        new_y = desired_y_min + scale * (y - global_min_y)
        return (new_x, new_y)
    for obj in scene:
        obj.apply_transformation(transform)


def merge_skill_lines(lines):
    """
    Merges multiple consolidated lines (strings) that belong to the same base object.
    Each line is expected to have the format:
      Header: (detail)
    where the detail may begin with a grouping phrase (e.g. "from lineIDs=[0, 1, 2]").
    
    This function groups lines by their base header (e.g., "Rectangle 0"), then:
      - Searches among the details for any grouping detail (i.e. a detail starting with "from")
        and places it as the first item.
      - All remaining details are combined into a comma‑separated list.
    Returns a list of merged consolidated lines.
    """
    merged = {}
    for line in lines:
        line = line.strip()
        # Split header and details at the first colon.
        if ':' in line:
            header_part, rest = line.split(':', 1)
            header_part = header_part.strip()
            rest = rest.strip()
        else:
            header_part = line
            rest = ""
        # For consistent formatting, expect details to be inside parentheses.
        details = ""
        if rest.startswith("(") and rest.endswith(")"):
            details = rest[1:-1].strip()
        else:
            details = rest

        # Group by the header.
        if header_part in merged:
            if details:
                merged[header_part].append(details)
        else:
            merged[header_part] = [details] if details else []

    # Rebuild merged lines.
    result = []
    for header, details_list in merged.items():
        grouping_detail = None
        other_details = []
        for d in details_list:
            # If a detail starts with "from" (ignoring case), treat it as the grouping.
            if d.lower().startswith("from"):
                grouping_detail = d
            elif d:
                other_details.append(d)
        # Build the final details list: grouping first (if present), then the other details.
        final_details = []
        if grouping_detail:
            final_details.append(grouping_detail)
        final_details.extend(other_details)
        # Rebuild the line in "Header: (detail1, detail2, ...)" format.
        if final_details:
            merged_line = f"{header}: (" + ", ".join(final_details) + ")"
        else:
            merged_line = header + ":"
        result.append(merged_line)
    return result
# Revised create_scene function with post-processing.


def create_scene(plan, avoid_types=None, canvas=(0,100,0,100), allow_partial=True, sigfigs=1, collapse_skills=True):
    UniqueIDGenerator.reset_counters()
    if avoid_types is None:
        avoid_types = ["BarGraph", "Bars", "Axis"]
    else:
        avoid_types.extend(["BarGraph", "Bars"])
    scene = build_scene_from_plan(plan)
    total = len(scene)
    min_total = 1
    max_total = 6
    available_types = [t for t in list(OBJECT_TYPES.keys()) if t not in avoid_types]
    while total < min_total and available_types:
        extra_type = random.choice(available_types)
        scene.append(OBJECT_TYPES[extra_type](canvas=canvas))
        total += 1
    while total > max_total and scene:
        scene.pop()
        total -= 1

    for obj in scene:
        obj.assign_geometry()

    skill_output = ""
    skill_trees = []
    line_count = 0
    oval_count = 0

    for obj in scene:
        tree = obj.perform_skills()
        line_count += count_low_level_nodes(tree, "RecognizeInstanceLine")
        oval_count += count_low_level_nodes(tree, "RecognizeInstanceOval")

        skill_trees.append(tree)
        if collapse_skills:
            # Get the consolidated lines from the tree.
            lines = collapse_skills_tree_single_line(tree, sigfigs=sigfigs)
            # Post-process lines from this object to merge those with the same base header.
            merged_lines = merge_skill_lines(lines)
            consolidated = " | ".join(merged_lines)
            skill_output += "\n" + consolidated
        else:
            lines = skills_tree_to_text(tree, sigfigs=sigfigs)
            skill_output += "\n" + "\n".join(lines)
    if not allow_partial:
        adjust_scene(scene, canvas=canvas)
    count_basic_string = "There are approximately " + str(line_count) + " lines and " + str(oval_count) + " ovals. "
    skill_output = count_basic_string + skill_output
    
    return scene, skill_output, skill_trees