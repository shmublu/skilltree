import math
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import json
import bisect
import os
import re

from .base import PlotObject, skills_tree_to_text
from .utilities import get_line_length_and_angle, rotate_point

###############################################################################
# Utility functions for style and geometry completion
###############################################################################
def random_color():
    if random.random() < 0.5: # 50% chance to return "black"
        return "black"
    else:
        return random.choice(["red", "blue", "green", "purple", "orange"])

def random_thickness():
    return random.uniform(1, 3)

def propagate_style(parent):
    """Force every child to use parent's color and thickness."""
    for child in parent.sub_references:
        child.color = parent.color
        child.thickness = parent.thickness
        if hasattr(child, "sub_references") and child.sub_references:
            propagate_style(child)

###############################################################################
# Low-Level: Line
###############################################################################
class LineLow(PlotObject):
    ALIAS = "Line"

    def __init__(self, p1=None, p2=None, color=None, thickness=None, canvas=(0, 100, 0, 100)):
        # Note: PlotObject's __init__ is assumed to be a pass-through or similar.
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        self.p1 = p1  # may be None
        self.p2 = p2  # may be None
        self._geometry_locked = (self.p1 is not None and self.p2 is not None)
    
    def _check_bounds(self):
        # Check that both endpoints have non-negative coordinates.
        if (self.p1[0] < 0 or self.p1[1] < 0 or
            self.p2[0] < 0 or self.p2[1] < 0):
            raise ValueError("Line endpoints must have non-negative coordinates.")
    
    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            canvas_width = xmax - xmin
            canvas_height = ymax - ymin
            # Determine allowed length based on canvas dimensions.
            min_possible_length = max(5, min(canvas_width, canvas_height) * 0.15)
            max_possible_length = min(canvas_width, canvas_height) * 0.8
            # If both endpoints missing, choose a random length and angle
            if self.p1 is None and self.p2 is None:
                L = random.uniform(min_possible_length, max_possible_length)
                angle = random.uniform(0, 360)
                rad = math.radians(angle)
                dx = L * math.cos(rad)
                dy = L * math.sin(rad)
                # Choose p1 so that p2 remains within canvas bounds.
                if dx >= 0:
                    x_low = xmin
                    x_high = xmax - dx
                else:
                    x_low = xmin - dx
                    x_high = xmax
                if dy >= 0:
                    y_low = ymin
                    y_high = ymax - dy
                else:
                    y_low = ymin - dy
                    y_high = ymax
                self.p1 = (random.uniform(x_low, x_high), random.uniform(y_low, y_high))
                self.p2 = (self.p1[0] + dx, self.p1[1] + dy)
            elif self.p1 is not None and self.p2 is None:
                # p1 fixed; choose p2 offset based on random length & angle.
                L = random.uniform(min_possible_length, max_possible_length)
                angle = random.uniform(0, 360)
                rad = math.radians(angle)
                dx = L * math.cos(rad)
                dy = L * math.sin(rad)
                p2_candidate = (self.p1[0] + dx, self.p1[1] + dy)
                # Clamp candidate to canvas bounds.
                p2_candidate = (min(max(p2_candidate[0], xmin), xmax),
                                min(max(p2_candidate[1], ymin), ymax))
                self.p2 = p2_candidate
            # (If p1 is None but p2 is provided, we leave them as-is.)
            self._geometry_locked = True
            # Check that the computed endpoints are non-negative.
            self._check_bounds()
            # If there were any parent class geometry assignments, call them here.
            # super().assign_geometry()  # Uncomment if PlotObject.assign_geometry() exists.
    
    def perform_skills(self, verbose=False):
        # Ensure geometry is assigned and valid
        if self.p1 is None or self.p2 is None:
            self.assign_geometry()
        self._check_bounds()
        length, angle = get_line_length_and_angle(self.p1, self.p2)
        tree = {
            "action": "RecognizeInstanceLine",
            "object": f"Line#{self.obj_id}",
            "children": [
                {"action": "LocalizeLine", "object": f"Line#{self.obj_id}", "details": f"(Endpoints: {self.p1}, {self.p2})"},
                {"action": "MeasureLine", "object": f"Line#{self.obj_id}", "details": f"(Length={length:.1f}, Angle={angle:.1f})"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        self._check_bounds()
        ax.plot([self.p1[0], self.p2[0]],
                [self.p1[1], self.p2[1]],
                color=self.color, lw=self.thickness)

    def set_bottom_left(self, x, y, angle=0, length=10, **kwargs):
        rad = math.radians(angle)
        self.p1 = (x, y)
        self.p2 = (x + length * math.cos(rad), y + length * math.sin(rad))
        self._geometry_locked = True
        # Check that new endpoints are non-negative.
        self._check_bounds()

    def get_bbox(self):
        return (min(self.p1[0], self.p2[0]),
                min(self.p1[1], self.p2[1]),
                max(self.p1[0], self.p2[0]),
                max(self.p1[1], self.p2[1]))

###############################################################################
# Low-Level: Oval
###############################################################################
class OvalLow(PlotObject):
    ALIAS = "Oval"

    def __init__(self, center=None, width=None, height=None, angle=None, color=None, thickness=None, canvas=(0, 100, 0, 100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        self.center = center  # may be None
        self.width = width    # may be None
        self.height = height  # may be None
        self.angle = angle    # may be None
        self._geometry_locked = (center is not None and width is not None and height is not None and angle is not None)
    
    def _check_bounds(self):
        # Calculate the rotated bounding box extents for the ellipse.
        # Semi-axes lengths:
        a = self.width / 2.0
        b = self.height / 2.0
        theta = math.radians(self.angle)
        # The offsets along x and y:
        x_offset = abs(a * math.cos(theta)) + abs(b * math.sin(theta))
        y_offset = abs(a * math.sin(theta)) + abs(b * math.cos(theta))
        x_min = self.center[0] - x_offset
        y_min = self.center[1] - y_offset
        if x_min < 0 or y_min < 0:
            raise ValueError("Oval's circumference must have non-negative coordinates.")
    
    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            canvas_width = xmax - xmin
            canvas_height = ymax - ymin
            if self.width is None:
                self.width = random.uniform(canvas_width * 0.15, canvas_width * 0.7)
            if self.height is None:
                self.height = random.uniform(canvas_height * 0.15, canvas_height * 0.7)
            if self.center is None:
                cx = random.uniform(xmin + self.width/2, xmax - self.width/2)
                cy = random.uniform(ymin + self.height/2, ymax - self.height/2)
                self.center = (cx, cy)
            if self.angle is None:
                self.angle = random.uniform(0, 360)
            self._geometry_locked = True
            # Check that the oval’s circumferential bounding box is non-negative.
            self._check_bounds()
            # If there were any parent class geometry assignments, call them here.
            # super().assign_geometry()  # Uncomment if PlotObject.assign_geometry() exists.
    
    def perform_skills(self, verbose=False):
        # Ensure geometry is assigned and valid.
        if not self._geometry_locked:
            self.assign_geometry()
        self._check_bounds()
        area = math.pi * (self.width / 2.0) * (self.height / 2.0)
        tree = {
            "action": "RecognizeInstanceOval",
            "object": f"Oval#{self.obj_id}",
            "children": [
                {"action": "LocalizeOval", "object": f"Oval#{self.obj_id}", "details": f"(Center={self.center}, W={self.width}, H={self.height}, Angle={self.angle:.1f})"},
                {"action": "MeasureOval", "object": f"Oval#{self.obj_id}", "details": f"(Area={area:.1f})"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        self._check_bounds()
        e = Ellipse(xy=self.center,
                    width=self.width,
                    height=self.height,
                    angle=self.angle,
                    edgecolor=self.color,
                    facecolor='none',
                    lw=self.thickness)
        ax.add_patch(e)

    def set_bottom_left(self, x, y, angle=0, width=10, height=10, **kwargs):
        rad = math.radians(angle)
        offset_x = width / 2.0
        offset_y = height / 2.0
        rotated_cx = x + offset_x * math.cos(rad) - offset_y * math.sin(rad)
        rotated_cy = y + offset_x * math.sin(rad) + offset_y * math.cos(rad)
        self.center = (rotated_cx, rotated_cy)
        self.width = width
        self.height = height
        self.angle = angle
        self._geometry_locked = True
        # Check that the oval’s circumferential bounding box is non-negative.
        self._check_bounds()

    def get_bbox(self):
        # Compute the axis-aligned bounding box for the rotated ellipse.
        a = self.width / 2.0
        b = self.height / 2.0
        theta = math.radians(self.angle)
        x_offset = abs(a * math.cos(theta)) + abs(b * math.sin(theta))
        y_offset = abs(a * math.sin(theta)) + abs(b * math.cos(theta))
        return (self.center[0] - x_offset,
                self.center[1] - y_offset,
                self.center[0] + x_offset,
                self.center[1] + y_offset)


###############################################################################
# Rectangle (with 4 lines)
###############################################################################
class RectangleObj(PlotObject):
    ALIAS = "Rectangle"

    def __init__(self, center=None, width=None, height=None, angle=None, color=None, thickness=None, canvas=(0,100,0,100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        self.center = center      # may be None
        self.width = width        # may be None
        self.height = height      # may be None
        self.angle = angle        # may be None
        self._geometry_locked = (center is not None and width is not None and height is not None and angle is not None)
        self.sub_references = []
        for _ in range(4):
            line = LineLow(color=self.color, thickness=self.thickness, canvas=self.canvas)
            self.sub_references.append(line)

    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        xmin, xmax, ymin, ymax = self.canvas
        canvas_width = xmax - xmin
        canvas_height = ymax - ymin
        if not self._geometry_locked:
            if self.center is None:
                if self.width is None:
                    self.width = random.uniform(canvas_width * 0.15, canvas_width * 0.7)
                if self.height is None:
                    self.height = random.uniform(canvas_height * 0.15, canvas_height * 0.7)
                if self.angle is None:
                    self.angle = random.uniform(0, 180)
                # Estimate bounding box dimensions after rotation.
                rad = math.radians(self.angle)
                bbox_width = abs(self.width * math.cos(rad)) + abs(self.height * math.sin(rad))
                bbox_height = abs(self.width * math.sin(rad)) + abs(self.height * math.cos(rad))
                cx = random.uniform(xmin + bbox_width/2, xmax - bbox_width/2)
                cy = random.uniform(ymin + bbox_height/2, ymax - bbox_height/2)
                self.center = (cx, cy)
            else:
                if self.width is None:
                    self.width = random.uniform(canvas_width * 0.1, canvas_width * 0.3)
                if self.height is None:
                    self.height = random.uniform(canvas_height * 0.1, canvas_height * 0.3)
                if self.angle is None:
                    self.angle = random.uniform(0, 180)
            half_w = self.width / 2.0
            half_h = self.height / 2.0
            corners = [
                (self.center[0] - half_w, self.center[1] - half_h),
                (self.center[0] + half_w, self.center[1] - half_h),
                (self.center[0] + half_w, self.center[1] + half_h),
                (self.center[0] - half_w, self.center[1] + half_h),
            ]
            if self.angle != 0:
                corners = [rotate_point(c, self.center, self.angle) for c in corners]
            lines = self.sub_references
            if len(lines) == 4:
                for i in range(4):
                    lines[i].p1 = corners[i]
                    lines[i].p2 = corners[(i + 1) % 4]
                    lines[i]._geometry_locked = True
            super().assign_geometry()
            propagate_style(self)
            self._geometry_locked = True

    def perform_skills(self, verbose=False):
        children_trees = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        line_ids = [child.obj_id for child in self.sub_references if isinstance(child, LineLow)]
        tree = {
            "action": "GroupLine",
            "object": f"Rectangle#{self.obj_id}",
            "details": f"from lineIDs={line_ids}",
            "children": children_trees + [
                {"action": "RecognizeInstanceRectangle", "object": f"Rectangle#{self.obj_id}"},
                {"action": "LocalizeRectangle", "object": f"Rectangle#{self.obj_id}", "details": f"(W={self.width:.1f}, H={self.height:.1f}, Angle={self.angle:.1f})"},
                {"action": "MeasureRectangle", "object": f"Rectangle#{self.obj_id}", "details": f"(Area={self.width*self.height:.1f}, Perimeter={2*(self.width+self.height):.1f})"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    def set_bottom_left(self, x, y, angle=0, width=10, height=10, **kwargs):
        self.width = width
        self.height = height
        self.angle = angle
        rad = math.radians(angle)
        offset_x = width / 2.0
        offset_y = height / 2.0
        rotated_cx = x + offset_x * math.cos(rad) - offset_y * math.sin(rad)
        rotated_cy = y + offset_x * math.sin(rad) + offset_y * math.cos(rad)
        self.center = (rotated_cx, rotated_cy)
        self._geometry_locked = True

    def get_bbox(self):
        bboxes = [line.get_bbox() for line in self.sub_references if isinstance(line, LineLow)]
        if bboxes:
            min_x = min(b[0] for b in bboxes)
            min_y = min(b[1] for b in bboxes)
            max_x = max(b[2] for b in bboxes)
            max_y = max(b[3] for b in bboxes)
            return (min_x, min_y, max_x, max_y)
        return (self.center[0] - self.width/2, self.center[1] - self.height/2,
                self.center[0] + self.width/2, self.center[1] + self.height/2)

###############################################################################
# Triangle
###############################################################################
class TriangleObj(PlotObject):
    ALIAS = "Triangle"

    def __init__(self, vertices=None, color=None, thickness=None, canvas=(0,100,0,100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        # vertices should be a list of three (x,y) tuples; if not provided, leave as None
        self.vertices = vertices if vertices is not None and len(vertices) == 3 else [None, None, None]
        self._geometry_locked = (None not in self.vertices)
        self.sub_references = []
        for _ in range(3):
            line = LineLow(color=self.color, thickness=self.thickness, canvas=self.canvas)
            self.sub_references.append(line)

    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        xmin, xmax, ymin, ymax = self.canvas
        if not self._geometry_locked:
            new_vertices = []
            for v in self.vertices:
                if v is None:
                    new_vertices.append((random.uniform(xmin, xmax), random.uniform(ymin, ymax)))
                else:
                    new_vertices.append(v)
            self.vertices = new_vertices
            self._geometry_locked = True
        lines = self.sub_references
        if len(lines) == 3:
            for i in range(3):
                lines[i].p1 = self.vertices[i]
                lines[i].p2 = self.vertices[(i + 1) % 3]
                lines[i]._geometry_locked = True
        super().assign_geometry()
        propagate_style(self)

    def perform_skills(self, verbose=False):
        children_trees = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        line_ids = [child.obj_id for child in self.sub_references if isinstance(child, LineLow)]
        x1, y1 = self.vertices[0]
        x2, y2 = self.vertices[1]
        x3, y3 = self.vertices[2]
        area = abs(x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2)) / 2.0
        tree = {
            "action": "GroupLine",
            "object": f"Triangle#{self.obj_id}",
            "details": f"from lineIDs={line_ids}",
            "children": children_trees + [
                {"action": "RecognizeInstanceTriangle", "object": f"Triangle#{self.obj_id}"},
                {"action": "LocalizeTriangle", "object": f"Triangle#{self.obj_id}", "details": f"(Vertices={self.vertices})"},
                {"action": "MeasureTriangle", "object": f"Triangle#{self.obj_id}", "details": f"(Area={area:.1f})"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    def set_bottom_left(self, x, y, **kwargs):
        dx = kwargs.get("dx", 10)
        dy = kwargs.get("dy", 10)
        angle = kwargs.get("angle", 0)
        rad = math.radians(angle)
        v1 = (x, y)
        v2 = (x + dx * math.cos(rad), y + dx * math.sin(rad))
        v3 = (x + dy * math.cos(rad + math.pi/4), y + dy * math.sin(rad + math.pi/4))
        self.vertices = [v1, v2, v3]
        self._geometry_locked = True

    def get_bbox(self):
        xs = [v[0] for v in self.vertices if v is not None]
        ys = [v[1] for v in self.vertices if v is not None]
        return (min(xs), min(ys), max(xs), max(ys))

###############################################################################
# Polygon
###############################################################################
class PolygonObj(PlotObject):
    ALIAS = "Polygon"

    def __init__(self, vertices=None, center=None, sides=None, radius=None, angle=None, color=None, thickness=None, canvas=(0,100,0,100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None

        if vertices is not None and isinstance(vertices, list) and len(vertices) >= 3:
            self.vertices = vertices
            self.sides = len(vertices)
            self.center = None
            self.radius = None
            self.angle = None
            self._geometry_locked = True
        else:
            self.vertices = None
            self.center = center    # may be None
            self.sides = sides      # may be None
            self.radius = radius    # may be None
            self.angle = angle      # may be None
            self._geometry_locked = False

        self.sub_references = []
        for _ in range(10):
            line = LineLow(color=self.color, thickness=self.thickness, canvas=self.canvas)
            self.sub_references.append(line)

    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        xmin, xmax, ymin, ymax = self.canvas
        canvas_width = xmax - xmin
        canvas_height = ymax - ymin
        if not self._geometry_locked:
            if self.vertices is None:
                if self.center is None:
                    if self.radius is None:
                        min_possible = max(5, min(canvas_width, canvas_height)*0.1)
                        max_possible = min(canvas_width, canvas_height)*0.3
                        self.radius = random.uniform(min_possible, max_possible)
                    cx = random.uniform(xmin + self.radius, xmax - self.radius)
                    cy = random.uniform(ymin + self.radius, ymax - self.radius)
                    self.center = (cx, cy)
                else:
                    if self.radius is None:
                        min_possible = max(5, min(canvas_width, canvas_height)*0.1)
                        max_possible = min(canvas_width, canvas_height)*0.3
                        self.radius = random.uniform(min_possible, max_possible)
                if self.sides is None:
                    self.sides = random.randint(3, 6)
                if self.angle is None:
                    self.angle = random.uniform(0, 180)
                angle_step = 360.0 / self.sides
                corners = []
                for i in range(self.sides):
                    theta = math.radians(self.angle + i * angle_step)
                    px = self.center[0] + self.radius * math.cos(theta)
                    py = self.center[1] + self.radius * math.sin(theta)
                    corners.append((px, py))
                self.vertices = corners
            else:
                self.sides = len(self.vertices)
            self._geometry_locked = True

        lines = self.sub_references
        if len(lines) >= self.sides:
            for i in range(self.sides):
                lines[i].p1 = self.vertices[i]
                lines[i].p2 = self.vertices[(i + 1) % self.sides]
                lines[i]._geometry_locked = True
            for j in range(self.sides, len(lines)):
                lines[j].p1 = (0, 0)
                lines[j].p2 = (0, 0)
                lines[j]._geometry_locked = True
        super().assign_geometry()
        propagate_style(self)

    def perform_skills(self, verbose=False):
        used_lines = [child.perform_skills(verbose=verbose) 
                      for child in self.sub_references[:self.sides] if isinstance(child, LineLow)]
        line_ids = [child.obj_id for child in self.sub_references[:self.sides] if isinstance(child, LineLow)]
        area = 0
        for i in range(self.sides):
            x1, y1 = self.vertices[i]
            x2, y2 = self.vertices[(i + 1) % self.sides]
            area += x1 * y2 - y1 * x2
        area = abs(area) / 2.0
        tree = {
            "action": "GroupLine",
            "object": f"Polygon#{self.obj_id}",
            "details": f"from lineIDs={line_ids}",
            "children": used_lines + [
                {"action": "RecognizeInstancePolygon", "object": f"Polygon#{self.obj_id}"},
                {"action": "LocalizePolygon", "object": f"Polygon#{self.obj_id}", "details": f"(Sides={self.sides}, Angle={self.angle if self.angle is not None else 'N/A'})"},
                {"action": "MeasurePolygon", "object": f"Polygon#{self.obj_id}", "details": f"(Area={area:.1f})"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        line_count = self.sides
        used_lines = self.sub_references[:line_count]
        for sub in used_lines:
            sub.render(ax)

    def set_bottom_left(self, x, y, angle=0, sides=3, radius=10, **kwargs):
        self.sides = sides
        self.radius = radius
        self.angle = angle
        self.center = (x + radius, y)
        self.vertices = None  # clear any previously set vertices
        self._geometry_locked = False

    def get_bbox(self):
        xs = [v[0] for v in self.vertices if v is not None]
        ys = [v[1] for v in self.vertices if v is not None]
        return (min(xs), min(ys), max(xs), max(ys))

###############################################################################
# Arrow
###############################################################################
class ArrowObj(PlotObject):
    ALIAS = "Arrow"

    def __init__(self, start=None, length=None, angle=None, color=None, thickness=None, arrow_angle=None, head_size_percent=None, canvas=(0,100,0,100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        self.start = start    # may be None
        self.length = length  # may be None
        self.angle = angle    # may be None
        self.arrow_angle = arrow_angle           
        self.head_size_percent = head_size_percent 
        self._geometry_locked = (start is not None and length is not None and angle is not None)
        self.sub_references = []
        for _ in range(3):
            line = LineLow(color=self.color, thickness=self.thickness, canvas=self.canvas)
            self.sub_references.append(line)

    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        xmin, xmax, ymin, ymax = self.canvas
        canvas_width = xmax - xmin
        canvas_height = ymax - ymin
        min_possible_length = max(20, min(canvas_width, canvas_height) * 0.1)
        max_possible_length = min(canvas_width, canvas_height) * 0.8
        if not self._geometry_locked:
            L = self.length if self.length is not None else random.uniform(min_possible_length, max_possible_length)
            angle = self.angle if self.angle is not None else random.uniform(0, 180)
            rad = math.radians(angle)
            dx = L * math.cos(rad)
            dy = L * math.sin(rad)
            if dx >= 0:
                x_low = xmin
                x_high = xmax - dx
            else:
                x_low = xmin - dx
                x_high = xmax
            if dy >= 0:
                y_low = ymin
                y_high = ymax - dy
            else:
                y_low = ymin - dy
                y_high = ymax
            if self.start is None:
                self.start = (random.uniform(x_low, x_high), random.uniform(y_low, y_high))
            if self.length is None:
                self.length = L
            if self.angle is None:
                self.angle = angle
            self._geometry_locked = True
        rad = math.radians(self.angle)
        x1, y1 = self.start
        x2 = x1 + self.length * math.cos(rad)
        y2 = y1 + self.length * math.sin(rad)
        lines = self.sub_references
        if len(lines) == 3:
            lines[0].p1 = (x1, y1)
            lines[0].p2 = (x2, y2)
            lines[0]._geometry_locked = True
            
            arrow_angle = self.arrow_angle if self.arrow_angle is not None else random.uniform(20, 60)
            head_size_percent = self.head_size_percent if self.head_size_percent is not None else random.uniform(15, 37)
            head_size = self.length * (head_size_percent / 100)
            
            left_rad = math.radians(self.angle + 180 - arrow_angle)
            right_rad = math.radians(self.angle + 180 + arrow_angle)
            lx = x2 + head_size * math.cos(left_rad)
            ly = y2 + head_size * math.sin(left_rad)
            rx = x2 + head_size * math.cos(right_rad)
            ry = y2 + head_size * math.sin(right_rad)
            lines[1].p1 = (x2, y2)
            lines[1].p2 = (lx, ly)
            lines[1]._geometry_locked = True
            lines[2].p1 = (x2, y2)
            lines[2].p2 = (rx, ry)
            lines[2]._geometry_locked = True
        super().assign_geometry()
        propagate_style(self)

    def perform_skills(self, verbose=False):
        children_trees = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        rad = math.radians(self.angle)
        dx = math.cos(rad)
        dy = math.sin(rad)
        tree = {
            "action": "GroupLine",
            "object": f"Arrow#{self.obj_id}",
            "details": f"from lineIDs={[child.obj_id for child in self.sub_references if isinstance(child, LineLow)]}",
            "children": children_trees + [
                {"action": "RecognizeInstanceArrow", "object": f"Arrow#{self.obj_id}"},
                {"action": "LocalizeArrow", "object": f"Arrow#{self.obj_id}", "details": f"(Length={self.length:.1f}, Angle={self.angle:.1f})"},
                {"action": "MeasureArrow", "object": f"Arrow#{self.obj_id}", "details": f"(ShaftLength={self.length:.1f})"},
                {"action": "ArrowDirection", "object": f"Arrow#{self.obj_id}", "details": f"(Vector=({dx:.2f}, {dy:.2f}))"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    def set_bottom_left(self, x, y, angle=0, length=20, **kwargs):
        self.start = (x, y)
        self.length = length
        self.angle = angle
        self._geometry_locked = True

    def get_bbox(self):
        bboxes = [ln.get_bbox() for ln in self.sub_references if isinstance(ln, LineLow)]
        if bboxes:
            min_x = min(b[0] for b in bboxes)
            min_y = min(b[1] for b in bboxes)
            max_x = max(b[2] for b in bboxes)
            max_y = max(b[3] for b in bboxes)
            return (min_x, min_y, max_x, max_y)
        return (self.start[0], self.start[1], self.start[0] + self.length, self.start[1] + self.length)

###############################################################################
# Bars (multiple rectangles)
###############################################################################
class BarsObj(PlotObject):
    ALIAS = "Bars"

    def __init__(self,
                 num_bars=None,
                 angle=30,
                 min_width=5,
                 max_width=6,
                 spacing=None,
                 min_height=15,
                 max_height=30,
                 base_position=None,
                 color=None,
                 thickness=None,
                 canvas=(0,100,0,100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        self.num_bars = num_bars if num_bars is not None else random.randint(2, 5)
        self.angle = angle
        self.min_width = min_width
        self.max_width = max_width
        self.spacing = spacing if spacing is not None else random.uniform(5, 10)
        self.min_height = min_height
        self.max_height = max_height
        self.base_position = base_position  # may be None
        self._geometry_locked = (base_position is not None)
        self.bars_list = []
        self.sub_references = []
        # Pass the canvas to each rectangle.
        for _ in range(self.num_bars):
            rect = RectangleObj(color=self.color, thickness=self.thickness, canvas=self.canvas)
            self.bars_list.append(rect)
            self.sub_references.append(rect)

    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        xmin, xmax, ymin, ymax = self.canvas
        if not self._geometry_locked:
            # Choose a base position within the canvas taking some margins.
            if self.base_position is None:
                margin_x = (xmax - xmin) * 0.1
                margin_y = (ymax - ymin) * 0.1
                base_x = random.uniform(xmin + margin_x, xmax - margin_x)
                base_y = random.uniform(ymin + margin_y, ymax - margin_y)
                self.base_position = (base_x, base_y)
            else:
                base_x, base_y = self.base_position
            # Compute the spacing offset along the given angle.
            angle_rad = math.radians(self.angle)
            delta = (self.max_width + self.spacing)
            delta_x = delta * math.cos(angle_rad)
            delta_y = delta * math.sin(angle_rad)
            current_x = base_x
            current_y = base_y
            for rect in self.bars_list:
                if rect.width is None:
                    rect.width = random.uniform(self.min_width, self.max_width)
                if rect.height is None:
                    rect.height = random.uniform(self.min_height, self.max_height)
                # Set the rectangle using its own method.
                rect.angle = self.angle if rect.angle is None else rect.angle
                rect.set_bottom_left(current_x, current_y, angle=self.angle,
                                     width=rect.width, height=rect.height)
                current_x += delta_x
                current_y += delta_y
            self._geometry_locked = True
        super().assign_geometry()
        propagate_style(self)


    def perform_skills(self, verbose=False):
        children_trees = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        rect_ids = [child.obj_id for child in self.sub_references if isinstance(child, RectangleObj)]
        tree = {
            "action": "GroupRectangle",
            "object": f"Bars#{self.obj_id}",
            "details": f"from rectangleIDs={rect_ids}",
            "children": children_trees + [
                {"action": "RecognizeInstanceBars", "object": f"Bars#{self.obj_id}"},
                {"action": "LocalizeBars", "object": f"Bars#{self.obj_id}", "details": "(Positions for each rectangle)"},
                {"action": "MeasureBars", "object": f"Bars#{self.obj_id}", "details": "(Heights, widths, spacing, etc.)"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    def set_bottom_left(self, x, y, angle=0, **kwargs):
        self.base_position = (x, y)
        self.angle = angle
        self._geometry_locked = False

    def get_bbox(self):
        bboxes = [obj.get_bbox() for obj in self.bars_list]
        if bboxes:
            min_x = min(b[0] for b in bboxes)
            min_y = min(b[1] for b in bboxes)
            max_x = max(b[2] for b in bboxes)
            max_y = max(b[3] for b in bboxes)
            return (min_x, min_y, max_x, max_y)
        return (0, 0, 0, 0)


###############################################################################
# Axis
###############################################################################
class AxisObj(PlotObject):
    ALIAS = "Axis"

    def __init__(self,
                 axis_length=50,
                 axis_angle=30,
                 min_tick_spacing=5,
                 max_tick_spacing=10,
                 min_tick_length=10,
                 max_tick_length=30,
                 start_position=None,
                 color=None,
                 thickness=None,
                 canvas=(0,100,0,100)):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        self.axis_length = axis_length
        self.axis_angle = axis_angle
        self.min_tick_spacing = min_tick_spacing
        self.max_tick_spacing = max_tick_spacing
        self.min_tick_length = min_tick_length
        self.max_tick_length = max_tick_length
        self.start_position = start_position  # may be None
        # Create the main line passing the canvas along.
        self.line = LineLow(color=self.color, thickness=self.thickness, canvas=self.canvas)
        self.sub_references = [self.line]
        self.ticks = []
        self.p1 = (0, 0)
        self.p2 = (0, 0)
        self._geometry_locked = (start_position is not None)

    def assign_geometry(self):
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        xmin, xmax, ymin, ymax = self.canvas
        canvas_width = xmax - xmin
        canvas_height = ymax - ymin
        if not self._geometry_locked:
            # Choose a start_position that ensures the entire axis fits within the canvas.
            rad = math.radians(self.axis_angle)
            dx = self.axis_length * math.cos(rad)
            dy = self.axis_length * math.sin(rad)
            # Ensure that the start and end are within the canvas.
            # Calculate allowed ranges for start_position.
            if dx >= 0:
                x_low = xmin
                x_high = xmax - dx
            else:
                x_low = xmin - dx
                x_high = xmax
            if dy >= 0:
                y_low = ymin
                y_high = ymax - dy
            else:
                y_low = ymin - dy
                y_high = ymax
            if self.start_position is None:
                x1 = random.uniform(x_low, x_high)
                y1 = random.uniform(y_low, y_high)
                self.start_position = (x1, y1)
            else:
                x1, y1 = self.start_position
            x2 = x1 + dx
            y2 = y1 + dy
            self.p1 = (x1, y1)
            self.p2 = (x2, y2)
            self.line.p1 = self.p1
            self.line.p2 = self.p2
            self.line._geometry_locked = True
            # Create ticks along the axis.
            tick_start = 0.0
            while tick_start < self.axis_length:
                spacing = random.uniform(self.min_tick_spacing, self.max_tick_spacing)
                if tick_start + spacing > self.axis_length:
                    break
                tick_start += spacing
                cx = x1 + tick_start * math.cos(rad)
                cy = y1 + tick_start * math.sin(rad)
                tick_len = random.uniform(self.min_tick_length, self.max_tick_length)
                half_t = tick_len / 2.0
                # Compute a tick perpendicular to the axis.
                rx = half_t * math.cos(rad + math.pi/2)
                ry = half_t * math.sin(rad + math.pi/2)
                tick_line = LineLow((cx - rx, cy - ry), (cx + rx, cy + ry),
                                      color=self.color, thickness=self.thickness, canvas=self.canvas)
                self.ticks.append(tick_line)
                self.sub_references.append(tick_line)
            self._geometry_locked = True
        super().assign_geometry()
        propagate_style(self)

    def perform_skills(self, verbose=False):
        line_tree = self.line.perform_skills(verbose=verbose)
        ticks_trees = [tick.perform_skills(verbose=verbose) for tick in self.ticks]
        group_line_details = f"from lineIDs=[{self.line.obj_id}" + "".join(f", {tick.obj_id}" for tick in self.ticks) + "]"
        tree = {
            "action": "GroupLine",
            "object": f"Axis#{self.obj_id}",
            "details": group_line_details,
            "children": [line_tree] + ticks_trees + [
                {"action": "RecognizeInstanceAxis", "object": f"Axis#{self.obj_id}"},
                {"action": "LocalizeAxis", "object": f"Axis#{self.obj_id}", "details": f"(Endpoints={self.p1}, {self.p2})"},
                {"action": "MeasureAxis", "object": f"Axis#{self.obj_id}", "details": f"(Length={get_line_length_and_angle(self.p1, self.p2)[0]:.1f}, Angle={get_line_length_and_angle(self.p1, self.p2)[1]:.1f})"}
            ]
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        self.line.render(ax)
        for tline in self.ticks:
            tline.render(ax)

    def set_bottom_left(self, x, y, angle=0, axis_length=50, **kwargs):
        self.start_position = (x, y)
        self.axis_angle = angle
        self.axis_length = axis_length
        self._geometry_locked = False

    def get_bbox(self):
        return (min(self.p1[0], self.p2[0]),
                min(self.p1[1], self.p2[1]),
                max(self.p1[0], self.p2[0]),
                max(self.p1[1], self.p2[1]))


###############################################################################
# BarGraph
###############################################################################
class BarGraphObj(PlotObject):
    ALIAS = "BarGraph"

    def __init__(self,
                 base_position=None,
                 axis_length=None,
                 bars_num=None,
                 bars_angle=0,
                 with_y_axis=True,
                 axis_margin=0,
                 color=None,
                 thickness=None,
                 canvas=(0,100,0,100),
                 **kwargs):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else None
        self.thickness = thickness if thickness is not None else None
        if self.color is None:
            self.color = random_color()
        if self.thickness is None:
            self.thickness = random_thickness()
        # Generate a base_position inside the canvas if not provided.
        if base_position is None:
            xmin, xmax, ymin, ymax = self.canvas
            margin = (xmax - xmin) * 0.1
            base_position = (random.uniform(xmin + margin, xmax - margin),
                             random.uniform(ymin + margin, ymax - margin))
        if axis_length is None:
            xmin, xmax, ymin, ymax = self.canvas
            axis_length = random.uniform(40, (xmax - xmin) * 0.5)
        if bars_num is None:
            bars_num = random.randint(2, 5)
        if bars_angle is None:
            bars_angle = random.uniform(0, 180)
        self.base_position = base_position
        self.axis_length = axis_length
        self.bars_num = bars_num
        self.bars_angle = bars_angle
        self.with_y_axis = with_y_axis
        self.axis_margin = axis_margin
        self._geometry_locked = False
        # Create the BarsObj, passing the canvas.
        self.bars_obj = BarsObj(num_bars=self.bars_num,
                                angle=self.bars_angle,
                                base_position=self.base_position,
                                color=self.color,
                                thickness=self.thickness,
                                canvas=self.canvas,
                                **kwargs)
        self.sub_references = [self.bars_obj]
        # Compute an offset for the axis start position.
        rad_offset = math.radians(self.bars_angle - 90)
        ax_start_x = self.base_position[0] + self.axis_margin * math.cos(rad_offset)
        ax_start_y = self.base_position[1] + self.axis_margin * math.sin(rad_offset)
        self.axis_obj_x = AxisObj(start_position=(ax_start_x, ax_start_y),
                                  axis_length=self.axis_length,
                                  axis_angle=self.bars_angle,
                                  color=self.color,
                                  thickness=self.thickness,
                                  canvas=self.canvas)
        self.sub_references.append(self.axis_obj_x)
        if self.with_y_axis:
            self.axis_obj_y = AxisObj(start_position=(ax_start_x, ax_start_y),
                                      axis_length=self.axis_length,
                                      axis_angle=((self.bars_angle + 90) % 360),
                                      color=self.color,
                                      thickness=self.thickness,
                                      canvas=self.canvas)
            self.sub_references.append(self.axis_obj_y)
        else:
            self.axis_obj_y = None

    def assign_geometry(self):
        if not self._geometry_locked:
            self.bars_obj._geometry_locked = False
            self.axis_obj_x._geometry_locked = False
            if self.axis_obj_y:
                self.axis_obj_y._geometry_locked = False
            self.axis_obj_x.assign_geometry()
            if self.axis_obj_y:
                self.axis_obj_y.assign_geometry()
            self.bars_obj.assign_geometry()
            self._geometry_locked = True
        super().assign_geometry()
        propagate_style(self)

    def perform_skills(self, verbose=False):
        axis_x_tree = self.axis_obj_x.perform_skills(verbose=verbose)
        children = [axis_x_tree]
        if self.axis_obj_y:
            axis_y_tree = self.axis_obj_y.perform_skills(verbose=verbose)
            children.append(axis_y_tree)
            children.append({"action": "GroupAxis", "object": f"BarGraph#{self.obj_id}",
                             "details": f"from AxisIDs=[{self.axis_obj_x.obj_id}, {self.axis_obj_y.obj_id}]"})
        else:
            children.append({"action": "GroupAxis", "object": f"BarGraph#{self.obj_id}",
                             "details": f"from AxisIDs=[{self.axis_obj_x.obj_id}]"})
        bars_tree = self.bars_obj.perform_skills(verbose=verbose)
        children.append(bars_tree)
        children.append({"action": "GroupBars", "object": f"BarGraph#{self.obj_id}",
                         "details": f"from BarsIDs=[{self.bars_obj.obj_id}]"})
        additional = [
            {"action": "RecognizeInstanceBarGraph", "object": f"BarGraph#{self.obj_id}"},
            {"action": "LocalizeBarGraph", "object": f"BarGraph#{self.obj_id}", "details": "(Overall bounding region, etc.)"},
            {"action": "MeasureBarGraph", "object": f"BarGraph#{self.obj_id}", "details": "(Number of bars, axis length, etc.)"}
        ]
        tree = {
            "action": "BarGraph",
            "object": f"BarGraph#{self.obj_id}",
            "children": children + additional
        }
        if verbose:
            print("\n".join(skills_tree_to_text(tree)))
        return tree

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    def set_bottom_left(self, x, y, angle=0, axis_length=50, bars_num=2, **kwargs):
        self.base_position = (x, y)
        self.bars_angle = angle
        self.axis_length = axis_length
        self.bars_num = bars_num
        self._geometry_locked = False

    def get_bbox(self):
        bboxes = []
        if hasattr(self.bars_obj, "get_bbox"):
            bboxes.append(self.bars_obj.get_bbox())
        if hasattr(self.axis_obj_x, "get_bbox"):
            bboxes.append(self.axis_obj_x.get_bbox())
        if self.axis_obj_y and hasattr(self.axis_obj_y, "get_bbox"):
            bboxes.append(self.axis_obj_y.get_bbox())
        if bboxes:
            return (min(b[0] for b in bboxes),
                    min(b[1] for b in bboxes),
                    max(b[2] for b in bboxes),
                    max(b[3] for b in bboxes))
        return (0, 0, 0, 0)