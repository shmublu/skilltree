#!/usr/bin/env python3
import math
import random
import json
import re
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle, Polygon
import matplotlib.colors as mcolors
import numpy as np

from base import PlotObject
from utilities import get_line_length_and_angle, rotate_point

###############################################################################
# Utility functions for style and geometry
###############################################################################
def random_border_color(fill_color=None):
    r = random.random()
    if fill_color is not None:
        if r < 0.25:
            return fill_color
        elif r < 0.25 + 0.24:
            return "black"
        else:
            return random.choice(["red", "blue", "green", "purple", "orange"])
    else:
        if r < 0.33:
            return "black"
        else:
            return random.choice(["red", "blue", "green", "purple", "orange"])

def random_fill_color():
    # Return colors with alpha transparency (0.3-0.5)
    alpha = random.uniform(0.2, 0.6)
    if random.random() < 0.5:
        rgba = mcolors.to_rgba("white", 0.0)
        return rgba
    base_color = random.choice(["red", "blue", "green", "purple", "orange"])
    rgba = mcolors.to_rgba(base_color, alpha)
    return rgba

def random_thickness():
    return random.uniform(1, 3)


def round_to_nearest(value, nearest=1):
    rounded_value = round(value / nearest) * nearest
    # If the result is an integer, return it as an int
    if isinstance(rounded_value, int) or rounded_value == int(rounded_value):
        return int(rounded_value)
    return rounded_value


def scale_shape(shape, scale_factor):
    """
    Create a scaled copy of a shape.
    
    Parameters:
    - shape: Any PlotObject instance
    - scale_factor: Factor to scale dimensions by
      - If scale_factor > 1: Dimensions get smaller (e.g., 14 becomes 2 with scale_factor=7)
      - If 0 < scale_factor < 1: Dimensions get larger (e.g., 2 becomes 14 with scale_factor=1/7)
    
    Returns:
    - New instance of the same shape type with scaled dimensions
    """
    # Create a new instance of the same class
    if isinstance(shape, Line):
        p1 = tuple(coord / scale_factor for coord in shape.p1) if shape.p1 else None
        p2 = tuple(coord / scale_factor for coord in shape.p2) if shape.p2 else None
        return Line(
            p1=p1, p2=p2,
            color=shape.color,
            thickness=shape.thickness,
            canvas=shape.canvas,
            label=shape.label
        )
    
    elif isinstance(shape, SolidOval):
        center = tuple(coord / scale_factor for coord in shape.center) if shape.center else None
        width = shape.width / scale_factor if shape.width else None
        height = shape.height / scale_factor if shape.height else None
        return SolidOval(
            center=center,
            width=width, height=height,
            angle=shape.angle,
            border_color=shape.border_color,
            fill_color=shape.fill_color,
            thickness=shape.thickness,
            canvas=shape.canvas,
            is_circle=shape.is_circle,
            label=shape.label
        )
    
    elif isinstance(shape, SolidRectangle):
        center = tuple(coord / scale_factor for coord in shape.center) if shape.center else None
        width = shape.width / scale_factor if shape.width else None
        height = shape.height / scale_factor if shape.height else None
        new_rect = SolidRectangle(
            center=center,
            width=width, height=height,
            angle=shape.angle,
            border_color=shape.border_color,
            fill_color=shape.fill_color,
            thickness=shape.thickness,
            canvas=shape.canvas,
            is_square=shape.is_square,
            label=shape.label
        )
        return new_rect
    
    elif isinstance(shape, SolidTriangle):
        vertices = None
        if shape.vertices and None not in shape.vertices:
            vertices = [tuple(coord / scale_factor for coord in vertex) for vertex in shape.vertices]
        return SolidTriangle(
            vertices=vertices,
            border_color=shape.border_color,
            fill_color=shape.fill_color,
            thickness=shape.thickness,
            canvas=shape.canvas,
            label=shape.label
        )
    
    elif isinstance(shape, SolidPolygon):
        vertices = None
        if shape.vertices and None not in shape.vertices:
            vertices = [tuple(coord / scale_factor for coord in vertex) for vertex in shape.vertices]
        return SolidPolygon(
            vertices=vertices,
            border_color=shape.border_color,
            fill_color=shape.fill_color,
            thickness=shape.thickness,
            canvas=shape.canvas,
            num_vertices=shape.num_vertices,
            label=shape.label
        )
    
    elif hasattr(shape, 'ALIAS') and 'Geo' in shape.ALIAS or 'Shapey' in shape.ALIAS:  # CompositeShape case
        center = tuple(coord / scale_factor for coord in shape.center) if shape.center else None
        # For composite shapes, we adjust the internal scale parameter
        new_scale = shape.scale / scale_factor
        return shape.__class__(
            center=center,
            scale=new_scale,
            angle=shape.angle,
            canvas=shape.canvas,
            label=shape.label
        )
    
    else:
        raise TypeError(f"Unsupported shape type: {type(shape)}")


