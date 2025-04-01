import random
import json
import uuid
import matplotlib.pyplot as plt
import math
import os
from typing import List, Dict, Tuple, Any, Optional, Union

# Import shapes (assume these classes are implemented elsewhere)
from shapes import Line, SolidOval, SolidRectangle, SolidTriangle, SolidPolygon
from shapes import CompositeShapeGenerator  # New composite shape generator

class SceneGenerator:
    """Class for generating scenes of geometric shapes based on different constraints and question types."""
    
    def __init__(self, canvas_size=(800, 600), max_attempts=100):
        """Initialize a scene generator."""
        self.canvas_width, self.canvas_height = canvas_size
        self.canvas = (0, self.canvas_width, 0, self.canvas_height)
        self.max_attempts = max_attempts
        self.shapes = []
        self.shape_classes = {
            "Line": Line,
            "SolidOval": SolidOval,
            "SolidRectangle": SolidRectangle,
            "SolidTriangle": SolidTriangle,
            "SolidPolygon": SolidPolygon
        }
        # Add composite shape generator and include its shape class.
        self.composite_shape_gen = CompositeShapeGenerator(canvas=self.canvas)
        self.shape_classes["CompositeShape"] = self.composite_shape_gen.ComponentShape

    def reset(self):
        """Clear all shapes in the scene."""
        self.shapes = []

    def shapes_intersect(self, shape1, shape2, resolution=50):
        """Returns True if shape1 and shape2 have an intersection over a small threshold."""
        overlap_self, overlap_other = shape1.intersect(shape2, resolution=resolution)
        threshold = 0.000001  # Very small threshold to detect minimal intersections
        return overlap_self > threshold or overlap_other > threshold

    def is_valid_placement(self, shape, intersect_rules, position_rules, shape_amounts):
        """Check if a shape placement is valid according to the given rules."""
        shape_type = shape.__class__.__name__
        
        # Check position constraints
        if shape_type in position_rules and position_rules[shape_type]:
            x_min, x_max, y_min, y_max = position_rules[shape_type]
            bbox = shape.get_bbox()
            if (bbox[0] < x_min or bbox[2] > x_max or 
                bbox[1] < y_min or bbox[3] > y_max):
                return False
        
        # Check intersection constraints
        if shape_type in intersect_rules and intersect_rules[shape_type]:
            intersections = {}
            for other_shape in self.shapes:
                other_type = other_shape.__class__.__name__
                if self.shapes_intersect(shape, other_shape):
                    intersections[other_type] = intersections.get(other_type, 0) + 1
            
            for other_type, max_count in intersect_rules[shape_type]:
                if other_type in intersections and intersections[other_type] > max_count:
                    return False
        
        # Check shape amount constraints
        shapes_by_type = self.get_shapes_by_type()
        if shape_type in shape_amounts and shape_amounts[shape_type]:
            min_count, max_count = shape_amounts[shape_type]
            current_count = len(shapes_by_type.get(shape_type, []))
            if current_count >= max_count:
                return False
        
        return True

    def add_shape(self, shape_type, intersect_rules={}, position_rules={}, shape_amounts={}, **kwargs):
        """Add a shape of the given type to the scene with the given constraints."""
        if shape_type not in self.shape_classes:
            raise ValueError(f"Unknown shape type: {shape_type}")
        
        ShapeClass = self.shape_classes[shape_type]
        
        for _ in range(self.max_attempts):
            shape = ShapeClass(canvas=self.canvas, **kwargs)
            shape.assign_geometry()
            if self.is_valid_placement(shape, intersect_rules, position_rules, shape_amounts):
                self.shapes.append(shape)
                return shape
        
        return None

    def get_shapes_by_type(self):
        """Return a dictionary mapping shape types to lists of shapes of that type."""
        result = {}
        for shape in self.shapes:
            shape_type = shape.__class__.__name__
            if shape_type not in result:
                result[shape_type] = []
            result[shape_type].append(shape)
        return result

    def count_shapes_by_type(self):
        """Return a dictionary mapping shape types to count of shapes."""
        shapes_by_type = self.get_shapes_by_type()
        return {k: len(v) for k, v in shapes_by_type.items()}

    def add_background_composite_shapes(self):
        """
        Add composite shapes to the background.
        Rule: if one composite shape is added, add at least 3 (up to 5) copies.
        They are generated at a small scale so they do not interfere with the question.
        """
        # Decide randomly whether to add background composite shapes.
        if random.random() < 0.5:
            num_instances = random.randint(3, 5)
            for _ in range(num_instances):
                x = random.uniform(0, self.canvas_width)
                y = random.uniform(0, self.canvas_height)
                # Use a small scale (e.g., 0.3) and a random rotation.
                shape = self.composite_shape_gen.generate_shape(center=(x, y), scale=0.3, angle=random.uniform(0, 360))
                self.shapes.append(shape)

    def render(self, ax=None, figsize=(10, 8)):
        """Render the scene to a matplotlib figure."""
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
                part = f"{obj_type} {idx}:"
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
        header_parts = []
        for obj_type, count in total_counts.items():
            header_parts.append(f"{count} {obj_type.lower()}{'s' if count != 1 else ''}")
        header = "There are approximately " + " and ".join(header_parts) + "."

        return header + "\n" + "\n".join(shape_lines)

    
    def save_to_json(self, filename, question, answer, path):
        """Save the scene, question, and answer to a JSON file in a single-line JSON format.
        Also, save the image immediately."""
        scene_id = str(uuid.uuid4().hex)
        image_path = f"{path}/scene_{scene_id}.png"
        skill_trace = self.get_skill_trace()
        assistant_response = (
            f"The scene contains shapes. Before I answer the question, let me parse the geometric shapes. {skill_trace}\n"
            f"After analyzing, I will now return to the original question: '{question}' - the answer is {answer}."
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

    #####################################################################
    # Methods for generating specific types of question scenes
    #####################################################################
    
    def generate_existence_scene(self, target_shape, min_shapes=3, max_shapes=6):
        """Generate a scene for 'Is there an X in this image?' questions."""
        self.reset()
        include_target = random.random() > 0.5
        num_shapes = random.randint(min_shapes, max_shapes)
        shape_types = list(self.shape_classes.keys())
        if include_target:
            self.add_shape(target_shape)
            num_shapes -= 1
        for _ in range(num_shapes):
            shape_type = random.choice([s for s in shape_types if s != target_shape])
            self.add_shape(shape_type)
        # Add background composite shapes (ensuring if one is added, at least 3 are added)
        self.add_background_composite_shapes()
        question = f"Is there a {target_shape.replace('Solid', '')} in this image?"
        answer = "Yes" if include_target else "No"
        return question, answer
    
    def generate_intersection_scene(self, shape_type1, shape_type2):
        """Generate a scene for 'Does an X intersect with a Y?' questions."""
        self.reset()
        should_intersect = random.random() > 0.5
        shape1 = self.add_shape(shape_type1)
        if should_intersect:
            for _ in range(self.max_attempts):
                shape2 = self.add_shape(shape_type2)
                if shape2 and self.shapes_intersect(shape1, shape2):
                    break
                if shape2:
                    self.shapes.remove(shape2)
        else:
            intersect_rules = {shape_type2: [(shape_type1, 0)]}
            self.add_shape(shape_type2, intersect_rules=intersect_rules)
        for _ in range(random.randint(1, 3)):
            st = random.choice(list(self.shape_classes.keys()))
            self.add_shape(st)
        self.add_background_composite_shapes()
        shape1_name = shape_type1.replace('Solid', '')
        shape2_name = shape_type2.replace('Solid', '')
        question = f"Does a {shape1_name} intersect with a {shape2_name} in this image?"
        shapes_by_type = self.get_shapes_by_type()
        intersection_exists = False
        if shape_type1 in shapes_by_type and shape_type2 in shapes_by_type:
            for s1 in shapes_by_type[shape_type1]:
                for s2 in shapes_by_type[shape_type2]:
                    if self.shapes_intersect(s1, s2):
                        intersection_exists = True
                        break
        answer = "Yes" if intersection_exists else "No"
        return question, answer

    def generate_intersection_count_scene(self, shape_type1, shape_type2, max_count=5):
        """Generate a scene for 'How many X intersect with Ys?' questions."""
        self.reset()
        target_intersections = random.randint(0, max_count)
        num_type1 = random.randint(max(1, target_intersections), max_count + 2)
        for _ in range(num_type1):
            self.add_shape(shape_type1)
        shapes_by_type = self.get_shapes_by_type()
        type1_shapes = shapes_by_type.get(shape_type1, [])
        intersecting_shapes1 = random.sample(type1_shapes, min(target_intersections, len(type1_shapes)))
        for shape1 in intersecting_shapes1:
            for _ in range(self.max_attempts):
                shape2 = self.add_shape(shape_type2)
                if shape2 and self.shapes_intersect(shape1, shape2):
                    break
                if shape2:
                    self.shapes.remove(shape2)
        num_non_intersecting = random.randint(0, 3)
        for _ in range(num_non_intersecting):
            intersect_rules = {shape_type2: [(shape_type1, 0)]}
            self.add_shape(shape_type2, intersect_rules=intersect_rules)
        shapes_by_type = self.get_shapes_by_type()
        intersection_count = 0
        if shape_type1 in shapes_by_type and shape_type2 in shapes_by_type:
            for shape1 in shapes_by_type[shape_type1]:
                for shape2 in shapes_by_type[shape_type2]:
                    if self.shapes_intersect(shape1, shape2):
                        intersection_count += 1
                        break
        self.add_background_composite_shapes()
        shape1_name = shape_type1.replace('Solid', '')
        shape2_name = shape_type2.replace('Solid', '')
        question = f"How many {shape1_name}s intersect with {shape2_name}s in this image?"
        answer = str(intersection_count)
        return question, answer

    def generate_position_scene(self, shape_type1, shape_type2, position):
        """Generate a scene for 'Is there an X above/below/left/right of a Y?' questions."""
        self.reset()
        should_satisfy = random.random() > 0.5
        if should_satisfy:
            if position == "above":
                shape2 = self.add_shape(shape_type2)
                bbox2 = shape2.get_bbox()
                position_rules = {shape_type1: (0, self.canvas_width, bbox2[3], self.canvas_height)}
                self.add_shape(shape_type1, position_rules=position_rules)
            elif position == "below":
                shape2 = self.add_shape(shape_type2)
                bbox2 = shape2.get_bbox()
                position_rules = {shape_type1: (0, self.canvas_width, 0, bbox2[1])}
                self.add_shape(shape_type1, position_rules=position_rules)
            elif position == "left of":
                shape2 = self.add_shape(shape_type2)
                bbox2 = shape2.get_bbox()
                position_rules = {shape_type1: (0, bbox2[0], 0, self.canvas_height)}
                self.add_shape(shape_type1, position_rules=position_rules)
            elif position == "right of":
                shape2 = self.add_shape(shape_type2)
                bbox2 = shape2.get_bbox()
                position_rules = {shape_type1: (bbox2[2], self.canvas_width, 0, self.canvas_height)}
                self.add_shape(shape_type1, position_rules=position_rules)
        else:
            self.add_shape(shape_type1)
            self.add_shape(shape_type2)
        for _ in range(random.randint(1, 3)):
            st = random.choice(list(self.shape_classes.keys()))
            self.add_shape(st)
        self.add_background_composite_shapes()
        shape1_name = shape_type1.replace('Solid', '')
        shape2_name = shape_type2.replace('Solid', '')
        question = f"Is there a {shape1_name} {position} a {shape2_name} in this image?"
        shapes_by_type = self.get_shapes_by_type()
        is_true = False
        if shape_type1 in shapes_by_type and shape_type2 in shapes_by_type:
            for shape1 in shapes_by_type[shape_type1]:
                for shape2 in shapes_by_type[shape_type2]:
                    bbox1 = shape1.get_bbox()
                    bbox2 = shape2.get_bbox()
                    if (position == "above" and bbox1[1] > bbox2[3]) or \
                       (position == "below" and bbox1[3] < bbox2[1]) or \
                       (position == "left of" and bbox1[2] < bbox2[0]) or \
                       (position == "right of" and bbox1[0] > bbox2[2]):
                        is_true = True
                        break
        answer = "Yes" if is_true else "No"
        return question, answer

    def generate_count_scene(self, target_shape, min_count=0, max_count=5):
        """Generate a scene for 'How many X are there?' questions."""
        self.reset()
        count = random.randint(min_count, max_count)
        for _ in range(count):
            self.add_shape(target_shape)
        num_others = random.randint(1, 5)
        shape_types = [s for s in self.shape_classes.keys() if s != target_shape]
        for _ in range(num_others):
            st = random.choice(shape_types)
            self.add_shape(st)
        self.add_background_composite_shapes()
        shape_name = target_shape.replace('Solid', '')
        question = f"How many {shape_name}s are there in this image?"
        answer = str(count)
        return question, answer

    def generate_multiple_count_scene(self, shape_type1, shape_type2, max_count=5):
        """Generate a scene for 'How many X and Y are there?' questions."""
        self.reset()
        count1 = random.randint(0, max_count)
        count2 = random.randint(0, max_count)
        for _ in range(count1):
            self.add_shape(shape_type1)
        for _ in range(count2):
            self.add_shape(shape_type2)
        num_others = random.randint(1, 3)
        shape_types = [s for s in self.shape_classes.keys() if s not in [shape_type1, shape_type2]]
        for _ in range(num_others):
            st = random.choice(shape_types)
            self.add_shape(st)
        self.add_background_composite_shapes()
        shape1_name = shape_type1.replace('Solid', '')
        shape2_name = shape_type2.replace('Solid', '')
        question = f"How many {shape1_name}s and {shape2_name}s are there in this image?"
        answer = str(count1 + count2)
        return question, answer

    def generate_most_common_scene(self, min_total=5, max_total=10):
        """Generate a scene for 'What shape occurs the most?' questions."""
        self.reset()
        total_shapes = random.randint(min_total, max_total)
        # Include composite shapes as candidates by using the full keys from shape_classes.
        shape_types = list(self.shape_classes.keys())
        chosen_majority = random.choice(shape_types)
        majority_count = int(total_shapes * random.uniform(0.4, 0.6))
        remaining_count = total_shapes - majority_count
        other_types = [t for t in shape_types if t != chosen_majority]
        other_counts = [0] * len(other_types)
        for _ in range(remaining_count):
            idx = random.randint(0, len(other_types) - 1)
            other_counts[idx] += 1
        for _ in range(majority_count):
            self.add_shape(chosen_majority)
        for shape_type, count in zip(other_types, other_counts):
            for _ in range(count):
                self.add_shape(shape_type)
        self.add_background_composite_shapes()
        question = "What shape occurs the most in this image?"
        # The answer may now be a composite shape as well.
        answer = chosen_majority.replace('Solid', '')
        return question, answer

    def generate_area_comparison_scene(self, comparison_type="highest"):
        """Generate a scene for 'Which shape has the highest/lowest area?' questions."""
        self.reset()
        shape_types = list(self.shape_classes.keys())
        target_shape = random.choice(shape_types)
        for shape_type in shape_types:
            if shape_type == target_shape:
                if comparison_type == "highest":
                    if shape_type == "SolidOval":
                        radius = random.uniform(80, 120)
                        self.add_shape(shape_type, width=radius*2, height=radius*2, is_circle=True)
                    elif shape_type == "SolidRectangle":
                        width = random.uniform(150, 200)
                        height = random.uniform(150, 200)
                        self.add_shape(shape_type, width=width, height=height)
                    else:
                        self.add_shape(shape_type)
                else:
                    if shape_type == "SolidOval":
                        radius = random.uniform(10, 20)
                        self.add_shape(shape_type, width=radius*2, height=radius*2, is_circle=True)
                    elif shape_type == "SolidRectangle":
                        width = random.uniform(20, 40)
                        height = random.uniform(20, 40)
                        self.add_shape(shape_type, width=width, height=height)
                    else:
                        self.add_shape(shape_type)
            else:
                if shape_type == "SolidOval":
                    radius = random.uniform(30, 60)
                    self.add_shape(shape_type, width=radius*2, height=radius*2, is_circle=True)
                elif shape_type == "SolidRectangle":
                    width = random.uniform(60, 100)
                    height = random.uniform(60, 100)
                    self.add_shape(shape_type, width=width, height=height)
                else:
                    self.add_shape(shape_type)
        self.add_background_composite_shapes()
        question = f"Which shape has the {comparison_type} area in this image?"
        answer = target_shape.replace('Solid', '')
        return question, answer

    def generate_scene_with_constraints(self, intersect_rules={}, position_rules={}, shape_amounts={}, question_type="", **kwargs):
        """Generate a scene based on provided constraints for a specific question type.
        
        This version randomly selects valid shape types (including the CompositeShape option)
        based on the question type. For example, questions about area comparison will never use
        a "Line" (which has no area). Other types are chosen from all valid keys.
        """
        # Define valid shape lists per question type.
        valid_for_existence = [s for s in self.shape_classes.keys() if s not in ["Line"]]
        valid_for_intersection = list(self.shape_classes.keys())  # All shapes allowed.
        valid_for_position = [s for s in self.shape_classes.keys() if s not in ["Line"]]
        valid_for_count = [s for s in self.shape_classes.keys() if s not in ["Line"]]
        valid_for_multiple_count = [s for s in self.shape_classes.keys() if s not in ["Line"]]
        valid_for_area = [s for s in self.shape_classes.keys() if s not in ["Line"]]

        if question_type == "existence":
            target_shape = kwargs.get("target_shape", random.choice(valid_for_existence))
            return self.generate_existence_scene(target_shape)
        elif question_type == "intersection":
            shape_type1 = kwargs.get("shape_type1", random.choice(valid_for_intersection))
            shape_type2 = kwargs.get("shape_type2", random.choice(valid_for_intersection))
            return self.generate_intersection_scene(shape_type1, shape_type2)
        elif question_type == "intersection_count":
            shape_type1 = kwargs.get("shape_type1", random.choice(valid_for_intersection))
            shape_type2 = kwargs.get("shape_type2", random.choice(valid_for_intersection))
            return self.generate_intersection_count_scene(shape_type1, shape_type2)
        elif question_type == "position":
            shape_type1 = kwargs.get("shape_type1", random.choice(valid_for_position))
            shape_type2 = kwargs.get("shape_type2", random.choice(valid_for_position))
            position = kwargs.get("position", random.choice(["above", "below", "left of", "right of"]))
            return self.generate_position_scene(shape_type1, shape_type2, position)
        elif question_type == "count":
            target_shape = kwargs.get("target_shape", random.choice(valid_for_count))
            return self.generate_count_scene(target_shape)
        elif question_type == "multiple_count":
            shape_type1 = kwargs.get("shape_type1", random.choice(valid_for_multiple_count))
            shape_type2 = kwargs.get("shape_type2", random.choice(valid_for_multiple_count))
            return self.generate_multiple_count_scene(shape_type1, shape_type2)
        elif question_type == "most_common":
            return self.generate_most_common_scene()
        elif question_type == "area_comparison":
            comparison_type = kwargs.get("comparison_type", random.choice(["highest", "lowest"]))
            # Only choose shapes that have an area (i.e. excluding Line)
            return self.generate_area_comparison_scene(comparison_type)
        else:
            # For a custom scene, randomly distribute shapes across all valid types.
            self.reset()
            for shape_type, (min_count, max_count) in shape_amounts.items():
                if max_count > 0:
                    count = random.randint(min_count, max_count)
                    for _ in range(count):
                        self.add_shape(shape_type, intersect_rules, position_rules, shape_amounts)
            self.add_background_composite_shapes()
            return "Custom scene created", "N/A"


def generate_dataset(output_file="scene_dataset.json", num_examples=50, output_image_path="output"):
    """Generate a dataset of scenes and questions.
    Each question-answer-image JSON entry is printed immediately in single-line JSON format
    and also written to the output file line-by-line.
    """
    generator = SceneGenerator()
    
    question_types = [
        "existence", "intersection", "intersection_count", 
        "position", "count", "multiple_count", 
        "most_common", "area_comparison"
    ]
    
    with open(output_file, 'w') as f_out:
        for _ in range(num_examples):
            # Randomly select a question type and generate scene
            question_type = random.choice(question_types)
            question, answer = generator.generate_scene_with_constraints(question_type=question_type)
            
            # Save scene immediately (image is saved during this call)
            temp_file = f"temp_scene_{uuid.uuid4().hex}.json"
            json_entry = generator.save_to_json(temp_file, question, answer, output_image_path)
            
            # Remove the temporary JSON file used internally
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            # Convert the entry to a single-line JSON string and output it immediately
            json_line = json.dumps(json_entry, separators=(',',':'))
            print(json_line)
            f_out.write(json_line + "\n")
    
    print(f"Generated {num_examples} examples and saved to {output_file}")
if __name__ == "__main__":
    # Example usage
    generator = SceneGenerator()
    
    # Example: Generate an existence question for rectangles
    question, answer = generator.generate_scene_with_constraints(question_type="existence", target_shape="SolidRectangle")
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    # Example: Generate an intersection question
    question, answer = generator.generate_scene_with_constraints(question_type="intersection", 
                                                               shape_type1="SolidRectangle", 
                                                               shape_type2="Line")
    print(f"Question: {question}")
    print(f"Answer: {answer}")
    
    # Example: Generate with specific constraints
    intersect_rules = {
        "SolidRectangle": [("Line", 1)],  # rectangle can intersect with a line once
        "SolidTriangle": [],
        "SolidOval": [],
        "SolidPolygon": [],
        "Line": []
    }
    
    position_rules = {
        "SolidRectangle": (0, 300, 0, 300),  # can only appear in this box
        "SolidTriangle": [],
        "SolidOval": [],
        "SolidPolygon": [],
        "Line": []
    }
    
    shape_amounts = {
        "SolidRectangle": (1, 3),  # min 1, max 3
        "SolidTriangle": (0, 4),   # min 0, max 4
        "SolidOval": (1, 2),       # min 1, max 2
        "SolidPolygon": (0, 1),    # min 0, max 1
        "Line": (2, 5)             # min 2, max 5
    }
    
    # Generate a custom scene with constraints
    generator.generate_scene_with_constraints(
        intersect_rules=intersect_rules,
        position_rules=position_rules,
        shape_amounts=shape_amounts
    )
    
    # Visualize
    fig, ax = generator.render()
    plt.show()
    
    # Generate a small dataset
    generate_dataset(num_examples=10, output_image_path="/n/fs/penciller/skilltree2/geometry/output")
