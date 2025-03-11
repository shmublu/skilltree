import random
import math
import bisect
import os
import json
import re
from scene.builder import create_scene, adjust_scene
from geometry import get_line_length_and_angle, LineLow, OvalLow, RectangleObj, TriangleObj, PolygonObj, ArrowObj
from display.renderer import display_and_save_scene
from geometry.intersections import intersect  

# 1. "Is there an <object type> in the image?"
def demo_question_object(answer=True, outdir="demo_output/question_object", canvas_size=(100,100)):
    width, height = canvas_size
    canvas = (0, width, 0, height)
    obj_type = random.choice(["Line", "Oval", "Rectangle", "Triangle", "Arrow"])
    if answer:
        plan = {obj_type: random.randint(1, 2)}
    else:
        plan = {obj_type: 0}
    scene, skill_output = create_scene(plan, canvas=canvas, avoid_types=[] if answer else [obj_type])
    if not answer:
        for obj in scene:
            if obj.ALIAS == obj_type:
                raise Exception(f"Error: {obj_type} instance found when answer should be false.")
    question_text = f"Is there a {obj_type} in the image? Do not consider objects part of larger objects."
    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)

# 2. "Are there any parallel/perpendicular lines in the image?"
def demo_question_parallel_perp_lines(answer=True,
                                      outdir="demo_output/question_parallel_perp_lines",
                                      canvas_size=(100, 100)):
    width, height = canvas_size
    canvas = (0, width, 0, height)
    epsilon = 4
    MAX_RETRY =  100
    margin = 5
    test_parallel = random.choice([True, False])
    relation_text = "parallel" if test_parallel else "perpendicular"
    question_text = f"Are there any {relation_text} lines in the image? Consider lines that are not touching as well."

    if answer:
        r = random.random()
        if r < 0.02:
            plan = {"Rectangle": 1}
            scene, skill_output = create_scene(plan, canvas=canvas, avoid_types=[])
            display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)
            return
        elif r < 0.04:
            plan = {"Bars": 1}
            scene, skill_output = create_scene(plan, canvas=canvas, avoid_types=[])
            display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)
            return
        elif r < 0.06:
            plan = {"Axis": 1}
            scene, skill_output = create_scene(plan, canvas=canvas, avoid_types=[])
            display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)
            return

    def compute_endpoint(p, angle, length):
        r = math.radians(angle)
        return (p[0] + length * math.cos(r), p[1] + length * math.sin(r))

    def generate_angles(base, valid):
        if valid:
            offset = random.uniform(-epsilon / 2, epsilon / 2)
            a1 = base % 360
            a2 = (base + (0 if test_parallel else 90) + offset) % 360
        else:
            a1 = base % 360
            choices = [10, 20, 30, 40] if test_parallel else [20, 40, 120]
            a2 = (base + random.choice(choices)) % 360
        return a1, a2

    def gather_all_lines(obj):
        lines = []
        stack = [obj]
        while stack:
            current = stack.pop()
            if getattr(current, "ALIAS", None) == "Line":
                lines.append(current)
            if hasattr(current, "sub_references"):
                stack.extend(current.sub_references)
        return lines

    for _ in range(MAX_RETRY):
        base = random.uniform(0, 360)
        angle1, angle2 = generate_angles(base, answer)
        p1 = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
        p2 = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
        len1 = random.uniform(10, width * 0.6)
        len2 = random.uniform(10, width * 0.6)
        plan = {"Line": [
            {"p1": p1, "p2": compute_endpoint(p1, angle1, len1)},
            {"p1": p2, "p2": compute_endpoint(p2, angle2, len2)}
        ]}
        scene, skill_output = create_scene(plan, canvas=canvas, avoid_types=[])

        all_lines = []
        for obj in scene:
            all_lines.extend(gather_all_lines(obj))
        if len(all_lines) < 2:
            continue

        angles = [get_line_length_and_angle(ln.p1, ln.p2)[1] for ln in all_lines]
        angles.sort()
        relation_found = False

        if test_parallel:
            for i in range(len(angles) - 1):
                if abs(angles[i+1] - angles[i]) <= epsilon:
                    relation_found = True
                    break
            if not relation_found and (360 - angles[-1] + angles[0]) <= epsilon:
                relation_found = True
        else:
            for angle in angles:
                target = angle + 90
                if target > 360:
                    target -= 360
                    idx1 = bisect.bisect_left(angles, target - epsilon)
                    idx2 = bisect.bisect_left(angles, (angle + 90) - epsilon)
                    if any(abs(a - target) <= epsilon for a in angles[idx1:]) or \
                       any(abs((a + 360) - (angle + 90)) <= epsilon for a in angles if a < target):
                        relation_found = True
                        break
                else:
                    idx = bisect.bisect_left(angles, target - epsilon)
                    while idx < len(angles) and angles[idx] <= target + epsilon:
                        relation_found = True
                        break
                    if relation_found:
                        break

        if (answer and relation_found) or (not answer and not relation_found):
            break

    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)