###############################################################################
# Line
###############################################################################
class Line(PlotObject):
    ALIAS = "Line"

    def __init__(self, p1=None, p2=None, color=None, thickness=None, canvas=(0, 800, 0, 600), label=None):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else random_border_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.p1 = p1  # may be None
        self.p2 = p2  # may be None
        self.label = label
        self.children = None
        if (self.p1 is not None and self.p2 is not None):
            self.lock_geometry()

    def assign_geometry(self):
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            canvas_width = xmax - xmin
            canvas_height = ymax - ymin
            # Choose a random length based on canvas.
            min_length = max(5, min(canvas_width, canvas_height) * 0.15)
            max_length = min(canvas_width, canvas_height) * 0.8
            L = random.uniform(min_length, max_length)
            angle = random.uniform(0, 360)
            rad = math.radians(angle)
            dx = L * math.cos(rad)
            dy = L * math.sin(rad)
            # Choose p1 so that p2 remains within canvas bounds.
            if dx >= 0:
                x_low, x_high = xmin, xmax - dx
            else:
                x_low, x_high = xmin - dx, xmax
            if dy >= 0:
                y_low, y_high = ymin, ymax - dy
            else:
                y_low, y_high = ymin - dy, ymax
            self.p1 = (random.uniform(x_low, x_high), random.uniform(y_low, y_high))
            self.p2 = (self.p1[0] + dx, self.p1[1] + dy)
            self._geometry_locked = True
        self.enforce_bounds()

    def render(self, ax):
        if not self._geometry_locked:
            self.assign_geometry()
        ax.plot([self.p1[0], self.p2[0]],
                [self.p1[1], self.p2[1]],
                color=self.color, lw=self.thickness)
        
        # Add label if set
        if self.label:
            # Calculate a position next to the line
            mid_x = (self.p1[0] + self.p2[0]) / 2
            mid_y = (self.p1[1] + self.p2[1]) / 2
            # Use a small offset perpendicular to the line
            length, angle = get_line_length_and_angle(self.p1, self.p2)
            perp_angle = angle + 90
            offset = 10  # pixels
            label_x = mid_x + offset * math.cos(math.radians(perp_angle))
            label_y = mid_y + offset * math.sin(math.radians(perp_angle))
            ax.text(label_x, label_y, self.label, ha='center', va='center')

    def set_bottom_left(self, x, y, angle=0, length=10, **kwargs):
        rad = math.radians(angle)
        self.p1 = (x, y)
        self.p2 = (x + length * math.cos(rad), y + length * math.sin(rad))
        self._geometry_locked = True
        self.enforce_bounds()

    def get_bbox(self):
        return (min(self.p1[0], self.p2[0]),
                min(self.p1[1], self.p2[1]),
                max(self.p1[0], self.p2[0]),
                max(self.p1[1], self.p2[1]))
    
    def contains_point(self, point):
        # Consider the line as having a small thickness tolerance.
        tol = 2  # pixels
        (x0, y0) = point
        (x1, y1) = self.p1
        (x2, y2) = self.p2
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x0 - x1, y0 - y1) <= tol
        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx*dx + dy*dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        distance = math.hypot(x0 - proj_x, y0 - proj_y)
        return distance <= tol

    def perform_skills(self, verbose=False):
        length, angle = get_line_length_and_angle(self.p1, self.p2)
        length = round_to_nearest(length, 1)
        angle = round_to_nearest(angle, 5)
        e1 = (round_to_nearest(self.p1[0]),round_to_nearest(self.p1[1]))
        e2 = (round_to_nearest(self.p2[0]),round_to_nearest(self.p2[1]))
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "RecognizeInstanceLine",
            "object": f"Line#{self.obj_id}" if not self.label else f"Line#{self.obj_id} labeled as {self.label}",
            "details": [
                {"action": "LocalizeLine", "object": f"Line#{self.obj_id}", "details": f"(Endpoints: {e1}, {e2}{label_info})"},
                {"action": "MeasureLine", "object": f"Line#{self.obj_id}", "details": f"(Length={length}, Angle={angle})"}
            ]
        }
        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)
        return tree


###############################################################################
# Solid Oval / Circle
###############################################################################
class SolidOval(PlotObject):
    ALIAS = "Oval"

    def __init__(self, center=None, width=None, height=None, angle=None,
                 border_color=None, fill_color=None, thickness=None, 
                 canvas=(0, 800, 0, 600), is_circle=False, label=None):
        super().__init__()
        self.canvas = canvas
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.border_color = border_color if border_color is not None else random_border_color(self.fill_color)
        
        self.thickness = thickness if thickness is not None else random_thickness()
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle
        self.children=None
        self.is_circle = is_circle  # if True, force width==height.
        self.label = label
        self._geometry_locked = (center is not None and width is not None and height is not None and angle is not None)

    def assign_geometry(self):
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            canvas_width = xmax - xmin
            canvas_height = ymax - ymin
            if self.width is None:
                self.width = random.uniform(canvas_width * 0.15, canvas_width * 0.7)
            if self.height is None:
                self.height = random.uniform(canvas_height * 0.15, canvas_height * 0.7)
            if self.is_circle:
                self.height = self.width
            if self.center is None:
                cx = random.uniform(xmin + self.width/2, xmax - self.width/2)
                cy = random.uniform(ymin + self.height/2, ymax - self.height/2)
                self.center = (cx, cy)
            if self.angle is None:
                self.angle = random.uniform(0, 360)
            self._geometry_locked = True
        self.enforce_bounds()

    def render(self, ax):
        if not self._geometry_locked:
            self.assign_geometry()
        e = Ellipse(xy=self.center,
                    width=self.width,
                    height=self.height,
                    angle=self.angle,
                    edgecolor=self.border_color,
                    facecolor=self.fill_color,
                    lw=self.thickness)
        ax.add_patch(e)
        
        # Add label if set
        if self.label:
            # Randomly choose to place the label inside or next to the shape
            if random.random() < 0.7:  # 70% chance to place inside
                ax.text(self.center[0], self.center[1], self.label, ha='center', va='center')
            else:
                # Place the label outside with a small offset
                offset = max(self.width, self.height) * 0.6
                offset_angle = random.uniform(0, 360)
                label_x = self.center[0] + offset * math.cos(math.radians(offset_angle))
                label_y = self.center[1] + offset * math.sin(math.radians(offset_angle))
                ax.text(label_x, label_y, self.label, ha='center', va='center')

    def set_bottom_left(self, x, y, angle=0, width=10, height=10, **kwargs):
        rad = math.radians(angle)
        offset_x = width / 2.0
        offset_y = height / 2.0
        cx = x + offset_x * math.cos(rad) - offset_y * math.sin(rad)
        cy = y + offset_x * math.sin(rad) + offset_y * math.cos(rad)
        self.center = (cx, cy)
        self.width = width
        self.height = width if self.is_circle else height
        self.angle = angle
        self._geometry_locked = True
        self.enforce_bounds()

    def get_bbox(self):
        a = self.width / 2.0
        b = self.height / 2.0
        theta = math.radians(self.angle)
        x_off = abs(a * math.cos(theta)) + abs(b * math.sin(theta))
        y_off = abs(a * math.sin(theta)) + abs(b * math.cos(theta))
        return (self.center[0] - x_off,
                self.center[1] - y_off,
                self.center[0] + x_off,
                self.center[1] + y_off)
    
    def contains_point(self, point):
        x, y = point
        cx, cy = self.center
        theta = math.radians(-self.angle)
        x_rot = math.cos(theta) * (x - cx) - math.sin(theta) * (y - cy)
        y_rot = math.sin(theta) * (x - cx) + math.cos(theta) * (y - cy)
        a = self.width / 2.0
        b = self.height / 2.0
        return (x_rot / a)**2 + (y_rot / b)**2 <= 1
    
    def perform_skills(self, verbose=False):
        center_rounded = tuple(round_to_nearest(coord, 1) for coord in self.center)
        width_rounded = round_to_nearest(self.width, 1)
        height_rounded = round_to_nearest(self.height,1)
        angle_rounded = round_to_nearest(self.angle, 5)
        area_rounded = round_to_nearest((self.width * self.height * math.pi / 4), 1)
        
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "RecognizeInstanceOval",
            "object": f"Oval#{self.obj_id}" if not self.label else f"Oval#{self.obj_id} labeled as {self.label}",
            "details": [
                {"action": "LocalizeOval", "object": f"SolidOval#{self.obj_id}", "details": f"(Center: {center_rounded}, W={width_rounded}, H={height_rounded}, Angle={angle_rounded}{label_info})"},
                {"action": "MeasureOval", "object": f"SolidOval#{self.obj_id}", "details": f" (Approximate Area={area_rounded})"}
            ]
        }
        
        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)
        
        return tree
