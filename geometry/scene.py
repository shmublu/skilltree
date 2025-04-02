import random
import json
import uuid
import matplotlib.pyplot as plt
import math
import os
from typing import List, Dict, Tuple, Any, Optional

# Import shapes (assume these classes are implemented elsewhere)
from shapes import Line, SolidOval, SolidRectangle, SolidTriangle, SolidPolygon
from shapes import CompositeShapeGenerator  # New composite shape generator
from base import UniqueIDGenerator

class SceneGenerator:
    """Class for generating scenes of geometric shapes based on different constraints and question types."""
    
    def __init__(self, base_canvas: Tuple[int, int]=None, max_attempts: int=50) -> None:
        """
        Initialize a scene generator.
        We expand the base canvas size by a random factor between 1.1 and 1.2
        to allow extra room and reduce boundary failures.
        """
        
        base_canvas = (random.randint(300, 800), random.randint(300, 800)) if not base_canvas else base_canvas
        base_width, base_height = base_canvas
        expansion = 1
        self.canvas_width = int(base_width * expansion)
        self.canvas_height = int(base_height * expansion)
        self.canvas = (0, self.canvas_width, 0, self.canvas_height)
        # Increase number of shapes to generate a richer scene.
        self.global_max_shapes: int = random.randint(7, 10)
        self.max_attempts: int = max_attempts
        self.shapes: List[Any] = []
        self.shape_classes: Dict[str, Any] = {
            "Line": Line,
            "SolidOval": SolidOval,
            "SolidRectangle": SolidRectangle,
            "SolidTriangle": SolidTriangle,
            "SolidPolygon": SolidPolygon
        }
        # Add composite shape generator and include its shape class.
        self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
        self.shape_classes["CompositeShape"] = self.composite_shape_gen.ComponentShape
        
        # Track failures per question type (retained from original code)
        self.fail_counts: Dict[str, int] = {}

    def reset(self) -> None:
        """Clear all shapes in the scene and reset the ID generator."""
        self.shapes = []
        UniqueIDGenerator.reset_counters()
        self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
        self.shape_classes["CompositeShape"] = self.composite_shape_gen.ComponentShape

    def get_random_parameters(self, shape_type: str) -> Dict[str, Any]:
        """
        Smart parameter generator for each shape type.
        Now, shapes can be anywhere on the canvas with a wider range of sizes.
        """
        params = {}
        if shape_type == "Line":
            params["p1"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
            params["p2"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
            params["thickness"] = random.uniform(1, 5)
        elif shape_type == "SolidOval":
            params["center"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
            params["width"] = random.uniform(10, self.canvas_width / 2)
            params["height"] = random.uniform(10, self.canvas_height / 2)
            params["angle"] = random.uniform(0, 360)
            params["thickness"] = random.uniform(1, 5)
            params["is_circle"] = random.choice([True, False])
        elif shape_type == "SolidRectangle":
            params["center"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
            params["width"] = random.uniform(10, self.canvas_width / 2)
            params["height"] = random.uniform(10, self.canvas_height / 2)
            params["thickness"] = random.uniform(1, 3)
        elif shape_type == "SolidTriangle":
            params["vertices"] = [
                (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
                for _ in range(3)
            ]
            params["thickness"] = random.uniform(1, 3)
        elif shape_type == "SolidPolygon":
            num_vertices = random.randint(5, 7)
            params["num_vertices"] = num_vertices
            params["vertices"] = [
                (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
                for _ in range(num_vertices)
            ]
            params["thickness"] = random.uniform(1, 5)
        # For CompositeShape, we rely on the composite shape generator’s own method.
        return params

    def shapes_intersect(self, shape1: Any, shape2: Any, resolution: int=50) -> bool:
        """Returns True if shape1 and shape2 have an intersection over a small threshold."""
        if shape1 is None or shape2 is None:
            return False
        try:
            overlap_self, overlap_other = shape1.intersect(shape2, resolution=resolution)
        except Exception:
            return False
        threshold: float = 0.000001  # Minimal threshold
        return overlap_self > threshold or overlap_other > threshold

    def is_valid_placement(self, shape: Any, intersect_rules: Dict[str, Any]={}, 
                           position_rules: Dict[str, Any]={}, shape_amounts: Dict[str, Tuple[int, int]]={}) -> bool:
        """Check if a shape placement is valid according to the given rules."""
        shape_type: str = shape.__class__.__name__
        # Check position constraints if provided.
        if shape_type in position_rules and position_rules[shape_type]:
            x_min, x_max, y_min, y_max = position_rules[shape_type]
            bbox = shape.get_bbox()
            if (bbox[0] < x_min or bbox[2] > x_max or 
                bbox[1] < y_min or bbox[3] > y_max):
                return False
        # Check intersection constraints if provided.
        if shape_type in intersect_rules and intersect_rules[shape_type]:
            intersections: Dict[str, int] = {}
            for other_shape in self.shapes:
                if other_shape is None:
                    continue
                other_type: str = other_shape.__class__.__name__
                if self.shapes_intersect(shape, other_shape):
                    intersections[other_type] = intersections.get(other_type, 0) + 1
            for other_type, max_count in intersect_rules[shape_type]:
                if other_type in intersections and intersections[other_type] > max_count:
                    return False
        # Check shape amount constraints if provided.
        shapes_by_type: Dict[str, List[Any]] = self.get_shapes_by_type()
        if shape_type in shape_amounts and shape_amounts[shape_type]:
            min_count, max_count = shape_amounts[shape_type]
            current_count: int = len(shapes_by_type.get(shape_type, []))
            if current_count >= max_count:
                return False
        return True

    def add_shape_no_retry(self, shape_type: str, intersect_rules: Dict[str, Any]={}, 
                             position_rules: Dict[str, Any]={}, shape_amounts: Dict[str, Tuple[int, int]]={}) -> Optional[Any]:
        """
        Add a shape of the given type to the scene with the given constraints.
        This version does not retry; it attempts once and adds the shape only if it passes geometry assignment and bounds.
        """
        if len(self.shapes) >= self.global_max_shapes:
            return None
        
        if shape_type not in self.shape_classes:
            raise ValueError(f"Unknown shape type: {shape_type}")
        
        # Save state in case of error.
        UniqueIDGenerator.save_checkpoint()
        try:
            if shape_type != "CompositeShape":
                params = self.get_random_parameters(shape_type)
                shape = self.shape_classes[shape_type](canvas=self.canvas, **params)
            else:
                # For composite shapes, we create a new generator for each shape.
                local_comp_gen = self.composite_shape_gen
                x = random.uniform(0, self.canvas_width)
                y = random.uniform(0, self.canvas_height)
                shape = local_comp_gen.generate_shape(
                    center=(x, y),
                    scale=random.uniform(0.2, 0.45),
                    angle=random.uniform(0, 360)
                )
            # Call assign_geometry and then enforce bounds.
            shape.assign_geometry()
            shape.enforce_bounds()
            # With ~15% probability, set a random label on the shape if available.
            if random.random() < 0.15:
                shape.set_label()
        except Exception:
            UniqueIDGenerator.load_checkpoint()
            return None
        
        # Accept the shape only if it passes valid placement.
        if not self.is_valid_placement(shape, intersect_rules, position_rules, shape_amounts):
            return None
        self.shapes.append(shape)
        return shape

    def generate_random_scene(self) -> None:
        """
        Generate a random scene with a set number of shapes without any retrying.
        Basic shapes (without children) are added first, then a group of composite shapes is added.
        """
        self.reset()
        # Add a random number of basic shapes.
        num_basic_shapes = random.randint(5, self.global_max_shapes)
        shape_types = list(self.shape_classes.keys())
        # Exclude composite shapes from basic shapes.
        basic_types = [st for st in shape_types if st != "CompositeShape"]
        for _ in range(num_basic_shapes):
            st = random.choice(basic_types)
            self.add_shape_no_retry(st)
        
        # Always add between 2 and 4 composite shapes.
        if random.random() < .05:
            num_composites = random.randint(2, 3)
            for _ in range(num_composites):
                self.add_shape_no_retry("CompositeShape")
            if random.random() < .2:
                self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
                num_composites = random.randint(2, 5)
                for _ in range(num_composites):
                    self.add_shape_no_retry("CompositeShape")

    def get_shapes_by_type(self) -> Dict[str, List[Any]]:
        """Return a dictionary mapping shape types to lists of shapes (including children recursively)."""
        result: Dict[str, List[Any]] = {}
        def add_shape_and_children(shape: Any) -> None:
            shape_type: str = shape.__class__.__name__
            if shape_type not in result:
                result[shape_type] = []
            result[shape_type].append(shape)
            children = shape.get_children()
            if children:
                for child in children:
                    add_shape_and_children(child)
        for shape in self.shapes:
            add_shape_and_children(shape)
        return result

    def count_shapes_by_type(self) -> Dict[str, int]:
        """Return a dictionary mapping shape types to counts."""
        shapes_by_type = self.get_shapes_by_type()
        return {k: len(v) for k, v in shapes_by_type.items()}

    def add_background_composite_shapes(self) -> None:
        """
        Add background composite shapes without retries.
        Each composite shape is generated with its own generator.
        """
        num_instances: int = random.randint(2, 4)
        for _ in range(num_instances):
            local_comp_gen = CompositeShapeGenerator(canvas=self.canvas)
            x = random.uniform(0, self.canvas_width)
            y = random.uniform(0, self.canvas_height)
            try:
                comp = local_comp_gen.generate_shape(
                    center=(x, y),
                    scale=random.uniform(0.2, 0.45),
                    angle=random.uniform(0, 360)
                )
                comp.assign_geometry()
                comp.enforce_bounds()
            except Exception:
                continue
            if comp.__class__.__name__ == "CompositeShape":
                self.shapes.append(comp)

    def all_shapes_valid(self) -> bool:
        """Check that all shapes in the scene pass enforce_bounds."""
        try:
            for shape in self.shapes:
                shape.enforce_bounds()
            return True
        except Exception:
            return False

    def render(self, ax: Optional[Any]=None, figsize: Tuple[int, int]=(10, 8)) -> Tuple[Any, Any]:
        """Render the scene to a matplotlib figure after verifying all shapes are within bounds."""
        if not self.all_shapes_valid():
            raise ValueError("Not all shapes are within bounds before rendering.")
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.figure
        ax.set_xlim(0, self.canvas_width)
        ax.set_ylim(0, self.canvas_height)
        for shape in self.shapes:
            shape.render(ax)
        ax.axis('off')
        return fig, ax


    def get_skill_trace(self):
        """
        Generate a linear skill trace string for all shapes in the scene.

        For each shape, the skill tree is flattened in depth-first order,
        with children objects (e.g. Lines) listed before their parent objects.
        When multiple nodes refer to the same object (by the "object" field), their details are merged.
        In the final header summary, only objects that are leaves (i.e. have no child objects)
        are counted. For example, a rectangle with no children is counted in the header,
        whereas a rectangle with border lines is not (only its child lines are).

        Returns:
            A string that starts with a header summarizing counts of leaf objects by type,
            followed by one line per shape showing the flattened object traces.
        """
        from collections import defaultdict

        def flatten_and_merge(tree):
            """
            Recursively flatten the skill tree with children before parents, and merge details for nodes
            with the same "object" field. Also, track if the node is a leaf (has no children).
            
            Returns:
                A list of tuples in the order encountered:
                    (object_id, object_type, merged_details, is_leaf)
                where object_id is the full string from the "object" field,
                object_type is the substring before '#' (if any),
                merged_details is a concatenation of all details for that object,
                and is_leaf is True if none of the occurrences had children.
            """
            merged = {}  # key: object id, value: [merged_details, is_leaf]
            processed = set()  # track objects we've processed to avoid duplicates
            
            # First collect all object information
            def collect_info(node):
                obj_id = node.get("object", "").strip()
                detail = node.get("details", "")
                has_children = "children" in node and node["children"]
                
                if obj_id:
                    if obj_id in merged:
                        # If any occurrence has children, mark as non-leaf
                        merged[obj_id][1] = merged[obj_id][1] and (not has_children)
                        # Merge detail if non-empty and not already included
                        if detail and detail not in merged[obj_id][0]:
                            merged[obj_id][0] += (", " if merged[obj_id][0] else "") + detail
                    else:
                        merged[obj_id] = [detail, not has_children]
                
                # Process children
                if has_children:
                    for child in node["children"]:
                        collect_info(child)
            
            # Collect all object information first
            collect_info(tree)
            
            # Now build ordered list with children before parents
            def build_ordered_list(node):
                result = []
                obj_id = node.get("object", "").strip()
                has_children = "children" in node and node["children"]
                
                # Process children first
                if has_children:
                    for child in node["children"]:
                        result.extend(build_ordered_list(child))
                
                # Then process this node if it has a valid object ID and hasn't been processed
                if obj_id and obj_id not in processed:
                    obj_type = obj_id.split("#")[0]
                    merged_details, is_leaf = merged[obj_id]
                    result.append((obj_id, obj_type, merged_details, is_leaf))
                    processed.add(obj_id)
                
                return result
            
            return build_ordered_list(tree)

        # Gather shapes in the order returned (regardless of type)
        shapes = []
        shapes_by_type = self.get_shapes_by_type()
        for shape_list in shapes_by_type.values():
            shapes.extend(shape_list)

        global_indices = defaultdict(int)  # for sequential numbering per object type
        total_counts = defaultdict(int)    # count only leaf objects
        shape_lines = []                  # to accumulate output lines per shape
        seen_objects = set()              # track objects we've already seen across all shapes

        for shape in shapes:
            tree = shape.perform_skills()
            flattened = flatten_and_merge(tree)
            
            # Build trace for this shape
            line_parts = []
            for obj_id, obj_type, details, is_leaf in flattened:
                # Skip if we've already seen this object
                if obj_id in seen_objects:
                    continue
                seen_objects.add(obj_id)
                
                # Assign index and count leaf objects
                idx = global_indices[obj_type]
                global_indices[obj_type] += 1
                if is_leaf:
                    total_counts[obj_type] += 1
                
                # Format the trace
                part = f"{obj_id}: "
                for d in details:
                    if "details" in d:
                        det = d["details"]
                        part += det
                    else:
                        continue
                line_parts.append(part)
            
            # Add this shape's trace to output
            if line_parts:
                shape_lines.append(" | ".join(line_parts))

        # Build header from leaf counts only, with simple pluralization.
        leaf_counts = defaultdict(int)
        for shape in shapes:
            if not shape.get_children():
                shape_type = shape.ALIAS
                leaf_counts[shape_type] += 1
        leaf_parts = []
        for shape_type, count in leaf_counts.items():
            leaf_parts.append(f"{count} {shape_type.lower()}{'s' if count != 1 else ''}")
        leaf_sentence = "There are approximately " + " and ".join(leaf_parts) + "."

    
        composite_aliases = []
        for shape in shapes:
            if getattr(shape, "is_composite", False):
                alias = getattr(shape, "ALIAS", None)
                composite_aliases.append(alias)
        # Remove duplicates
        composite_aliases = list(set(composite_aliases))
        if composite_aliases:
            if len(composite_aliases) == 1:
                composite_sentence = f" I see a repeated complex object in the image; I will call it {composite_aliases[0]}."
            else:
                composite_sentence = f" I see repeated complex objects in the image; I will call them {', '.join(composite_aliases)}."
        else:
            composite_sentence = ""
        header = leaf_sentence + composite_sentence + " I will use a pixel as a unit, which may not correspond to in-image measurements, and put the origin at the bottom-left corner. "

        return header + "\n" + " ".join(shape_lines)

    def save_to_json(self, filename: str, question: str, answer: str, path: str) -> Dict[str, Any]:
        """
        Save the scene, question, and answer to a JSON file in single-line JSON format.
        Also, save the image immediately.
        """
        scene_id = str(uuid.uuid4().hex)
        image_path = f"{path}/scene_{scene_id}.png"
        if not self.all_shapes_valid():
            raise ValueError("Final scene contains shapes out of bounds.")
        skill_trace = self.get_skill_trace()
        assistant_response = (
            f"The scene contains shapes. Before I answer, let me parse them: {skill_trace}\n"
            f"Then, the original question: '{question}' - the answer is {answer}."
        )
        json_entry = {
            "messages": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": assistant_response}
            ],
            "images": [image_path]
        }
        with open(filename, 'w') as f:
            json.dump(json_entry, f, separators=(',',':'))
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        fig, ax = self.render()
        fig.savefig(image_path, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        return json_entry

    def generate_question_and_answer(self) -> Tuple[str, str]:
        """
        Generate a random question and its answer based on the current scene.
        No retries are done; the question is computed from the scene as is.
        """
        question_types = ["existence", "intersection", "intersection_count", 
                          "position", "count", "multiple_count", "most_common", "area_comparison"]
        chosen = random.choice(question_types)
        if chosen == "existence":
            valid = [s for s in self.shape_classes.keys() if s != "Line"]
            target = random.choice(valid)
            shapes_by_type = self.get_shapes_by_type()
            answer = "Yes" if target in shapes_by_type and len(shapes_by_type[target]) > 0 else "No"
            question_text = f"Is there a {target.replace('Solid','')} in this image?"
            return question_text, answer
        elif chosen == "intersection":
            shape_types = list(self.shape_classes.keys())
            shape1 = random.choice(shape_types)
            shape2 = random.choice(shape_types)
            shapes_by_type = self.get_shapes_by_type()
            exists = False
            if shape1 in shapes_by_type and shape2 in shapes_by_type:
                for s1 in shapes_by_type[shape1]:
                    for s2 in shapes_by_type[shape2]:
                        if self.shapes_intersect(s1, s2):
                            exists = True
                            break
            answer = "Yes" if exists else "No"
            question_text = f"Does a {shape1.replace('Solid','')} intersect with a {shape2.replace('Solid','')} in this image?"
            return question_text, answer
        elif chosen == "intersection_count":
            shape_types = list(self.shape_classes.keys())
            shape1 = random.choice(shape_types)
            shape2 = random.choice(shape_types)
            shapes_by_type = self.get_shapes_by_type()
            count = 0
            if shape1 in shapes_by_type and shape2 in shapes_by_type:
                for s1 in shapes_by_type[shape1]:
                    for s2 in shapes_by_type[shape2]:
                        if self.shapes_intersect(s1, s2):
                            count += 1
                            break
            question_text = f"How many {shape1.replace('Solid','')}s intersect with {shape2.replace('Solid','')}s in this image?"
            return question_text, str(count)
        elif chosen == "position":
            valid = [s for s in self.shape_classes.keys() if s != "Line"]
            shape1 = random.choice(valid)
            shape2 = random.choice(valid)
            relation = random.choice(["above", "below", "left of", "right of"])
            shapes_by_type = self.get_shapes_by_type()
            exists = False
            if shape1 in shapes_by_type and shape2 in shapes_by_type:
                for s1 in shapes_by_type[shape1]:
                    for s2 in shapes_by_type[shape2]:
                        bbox1 = s1.get_bbox()
                        bbox2 = s2.get_bbox()
                        if (relation == "above" and bbox1[1] > bbox2[3]) or \
                           (relation == "below" and bbox1[3] < bbox2[1]) or \
                           (relation == "left of" and bbox1[2] < bbox2[0]) or \
                           (relation == "right of" and bbox1[0] > bbox2[2]):
                            exists = True
                            break
            answer = "Yes" if exists else "No"
            question_text = f"Is there a {shape1.replace('Solid','')} {relation} a {shape2.replace('Solid','')} in this image?"
            return question_text, answer
        elif chosen == "count":
            valid = [s for s in self.shape_classes.keys() if s != "Line"]
            target = random.choice(valid)
            shapes_by_type = self.get_shapes_by_type()
            count = len(shapes_by_type.get(target, []))
            question_text = f"How many {target.replace('Solid','')}s are there in this image?"
            return question_text, str(count)
        elif chosen == "multiple_count":
            valid = [s for s in self.shape_classes.keys() if s != "Line"]
            shape1 = random.choice(valid)
            shape2 = random.choice(valid)
            shapes_by_type = self.get_shapes_by_type()
            count = len(shapes_by_type.get(shape1, [])) + len(shapes_by_type.get(shape2, []))
            question_text = f"How many {shape1.replace('Solid','')}s and {shape2.replace('Solid','')}s are there in this image?"
            return question_text, str(count)
        elif chosen == "most_common":
            shapes_by_type = self.get_shapes_by_type()
            counts = {k: len(v) for k, v in shapes_by_type.items()}
            if not counts:
                answer = "N/A"
                question_text = "Which shape appears the most in this image?"
            else:
                max_count_val = max(counts.values())
                most_common = [k for k, v in counts.items() if v == max_count_val]
                answer = ", ".join([mc.replace('Solid','') for mc in most_common])
                question_text = "Which shape appears the most in this image?"
            return question_text, answer
        elif chosen == "area_comparison":
            shape_types = list(self.shape_classes.keys())
            best = None
            best_area = -math.inf
            for shape in self.shapes:
                try:
                    area = shape.get_area()
                    if area > best_area:
                        best_area = area
                        best = shape.__class__.__name__
                except Exception:
                    continue
            if best is None:
                best = random.choice(shape_types)
            relation = random.choice(["highest", "lowest"])
            question_text = f"Which shape has the {relation} area in this image?"
            answer = best.replace('Solid','')
            return question_text, answer

def generate_dataset(output_file: str="scene_dataset7.json", num_examples: int=50, output_image_path: str="output") -> None:
    """
    Generate a dataset of scenes and questions.
    Each entry is output in a single-line JSON format.
    This function generates each scene once without retries.
    """
    generator = SceneGenerator()
    
    with open(output_file, 'w') as f_out:
        for _ in range(num_examples):
            generator.generate_random_scene()
            question, answer = generator.generate_question_and_answer()
            temp_file = f"temp_scene_{uuid.uuid4().hex}.json"
            try:
                json_entry = generator.save_to_json(temp_file, question, answer, output_image_path)
            except Exception:
                continue
            if os.path.exists(temp_file):
                os.remove(temp_file)
            json_line = json.dumps(json_entry, separators=(',',':'))
            print(json_line)
            f_out.write(json_line + "\n")
    
    print(f"Generated {num_examples} examples and saved to {output_file}")
    print("Failure counts per question type:", generator.fail_counts)

if __name__ == "__main__":
    generator = SceneGenerator()
    
    # Generate a random scene (no retries) and then generate a random question & answer from it.
    generator.generate_random_scene()
    question, answer = generator.generate_question_and_answer()
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    try:
        fig, ax = generator.render()
        plt.show()
    except Exception as e:
        print("Rendering failed:", e)
    
    generate_dataset(num_examples=20000, output_image_path="/n/fs/penciller/skilltree2/geometry/output")
