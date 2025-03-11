import random
import math
from geometry import UniqueIDGenerator
from geometry.shapes import LineLow, OvalLow, RectangleObj, BarsObj, AxisObj, BarGraphObj, TriangleObj, PolygonObj, ArrowObj
from geometry.base import skills_tree_to_text
##############################################################################
# High-level object type mapping.
##############################################################################
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
##############################################################################
# Build a scene from a plan.
##############################################################################
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

##############################################################################
# Adjust the scene: Scale & Translate scene to fully fit within canvas.
##############################################################################
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

##############################################################################
# Create Scene (scene construction without display/saving)
##############################################################################
def create_scene(plan, avoid_types=None, canvas=(0,100,0,100), allow_partial=True):
    UniqueIDGenerator.reset_counters()
    if avoid_types is None:
        avoid_types = ["BarGraph", "Bars", "Axis"]
    else:
        avoid_types.extend(["BarGraph", "Bars"])
    scene = build_scene_from_plan(plan)
    total = len(scene)
    min_total = 3
    max_total = 6
    available_types = [t for t in list(OBJECT_TYPES.keys()) if t not in avoid_types]
    while total < min_total and available_types:
        extra_type = random.choice(available_types)
        scene.append(OBJECT_TYPES[extra_type]())
        total += 1
    while total > max_total and scene:
        scene.pop()
        total -= 1

    for obj in scene:
        obj.assign_geometry()

    skill_output = ""
    for obj in scene:
        skill_result = obj.perform_skills()
        if isinstance(skill_result, dict):
            # Convert tree structure to text
            lines = skills_tree_to_text(skill_result)
            skill_text = "\n".join(lines)
            skill_output += "\n" + skill_text
        else:
            skill_output += "\n" + skill_result

    if not allow_partial:
        adjust_scene(scene, canvas=canvas)
    return scene, skill_output