###############################################################################
# Solid Rectangle / Square
###############################################################################
class SolidRectangle(PlotObject):
    ALIAS = "Rectangle"

    def __init__(self, center=None, width=None, height=None, angle=None,
                 border_color=None, fill_color=None, thickness=None,
                 canvas=(0, 800, 0, 600), is_square=False, label=None):
        super().__init__()
        self.canvas = canvas
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.border_color = border_color if border_color is not None else random_border_color(self.fill_color)
        
        self.thickness = thickness if thickness is not None else random_thickness()
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle
        self.is_square = is_square
        self.label = label
        if (center is not None and width is not None and height is not None and angle is not None):
            self.lock_geometry()
    def assign_geometry(self):
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            canvas_width = xmax - xmin
            canvas_height = ymax - ymin
            if self.width is None:
                self.width = random.uniform(canvas_width * 0.15, canvas_width * 0.7)
            if self.height is None:
                self.height = random.uniform(canvas_height * 0.15, canvas_height * 0.7)
            if self.is_square:
                abs(self.height - self.width) < self.width * .02
            if self.center is None:
                rad = math.radians(self.angle if self.angle is not None else 0)
                bbox_w = abs(self.width * math.cos(rad)) + abs(self.height * math.sin(rad))
                bbox_h = abs(self.width * math.sin(rad)) + abs(self.height * math.cos(rad))
                cx = random.uniform(xmin + bbox_w/2, xmax - bbox_w/2)
                cy = random.uniform(ymin + bbox_h/2, ymax - bbox_h/2)
                self.center = (cx, cy)
            if self.angle is None:
                self.angle = random.uniform(0, 180)
        self.enforce_bounds()
        self.lock_geometry()
    def create_children(self):
        if not self._geometry_locked:
            return
        self.children = None
        # Create child line objects for each edge if border and fill colors differ.
        if self.border_color != self.fill_color:
            self.children = []
            corners = self.get_corners()
            rounded_corners = [
                tuple(round_to_nearest(coord, 1) for coord in corner)
                for corner in corners
            ]
            n = len(rounded_corners)
            for i in range(n):
                p1 = rounded_corners[i]
                p2 = rounded_corners[(i + 1) % n]
                line = Line(p1=p1, p2=p2, color=self.border_color, thickness=self.thickness, canvas=self.canvas)
                line.lock_geometry()
                self.children.append(line)
    def render(self, ax):
        if not self._geometry_locked:
            raise AssertionError("Geoemetry was not assigned and tried to print skills.")
        rect = Rectangle((-self.width/2, -self.height/2), self.width, self.height,
                         edgecolor=self.border_color,
                         facecolor=self.fill_color,
                         lw=self.thickness)
        import matplotlib.transforms as transforms
        t = transforms.Affine2D().rotate_deg(self.angle).translate(self.center[0], self.center[1]) + ax.transData
        rect.set_transform(t)
        ax.add_patch(rect)
        
        # Add label if set
        if self.label:
            # Randomly choose to place the label inside or next to the shape
            if random.random() < 0.7:  # 70% chance to place inside
                ax.text(self.center[0], self.center[1], self.label, ha='center', va='center')
            else:
                # Place the label outside with a small offset
                offset_x = self.width * 0.6
                offset_y = self.height * 0.6
                angle_rad = math.radians(self.angle + random.choice([0, 90, 180, 270]))
                label_x = self.center[0] + offset_x * math.cos(angle_rad)
                label_y = self.center[1] + offset_y * math.sin(angle_rad)
                ax.text(label_x, label_y, self.label, ha='center', va='center')

    def set_bottom_left(self, x, y, angle=0, width=10, height=10, **kwargs):
        rad = math.radians(angle)
        offset_x = width / 2.0
        offset_y = height / 2.0
        cx = x + offset_x * math.cos(rad) - offset_y * math.sin(rad)
        cy = y + offset_x * math.sin(rad) + offset_y * math.cos(rad)
        self.center = (cx, cy)
        self.width = width
        self.height = width if self.is_square else height
        self.angle = angle
        self.enforce_bounds()
        self.lock_geometry()

    def get_bbox(self):
        rad = math.radians(self.angle)
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        corners = [
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h)
        ]
        rotated = [rotate_point(c, (0, 0), self.angle) for c in corners]
        abs_corners = [(self.center[0] + x, self.center[1] + y) for (x, y) in rotated]
        xs = [pt[0] for pt in abs_corners]
        ys = [pt[1] for pt in abs_corners]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def contains_point(self, point):
        if not self._geometry_locked:
            raise AssertionError("Geometry was not assigned and tried to access geometry.")
        x, y = point
        cx, cy = self.center
        theta = math.radians(-self.angle)
        x_rot = math.cos(theta) * (x - cx) - math.sin(theta) * (y - cy)
        y_rot = math.sin(theta) * (x - cx) + math.cos(theta) * (y - cy)
        return (abs(x_rot) <= self.width / 2) and (abs(y_rot) <= self.height / 2)
    
    def get_corners(self):
        if not self._geometry_locked:
            raise AssertionError("Geometry was not assigned and tried to access geometry.")
        # Compute the four corners of the rectangle.
        rad = math.radians(self.angle)
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        corners = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
        rotated = [rotate_point(c, (0, 0), self.angle) for c in corners]
        return [(self.center[0] + x, self.center[1] + y) for (x, y) in rotated]

    def perform_skills(self, verbose=False):
        if not self._geometry_locked:
            raise AssertionError("Geometry was not assigned and tried to access geometry.")
        children_trees = []
        line_ids = []

        # Create child line objects for each edge if border and fill colors differ.
        if self.border_color != self.fill_color:
            corners = self.get_corners()
            rounded_corners = [
                tuple(round_to_nearest(coord, 1) for coord in corner)
                for corner in corners
            ]
            n = len(rounded_corners)
            for c in self.children:
                children_trees.append(c.perform_skills(verbose=verbose))
                line_ids.append(c.obj_id)
        else:
            rounded_corners = [
                tuple(round_to_nearest(coord, 1) for coord in corner)
                for corner in self.get_corners()
            ]

        # Round width, height, and angle
        rounded_width = round_to_nearest(self.width, 1)
        rounded_height = round_to_nearest(self.height, 1)
        rounded_angle = round_to_nearest(self.angle, 5)

        # Compute area and perimeter using rounded values
        area = rounded_width * rounded_height
        perimeter = 2 * (rounded_width + rounded_height)

        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "GroupLine",
            "object": f"Rectangle#{self.obj_id}" if not self.label else f"Rectangle#{self.obj_id} labeled as {self.label}",
            "details": [
                {"action": "RecognizeInstanceRectangle", "object": f"Rectangle#{self.obj_id}"},
                {"action": "LocalizeRectangle", "object": f"Rectangle#{self.obj_id}", "details": f"(Corners: {rounded_corners[0]}, {rounded_corners[1]}, {rounded_corners[2]}, {rounded_corners[3]}) (W={rounded_width}, H={rounded_height}, Angle={rounded_angle}{label_info}, " + f"from lineIDs={line_ids})" if line_ids else ""},
                {"action": "MeasureRectangle", "object": f"Rectangle#{self.obj_id}", "details": f"(Area={area}, Perimeter={perimeter})"}
            ],
            "children": children_trees
        }

        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)

        return tree


