import math
import random, string
import json
import matplotlib
import matplotlib.pyplot as plt
import re
from decimal import Decimal, ROUND_HALF_UP
import copy
from utilities import color_to_name
# Disable interactive mode and set backend for consistency.
plt.ioff()
matplotlib.use("Agg", force=True)


class UniqueIDGenerator:
    counters = {}
    _checkpoint = None

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

    @staticmethod
    def save_checkpoint():
        UniqueIDGenerator._checkpoint = copy.deepcopy(UniqueIDGenerator.counters)

    @staticmethod
    def load_checkpoint():
        if UniqueIDGenerator._checkpoint is not None:
            UniqueIDGenerator.counters = copy.deepcopy(UniqueIDGenerator._checkpoint)
        else:
            raise ValueError("No checkpoint has been saved.")
class PlotObject:
    # Default canvas dimensions. No part of any object should be outside [0,0]-[CANVAS_WIDTH,CANVAS_HEIGHT].
    CANVAS_WIDTH = 800
    CANVAS_HEIGHT = 600

    ALIAS = "PlotObject"

    def __init__(self):
        self.obj_id = UniqueIDGenerator.get_unique_id(self.ALIAS)
        self._geometry_locked = False
        self.sub_references = []  # For future composite objects; currently not used.
        # Optional visual attributes
        self.label = None              # Text label (optional)
        self.has_border = False        # Shapes (except lines) can have borders.
        self.border_color = "black"    # Color for border.
        self.fill_color = "none"       # Fill color (default is transparent).
        
        # Note: Coordinates/geometry attributes will be defined in subclasses.
    def __str__(self):
        """Return label if set, otherwise a default string consisting of the alias and id."""
        return self.label if self.label is not None else f"{self.ALIAS}#{self.obj_id}"
    def _assign_geometry(self):
        """Assign geometry to self and propagate to children if necessary."""
        for child in self.sub_references:
            child.assign_geometry()

    def perform_skills(self, verbose=False):
        """Collect and return a skills tree of this object."""
        children = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        tree = {"action": "Base", "object": f"{self.ALIAS}#{self.obj_id}", "children": children}
        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)
        return tree
    def lock_geometry(self):
        self._geometry_locked = True
        if hasattr(self, "create_children") and callable(self.create_children):
            self.create_children()
    def skills_tree_to_text(self, tree, indent=0):
        """Helper to convert a skills tree dict into indented text lines."""
        lines = [(" " * indent) + f"{tree['action']} -> {tree['object']}"]
        for child in tree.get("children", []):
            lines.extend(self.skills_tree_to_text(child, indent + 4))
        return lines
    def get_children(self):
        """Method to get children shapes; returns a list of PlotObjects. If there are none, returns None"""
        return getattr(self, 'children', None)
    def get_color(self):
        color = getattr(self, 'color', None)
        if color:
            return color
        try:
            fill_color = getattr(self, 'fill_color', None)
            border_color = getattr(self, 'border_color', None)
            return color_to_name(fill_color) + " and " + color_to_name(border_color)
        except:
            return None
    def get_label(self):
        return self.label
    def get_alias(self):
        return self.ALIAS
    def get_area(self):
        if hasattr(self, 'p1') or hasattr(self, 'p2') or getattr(self, 'is_composite', False):
            return 0
        alias = self.ALIAS
        if alias == 'Oval':
            return math.pi * (self.width / 2) * (self.height / 2)

        elif alias == 'Rectangle':
            return self.width * self.height

        elif alias == 'Triangle':
            return 0.5 * abs(self.vertices[0][0] * (self.vertices[1][1] - self.vertices[2][1]) +
                             self.vertices[1][0] * (self.vertices[2][1] - self.vertices[0][1]) +
                             self.vertices[2][0] * (self.vertices[0][1] - self.vertices[1][1]))

        elif alias == 'Polygon':
            vertices = self.vertices
            n = len(vertices)
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += vertices[i][0] * vertices[j][1]
                area -= vertices[j][0] * vertices[i][1]
            return abs(area) / 2.0

        else:
            return 0  # Default to 0 if shape is unknown
    def render(self, ax):
        """Render self (and children) on the provided matplotlib axis."""
        for child in self.sub_references:
            child.render(ax)  
    def __repr__(self):
        return f"{self.ALIAS}#{self.obj_id}"
    def set_label(self):
        import random
        import string

        choice = random.random()
        if random.random() < .25:
            clist = self.get_children()
            for c in clist:
                if random.random() < .25:
                    c.set_label()
            return
            

        if choice < 1/3:
            # Random string with first letter capitalized
            length = random.randint(3, 10)
            random_string = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
            self.label = random_string.capitalize()
        elif choice < 2/3:
            # Number between 1 and 1000
            self.label = str(random.randint(1, 1000))
        elif choice < 2/3 + 1/4:
            # Random alphanumeric string
            length = random.randint(3, 10)
            self.label = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
        else:
            # Two random words from two lists of nouns
            nouns_list1 = ["Apple", "Mountain", "Ocean", "Forest", "Diamond", "Castle", "River", "Desert", "Island", "Galaxy", "Thunder", "Crystal", "Dragon", "Phoenix", "Emerald", "Banana", "President", "Large", "Small", "Giant"]
            nouns_list2 = ["Wizard", "Knight", "Hunter", "Tiger", "Eagle", "Falcon", "Warrior", "Shadow", "Spirit", "Legend", "Phantom", "Guardian", "Titan", "Voyager", "Pioneer", "Winner", "Object", "Shape-thing", "Cannonball"]
            
            noun1 = random.choice(nouns_list1)
            noun2 = random.choice(nouns_list2)
            self.label = f"{noun1} {noun2}"
    def set_bottom_left(self, x, y, angle=0, **kwargs):
        """To be overridden by subclasses to set the shape’s position."""
        pass
    def to_dict(self):
        """Export object structure as a JSON–serializable dict."""
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

    def apply_transformation(self, func):
        """
        Recursively apply an affine transformation function to all coordinate attributes.
        Expected to transform any attribute that is a 2-tuple representing a coordinate.
        """
        for attr in ['p1', 'p2', 'center', 'base_position']:
            if hasattr(self, attr):
                value = getattr(self, attr)
                if value is not None and isinstance(value, tuple) and len(value) == 2:
                    setattr(self, attr, func(value))
        if hasattr(self, 'vertices') and self.vertices is not None:
            self.vertices = [func(v) if v is not None else None for v in self.vertices]
        for child in self.sub_references:
            child.apply_transformation(func)

    def get_bbox(self):
        """
        Return an exact bounding box as (min_x, min_y, max_x, max_y).
        This method looks for known attributes (p1/p2, center with dimensions, or vertices)
        and falls back to children bboxes if needed.
        """
        # Case 1: Defined by two points (e.g. a line)
        if hasattr(self, 'p1') and hasattr(self, 'p2') and self.p1 and self.p2:
            return (min(self.p1[0], self.p2[0]),
                    min(self.p1[1], self.p2[1]),
                    max(self.p1[0], self.p2[0]),
                    max(self.p1[1], self.p2[1]))
        # Case 2: Defined by center, width, and height (e.g. rectangle, triangle, oval)
        if hasattr(self, 'center') and hasattr(self, 'width') and hasattr(self, 'height'):
            return (self.center[0] - self.width/2, self.center[1] - self.height/2,
                    self.center[0] + self.width/2, self.center[1] + self.height/2)
        # Case 3: Defined by vertices (could be used for polygons and triangles)
        if hasattr(self, 'vertices') and self.vertices:
            xs = [v[0] for v in self.vertices if v is not None]
            ys = [v[1] for v in self.vertices if v is not None]
            return (min(xs), min(ys), max(xs), max(ys))
        # Fall back: Use children’s bounding boxes.
        bboxes = [child.get_bbox() for child in self.sub_references if hasattr(child, "get_bbox")]
        if bboxes:
            return (min(b[0] for b in bboxes),
                    min(b[1] for b in bboxes),
                    max(b[2] for b in bboxes),
                    max(b[3] for b in bboxes))
        return (0, 0, 0, 0)

    def enforce_bounds(self):
        bbox = self.get_bbox()
        xmin, xmax, ymin, ymax = self.canvas
        if (bbox[0] < xmin or bbox[2] > xmax or bbox[1] < ymin or bbox[3] > ymax):
            raise ValueError(f"Shape exceeds canvas bounds: {bbox} vs canvas {self.canvas}")
    

    def generate_random_label(self, label_type="alpha", length=6):
        """
        Generate and assign a random label.
        label_type options:
         - "alpha": a random alphanumeric string.
         - "number": a random integer string.
         - "word": a word-like label (first letter capitalized, followed by lowercase letters).
        """
        if label_type == "alpha":
            # Random mix of letters and digits.
            chars = string.ascii_letters + string.digits
            self.label = ''.join(random.choice(chars) for _ in range(length))
        elif label_type == "number":
            # Random number between 0 and 10^length - 1.
            self.label = str(random.randint(0, 10**length - 1))
        elif label_type == "word":
            # Generate a word-like label: first letter capital, then random lowercase letters.
            word_length = random.randint(3, max(3, length))
            self.label = random.choice(string.ascii_uppercase) + ''.join(random.choice(string.ascii_lowercase) for _ in range(word_length - 1))
        else:
            raise ValueError("label_type must be 'alpha', 'number', or 'word'")
        return self.label

    ##########################################################################
    # Numerical integration methods for exact area and centroid estimation.
    ##########################################################################
    def numerical_area(self, resolution=100):
        """Estimate the area of the shape by sampling over its bounding box."""
        bbox = self.get_bbox()
        min_x, min_y, max_x, max_y = bbox
        dx = (max_x - min_x) / resolution
        dy = (max_y - min_y) / resolution
        count = 0
        for i in range(resolution):
            for j in range(resolution):
                x = min_x + (i + 0.5) * dx
                y = min_y + (j + 0.5) * dy
                if self.contains_point((x, y)):
                    count += 1
        return count / (resolution * resolution) * ((max_x - min_x) * (max_y - min_y))

    def numerical_centroid(self, resolution=100):
        """Estimate the centroid of the shape by sampling over its bounding box."""
        bbox = self.get_bbox()
        min_x, min_y, max_x, max_y = bbox
        dx = (max_x - min_x) / resolution
        dy = (max_y - min_y) / resolution
        sum_x = 0
        sum_y = 0
        count = 0
        for i in range(resolution):
            for j in range(resolution):
                x = min_x + (i + 0.5) * dx
                y = min_y + (j + 0.5) * dy
                if self.contains_point((x, y)):
                    sum_x += x
                    sum_y += y
                    count += 1
        if count == 0:
            return ((min_x + max_x) / 2, (min_y + max_y) / 2)
        return (sum_x / count, sum_y / count)

    ##########################################################################
    # New methods for intersect and relative_position between shapes.
    # These use numerical integration over the exact shape boundaries.
    ##########################################################################
    def intersect(self, other, resolution=100):
        """
        Compute the percent overlap between this shape and another shape using numerical integration.
        Returns a tuple:
          (overlap_percentage_of_self, overlap_percentage_of_other)
        """
        # Determine the overlapping region between the bounding boxes.
        bbox1 = self.get_bbox()
        bbox2 = other.get_bbox()
        inter_min_x = max(bbox1[0], bbox2[0])
        inter_min_y = max(bbox1[1], bbox2[1])
        inter_max_x = min(bbox1[2], bbox2[2])
        inter_max_y = min(bbox1[3], bbox2[3])
        if inter_min_x >= inter_max_x or inter_min_y >= inter_max_y:
            return (0.0, 0.0)
        dx = (inter_max_x - inter_min_x) / resolution
        dy = (inter_max_y - inter_min_y) / resolution
        count = 0
        for i in range(resolution):
            for j in range(resolution):
                x = inter_min_x + (i + 0.5) * dx
                y = inter_min_y + (j + 0.5) * dy
                if self.contains_point((x, y)) and other.contains_point((x, y)):
                    count += 1
        inter_area = count / (resolution * resolution) * ((inter_max_x - inter_min_x) * (inter_max_y - inter_min_y))
        area_self = self.numerical_area(resolution)
        area_other = other.numerical_area(resolution)
        overlap_self = inter_area / area_self if area_self > 0 else 0
        overlap_other = inter_area / area_other if area_other > 0 else 0
        return (overlap_self, overlap_other)

    def relative_position(self, other, resolution=100):
        """
        Compute the vector between the non-overlapping mass distributions of self and other
        using numerical integration.
        Returns a tuple:
          (overlap_percentage_self, overlap_percentage_other, scaled_vector)
        where scaled_vector is computed as the vector between the centroids of the non-overlapping areas,
        scaled by (non_overlap_self + non_overlap_other) / (overlap_area + epsilon).
        """
        # First compute intersection area and also build masks of points.
        bbox1 = self.get_bbox()
        bbox2 = other.get_bbox()
        inter_min_x = max(bbox1[0], bbox2[0])
        inter_min_y = max(bbox1[1], bbox2[1])
        inter_max_x = min(bbox1[2], bbox2[2])
        inter_max_y = min(bbox1[3], bbox2[3])
        dx = dy = 1  # For integration over individual shapes, we use the grid spacing from their bbox.
        # For non-overlap, we integrate over each shape's bbox.
        def compute_non_overlap(shape, other_shape, resolution):
            bbox = shape.get_bbox()
            min_x, min_y, max_x, max_y = bbox
            dx = (max_x - min_x) / resolution
            dy = (max_y - min_y) / resolution
            sum_x = 0
            sum_y = 0
            count = 0
            for i in range(resolution):
                for j in range(resolution):
                    x = min_x + (i + 0.5) * dx
                    y = min_y + (j + 0.5) * dy
                    if shape.contains_point((x, y)) and not (other_shape.contains_point((x, y))):
                        sum_x += x
                        sum_y += y
                        count += 1
            area = count / (resolution * resolution) * ((max_x - min_x) * (max_y - min_y))
            centroid = (sum_x / count, sum_y / count) if count > 0 else shape.numerical_centroid(resolution)
            return area, centroid

        area_self = self.numerical_area(resolution)
        area_other = other.numerical_area(resolution)
        # Intersection area
        if inter_min_x < inter_max_x and inter_min_y < inter_max_y:
            inter_dx = (inter_max_x - inter_min_x) / resolution
            inter_dy = (inter_max_y - inter_min_y) / resolution
            inter_count = 0
            sum_ix = 0
            sum_iy = 0
            for i in range(resolution):
                for j in range(resolution):
                    x = inter_min_x + (i + 0.5) * inter_dx
                    y = inter_min_y + (j + 0.5) * inter_dy
                    if self.contains_point((x, y)) and other.contains_point((x, y)):
                        inter_count += 1
                        sum_ix += x
                        sum_iy += y
            inter_area = inter_count / (resolution * resolution) * ((inter_max_x - inter_min_x) * (inter_max_y - inter_min_y))
            int_centroid = (sum_ix / inter_count, sum_iy / inter_count) if inter_count > 0 else ((inter_min_x+inter_max_x)/2, (inter_min_y+inter_max_y)/2)
        else:
            inter_area = 0
            int_centroid = ((bbox1[0]+bbox1[2])/2, (bbox1[1]+bbox1[3])/2)

        non_area_self, non_cent_self = compute_non_overlap(self, other, resolution)
        non_area_other, non_cent_other = compute_non_overlap(other, self, resolution)

        # Vector from self's non-overlap centroid to other's non-overlap centroid.
        vec = (non_cent_other[0] - non_cent_self[0], non_cent_other[1] - non_cent_self[1])
        scale_factor = (non_area_self + non_area_other) / (inter_area + 1e-6)
        scaled_vec = (vec[0] * scale_factor, vec[1] * scale_factor)

        overlap_self = inter_area / area_self if area_self > 0 else 0
        overlap_other = inter_area / area_other if area_other > 0 else 0
        return (overlap_self, overlap_other, scaled_vec)

    # Default contains_point method; to be overridden in subclasses.
    def contains_point(self, point):
        # By default, we assume the object does not define an interior.
        return False