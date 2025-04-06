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
from utilities import replace_polygon
from shapes import scale_shape

class SceneGenerator:
    """Class for generating scenes of geometric shapes based on different constraints and question types."""
    
    def __init__(self, base_canvas: Tuple[int, int]=None, max_attempts: int=50) -> None:
        """
        Initialize a scene generator.
        We expand the base canvas size by a random factor between 1.1 and 1.2
        to allow extra room and reduce boundary failures.
        """
        UniqueIDGenerator.reset_counters()
        self.base_canvas = (random.randint(300, 800), random.randint(300, 800)) if not base_canvas else base_canvas
        base_width, base_height = self.base_canvas
        expansion = 1
        self.scale = 1
        self.canvas_width = int(base_width * expansion)
        self.canvas_height = int(base_height * expansion)
        self.canvas = (0, self.canvas_width, 0, self.canvas_height)
        # Increase number of shapes to generate a richer scene.
        self.global_max_shapes: int = random.randint(3, 25)
        self.max_attempts: int = max_attempts
        self.scale_line_present: bool = False
        self.scale_factor: float = 1.0
        self.shapes: List[Any] = []
        self.shape_classes: Dict[str, Any] = {
            "Line": Line,
            "SolidOval": SolidOval,
            "SolidRectangle": SolidRectangle,
            "SolidTriangle": SolidTriangle,
            "SolidPolygon": SolidPolygon
        }
        self.shape_weights: Dict[str, Any] = {
            "Line": 1,
            "SolidOval": 1.25,
            "SolidRectangle": 1.75,
            "SolidTriangle": 1.25,
            "SolidPolygon": 2
        }
        # Add composite shape generator and include its shape class.
        self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
        #self.shape_classes["the repeating, complex object"] = self.composite_shape_gen.ComponentShape
        
        # Track failures per question type (retained from original code)
        self.fail_counts: Dict[str, int] = {}

    def reset(self) -> None:
        """Clear all shapes in the scene and reset the ID generator."""
        self.shapes = []
        UniqueIDGenerator.reset_counters()
        self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
        self.base_canvas = (random.randint(300, 800), random.randint(300, 800)) if not self.base_canvas else self.base_canvas
        base_width, base_height = self.base_canvas
        expansion = 1
        self.scale = 1
        self.scale_line_present: bool = False
        self.scale_factor: float = 1.0
        self.canvas_width = int(base_width * expansion)
        self.canvas_height = int(base_height * expansion)
        self.canvas = (0, self.canvas_width, 0, self.canvas_height)
        # Increase number of shapes to generate a richer scene.
        self.global_max_shapes: int = random.randint(3, 15)
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
        #self.shape_classes["the repeating, complex object"] = self.composite_shape_gen.ComponentShape
        
        # Track failures per question type (retained from original code)
        self.fail_counts: Dict[str, int] = {}
        #self.shape_classes["the repeating, complex object"] = self.composite_shape_gen.ComponentShape

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
            is_circle = True if random.random() < 0.2 else False
            params["center"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
            params["width"] = random.uniform(10, self.canvas_width / 2)
            params["height"] = random.uniform(10, self.canvas_height / 2) if not is_circle else params["width"]
            params["angle"] = random.uniform(0, 360)
            params["thickness"] = random.uniform(1, 4)
            params["is_circle"] = is_circle or abs(params["width"] - params["height"]) < (2 * self.scale)
        elif shape_type == "SolidRectangle":
            is_square = True if random.random() < 0.2 else False
            params["center"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
            params["width"] = random.uniform(10, int(self.canvas_width / 2.5))
            params["height"] = random.uniform(10, int(self.canvas_height / 2.5)) if not is_square else params["width"]
            params["thickness"] = random.uniform(1, 3)
            params["is_square"] = is_square or abs(params["height"] - params["width"]) < (2 * self.scale)
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
        else:
            # For CompositeShape
            params["scale"] = random.uniform(0.4, 1.25)
            params["angle"] = random.uniform(0, 360)
            params["center"] = (random.uniform(0, self.canvas_width), random.uniform(0, self.canvas_height))
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
        
        if shape_type not in self.shape_classes and shape_type != "CompositeShape":
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
                    scale=random.uniform(0.3, 0.8),
                    angle=random.uniform(0, 360)
                )
            # Call assign_geometry and then enforce bounds.
            shape.assign_geometry()
            shape.enforce_bounds()
            # With ~15% probability, set a random label on the shape if available.
            if random.random() < 0.15:
                shape.set_label()
        except Exception as e:
            print(e)
            UniqueIDGenerator.load_checkpoint()
            return None
        
        # Accept the shape only if it passes valid placement.
        if not self.is_valid_placement(shape, intersect_rules, position_rules, shape_amounts):
            UniqueIDGenerator.load_checkpoint()
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
        
        num_basic_shapes = random.choices(range(1, self.global_max_shapes + 1), weights=[1 if i not in (3, 4) else 2 for i in range(1, self.global_max_shapes + 1)])[0]
        shape_types = list(self.shape_classes.keys())
        if random.random() < .075:
            num_basic_shapes -= 1
            num_composites = random.randint(2, 4)
            for _ in range(num_composites):
                self.add_shape_no_retry("CompositeShape")
            if random.random() < .1:
                num_basic_shapes -= 1
                self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
                num_composites = random.randint(2, 3)
                for _ in range(num_composites):
                    self.add_shape_no_retry("CompositeShape")
        # Exclude composite shapes from basic shapes.
        num_current_shapes = self.get_total_number_of_shapes()
        num_basic_shapes = random.choices(range(2, self.global_max_shapes + 1), weights=[1 if i not in (4, 5) else 2 for i in range(2, self.global_max_shapes + 1)])[0]
        
        basic_types = [st for st in shape_types if st != "CompositeShape"]
        for i in range(num_basic_shapes):
            print(self.shapes, UniqueIDGenerator.counters)
            if i < self.get_total_number_of_shapes():
                continue
            new_current_shapes = self.get_total_number_of_shapes()
            st = random.choice(basic_types)
            self.add_shape_no_retry(st)
        while len(self.shapes) < 1:
            st = random.choice(basic_types)
            self.add_shape_no_retry(st)
        if random.random() < 0.99:
            # Choose a random label between 1 and 50 and an actual length between 1/10 and 1/3 of the canvas width.
            scale_label = random.randint(1, 50)
            actual_length = random.uniform(self.canvas_width / 10, self.canvas_width / 3)
            self.scale_factor = actual_length / scale_label
            angle = random.uniform(0, 2 * math.pi)
            dx, dy = actual_length * math.cos(angle), actual_length * math.sin(angle)
            p1 = (random.uniform(max(0, -dx), min(self.canvas_width, self.canvas_width - dx)),
                random.uniform(max(0, -dy), min(self.canvas_height, self.canvas_height - dy)))
            p2 = (p1[0] + dx, p1[1] + dy)
            scale_line = Line(p1=p1, p2=p2, thickness=2, canvas=self.canvas)
            scale_line.set_label(str(scale_label))
            # Mark this line as the scale indicator.
            scale_line.is_scale_line = True
            self.shapes.append(scale_line)
            self.scale_line_present = True
        else:
            self.scale_line_present = False
            self.scale_factor = 1.0

        

    def get_shapes_by_type(self) -> Dict[str, List[Any]]:
        """Return a dictionary mapping shape types (including hierarchical aliases) to lists of shapes (including children recursively)."""
        result: Dict[str, List[Any]] = {}
        def add_shape_and_children(shape: Any) -> None:
            # Get the hierarchical aliases for the shape.
            for alias in self.get_hierarchical_aliases(shape):
                if alias not in result:
                    result[alias] = []
                result[alias].append(shape)
            children = shape.get_children()
            if children:
                for child in children:
                    add_shape_and_children(child)
        for shape in self.shapes:
            add_shape_and_children(shape)
        return result

    def get_hierarchical_aliases(self, shape: Any) -> List[str]:
        """
        Returns a list of aliases for the shape.
        Uses shape.get_alias() (the specific type, e.g. "Square") and shape.ALIAS (the main type, e.g. "Rectangle").
        If they differ, both are returned so that questions can be generated properly.
        """
        specific = shape.get_alias()   # e.g. "Square" or "Circle"
        main = shape.ALIAS             # e.g. "Rectangle" for a square, "Oval" for a circle
        aliases = [specific]
        if specific.lower() != main.lower():
            aliases.append(main)
        return aliases
    def is_ancestor(self, ancestor: Any, descendant: Any) -> bool:
        """
        Recursively checks if 'ancestor' is an ancestor (or parent) of 'descendant'.
        This is done by checking the children (via get_children()).
        """
        children = ancestor.get_children()
        if not children:
            return False
        for child in children:
            if child.get_identifier() == descendant.get_identifier():
                return True
            if self.is_ancestor(child, descendant):
                return True
        return False

    def is_related(self, shape1: Any, shape2: Any) -> bool:
        """
        Returns True if shape1 is an ancestor/descendant of shape2.
        This helps avoid counting intersections between a shape and its own components.
        """
        return self.is_ancestor(shape1, shape2) or self.is_ancestor(shape2, shape1)

        
    
    def get_total_number_of_shapes(self) -> int:
        """Return the total number of unique shapes (including children recursively)."""
        unique_shapes = set()
        for shape in self.get_flattened_shapes():
            unique_shapes.add(shape.get_identifier())  # assuming each shape has a unique identifier
        return len(unique_shapes)

    def count_shapes_by_type(self) -> Dict[str, int]:
        """Return a dictionary mapping shape types to counts."""
        shapes_by_type = self.get_shapes_by_type()
        return {k: len(v) for k, v in shapes_by_type.items()}

    def all_shapes_valid(self) -> bool:
        """Check that all shapes in the scene pass enforce_bounds."""
        try:
            for shape in self.shapes:
                shape.enforce_bounds()
            return True
        except Exception:
            return False

    def render(self, ax: Optional[Any] = None, dpi: int = 100) -> Tuple[Any, Any]:
        """
        Render the scene to a matplotlib figure after verifying all shapes are within bounds.
        The figure is created such that one coordinate unit approximately equals one pixel,
        while the overall image size remains as intended.
        """
        if not self.all_shapes_valid():
            raise ValueError("Not all shapes are within bounds before rendering.")
        
        # Create a figure sized exactly to the canvas dimensions (in inches) given the dpi.
        if ax is None:
            fig_width = self.canvas_width / dpi
            fig_height = self.canvas_height / dpi
            fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi)
            # Use an axes that spans the entire figure to match the canvas exactly.
            ax = fig.add_axes([0, 0, 1, 1])
        else:
            fig = ax.figure
        
        # Set axes limits to match canvas dimensions.
        ax.set_xlim(0, self.canvas_width)
        ax.set_ylim(0, self.canvas_height)
        
        # Render each shape.
        for shape in self.shapes:
            shape.render(ax)
        
        ax.axis('off')
        return fig, ax
    def get_flattened_shapes(self):
        def collect_children(node):
            children = node.get_children()
            if not children:
                return [node]
            flattened = [node]
            for child in children:
                flattened.extend(collect_children(child))
            return flattened
        
        flattened_shapes = []
        for shape in self.shapes:
            flattened_shapes.extend(collect_children(shape))
        
        return flattened_shapes
    
    def _collect_flattened_shapes(self, shape: Any) -> List[Any]:
        # Helper to recursively collect a flattened list of shapes from a single shape.
        def collect_children(node):
            children = node.get_children()
            if not children:
                return [node]
            flattened = [node]
            for child in children:
                flattened.extend(collect_children(child))
            return flattened
        return collect_children(shape)
    
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
        from shapes import scale_shape  # import the scaling function

        # ---- Modified scaling for skill trace ----
        use_scale = False
        scale_info = ""
        if self.scale_line_present:
            use_scale = True
            scale_factor = self.scale_factor
            scale_info = f" I see a line labeled with a number that I assume is its length; using that as a context clue, I will assume everything in the image is at that scale, and scale by {scale_factor:.2f} from pixel space."
            shapes_for_trace = []
            for shape in self.shapes:
                # Produce a scaled copy for skill trace only (rendering remains unchanged)
                scaled_shape = scale_shape(shape, scale_factor)
                shapes_for_trace.extend(self._collect_flattened_shapes(scaled_shape))
        else:
            scale_info = " I will use a pixel as a unit, which may not correspond to in-image measurements, and put the origin at the bottom-left corner. "
            shapes_for_trace = self.get_flattened_shapes()
        # ---- End modified scaling ----

        def flatten_and_merge(tree):
            # merged: key -> object id, value is a tuple ([list of detail strings], is_leaf)
            merged = {}
            processed = set()

            def collect_info(node):
                obj_id = node.get("object", "").strip()
                detail = node.get("details", "")
                has_children = "children" in node and bool(node["children"])
                # Extract detail text cleanly.
                detail_text = ""
                if isinstance(detail, str):
                    detail_text = detail.strip()
                elif isinstance(detail, list):
                    detail_parts = [d.get("details", "").strip() for d in detail 
                                    if isinstance(d, dict) and d.get("details", "").strip()]
                    detail_text = "; ".join(detail_parts)
                if obj_id:
                    if obj_id in merged:
                        merged[obj_id][1] = merged[obj_id][1] and (not has_children)
                        if detail_text and detail_text not in merged[obj_id][0]:
                            merged[obj_id][0].append(detail_text)
                    else:
                        merged[obj_id] = ([detail_text] if detail_text else [], not has_children)
                if has_children:
                    for child in node["children"]:
                        collect_info(child)
            collect_info(tree)

            def build_ordered_list(node):
                result = []
                obj_id = node.get("object", "").strip()
                has_children = "children" in node and bool(node["children"])
                if has_children:
                    for child in node["children"]:
                        result.extend(build_ordered_list(child))
                if obj_id and obj_id not in processed:
                    obj_type = obj_id.split("#")[0]
                    detail_list, is_leaf = merged.get(obj_id, ([], True))
                    merged_details = "; ".join([part for part in detail_list if part])
                    result.append((obj_id, obj_type, merged_details, is_leaf))
                    processed.add(obj_id)
                return result

            return build_ordered_list(tree)

        global_indices = defaultdict(int)
        total_counts = defaultdict(int)
        shape_lines = []
        seen_objects = set()

        for shape in shapes_for_trace:
            tree = shape.perform_skills()
            flattened = flatten_and_merge(tree)
            line_parts = []
            for obj_id, obj_type, details, is_leaf in flattened:
                if obj_id in seen_objects:
                    continue
                seen_objects.add(obj_id)
                idx = global_indices[obj_type]
                global_indices[obj_type] += 1
                if is_leaf:
                    total_counts[obj_type] += 1
                part = f"{obj_id}: "
                if isinstance(details, str):
                    part += details
                else:
                    part += details
                line_parts.append(part)
            if line_parts:
                shape_lines.append(" | ".join(line_parts))

        leaf_counts = defaultdict(int)
        for shape in shapes_for_trace:
            if not shape.get_children():
                shape_type = shape.ALIAS
                leaf_counts[shape_type] += 1
        leaf_parts = []
        for shape_type, count in leaf_counts.items():
            leaf_parts.append(f"{count} {shape_type.lower()}{'s' if count != 1 else ''}")
        leaf_sentence = "There are approximately " + " and ".join(leaf_parts) + "."
        composite_aliases = []
        for shape in shapes_for_trace:
            if getattr(shape, "is_composite", False):
                alias = getattr(shape, "ALIAS", None)
                composite_aliases.append(alias)
        composite_aliases = list(set(composite_aliases))
        if composite_aliases:
            if len(composite_aliases) == 1:
                composite_sentence = f" I see a repeated complex object in the image; I will call it {composite_aliases[0]}."
            else:
                composite_sentence = f" I see repeated complex objects in the image; I will call them {' and '.join(composite_aliases)}."
        else:
            composite_sentence = ""
        header = leaf_sentence + composite_sentence + scale_info

        return header + "\n" + " ".join(shape_lines)

    
    
    def save_to_json(self, filename: str, question: str, answer: str, path: str, alpaca_output: bool = False) -> Dict[str, Any]:
        """
        Save the scene, question, and answer to a JSON file in single-line JSON format.
        Also, save the image immediately.
        
        If alpaca_output is True, use a different assistant output format.
        """
        scene_id = str(uuid.uuid4().hex)
        image_path = f"{path}/scene_{scene_id}.png"
        if not self.all_shapes_valid():
            raise ValueError("Final scene contains shapes out of bounds.")
        skill_trace = self.get_skill_trace()
        if alpaca_output:
            # Example Alpaca-style output formatting.
            assistant_response = (
                f"Question: {question}\n"
                f"Answer: {answer}\n"
                f"Skill Trace:\n{skill_trace}"
            )
        else:
            assistant_response = (
                f"The scene contains 2D shapes or geometry. Before I answer, let me parse them: {skill_trace}\n"
                f"I will now use that information and return to the original question: '{question}' - the answer is {answer}."
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

    
    
    def generate_question_and_answer(self) -> Tuple[str, str, List[str]]:
        """
        Generate a random question and its answer based on the current scene.
        No retries are done; the question is computed from the scene as is.
        Returns a tuple of (question_text, answer, list_of_shape_identifiers)
        """
        question_types = ["existence", "intersection", "intersection_count", 
                        "position", "count", "multiple_count", "most_common", "area_comparison"]
        chosen = random.choice(question_types)
        shapes_by_type = self.get_shapes_by_type()
        shapes_involved: List[str] = []

        if chosen == "existence":
            # Use natural shape names instead of internal keys.
            valid = ["Circle", "Oval", "Square", "Rectangle", "Triangle", "Polygon"]
            # 90% chance to pick an object type already in the scene if possible.
            if random.random() < 0.9 and shapes_by_type:
                target = random.choice(list(shapes_by_type.keys()))
            else:
                target = random.choice(valid)
            if target in shapes_by_type and len(shapes_by_type[target]) > 0:
                shape_obj = random.choice(shapes_by_type[target])
                shapes_involved = [shape_obj.get_identifier()]
                s = self.describe_object(shape_obj)
                answer = f"there is a {s} present. Therefore, yes"
            else:
                answer = "no"
                shapes_involved = []
            question_text = f"Is there a {target} in this image?"
            return question_text, answer, shapes_involved


        elif chosen == "intersection" or True:
            # 90% chance to use objects from the scene if at least two different types exist.
            if random.random() < 0.9 and len(list(shapes_by_type.keys())) >= 2:
                shape1 = random.choice(list(shapes_by_type.keys()))
                shape2 = random.choice([st for st in list(shapes_by_type.keys()) if st != shape1])
            else:
                shape_types = list(self.shape_classes.keys())
                shape1 = random.choice(shape_types)
                shape2 = random.choice(shape_types)
            exists = False
            shape_int1 = None
            shape_int2 = None
            if shape1 in shapes_by_type and shape2 in shapes_by_type:
                for s1 in shapes_by_type[shape1]:
                    for s2 in shapes_by_type[shape2]:
                        # Skip if one shape is an ancestor or descendant of the other.
                        if self.is_related(s1, s2):
                            continue
                        if self.shapes_intersect(s1, s2):
                            exists = True
                            shape_int1 = s1
                            shape_int2 = s2
                            break
                    if exists:
                        break
            if exists:
                answer = f"that I see a {self.describe_object(shape_int1)} and a {self.describe_object(shape_int2)} intersecting with each other. So, my final answer is yes"
                shapes_involved = [shape_int1.get_identifier(), shape_int2.get_identifier()]
            else:
                answer = f"there is no such {replace_polygon(shape1.replace('Solid', ''))} overlapping with a {replace_polygon(shape2.replace('Solid', ''))} in this image. So, no"
                shapes_involved = []
            question_text = f"Does a {replace_polygon(shape1.replace('Solid',''))} intersect with a {replace_polygon(shape2.replace('Solid',''))} in this image? Do not count parts of objects intersecting with themselves."
            return question_text, answer, shapes_involved


        elif chosen == "intersection_count":
            if random.random() < 0.9 and len(list(shapes_by_type.keys())) >= 2:
                shape1 = random.choice(list(shapes_by_type.keys()))
                shape2 = random.choice([st for st in list(shapes_by_type.keys()) if st != shape1])
            else:
                valid = ["Circle", "Oval", "Square", "Rectangle", "Triangle", "Polygon"]
                shape1 = random.choice(valid)
                shape2 = random.choice(valid)
            intersection_pairs = set()  # use frozenset to deduplicate pairs
            if shape1 in shapes_by_type and shape2 in shapes_by_type:
                for s1 in shapes_by_type[shape1]:
                    for s2 in shapes_by_type[shape2]:
                        # Avoid comparing a shape with itself and skip if one is an ancestor of the other.
                        if s1.get_identifier() == s2.get_identifier() or self.is_related(s1, s2):
                            continue
                        if self.shapes_intersect(s1, s2):
                            pair = frozenset({s1.get_identifier(), s2.get_identifier()})
                            intersection_pairs.add(pair)
            count = len(intersection_pairs)
            question_text = f"How many {shape1}s intersect with {shape2}s in this image? Do not count parts of objects intersecting with themselves."
            shapes_involved = []  # Optionally, you could list some of the identifiers from the pairs.
            return question_text, str(count), shapes_involved


        elif chosen == "position":
            valid = [s for s in self.shape_classes.keys() if s != "Line"]
            if random.random() < 0.9 and len(list(shapes_by_type.keys())) >= 2:
                shape1 = random.choice(list(shapes_by_type.keys()))
                shape2 = random.choice([st for st in list(shapes_by_type.keys()) if st != shape1])
            else:
                shape1 = random.choice(valid)
                shape2 = random.choice(valid)
            relation = random.choice(["above", "below", "left of", "right of"])
            
            exists = False
            shape_int1 = None
            shape_int2 = None
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
                            shape_int1 = s1
                            shape_int2 = s2
                            break
                    if exists:
                        break
            if exists:
                answer = f",because a {self.describe_object(shape_int1)} is entirely {relation} a {self.describe_object(shape_int2)}, yes"
                shapes_involved = [shape_int1.get_identifier(), shape_int2.get_identifier()]
            else:
                answer = f"there is no {shape1.replace('Solid', '')} entirely {relation} a {shape2.replace('Solid', '')} in the image provided, so no"
                shapes_involved = []
            question_text = f"Is there a {replace_polygon(shape1.replace('Solid',''))} entirely {relation} a {replace_polygon(shape2.replace('Solid',''))} in this image?"
            return question_text, answer, shapes_involved

        elif chosen == "count":
            valid = ["Circle", "Oval", "Square", "Rectangle", "Triangle", "Polygon"]
            if random.random() < 0.9 and shapes_by_type:
                target = random.choice(list(shapes_by_type.keys()))
            else:
                target = random.choice(valid)
            count = len(shapes_by_type.get(target, []))
            if target in shapes_by_type and shapes_by_type[target]:
                shape_obj = random.choice(shapes_by_type[target])
                shapes_involved = [shape_obj.get_identifier()]
            else:
                shapes_involved = []
            question_text = f"How many {target}s are there in this image?"
            return question_text, str(count), shapes_involved


        elif chosen == "multiple_count":
            valid = ["Circle", "Oval", "Square", "Rectangle", "Triangle", "Polygon"]
            if random.random() < 0.9 and len(list(shapes_by_type.keys())) >= 2:
                shape1 = random.choice(list(shapes_by_type.keys()))
                shape2 = random.choice([st for st in list(shapes_by_type.keys()) if st != shape1])
            else:
                shape1 = random.choice(valid)
                shape2 = random.choice([s for s in valid if s != shape1])
            # Compute the union of shapes (by unique identifier) to avoid double counting.
            union_ids = set()
            if shape1 in shapes_by_type:
                union_ids.update(s.get_identifier() for s in shapes_by_type[shape1])
            if shape2 in shapes_by_type:
                union_ids.update(s.get_identifier() for s in shapes_by_type[shape2])
            count = len(union_ids)
            
            # For shapes_involved, we can include one representative from each category.
            involved = []
            if shape1 in shapes_by_type:
                involved.append(random.choice(shapes_by_type[shape1]).get_identifier())
            if shape2 in shapes_by_type:
                involved.append(random.choice(shapes_by_type[shape2]).get_identifier())
            question_text = f"How many {shape1}s and {shape2}s are there in this image?"
            return question_text, str(count), involved


        elif chosen == "most_common":
            counts = {k: len(v) for k, v in shapes_by_type.items()}
            if not counts:
                answer = "N/A"
                question_text = "Which shape appears the most times in this picture?"
                shapes_involved = []
            else:
                max_count_val = max(counts.values())
                most_common = [k for k, v in counts.items() if v == max_count_val]
                answer = ", ".join([replace_polygon(mc.replace('Solid','')) for mc in most_common])
                # choose one representative object if possible
                if most_common and shapes_by_type.get(most_common[0]):
                    shapes_involved = [random.choice(shapes_by_type[most_common[0]]).get_identifier()]
                else:
                    shapes_involved = []
                question_text = "Which shape appears the most times in this image?"
            return question_text, answer, shapes_involved

        elif chosen == "area_comparison":
            shapes = self.get_flattened_shapes()
            highest_shape = None
            highest_area = -math.inf
            lowest_area = math.inf
            lowest_shape = None
            for shape in shapes:
                try:
                    area = shape.get_area()
                    if area > highest_area and area > 0:
                        highest_area = area
                        highest_shape = shape
                    if area < lowest_area and area > 0:
                        lowest_area = area
                        lowest_shape = shape
                except Exception:
                    continue
            relation = random.choice(["highest", "lowest"])
            if relation == "highest":
                best = highest_shape
            else:
                best = lowest_shape
            question_text = f"Which shape-type has the shape with the {relation} area in this image?"
            if best:
                answer = f"the {self.describe_object(best)} has the {relation} area, so {replace_polygon(best.get_alias())}"
                shapes_involved = [best.get_identifier()]
            else:
                answer = "there are no shapes with non-undefined area in the scene"
                shapes_involved = []
            return question_text, answer, shapes_involved

    
    
    def describe_object(self, shape):
        shape_name = replace_polygon(shape.get_alias())
        color = shape.get_color()
        label = shape.get_label()
        color_desc = (color + " ") if color else ""
        label_desc = (" labeled as "  + label + " ") if label else ""
        description = f"{color_desc}{shape_name}{label_desc}"
        return description
def generate_dataset(output_file: str="scene_dataset7.json", num_examples: int=50, output_image_path: str="output") -> None:
    """
    Generate a dataset of scenes and questions.
    Each entry is output in a single-line JSON format.
    This function generates each scene once without retries.
    """
    generator = SceneGenerator()
    
    with open(output_file, 'w') as f_out:
        for _ in range(num_examples):
            generator = SceneGenerator()
            generator.generate_random_scene()
            question, answer, shapes = generator.generate_question_and_answer()
            temp_file = f"temp_scene_{uuid.uuid4().hex}.json"
            try:
                json_entry = generator.save_to_json(temp_file, question, answer, output_image_path)
            except Exception as e:
                print(e)
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
    
    try:
        fig, ax = generator.render()
        plt.show()
    except Exception as e:
        print("Rendering failed:", e)
    
    generate_dataset(num_examples=1, output_image_path="/n/fs/penciller/skilltree2/geometry/output-tests")