###############################################################################
# Solid Triangle
###############################################################################
class SolidTriangle(PlotObject):
    ALIAS = "Triangle"

    def __init__(self, vertices=None, border_color=None, fill_color=None, thickness=None,
                 canvas=(0, 800, 0, 600), label=None):
        super().__init__()
        self.canvas = canvas
        self.border_color = border_color if border_color is not None else random_border_color()
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.vertices = vertices if (vertices is not None and len(vertices) == 3) else [None, None, None]
        self.label = label
        if (None not in self.vertices):
            self.lock_geometry()

    def assign_geometry(self):
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            self.vertices = [v if v is not None else (random.uniform(xmin, xmax), random.uniform(ymin, ymax))
                             for v in self.vertices]
            self._geometry_locked = True
        self.enforce_bounds()
        self.lock_geometry()

    def render(self, ax):
        if not self._geometry_locked:
            raise AssertionError("Geoemetry was not assigned and tried to print skills.")
        poly = Polygon(self.vertices, closed=True,
                       edgecolor=self.border_color,
                       facecolor=self.fill_color,
                       lw=self.thickness)
        ax.add_patch(poly)
        
        # Add label if set
        if self.label:
            # Calculate the centroid of the triangle
            centroid_x = sum(p[0] for p in self.vertices) / 3
            centroid_y = sum(p[1] for p in self.vertices) / 3
            
            # Randomly choose to place the label inside or next to the shape
            if random.random() < 0.7:  # 70% chance to place inside
                ax.text(centroid_x, centroid_y, self.label, ha='center', va='center')
            else:
                # Place label outside with a small offset from one of the vertices
                vertex = random.choice(self.vertices)
                offset_angle = random.uniform(0, 360)
                offset = 20  # pixels
                label_x = vertex[0] + offset * math.cos(math.radians(offset_angle))
                label_y = vertex[1] + offset * math.sin(math.radians(offset_angle))
                ax.text(label_x, label_y, self.label, ha='center', va='center')

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
        self.enforce_bounds()

    def get_bbox(self):
        xs = [v[0] for v in self.vertices if v is not None]
        ys = [v[1] for v in self.vertices if v is not None]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def contains_point(self, point):
        def sign(p1, p2, p3):
            return (p1[0]-p3[0])*(p2[1]-p3[1]) - (p2[0]-p3[0])*(p1[1]-p3[1])
        pt = point
        v1, v2, v3 = self.vertices
        b1 = sign(pt, v1, v2) < 0.0
        b2 = sign(pt, v2, v3) < 0.0
        b3 = sign(pt, v3, v1) < 0.0
        return ((b1 == b2) and (b2 == b3))
    def create_children(self):
        if not self._geometry_locked:
            return
        self.children = None
        if self.border_color != self.fill_color: 
            pts = self.vertices
            n = len(pts)
            self.children = []
            for i in range(n):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                line = Line(p1=p1, p2=p2, color=self.border_color, thickness=self.thickness, canvas=self.canvas)
                line.lock_geometry()
                self.children.append(line)
        
    def perform_skills(self, verbose=False):
        if not self._geometry_locked:
            raise AssertionError("Geoemetry was not assigned and tried to print skills.")
        children_trees = []
        line_ids = []

        if self.border_color != self.fill_color:
            for c in self.children:
                children_trees.append(c.perform_skills(verbose=verbose))
                line_ids.append(c.obj_id)

        # Round all vertex coordinates
        rounded_vertices = [
            tuple(round_to_nearest(coord, 1) for coord in vertex)
            for vertex in self.vertices
        ]

        # Compute triangle area using the determinant formula with rounded values
        (x1, y1), (x2, y2), (x3, y3) = rounded_vertices
        area = abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0
        rounded_area = round_to_nearest(area, 1)

        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "GroupLine",
            "object": f"Triangle#{self.obj_id}" if not self.label else f"Triangle#{self.obj_id} labeled as {self.label}",
            "details": [
                {"action": "RecognizeInstanceTriangle", "object": f"Triangle#{self.obj_id}"},
                {"action": "LocalizeTriangle", "object": f"Triangle#{self.obj_id}", "details": f"(Vertices: {rounded_vertices}),"  + f"from lineIDs={line_ids})" if line_ids else ""},
                {"action": "MeasureTriangle", "object": f"Triangle#{self.obj_id}", "details": f"(Area={rounded_area})"}
            ],
            "children": children_trees
        }

        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)

        return tree



