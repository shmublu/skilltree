#!/usr/bin/env python3
import math
import random
import json
import re
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle, Polygon
import matplotlib.colors as mcolors

from base import PlotObject
from utilities import get_line_length_and_angle, rotate_point

###############################################################################
# Utility functions for style and geometry
###############################################################################
def random_color():
    # 50% chance to return "black", otherwise a random choice.
    if random.random() < 0.5:
        return "black"
    else:
        return random.choice(["red", "blue", "green", "purple", "orange"])

def random_thickness():
    return random.uniform(1, 3)

def random_fill_color():
    # Return colors with alpha transparency (0.3-0.5)
    alpha = random.uniform(0.3, 0.5)
    if random.random() < 0.5:
        rgba = mcolors.to_rgba("white", alpha)
        return rgba
    base_color = random.choice(["lightcoral", "skyblue", "lightgreen", "plum", "gold"])
    rgba = mcolors.to_rgba(base_color, alpha)
    return rgba

###############################################################################
# Line
###############################################################################
class Line(PlotObject):
    ALIAS = "Line"

    def __init__(self, p1=None, p2=None, color=None, thickness=None, canvas=(0, 800, 0, 600), label=None):
        super().__init__()
        self.canvas = canvas
        self.color = color if color is not None else random_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.p1 = p1  # may be None
        self.p2 = p2  # may be None
        self.label = label
        self._geometry_locked = (self.p1 is not None and self.p2 is not None)

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
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "RecognizeInstanceLine",
            "object": f"Line#{self.obj_id}" if not self.label else f"Line labeled as {self.label}",
            "details": [
                {"action": "LocalizeLine", "object": f"Line#{self.obj_id}", "details": f"(Endpoints: {self.p1}, {self.p2}{label_info})"},
                {"action": "MeasureLine", "object": f"Line#{self.obj_id}", "details": f"(Length={length:.1f}, Angle={angle:.1f})"}
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
    ALIAS = "SolidOval"

    def __init__(self, center=None, width=None, height=None, angle=None,
                 border_color=None, fill_color=None, thickness=None, 
                 canvas=(0, 800, 0, 600), is_circle=False, label=None):
        super().__init__()
        self.canvas = canvas
        self.border_color = border_color if border_color is not None else random_color()
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle
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
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "RecognizeInstanceOval",
            "object": f"Oval#{self.obj_id}" if not self.label else f"Oval labeled as {self.label}",
            "details": [
                {"action": "LocalizeOval", "object": f"SolidOval#{self.obj_id}", "details": f"(Center: {self.center}, W={self.width:.1f}, H={self.height:.1f}, Angle={self.angle:.1f}{label_info})"},
                {"action": "MeasureOval", "object": f"SolidOval#{self.obj_id}", "details": f"(Approximate Area={self.width*self.height*math.pi/4:.1f})"}
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
    ALIAS = "SolidRectangle"

    def __init__(self, center=None, width=None, height=None, angle=None,
                 border_color=None, fill_color=None, thickness=None,
                 canvas=(0, 800, 0, 600), is_square=False, label=None):
        super().__init__()
        self.canvas = canvas
        self.border_color = border_color if border_color is not None else random_color()
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.center = center
        self.width = width
        self.height = height
        self.angle = angle
        self.is_square = is_square
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
            if self.is_square:
                self.height = self.width
            if self.center is None:
                rad = math.radians(self.angle if self.angle is not None else 0)
                bbox_w = abs(self.width * math.cos(rad)) + abs(self.height * math.sin(rad))
                bbox_h = abs(self.width * math.sin(rad)) + abs(self.height * math.cos(rad))
                cx = random.uniform(xmin + bbox_w/2, xmax - bbox_w/2)
                cy = random.uniform(ymin + bbox_h/2, ymax - bbox_h/2)
                self.center = (cx, cy)
            if self.angle is None:
                self.angle = random.uniform(0, 180)
            self._geometry_locked = True
        self.enforce_bounds()

    def render(self, ax):
        if not self._geometry_locked:
            self.assign_geometry()
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
        self._geometry_locked = True
        self.enforce_bounds()

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
        x, y = point
        cx, cy = self.center
        theta = math.radians(-self.angle)
        x_rot = math.cos(theta) * (x - cx) - math.sin(theta) * (y - cy)
        y_rot = math.sin(theta) * (x - cx) + math.cos(theta) * (y - cy)
        return (abs(x_rot) <= self.width / 2) and (abs(y_rot) <= self.height / 2)
    
    def get_corners(self):
        # Compute the four corners of the rectangle.
        rad = math.radians(self.angle)
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        corners = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
        rotated = [rotate_point(c, (0, 0), self.angle) for c in corners]
        return [(self.center[0] + x, self.center[1] + y) for (x, y) in rotated]

    def perform_skills(self, verbose=False):
        children_trees = []
        line_ids = []
        # Create child line objects for each edge if border and fill colors differ.
        if self.border_color != self.fill_color:
            corners = self.get_corners()
            n = len(corners)
            for i in range(n):
                p1 = corners[i]
                p2 = corners[(i+1) % n]
                line = Line(p1=p1, p2=p2, color=self.border_color, thickness=self.thickness, canvas=self.canvas)
                line._geometry_locked = True
                children_trees.append(line.perform_skills(verbose=verbose))
                line_ids.append(line.obj_id)
        area = self.width * self.height
        perimeter = 2 * (self.width + self.height)
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "GroupLine",
            "object": f"Rectangle#{self.obj_id}"  if not self.label else f"Rectangle labeled as {self.label}",
            "details": [
                {"action": "RecognizeInstanceRectangle", "object": f"Rectangle#{self.obj_id}"},
                {"action": "LocalizeRectangle", "object": f"Rectangle#{self.obj_id}", "details": f"(Corners: {corners[0]}, {corners[1]}, {corners[2]}, {corners[3]}) (W={self.width:.1f}, H={self.height:.1f}, Angle={self.angle:.1f}{label_info}, from lineIDs={line_ids})"},
                {"action": "MeasureRectangle", "object": f"Rectangle#{self.obj_id}", "details": f"(Area={area:.1f}, Perimeter={perimeter:.1f})"}
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
    ALIAS = "SolidTriangle"

    def __init__(self, vertices=None, border_color=None, fill_color=None, thickness=None,
                 canvas=(0, 800, 0, 600), label=None):
        super().__init__()
        self.canvas = canvas
        self.border_color = border_color if border_color is not None else random_color()
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.vertices = vertices if (vertices is not None and len(vertices) == 3) else [None, None, None]
        self.label = label
        self._geometry_locked = (None not in self.vertices)

    def assign_geometry(self):
        if not self._geometry_locked:
            xmin, xmax, ymin, ymax = self.canvas
            self.vertices = [v if v is not None else (random.uniform(xmin, xmax), random.uniform(ymin, ymax))
                             for v in self.vertices]
            self._geometry_locked = True
        self.enforce_bounds()

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
    
    def perform_skills(self, verbose=False):
        children_trees = []
        line_ids = []
        if self.border_color != self.fill_color:
            pts = self.vertices
            n = len(pts)
            for i in range(n):
                p1 = pts[i]
                p2 = pts[(i+1) % n]
                line = Line(p1=p1, p2=p2, color=self.border_color, thickness=self.thickness, canvas=self.canvas)
                line._geometry_locked = True
                children_trees.append(line.perform_skills(verbose=verbose))
                line_ids.append(line.obj_id)
        # Compute triangle area using the determinant formula.
        x1, y1 = self.vertices[0]
        x2, y2 = self.vertices[1]
        x3, y3 = self.vertices[2]
        area = abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2.0
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "GroupLine",
            "object": f"Triangle#{self.obj_id}"  if not self.label else f"Triangle labeled as {self.label}",
            "details": [
                {"action": "RecognizeInstanceTriangle", "object": f"Triangle#{self.obj_id}"},
                {"action": "LocalizeTriangle", "object": f"Triangle#{self.obj_id}", "details": f"(Vertices: {self.vertices}), from lineIDs={line_ids})"},
                {"action": "MeasureTriangle", "object": f"Triangle#{self.obj_id}", "details": f"(Area={area:.1f})"}
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
        self.border_color = border_color if border_color is not None else random_color()
        self.fill_color = fill_color if fill_color is not None else random_fill_color()
        self.thickness = thickness if thickness is not None else random_thickness()
        self.num_vertices = max(num_vertices, 3)
        self.label = label
        if vertices is None or len(vertices) < 3:
            self.vertices = None
            self._geometry_locked = False
        else:
            self.vertices = vertices
            self._geometry_locked = True

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
            self._geometry_locked = True
        self.enforce_bounds()

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
        self._geometry_locked = True
        self.enforce_bounds()

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
        children_trees = []
        line_ids = []
        if self.border_color != self.fill_color:
            pts = self.vertices
            n = len(pts)
            for i in range(n):
                p1 = pts[i]
                p2 = pts[(i + 1) % n]
                line = Line(p1=p1, p2=p2, color=self.border_color, thickness=self.thickness, canvas=self.canvas)
                line._geometry_locked = True
                children_trees.append(line.perform_skills(verbose=verbose))
                line_ids.append(line.obj_id)
        label_info = f", Label='{self.label}'" if self.label else ""
        tree = {
            "action": "GroupLine",
            "object": f"Polygon#{self.obj_id}"  if not self.label else f"Polygon labeled as {self.label}",
            "details": [
                {"action": "RecognizeInstancePolygon", "object": f"Polygon#{self.obj_id}"},
                {"action": "LocalizePolygon", "object": f"Polygon#{self.obj_id}", "details": f"(Vertices: {self.vertices}),  from lineIDs={line_ids})"},
                {"action": "MeasurePolygon", "object": f"Polygon#{self.obj_id}", "details": ""}
            ],
            "children": children_trees 
        }
        if verbose:
            for line in self.skills_tree_to_text(tree):
                print(line)
        return tree






class ShapeGeneratorFactory(PlotObject):
    ALIAS = "ShapeGeneratorFactory"
    
    # Define a list of adjectives and nouns for random naming
    ADJECTIVES = ["Cosmic", "Mystic", "Geometric", "Harmonic", "Crystal", "Elegant", "Dynamic", 
                  "Balanced", "Radiant", "Fluid", "Quantum", "Vibrant", "Symmetric", "Arcane"]
    NOUNS = ["Star", "Bloom", "Nexus", "Prism", "Vortex", "Sigil", "Emblem", 
             "Glyph", "Mandala", "Cipher", "Rune", "Totem", "Insignia", "Crest"]
    
    # Define pattern types for shape arrangement
    PATTERNS = ["radial", "concentric", "stacked", "mirrored", "interlocked"]
    
    def __init__(self, pattern_type=None, components=None, canvas=(0, 800, 0, 600)):
        super().__init__()
        self.canvas = canvas
        
        # Generate a unique name for this shape type
        self.shape_name = f"{random.choice(self.ADJECTIVES)}{random.choice(self.NOUNS)}"
        
        # Pattern configuration
        self.pattern_type = pattern_type if pattern_type else random.choice(self.PATTERNS)
        
        # Components to use (limited to 4 max, not including doodle)
        self.components = components if components else self._select_random_components()
        self.num_components = len(self.components)
        
        # Doodle configuration
        self.has_doodle = random.random() < 0.5  # 50% chance to include a doodle
        self.doodle_points = self._generate_doodle() if self.has_doodle else None
        
        # Generate the new shape class
        self.shape_class = self._create_shape_class()
    
    def _select_random_components(self):
        """Select random component types to use in the new shape."""
        available_shapes = [Line, SolidOval, SolidRectangle, SolidTriangle, SolidPolygon]
        num_components = random.randint(2, 4)  # Between 2 and 4 components
        return random.sample(available_shapes, num_components)
    
    def _generate_doodle(self):
        """Generate a smooth doodle curve."""
        num_control_points = random.randint(5, 10)
        
        # Generate control points in a normalized space (0-1)
        control_points = []
        for i in range(num_control_points):
            angle = 2 * math.pi * i / num_control_points
            # Add some randomness to the radius
            radius = 0.3 + 0.1 * random.random()
            x = 0.5 + radius * math.cos(angle)
            y = 0.5 + radius * math.sin(angle)
            # Add some random jitter
            x += random.uniform(-0.05, 0.05)
            y += random.uniform(-0.05, 0.05)
            control_points.append((x, y))
        
        # Close the loop
        control_points.append(control_points[0])
        
        # Generate more points for a smoother curve
        smooth_points = []
        steps = 100
        for i in range(len(control_points) - 1):
            p0 = control_points[i]
            p1 = control_points[(i + 1) % len(control_points)]
            for t in range(steps):
                # Linear interpolation for simplicity
                # Could be enhanced with spline interpolation for smoother curves
                alpha = t / steps
                x = p0[0] * (1 - alpha) + p1[0] * alpha
                y = p0[1] * (1 - alpha) + p1[1] * alpha
                smooth_points.append((x, y))
        
        return smooth_points
    
    def _create_shape_class(self):
        """Create a new shape class with the configured components and pattern."""
        pattern_type = self.pattern_type
        components = self.components
        doodle_points = self.doodle_points
        shape_name = self.shape_name
        
        # Define the new shape class
        class CustomShape(PlotObject):
            ALIAS = shape_name
            
            def __init__(self, center=None, scale=1.0, angle=0, 
                         color_scheme=None, canvas=(0, 800, 0, 600), label=None):
                super().__init__()
                self.canvas = canvas
                self.center = center
                self.scale = scale
                self.angle = angle
                self.label = label
                
                # Set default color scheme if none provided
                if color_scheme is None:
                    self.color_scheme = {
                        "primary": random_color(),
                        "secondary": random_color(),
                        "fill": random_fill_color(),
                        "doodle": random_color(),
                        "thickness": random_thickness()
                    }
                else:
                    self.color_scheme = color_scheme
                
                # Will store the component shapes
                self.shapes = []
                self._geometry_locked = (center is not None)
            
            def assign_geometry(self):
                if not self._geometry_locked:
                    xmin, xmax, ymin, ymax = self.canvas
                    if self.center is None:
                        self.center = (
                            random.uniform(xmin + 100, xmax - 100),
                            random.uniform(ymin + 100, ymax - 100)
                        )
                    
                    # Clear any existing shapes
                    self.shapes = []
                    
                    # Create the component shapes based on the pattern
                    if pattern_type == "radial":
                        self._create_radial_pattern()
                    elif pattern_type == "concentric":
                        self._create_concentric_pattern()
                    elif pattern_type == "stacked":
                        self._create_stacked_pattern()
                    elif pattern_type == "mirrored":
                        self._create_mirrored_pattern()
                    elif pattern_type == "interlocked":
                        self._create_interlocked_pattern()
                    
                    # Add doodle if present
                    if doodle_points:
                        self._add_doodle()
                    
                    self._geometry_locked = True
                
                self.enforce_bounds()
            
            def _create_radial_pattern(self):
                """Create shapes arranged in a radial pattern."""
                num_shapes = len(components)
                angle_step = 360 / num_shapes
                base_distance = 40 * self.scale
                
                for i, shape_class in enumerate(components):
                    component_angle = self.angle + i * angle_step
                    rad = math.radians(component_angle)
                    
                    # Position relative to center
                    rel_x = base_distance * math.cos(rad)
                    rel_y = base_distance * math.sin(rad)
                    
                    # Absolute position
                    pos_x = self.center[0] + rel_x
                    pos_y = self.center[1] + rel_y
                    
                    # Create and add the shape
                    shape = self._create_component(shape_class, (pos_x, pos_y), component_angle)
                    self.shapes.append(shape)
            
            def _create_concentric_pattern(self):
                """Create shapes arranged in concentric rings."""
                num_shapes = len(components)
                angle_offset = 360 / num_shapes
                
                for i, shape_class in enumerate(components):
                    # Alternate between inner and outer rings
                    ring_radius = (20 + 15 * (i % 2)) * self.scale
                    component_angle = self.angle + i * angle_offset
                    rad = math.radians(component_angle)
                    
                    # Position relative to center
                    rel_x = ring_radius * math.cos(rad)
                    rel_y = ring_radius * math.sin(rad)
                    
                    # Absolute position
                    pos_x = self.center[0] + rel_x
                    pos_y = self.center[1] + rel_y
                    
                    # Create and add the shape
                    shape = self._create_component(shape_class, (pos_x, pos_y), component_angle)
                    self.shapes.append(shape)
            
            def _create_stacked_pattern(self):
                """Create shapes stacked on top of each other."""
                base_offset = 10 * self.scale
                
                for i, shape_class in enumerate(components):
                    # Stack with small offsets
                    offset_x = i * base_offset
                    offset_y = i * base_offset
                    
                    # Rotate the offset
                    rad = math.radians(self.angle)
                    rotated_x = offset_x * math.cos(rad) - offset_y * math.sin(rad)
                    rotated_y = offset_x * math.sin(rad) + offset_y * math.cos(rad)
                    
                    # Absolute position
                    pos_x = self.center[0] + rotated_x
                    pos_y = self.center[1] + rotated_y
                    
                    # Create and add the shape with decreasing size
                    size_factor = 1.0 - (i * 0.15)  # Each shape gets smaller
                    shape = self._create_component(
                        shape_class, (pos_x, pos_y), 
                        self.angle, size_factor
                    )
                    self.shapes.append(shape)
            
            def _create_mirrored_pattern(self):
                """Create shapes in a mirrored arrangement."""
                base_distance = 30 * self.scale
                
                for i, shape_class in enumerate(components):
                    # Alternate between left and right sides
                    side_factor = 1 if i % 2 == 0 else -1
                    
                    # Position relative to center
                    rel_x = side_factor * base_distance
                    rel_y = (i // 2) * 15 * self.scale  # Offset vertically for pairs
                    
                    # Rotate the offset
                    rad = math.radians(self.angle)
                    rotated_x = rel_x * math.cos(rad) - rel_y * math.sin(rad)
                    rotated_y = rel_x * math.sin(rad) + rel_y * math.cos(rad)
                    
                    # Absolute position
                    pos_x = self.center[0] + rotated_x
                    pos_y = self.center[1] + rotated_y
                    
                    # Create and add the shape
                    # Mirror the angle for opposite sides
                    component_angle = self.angle + (180 if side_factor < 0 else 0)
                    shape = self._create_component(shape_class, (pos_x, pos_y), component_angle)
                    self.shapes.append(shape)
            
            def _create_interlocked_pattern(self):
                """Create shapes that interlock with each other."""
                num_shapes = len(components)
                angle_step = 360 / num_shapes
                base_distance = 25 * self.scale
                
                for i, shape_class in enumerate(components):
                    # Calculate position in a tighter arrangement
                    component_angle = self.angle + i * angle_step
                    rad = math.radians(component_angle)
                    
                    # Alternate between inner and outer positions
                    distance = base_distance * (0.8 if i % 2 == 0 else 1.2)
                    
                    # Position relative to center
                    rel_x = distance * math.cos(rad)
                    rel_y = distance * math.sin(rad)
                    
                    # Absolute position
                    pos_x = self.center[0] + rel_x
                    pos_y = self.center[1] + rel_y
                    
                    # Create and add the shape with rotation towards center
                    shape = self._create_component(
                        shape_class, (pos_x, pos_y), 
                        component_angle + 90  # Rotate to face inward/outward
                    )
                    self.shapes.append(shape)
            
            def _add_doodle(self):
                """Add a doodle around or through the shape."""
                # Scale and position the doodle
                scaled_doodle = []
                doodle_size = 60 * self.scale
                
                for x, y in doodle_points:
                    # Scale from [0,1] to proper size and position
                    scaled_x = self.center[0] + (x - 0.5) * doodle_size
                    scaled_y = self.center[1] + (y - 0.5) * doodle_size
                    
                    # Rotate around center
                    rotated_point = rotate_point(
                        (scaled_x, scaled_y), 
                        self.center, 
                        self.angle
                    )
                    scaled_doodle.append(rotated_point)
                
                # Store the doodle points for rendering
                self.doodle = scaled_doodle
            
            def _create_component(self, shape_class, position, angle, size_factor=1.0):
                """Helper method to create a component shape."""
                base_size = 20 * self.scale * size_factor
                
                if shape_class == Line:
                    p1 = position
                    angle_rad = math.radians(angle)
                    length = base_size
                    p2 = (
                        p1[0] + length * math.cos(angle_rad), 
                        p1[1] + length * math.sin(angle_rad)
                    )
                    return Line(
                        p1=p1, p2=p2, 
                        color=self.color_scheme["primary"], 
                        thickness=self.color_scheme["thickness"],
                        canvas=self.canvas,
                        label=f"{self.label}-L{len(self.shapes)+1}" if self.label else None
                    )
                
                elif shape_class == SolidOval:
                    return SolidOval(
                        center=position, 
                        width=base_size, 
                        height=base_size * 0.7, 
                        angle=angle, 
                        border_color=self.color_scheme["primary"],
                        fill_color=self.color_scheme["fill"],
                        thickness=self.color_scheme["thickness"],
                        canvas=self.canvas,
                        label=f"{self.label}-O{len(self.shapes)+1}" if self.label else None
                    )
                
                elif shape_class == SolidRectangle:
                    return SolidRectangle(
                        center=position, 
                        width=base_size, 
                        height=base_size * 0.8, 
                        angle=angle, 
                        border_color=self.color_scheme["primary"],
                        fill_color=self.color_scheme["fill"],
                        thickness=self.color_scheme["thickness"],
                        canvas=self.canvas,
                        label=f"{self.label}-R{len(self.shapes)+1}" if self.label else None
                    )
                
                elif shape_class == SolidTriangle:
                    # Create a triangle with vertices around the position
                    side_length = base_size
                    half_side = side_length / 2
                    height = side_length * math.sqrt(3) / 2
                    
                    # Calculate vertices before rotation
                    v1 = (position[0], position[1] - height * 2/3)
                    v2 = (position[0] - half_side, position[1] + height * 1/3)
                    v3 = (position[0] + half_side, position[1] + height * 1/3)
                    
                    # Rotate vertices around position
                    vertices = [
                        rotate_point(v1, position, angle),
                        rotate_point(v2, position, angle),
                        rotate_point(v3, position, angle)
                    ]
                    
                    return SolidTriangle(
                        vertices=vertices, 
                        border_color=self.color_scheme["primary"],
                        fill_color=self.color_scheme["fill"],
                        thickness=self.color_scheme["thickness"],
                        canvas=self.canvas,
                        label=f"{self.label}-T{len(self.shapes)+1}" if self.label else None
                    )
                
                elif shape_class == SolidPolygon:
                    # Create a regular polygon
                    num_vertices = random.randint(5, 6)
                    radius = base_size / 2
                    
                    vertices = []
                    for i in range(num_vertices):
                        vertex_angle = 360 * i / num_vertices + angle
                        vertex_x = position[0] + radius * math.cos(math.radians(vertex_angle))
                        vertex_y = position[1] + radius * math.sin(math.radians(vertex_angle))
                        vertices.append((vertex_x, vertex_y))
                    
                    return SolidPolygon(
                        vertices=vertices, 
                        num_vertices=num_vertices, 
                        border_color=self.color_scheme["primary"],
                        fill_color=self.color_scheme["fill"],
                        thickness=self.color_scheme["thickness"],
                        canvas=self.canvas,
                        label=f"{self.label}-P{len(self.shapes)+1}" if self.label else None
                    )
                
                return None
            
            def render(self, ax):
                """Render the custom shape with all its components."""
                if not self._geometry_locked:
                    self.assign_geometry()
                
                # Render all component shapes
                for shape in self.shapes:
                    shape.render(ax)
                
                # Render the doodle if present
                if hasattr(self, 'doodle') and self.doodle:
                    doodle_xs = [p[0] for p in self.doodle]
                    doodle_ys = [p[1] for p in self.doodle]
                    ax.plot(
                        doodle_xs, doodle_ys, 
                        color=self.color_scheme.get("doodle", "black"), 
                        linewidth=self.color_scheme.get("thickness", 2),
                        alpha=0.8,
                        zorder=10  # Ensure doodle is drawn on top
                    )
                
                # Add label if set
                if self.label:
                    # Place the label at the center of the shape
                    ax.text(
                        self.center[0], self.center[1], 
                        self.label, 
                        ha='center', va='center',
                        fontsize=10, fontweight='bold',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=2)
                    )
            
            def set_bottom_left(self, x, y, **kwargs):
                """Set the bottom left position of the shape's bounding box."""
                bbox = self.get_bbox()
                current_bl_x, current_bl_y = bbox[0], bbox[1]
                
                # Calculate the shift needed
                shift_x = x - current_bl_x
                shift_y = y - current_bl_y
                
                # Update center
                self.center = (self.center[0] + shift_x, self.center[1] + shift_y)
                
                # Update all component shapes
                for shape in self.shapes:
                    shape.set_bottom_left(shape.get_bbox()[0] + shift_x, shape.get_bbox()[1] + shift_y)
                
                # Update doodle if present
                if hasattr(self, 'doodle') and self.doodle:
                    self.doodle = [(p[0] + shift_x, p[1] + shift_y) for p in self.doodle]
                
                self.enforce_bounds()
            
            def get_bbox(self):
                """Get the bounding box of the entire custom shape."""
                if not self._geometry_locked:
                    self.assign_geometry()
                
                all_points = []
                for shape in self.shapes:
                    bbox = shape.get_bbox()
                    all_points.extend([(bbox[0], bbox[1]), (bbox[2], bbox[3])])
                
                if hasattr(self, 'doodle') and self.doodle:
                    all_points.extend(self.doodle)
                
                x_coords, y_coords = zip(*all_points)
                return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            
            def contains_point(self, point):
                """Check if the point is contained in any of the component shapes."""
                for shape in self.shapes:
                    if shape.contains_point(point):
                        return True
                
                # Check if point is on the doodle (with some tolerance)
                if hasattr(self, 'doodle') and self.doodle:
                    tolerance = 2  # pixels
                    for i in range(len(self.doodle) - 1):
                        p1, p2 = self.doodle[i], self.doodle[i+1]
                        if self._point_to_line_distance(point, p1, p2) <= tolerance:
                            return True
                
                return False
            
            def _point_to_line_distance(self, point, line_start, line_end):
                """Calculate the distance from a point to a line segment."""
                x, y = point
                x1, y1 = line_start
                x2, y2 = line_end
                
                A = x - x1
                B = y - y1
                C = x2 - x1
                D = y2 - y1
                
                dot = A * C + B * D
                len_sq = C * C + D * D
                param = dot / len_sq if len_sq != 0 else -1
                
                if param < 0:
                    xx = x1
                    yy = y1
                elif param > 1:
                    xx = x2
                    yy = y2
                else:
                    xx = x1 + param * C
                    yy = y1 + param * D
                
                dx = x - xx
                dy = y - yy
                return math.sqrt(dx * dx + dy * dy)
            
            def perform_skills(self, verbose=False):
                """Generate a skills tree for this custom shape."""
                children_trees = [shape.perform_skills(verbose=False) for shape in self.shapes]
                
                tree = {
                    "action": "RecognizeCustomShape",
                    "object": f"{self.ALIAS}#{id(self)}",
                    "details": [
                        {"action": "IdentifyShapeType", "details": f"Shape Type: {self.ALIAS}"},
                        {"action": "CountComponents", "details": f"Number of Components: {len(self.shapes)}"},
                        {"action": "DescribeArrangement", "details": f"Arrangement: {pattern_type} pattern"},
                        {"action": "LocalizeShape", "details": f"Center: {self.center}, Scale: {self.scale}, Angle: {self.angle}"}
                    ],
                    "children": children_trees
                }
                
                if hasattr(self, 'doodle') and self.doodle:
                    tree["details"].append({"action": "IdentifyDoodle", "details": "Doodle present"})
                
                if verbose:
                    for line in self.skills_tree_to_text(tree):
                        print(line)
                
                return tree
        
        return CustomShape
    
    def generate_shape(self, **kwargs):
        """Generate an instance of the custom shape."""
        return self.shape_class(**kwargs)