# 3. "Are there any arrows pointing <upward | downward | leftward | rightward>?"
def demo_question_arrow_direction(answer=True, outdir="demo_output/question_arrow_direction", canvas_size=(100,100)):
    MAX_RETRY = 50
    width, height = canvas_size
    canvas = (0, width, 0, height)
    direction = random.choice(["upward", "downward", "leftward", "rightward"])
    tol_adjust = 30
    direction_angles = {"upward": 270, "downward": 90, "leftward": 180, "rightward": 0}

    NO_ARROW_PROB_FALSE = 0.15

    attempt = 0
    scene = None
    plan = None
    while attempt < MAX_RETRY:
        attempt += 1
        if answer:
            base_angle = direction_angles[direction]
            angle = base_angle + random.uniform(-tol_adjust, tol_adjust)
            length = random.uniform(20, min(width, height) / 1.5)
            margin = 5
            start_x = random.uniform(margin, width - margin)
            start_y = random.uniform(margin, height - margin)
            plan = {"Arrow": [{
                "angle": angle,
                "length": length,
                "start": (start_x, start_y)
            }]}
        else:
            if random.random() < NO_ARROW_PROB_FALSE:
                plan = {}
            else:
                wrong_directions = [d for d in direction_angles if d != direction]
                wrong_direction = random.choice(wrong_directions)
                base_angle = direction_angles[wrong_direction]
                angle = base_angle + random.uniform(-tol_adjust, tol_adjust)
                length = random.uniform(20, min(width, height) / 1.5)
                margin = 5
                start_x = random.uniform(margin, width - margin)
                start_y = random.uniform(margin, height - margin)
                plan = {"Arrow": [{
                    "angle": angle,
                    "length": length,
                    "start": (start_x, start_y)
                }]}
        scene, skill_output = create_scene(plan, canvas=canvas)
        if not answer:
            arrow_objs = [obj for obj in scene if obj.ALIAS == "Arrow"]
            if not arrow_objs:
                break
            violation = False
            for obj in arrow_objs:
                if abs(obj.angle - direction_angles[direction]) < tol_adjust:
                    violation = True
                    break
            if violation:
                if attempt == MAX_RETRY:
                    raise Exception("Check failed: An arrow pointing the target direction was found when answer should be false.")
                continue
        break

    question_text = f"Is there an arrow pointing {direction}?"
    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)