###############################################################################
# Solid Polygon
###############################################################################
class SolidPolygon(PlotObject):
    ALIAS = "SolidPolygon"

    def __init__(self, vertices=None, border_color=None, fill_color=None, thickness=None,
                 canvas=(0, 800, 0, 600), num_vertices=5, label=None):
        super().__init__()
        self.canvas = canvas
        self.border_color = border_color if border_color is not None else random_border_color()
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.num_vertices = max(num_vertices, 3)
        self.label = label
        self.children = None
        if vertices is None or len(vertices) < 3:
            self.vertices = None
        else:
            self.vertices = vertices
            self.lock_geometry()
            self.create_children()

    def _generate_random_convex_polygon(self):
        xmin, xmax, ymin, ymax = self.canvas
        pts = [(random.uniform(xmin, xmax), random.uniform(ymin, ymax))
               for _ in range(self.num_vertices)]
        cx = sum(p[0] for p in pts) / self.num_vertices
        cy = sum(p[1] for p in pts) / self.num_vertices
        pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        return pts

    def assign_geometry(self):
        if not self._geometry_locked:
            self.vertices = self._generate_random_convex_polygon()
            self.enforce_bounds()
            self.lock_geometry()
            self.create_children()

    def create_children(self):
        """Create child line objects along the polygon’s edges if the border
        and fill colors differ. This function is called once the geometry is locked."""
        if not self._geometry_locked:
            return
        self.children = None
        if self.border_color != self.fill_color:
            self.children = []
            pts = self.vertices
            n = len(pts)
            for i in range(n):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                line = Line(p1=p1, p2=p2, color=self.border_color, thickness=self.thickness, canvas=self.canvas)
                line.lock_geometry()
                self.children.append(line)

    def render(self, ax):
        if not self._geometry_locked:
            self.assign_geometry()
        poly = Polygon(self.vertices, closed=True,
                       edgecolor=self.border_color,
                       facecolor=self.fill_color,
                       lw=self.thickness)
        ax.add_patch(poly)
        
        # Add label if set
        if self.label:
            # Calculate the centroid
            centroid_x = sum(p[0] for p in self.vertices) / len(self.vertices)
            centroid_y = sum(p[1] for p in self.vertices) / len(self.vertices)
            
            # Randomly choose to place the label inside or next to the shape
            if random.random() < 0.7:  # 70% chance to place inside
                ax.text(centroid_x, centroid_y, self.label, ha='center', va='center')
            else:
                # Place label outside with a small offset from one of the vertices
                vertex = random.choice(self.vertices)
                offset_angle = random.uniform(0, 360)
                offset = 20  # pixels
                label_x = vertex[0] + offset * math.cos(math.radians(offset_angle))
                label_y = vertex[1] + offset * math.sin(math.radians(offset_angle))
                ax.text(label_x, label_y, self.label, ha='center', va='center')

    def set_bottom_left(self, x, y, **kwargs):
        dx = kwargs.get("dx", 10)
        dy = kwargs.get("dy", 10)
        base_vertex = (x, y)
        xmin, xmax, ymin, ymax = self.canvas
        pts = [base_vertex]
        for _ in range(self.num_vertices - 1):
            pts.append((random.uniform(xmin, xmax), random.uniform(ymin, ymax)))
        cx = sum(p[0] for p in pts) / self.num_vertices
        cy = sum(p[1] for p in pts) / self.num_vertices
        pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        self.vertices = pts
        self.enforce_bounds()
        self.lock_geometry()
        self.create_children()

    def get_bbox(self):
        xs = [p[0] for p in self.vertices]
        ys = [p[1] for p in self.vertices]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def contains_point(self, point):
        x, y = point
        count = 0
        n = len(self.vertices)
        for i in range(n):
            x1, y1 = self.vertices[i]
            x2, y2 = self.vertices[(i + 1) % n]
            if ((y1 > y) != (y2 > y)):
                x_intersect = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-6) + x1
                if x < x_intersect:
                    count += 1
        return count % 2 == 1
    
    def perform_skills(self, verbose=False):
        if not self._geometry_locked:
            raise AssertionError("Geometry was not assigned and locked.")
        children_trees = []
        line_ids = []
        if self.children is not None:
            for child in self.children:
                children_trees.append(child.perform_skills(verbose=verbose))
                line_ids.append(child.obj_id)
                
        # Round all vertex coordinates for display purposes
        rounded_vertices = [
            tuple(round_to_nearest(coord, 1) for coord in vertex)
            for vertex in self.vertices
        ]

        # Calculate the area using the shoelace formula
        def shoelace_area(vertices):
            area = 0
            n = len(vertices)
            for i in range(n):
                x1, y1 = vertices[i]
                x2, y2 = vertices[(i + 1) % n]
                area += x1 * y2 - x2 * y1
            return abs(area) / 2

        area = shoelace_area(self.vertices)

        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "GroupLine",
            "object": f"Polygon#{self.obj_id}" if not self.label else f"Polygon#{self.obj_id} labeled as {self.label}",
            "details": [
                {"action": "RecognizeInstancePolygon", "object": f"Polygon#{self.obj_id}"},
                {"action": "LocalizePolygon", "object": f"Polygon#{self.obj_id}", "details": f"(Vertices: {rounded_vertices}), " + f"from lineIDs={line_ids})" if line_ids else ""},
                {"action": "MeasurePolygonArea", "object": f"Polygon#{self.obj_id}", "details": f" Area: {area})"}
            ],
            "children": children_trees
        }

        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)
        return tree


class CompositeShapeGenerator:
    """
    Generates a new shape class with a fixed arrangement of components
    that can be instantiated with different scales, rotations, etc.
    
    Now you can specify the allowed component types (including a doodle)
    and the maximum count for each.
    """
    
    def __init__(self, canvas=(0, 800, 0, 600), allowed_components=None, color_mode=None):
        self.canvas = canvas
        # allowed_components is a dict mapping component type to maximum count.
        # Use component classes for solid parts and the string 'Doodle' for doodles.
        # Updated default: allow up to 2 doodles.
        self.allowed_components = allowed_components or {
            Line: 2,
            SolidOval: 2,
            SolidRectangle: 2,
            SolidTriangle: 2,
            'Doodle': 2
        }
        # Minimum and maximum numbers for solid shapes (if no doodle is provided)
        self.min_total_s = 1
        self.max_total_s = 3
        self.shape_name = self._generate_name()
        self.shape_amount = 0
        self.color_mode = color_mode  # Can be "fixed", "mapped", or None (unfixed)
        
        # Create blueprints based on allowed components.
        self.component_blueprints = self._create_component_blueprints()
        self.doodle_blueprints = self._create_doodle_blueprints()
        
        # Enforce minimum configuration:
        # Valid configurations are:
        #   - at least one doodle (even if no solid shape)
        #   - at least two solid shapes (if no doodle)
        #   - or at least one doodle and one solid shape.
        total_components = len(self.component_blueprints) + len(self.doodle_blueprints)
        if total_components < 2:
            if len(self.doodle_blueprints) == 0:
                self.doodle_blueprints.append(self._create_doodle_blueprint())
            if (len(self.component_blueprints) == 0 and
                (len(self.component_blueprints) + len(self.doodle_blueprints)) < 2):
                available = [t for t in self.allowed_components if t != 'Doodle']
                if available:
                    comp_type = random.choice(available)
                    self.component_blueprints.append({
                        'type': comp_type,
                        'rel_distance': random.uniform(20, 60),
                        'rel_angle': random.uniform(0, 360),
                        'rel_rotation': random.uniform(0, 360),
                        'size_factor': random.uniform(0.7, 1.3),
                        'border_color': random_border_color(),
                        'fill_color': random_fill_color(),
                        'thickness': random_thickness()
                    })
        if self.color_mode == "mapped":
            for bp in self.component_blueprints:
                bp['orig_border_color'] = bp['border_color']
                if 'fill_color' in bp:
                    bp['orig_fill_color'] = bp['fill_color']
            for doodle in self.doodle_blueprints:
                doodle['orig_color'] = doodle['color']
        
        # Generate the shape class.
        self.ComponentShape = self._create_shape_class()
    
    def _generate_name(self):
        prefixes = ["Geo","Doodle", "Shapey", "Apple," "Symbio", "Poly", "Mecha", "Astro", "Neuro", "Personlike", "Blobby"]
        suffixes = ["Form", "Thingamajig", "Glyph", "Shape", "Struct", "Node", "Sigil", "Blob"]
        return f"{random.choice(prefixes)}{random.choice(suffixes)}"
    
    def _create_component_blueprints(self):
        blueprints = []
        total_objs = 0
        for comp_type, max_count in self.allowed_components.items():
            if comp_type == 'Doodle':
                continue
            count = random.randint(0, max_count)
            for i in range(count):
                if total_objs >= self.max_total_s:
                    break
                total_objs += 1
                blueprints.append({
                    'type': comp_type,
                    'rel_distance': random.uniform(0, 60),
                    'rel_angle': random.uniform(0, 360),
                    'rel_rotation': random.uniform(0, 360),
                    'size_factor': random.uniform(0.5, 1.8),
                    'border_color': random_border_color(),
                    'fill_color': random_fill_color(),
                    'thickness': random_thickness()
                })
        return blueprints
    
    def _create_doodle_blueprints(self):
        doodles = []
        doodle_count_max = self.allowed_components.get('Doodle', 0)
        doodle_count = random.randint(0, doodle_count_max)
        for i in range(doodle_count):
            doodles.append(self._create_doodle_blueprint())
        return doodles
    
    def _create_doodle_blueprint(self):
        num_points = random.randint(15, 25)
        points = []
        current_point = (0, 0)
        points.append(current_point)
        angle = random.uniform(0, 2 * math.pi)
        step_length = random.uniform(10, 20)
        base_max_delta_angle = math.radians(30)
        curviness = random.uniform(0.75, 3.5)
        max_delta_angle = base_max_delta_angle * curviness
        
        for i in range(1, num_points):
            delta_angle = random.uniform(-max_delta_angle, max_delta_angle)
            angle += delta_angle
            step = step_length * random.uniform(0.95, 1.05)
            new_x = current_point[0] + step * math.cos(angle)
            new_y = current_point[1] + step * math.sin(angle)
            tolerance = 0.05 * step
            new_x += random.uniform(-tolerance, tolerance)
            new_y += random.uniform(-tolerance, tolerance)
            new_point = (new_x, new_y)
            points.append(new_point)
            current_point = new_point
        
        def smooth(points, window_size=3):
            smoothed = []
            n = len(points)
            for i in range(n):
                sum_x, sum_y, count = 0, 0, 0
                for j in range(max(0, i - window_size), min(n, i + window_size + 1)):
                    sum_x += points[j][0]
                    sum_y += points[j][1]
                    count += 1
                smoothed.append((sum_x / count, sum_y / count))
            return smoothed
        
        smoothed_points = smooth(points, window_size=2)
        start_coord = smoothed_points[0]
        end_coord = smoothed_points[-1]
        total_length = 0
        for i in range(1, len(smoothed_points)):
            dx = smoothed_points[i][0] - smoothed_points[i-1][0]
            dy = smoothed_points[i][1] - smoothed_points[i-1][1]
            total_length += math.hypot(dx, dy)
        
        return {
            'points': smoothed_points,
            'color': random_border_color(),
            'thickness': random_thickness(),
            'skill_trace': {
                'start_coord': start_coord,
                'end_coord': end_coord,
                'length': total_length,
                'curviness': curviness
            }
        }
    
    def _create_shape_class(self):
        generator = self
        
        class CompositeShape(PlotObject):
            ALIAS = generator.shape_name

            def __init__(self, center=None, scale=1.0, angle=0, canvas=(0, 800, 0, 600), label=None):
                super().__init__()
                self.canvas = canvas
                self.center = center if center else ((canvas[0] + canvas[1]) / 2, (canvas[2] + canvas[3]) / 2)
                self.scale = scale
                self.angle = angle
                self.label = label
                self.is_composite = True
                # Store the color_mode from the generator so that recolor() can access it.
                self.color_mode = generator.color_mode
                
                self.component_blueprints = generator.component_blueprints
                self.doodle_blueprints = generator.doodle_blueprints
                self.components = []
                self._geometry_locked = False
            
            def _instantiate_components(self):
                self.components = []
                for bp in self.component_blueprints:
                    rel_x = bp['rel_distance'] * math.cos(math.radians(bp['rel_angle']))
                    rel_y = bp['rel_distance'] * math.sin(math.radians(bp['rel_angle']))
                    scaled_x = rel_x * self.scale
                    scaled_y = rel_y * self.scale
                    tol_factor_x = random.uniform(0.95, 1.05)
                    tol_factor_y = random.uniform(0.95, 1.05)
                    scaled_x *= tol_factor_x
                    scaled_y *= tol_factor_y
                    rotated_x = (scaled_x * math.cos(math.radians(self.angle)) -
                                 scaled_y * math.sin(math.radians(self.angle)))
                    rotated_y = (scaled_x * math.sin(math.radians(self.angle)) +
                                 scaled_y * math.cos(math.radians(self.angle)))
                    abs_x = self.center[0] + rotated_x
                    abs_y = self.center[1] + rotated_y
                    abs_rotation = (bp['rel_rotation'] + self.angle) % 360
                    
                    if bp['type'] == Line:
                        length = 30 * self.scale * bp['size_factor']
                        angle_rad = math.radians(abs_rotation)
                        p1 = (abs_x, abs_y)
                        p2 = (abs_x + length * math.cos(angle_rad),
                              abs_y + length * math.sin(angle_rad))
                        component = Line(
                            p1=p1, p2=p2,
                            color=bp['border_color'],
                            thickness=bp['thickness'],
                            canvas=self.canvas,
                            label=f"{self.label}-L{len(self.components)+1}" if self.label else None
                        )
                    
                    elif bp['type'] == SolidOval:
                        width = 40 * self.scale * bp['size_factor']
                        height = 30 * self.scale * bp['size_factor']
                        component = SolidOval(
                            center=(abs_x, abs_y),
                            width=width, height=height,
                            angle=abs_rotation,
                            border_color=bp['border_color'],
                            fill_color=bp['fill_color'],
                            thickness=bp['thickness'],
                            canvas=self.canvas,
                            label=f"{self.label}-O{len(self.components)+1}" if self.label else None
                        )
                    
                    elif bp['type'] == SolidRectangle:
                        width = 40 * self.scale * bp['size_factor']
                        height = 30 * self.scale * bp['size_factor']
                        component = SolidRectangle(
                            center=(abs_x, abs_y),
                            width=width, height=height,
                            angle=abs_rotation,
                            border_color=bp['border_color'],
                            fill_color=bp['fill_color'],
                            thickness=bp['thickness'],
                            canvas=self.canvas,
                            label=f"{self.label}-R{len(self.components)+1}" if self.label else None
                        )
                    
                    elif bp['type'] == SolidTriangle:
                        size = 30 * self.scale * bp['size_factor']
                        vertices = [
                            (abs_x, abs_y + size),
                            (abs_x - size * 0.866, abs_y - size * 0.5),
                            (abs_x + size * 0.866, abs_y - size * 0.5)
                        ]
                        rotated_vertices = [
                            rotate_point(v, (abs_x, abs_y), abs_rotation) for v in vertices
                        ]
                        component = SolidTriangle(
                            vertices=rotated_vertices,
                            border_color=bp['border_color'],
                            fill_color=bp['fill_color'],
                            thickness=bp['thickness'],
                            canvas=self.canvas,
                            label=f"{self.label}-T{len(self.components)+1}" if self.label else None
                        )
                    else:
                        continue
                    
                    self.components.append(component)
            
            def _get_transformed_doodle(self, doodle_blueprint):
                transformed_points = []
                for x, y in doodle_blueprint['points']:
                    scaled_x = x * self.scale
                    scaled_y = y * self.scale
                    rotated_x = (scaled_x * math.cos(math.radians(self.angle)) -
                                 scaled_y * math.sin(math.radians(self.angle)))
                    rotated_y = (scaled_x * math.sin(math.radians(self.angle)) +
                                 scaled_y * math.cos(math.radians(self.angle)))
                    abs_x = self.center[0] + rotated_x
                    abs_y = self.center[1] + rotated_y
                    transformed_points.append((abs_x, abs_y))
                return transformed_points
            
            def assign_geometry(self):
                    if not self._geometry_locked:
                        self._instantiate_components()
                        self.enforce_bounds()
                        self.lock_geometry()  # Now uses the base class method which calls create_children.
            def create_children(self):
                """Store component objects as children."""
                if not self._geometry_locked:
                    return
                self.children = []
                for comp in self.components:
                    if hasattr(comp, 'perform_skills'):
                        self.children.append(comp)
            
            def render(self, ax):
                if not self._geometry_locked:
                    self.assign_geometry()
                for component in self.components:
                    component.render(ax)
                for doodle in self.doodle_blueprints:
                    doodle_points = self._get_transformed_doodle(doodle)
                    xs = [p[0] for p in doodle_points]
                    ys = [p[1] for p in doodle_points]
                    ax.plot(xs, ys, 
                            color=doodle['color'],
                            linewidth=doodle['thickness'],
                            alpha=0.7)
                if self.label:
                    ax.text(self.center[0], self.center[1], self.label,
                            ha='center', va='center',
                            fontsize=10, fontweight='bold',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
            
            def set_bottom_left(self, x, y, **kwargs):
                if not self._geometry_locked:
                    self.assign_geometry()
                bbox = self.get_bbox()
                current_bl_x, current_bl_y = bbox[0], bbox[1]
                shift_x = x - current_bl_x
                shift_y = y - current_bl_y
                self.center = (self.center[0] + shift_x, self.center[1] + shift_y)
                self._geometry_locked = False
                if 'angle' in kwargs:
                    self.angle = kwargs['angle']
                if 'scale' in kwargs:
                    self.scale = kwargs['scale']
            
            def get_bbox(self):
                all_points = []
                for component in self.components:
                    bbox = component.get_bbox()
                    all_points.extend([(bbox[0], bbox[1]), (bbox[2], bbox[3])])
                for doodle in self.doodle_blueprints:
                    transformed = self._get_transformed_doodle(doodle)
                    all_points.extend(transformed)
                x_coords = [p[0] for p in all_points]
                y_coords = [p[1] for p in all_points]
                return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            
            def contains_point(self, point):
                if not self._geometry_locked:
                    self.assign_geometry()
                for component in self.components:
                    if component.contains_point(point):
                        return True
                tolerance = 3 * (random_thickness() if self.doodle_blueprints else 1)
                for doodle in self.doodle_blueprints:
                    transformed = self._get_transformed_doodle(doodle)
                    for i in range(len(transformed) - 1):
                        p1 = transformed[i]
                        p2 = transformed[i + 1]
                        if self._point_to_line_distance(point, p1, p2) <= tolerance:
                            return True
                return False
            
            def _point_to_line_distance(self, point, line_p1, line_p2):
                x, y = point
                x1, y1 = line_p1
                x2, y2 = line_p2
                line_length_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
                if line_length_sq == 0:
                    return math.hypot(x - x1, y - y1)
                t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_length_sq))
                proj_x = x1 + t * (x2 - x1)
                proj_y = y1 + t * (y2 - y1)
                return math.hypot(x - proj_x, y - proj_y)
            
            def perform_skills(self, verbose=False):
                if not self._geometry_locked:
                    self.assign_geometry()

                # Get the skills trees for each component child
                children_trees = [component.perform_skills(verbose=False) for component in self.components]

                # Compute approximate area as sum of component areas.
                area = 0
                for component in self.components:
                    if hasattr(component, 'width') and hasattr(component, 'height'):
                        area += component.width * component.height
                    elif hasattr(component, 'vertices'):
                        vertices = component.vertices
                        n = len(vertices)
                        a = 0
                        for i in range(n):
                            j = (i + 1) % n
                            a += vertices[i][0] * vertices[j][1]
                            a -= vertices[j][0] * vertices[i][1]
                        area += abs(a) / 2

                # Round key skill fields
                rounded_center = (round_to_nearest(self.center[0], 1), round_to_nearest(self.center[1], 1))
                rounded_scale = round_to_nearest(self.scale, 1) + 1
                rounded_angle = round_to_nearest(self.angle, 1)
                rounded_area = round_to_nearest(area, 1)

                label_info = f", Label='{self.label}'" if self.label else ""

                # Create a standardized component list string: each entry is "Type#ID"
                component_list = ", ".join(f"{component.ALIAS}#{component.obj_id}" for component in self.components) + "" if not self.doodle_blueprints else " and a curved drawn doodle"

                tree = {
                    "action": "RecognizeCompositeShape",
                    "object": f"{self.ALIAS}#{self.obj_id}" if not self.label else f"{self.ALIAS}#{self.obj_id} labeled as {self.label}",
                    "details": [
                        {
                            "action": "LocalizeCompositeShape",
                            "object": f"{self.ALIAS}#{self.obj_id}",
                            "details": f"Center: {rounded_center}, Scale: {rounded_scale}, Angle: {rounded_angle}{label_info}"
                        },
                        {
                            "action": "ListComponents",
                            "object": f"{self.ALIAS}#{self.obj_id}",
                            "details": f"Component list: {component_list}"
                        },
                        {
                            "action": "MeasureCompositeShape",
                            "object": f"{self.ALIAS}#{self.obj_id}",
                            "details": f"Approximate Area (including white-space between parts of it): {rounded_area}"
                        }
                    ],
                    "children": children_trees
                }

                if verbose:
                    for line in self.skills_tree_to_text(tree):
                        print(line)

                return tree

            
            def enforce_bounds(self):
                bbox = self.get_bbox()
                xmin, xmax, ymin, ymax = self.canvas
                if (bbox[0] < xmin or bbox[2] > xmax or bbox[1] < ymin or bbox[3] > ymax):
                    raise ValueError(f"Shape exceeds canvas bounds: {bbox} vs canvas {self.canvas}")
            
            def recolor(self, border_color=None, fill_color=None, doodle_color=None):
                """
                Recolor the composite shape.
                Behavior depends on the color_mode:
                - If color_mode is "fixed": any provided new color will override every component.
                - If color_mode is "mapped": each blueprint retains its original color identity.
                  If a dictionary is provided, it maps original colors to new colors;
                  if a single color is provided, it is applied to every original color.
                - Otherwise (unfixed): each blueprint is updated individually.
                """
                for bp in self.component_blueprints:
                    if self.color_mode == "fixed":
                        if border_color is not None:
                            bp['border_color'] = border_color
                        if fill_color is not None and 'fill_color' in bp:
                            bp['fill_color'] = fill_color
                    elif self.color_mode == "mapped":
                        if border_color is not None:
                            if isinstance(border_color, dict):
                                bp['border_color'] = border_color.get(bp.get('orig_border_color'), bp['border_color'])
                            else:
                                bp['border_color'] = border_color
                        if fill_color is not None and 'fill_color' in bp:
                            if isinstance(fill_color, dict):
                                bp['fill_color'] = fill_color.get(bp.get('orig_fill_color'), bp['fill_color'])
                            else:
                                bp['fill_color'] = fill_color
                    else:
                        if border_color is not None:
                            bp['border_color'] = border_color
                        if fill_color is not None and 'fill_color' in bp:
                            bp['fill_color'] = fill_color
                for component in self.components:
                    if hasattr(component, 'color') and border_color is not None:
                        component.color = border_color
                    if hasattr(component, 'border_color') and border_color is not None:
                        component.border_color = border_color
                    if hasattr(component, 'fill_color') and fill_color is not None:
                        component.fill_color = fill_color
                for doodle in self.doodle_blueprints:
                    if self.color_mode == "fixed":
                        if doodle_color is not None:
                            doodle['color'] = doodle_color
                    elif self.color_mode == "mapped":
                        if doodle_color is not None:
                            if isinstance(doodle_color, dict):
                                doodle['color'] = doodle_color.get(doodle.get('orig_color'), doodle['color'])
                            else:
                                doodle['color'] = doodle_color
                    else:
                        if doodle_color is not None:
                            doodle['color'] = doodle_color
                self._geometry_locked = False
        
        return CompositeShape

    def generate_shape(self, **kwargs):
        return self.ComponentShape(**kwargs)