# 4. "Does a <shape 1> intersect with a <shape 2>?"
def demo_question_intersect_objects(answer=True,
                                    outdir="demo_output/question_intersect_objects",
                                    canvas_size=(100, 100)):
    import random, math, bisect, os, json, re
    from scene.builder import create_scene
    from display.renderer import display_and_save_scene
    from geometry.intersections import intersect  # Import the full intersect function

    width, height = canvas_size
    canvas = (0, width, 0, height)
    
    candidate_types = ["Line", "Oval", "Circle", "Rectangle", "Square", "Triangle"]
    type1 = random.choice(candidate_types)
    type2 = random.choice(candidate_types)
    question_text = f"Does an {type1} intersect with an {type2}?"
    
    def geom_type(shape):
        if shape == "Line":
            return "line"
        elif shape in ["Oval", "Circle"]:
            return "oval"
        else:
            return "polygon"
    
    margin = 5
    def gen_params(shape):
        if shape == "Line":
            p1 = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            p2 = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            return {"p1": p1, "p2": p2}
        elif shape in ["Oval", "Circle", "Rectangle", "Square"]:
            center = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            w = random.uniform(10, width / 2)
            h = random.uniform(10, height / 2)
            if shape in ["Circle", "Square"]:
                h = w  # force equal dimensions
            angle = random.uniform(0, 360)
            return {"center": center, "width": w, "height": h, "angle": angle}
        elif shape == "Triangle":
            center = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            pts = []
            for _ in range(3):
                pts.append((center[0] + random.uniform(-0.3 * width, 0.3 * width),
                            center[1] + random.uniform(-0.3 * height, 0.3 * height)))
            return {"vertices": pts}
        elif shape == "Polygon":
            center = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            pts = []
            count = 5
            for i in range(count):
                ang = 2 * math.pi * i / count + random.uniform(-0.2, 0.2)
                r = random.uniform(10, 30)
                pts.append((center[0] + r * math.cos(ang),
                            center[1] + r * math.sin(ang)))
            return {"vertices": pts}
    
    def wiggle_params(params, shape, delta=5, angle_delta=10):
        new_params = params.copy()
        if shape == "Line":
            new_params["p1"] = (params["p1"][0] + random.uniform(-delta, delta),
                                params["p1"][1] + random.uniform(-delta, delta))
            new_params["p2"] = (params["p2"][0] + random.uniform(-delta, delta),
                                params["p2"][1] + random.uniform(-delta, delta))
        elif shape in ["Oval", "Circle", "Rectangle", "Square"]:
            new_params["center"] = (params["center"][0] + random.uniform(-delta, delta),
                                    params["center"][1] + random.uniform(-delta, delta))
            new_params["angle"] = (params["angle"] + random.uniform(-angle_delta, angle_delta)) % 360
        elif shape in ["Triangle", "Polygon"]:
            new_vertices = []
            for (x, y) in params["vertices"]:
                new_vertices.append((x + random.uniform(-delta, delta),
                                     y + random.uniform(-delta, delta)))
            new_params["vertices"] = new_vertices
        return new_params

    MAX_INITIAL_TRIES = 100
    params1 = None
    params2 = None
    for _ in range(MAX_INITIAL_TRIES):
        p1 = gen_params(type1)
        p2 = gen_params(type2)
        does_int = intersect(p1, type1, p2, type2)
        if answer and does_int:
            params1, params2 = p1, p2
            break
        elif (not answer) and (not does_int):
            params1, params2 = p1, p2
            break
    if params1 is None or params2 is None:
        raise Exception("Could not generate initial parameters meeting the condition.")
    
    WIGGLE_ATTEMPTS = 10
    if answer:
        for _ in range(WIGGLE_ATTEMPTS):
            new_p1 = wiggle_params(params1, type1)
            if intersect(new_p1, type1, params2, type2):
                params1 = new_p1
            new_p2 = wiggle_params(params2, type2)
            if intersect(params1, type1, new_p2, type2):
                params2 = new_p2
    else:
        for _ in range(WIGGLE_ATTEMPTS):
            new_p1 = wiggle_params(params1, type1)
            if not intersect(new_p1, type1, params2, type2):
                params1 = new_p1
            new_p2 = wiggle_params(params2, type2)
            if not intersect(params1, type1, new_p2, type2):
                params2 = new_p2
    
    if type1 == "Square":
        type1 = "Rectangle"
    if type2 == "Square":
        type2 = "Rectangle"
    if type1 == "Circle":
        type1 = "Oval"
    if type2 == "Circle":
        type2 = "Oval"

    def interfering_types(type):
        if type == "Line":
            return ["Line", "Square", "Polygon", "Arrow", "Rectangle", "Triangle"]
        elif type == "Oval":
            return ["Circle", "Oval"]
        elif type == "Circle":
            return ["Circle"]
        elif type == "Rectangle":
            return ["Square", "Polygon", "Rectangle"]
        elif type == "Triangle":
            return ["Triangle", "Polygon"]
        elif type == "Polygon":
            return ["Polygon", "Triangle", "Rectangle", "Square"]

    if type1 == type2:
        plan = {type1: [params1, params2]}
    else:
        plan = {type1: [params1], type2: [params2]}
    MAX_RETRY = 150
    final_scene = None
    for attempt in range(MAX_RETRY):
        temp_scene, skill_output = create_scene(plan, canvas=canvas, avoid_types=["BarGraph", "Bars", "Axis"])
        if answer:
            final_scene = temp_scene
            break
        relevant_objs = []
        types = interfering_types(type1) + interfering_types(type2)
        for obj in temp_scene:
            if hasattr(obj, "ALIAS") and obj.ALIAS == "Line" and "Line" in types:
                relevant_objs.append(("Line", {"p1": obj.p1, "p2": obj.p2}))
            elif hasattr(obj, "ALIAS") and obj.ALIAS == "Oval" and "Oval" in types:
                relevant_objs.append(("Oval", {"center": obj.center, "width": obj.width, "height": obj.height, "angle": obj.angle}))
            elif hasattr(obj, "ALIAS") and obj.ALIAS == "Rectangle" and "Rectangle" in types:
                vs = []
                for ln in obj.sub_references:
                    vs.append(ln.p1)
                relevant_objs.append(("polygon", {"vertices": vs}))
            elif hasattr(obj, "ALIAS") and obj.ALIAS == "Triangle" and "Triangle" in types:
                relevant_objs.append(("polygon", {"vertices": obj.vertices}))
            elif hasattr(obj, "ALIAS") and obj.ALIAS == "Polygon" and "Polygon" in types:
                vs = []
                for ln in obj.sub_references[:obj.sides]:
                    vs.append(ln.p1)
                relevant_objs.append(("polygon", {"vertices": vs}))

        any_intersect = False
        for i in range(len(relevant_objs)):
            for j in range(i+1, len(relevant_objs)):
                if intersect(relevant_objs[i][1], relevant_objs[i][0],
                             relevant_objs[j][1], relevant_objs[j][0]):
                    any_intersect = True
                    break
            if any_intersect:
                break

        if not any_intersect:
            final_scene = temp_scene
            break

    scene = final_scene if final_scene else None
    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=skill_output + "\n" + str(answer), canvas=canvas)