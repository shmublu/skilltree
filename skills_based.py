import math
import random
import os
import json
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import bisect

# We disable interactive mode and enforce a specific backend for consistency.
plt.ioff()
matplotlib.use("TkAgg", force=True)

##############################################################################
# ID Generator
##############################################################################
class UniqueIDGenerator:
    counters = {}

    @staticmethod
    def get_unique_id(alias):
        if alias not in UniqueIDGenerator.counters:
            UniqueIDGenerator.counters[alias] = 0
        this_id = UniqueIDGenerator.counters[alias]
        UniqueIDGenerator.counters[alias] += 1
        return this_id

QUESTIONS = {
    "Is there an <object type> in the image?": [],
    "Are there any parallel lines in the image?": [],
    "Are there any perpendicular lines in the image?": [],
    "Are there any arrows pointing <upward | downward | leftward | rightward>?": [],
}

##############################################################################
# Helper functions for angle comparisons and checks
##############################################################################
def angle_difference(a, b):
    diff = abs(a - b) % 360
    if diff > 180:
        diff = 360 - diff
    return diff

def is_arrow_pointing_direction(arrow, target_direction, tol=5):
    direction_angles = {"upward": 90, "downward": 270, "leftward": 180, "rightward": 0}
    target_angle = direction_angles[target_direction]
    return angle_difference(arrow.angle, target_angle) <= tol

def are_lines_parallel(line1, line2, tol=5):
    _, a1 = get_line_length_and_angle(line1.p1, line1.p2)
    _, a2 = get_line_length_and_angle(line2.p1, line2.p2)
    return angle_difference(a1, a2) <= tol

def are_lines_perpendicular(line1, line2, tol=5):
    _, a1 = get_line_length_and_angle(line1.p1, line1.p2)
    _, a2 = get_line_length_and_angle(line2.p1, line2.p2)
    return abs(angle_difference(a1, a2) - 90) <= tol

##############################################################################
# Base PlotObject with transformation and bounding-box support
##############################################################################
class PlotObject:
    ALIAS = "PlotObject"

    def __init__(self):
        self.obj_id = UniqueIDGenerator.get_unique_id(self.ALIAS)
        self.sub_references = []

    def assign_geometry(self):
        for child in self.sub_references:
            child.assign_geometry()

    def perform_skills(self):
        for child in self.sub_references:
            child.perform_skills()

    def render(self, ax):
        for child in self.sub_references:
            child.render(ax)

    def __repr__(self):
        return f"{self.ALIAS}#{self.obj_id}"

    def set_bottom_left(self, x, y, angle=0, **kwargs):
        # To be overridden by subclasses.
        pass

    # Export object structure as a JSON–serializable dict.
    def to_dict(self):
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

    # Recursively apply an affine transformation function to all coordinate attributes.
    def apply_transformation(self, func):
        for attr in ['p1', 'p2', 'center', 'base_position']:
            if hasattr(self, attr):
                value = getattr(self, attr)
                if value is not None and isinstance(value, tuple) and len(value) == 2:
                    setattr(self, attr, func(value))
        if hasattr(self, 'vertices') and self.vertices is not None:
            self.vertices = [func(v) if v is not None else None for v in self.vertices]
        for child in self.sub_references:
            child.apply_transformation(func)

    # Return a bounding box (min_x, min_y, max_x, max_y).
    def get_bbox(self):
        if hasattr(self, 'p1') and hasattr(self, 'p2'):
            return (min(self.p1[0], self.p2[0]),
                    min(self.p1[1], self.p2[1]),
                    max(self.p1[0], self.p2[0]),
                    max(self.p1[1], self.p2[1]))
        if hasattr(self, 'center') and hasattr(self, 'width') and hasattr(self, 'height'):
            return (self.center[0] - self.width/2, self.center[1] - self.height/2,
                    self.center[0] + self.width/2, self.center[1] + self.height/2)
        if hasattr(self, 'vertices') and self.vertices:
            xs = [v[0] for v in self.vertices if v is not None]
            ys = [v[1] for v in self.vertices if v is not None]
            return (min(xs), min(ys), max(xs), max(ys))
        bboxes = [child.get_bbox() for child in self.sub_references if hasattr(child, "get_bbox")]
        if bboxes:
            return (min(b[0] for b in bboxes),
                    min(b[1] for b in bboxes),
                    max(b[2] for b in bboxes),
                    max(b[3] for b in bboxes))
        return (0, 0, 0, 0)

##############################################################################
# Low-Level: Line
##############################################################################
def get_line_length_and_angle(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx)) % 360
    return (length, angle)

class LineLow(PlotObject):
    ALIAS = "Line"

    def __init__(self, p1=None, p2=None):
        super().__init__()
        if p1 is not None and p2 is not None:
            self.p1 = p1
            self.p2 = p2
            self._geometry_locked = True
        else:
            self.p1 = (0, 0)
            self.p2 = (0, 0)

    def assign_geometry(self):
        if not hasattr(self, "_geometry_locked") or not self._geometry_locked:
            length = random.uniform(10, 30)
            angle = random.uniform(0, 360)
            cx = random.uniform(20, 80)
            cy = random.uniform(20, 80)
            dx = (length / 2) * math.cos(math.radians(angle))
            dy = (length / 2) * math.sin(math.radians(angle))
            self.p1 = (cx - dx, cy - dy)
            self.p2 = (cx + dx, cy + dy)
        super().assign_geometry()

    def perform_skills(self):
        print(f"RecognizeInstanceLine => Line#{self.obj_id}")
        print(f"LocalizeLine => Line#{self.obj_id} (Endpoints: {self.p1}, {self.p2})")
        length, angle = get_line_length_and_angle(self.p1, self.p2)
        print(f"MeasureLine => Line#{self.obj_id} (Length={length:.1f}, Angle={angle:.1f})")

    def render(self, ax):
        ax.plot([self.p1[0], self.p2[0]],
                [self.p1[1], self.p2[1]],
                color='k', lw=2)

    def set_bottom_left(self, x, y, angle=0, length=10, **kwargs):
        rad = math.radians(angle)
        self.p1 = (x, y)
        self.p2 = (x + length * math.cos(rad), y + length * math.sin(rad))
        self._geometry_locked = True

    def get_bbox(self):
        return (min(self.p1[0], self.p2[0]),
                min(self.p1[1], self.p2[1]),
                max(self.p1[0], self.p2[0]),
                max(self.p1[1], self.p2[1]))

##############################################################################
# Low-Level: Oval
##############################################################################
class OvalLow(PlotObject):
    ALIAS = "Oval"

    def __init__(self, center=None, width=None, height=None, angle=None):
        super().__init__()
        if center is not None and width is not None and height is not None and angle is not None:
            self.center = center
            self.width = width
            self.height = height
            self.angle = angle
            self._geometry_locked = True
        else:
            self.center = (0, 0)
            self.width = 10
            self.height = 10
            self.angle = 0

    def assign_geometry(self):
        if not hasattr(self, "_geometry_locked") or not self._geometry_locked:
            cx = random.uniform(20, 80)
            cy = random.uniform(20, 80)
            w = random.uniform(10, 30)
            h = random.uniform(10, 30)
            ang = random.uniform(0, 360)
            self.center = (cx, cy)
            self.width = w
            self.height = h
            self.angle = ang
        super().assign_geometry()

    def perform_skills(self):
        print(f"RecognizeInstanceOval => Oval#{self.obj_id}")
        print(f"LocalizeOval => Oval#{self.obj_id} (Center={self.center}, W={self.width}, H={self.height}, Angle={self.angle:.1f})")
        area = math.pi * (self.width / 2.0) * (self.height / 2.0)
        print(f"MeasureOval => Oval#{self.obj_id} (Area={area:.1f})")

    def render(self, ax):
        e = Ellipse(xy=self.center,
                    width=self.width,
                    height=self.height,
                    angle=self.angle,
                    edgecolor='k',
                    facecolor='none',
                    lw=2)
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

    def get_bbox(self):
        return (self.center[0] - self.width/2,
                self.center[1] - self.height/2,
                self.center[0] + self.width/2,
                self.center[1] + self.height/2)

##############################################################################
# Rectangle (with 4 lines)
##############################################################################
def rotate_point(pt, center, ang_deg):
    r = math.radians(ang_deg)
    (x, y) = pt
    (cx, cy) = center
    dx, dy = x - cx, y - cy
    rx = cx + dx * math.cos(r) - dy * math.sin(r)
    ry = cy + dx * math.sin(r) + dy * math.cos(r)
    return (rx, ry)

class RectangleObj(PlotObject):
    ALIAS = "Rectangle"

    def __init__(self, center=None, width=None, height=None, angle=None):
        super().__init__()
        if center is not None and width is not None and height is not None and angle is not None:
            self.center = center
            self.width = width
            self.height = height
            self.angle = angle
            self._geometry_locked = True
        else:
            self.center = (0, 0)
            self.width = 0
            self.height = 0
            self.angle = 0
        for _ in range(4):
            line = LineLow()
            self.sub_references.append(line)

    def assign_geometry(self):
        if not hasattr(self, "_geometry_locked") or not self._geometry_locked:
            self.center = (random.uniform(30, 70), random.uniform(30, 70))
            self.width = random.uniform(10, 30)
            self.height = random.uniform(10, 30)
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
        lines = [ln for ln in self.sub_references if isinstance(ln, LineLow)]
        if len(lines) == 4:
            for i in range(4):
                lines[i].p1 = corners[i]
                lines[i].p2 = corners[(i + 1) % 4]
                lines[i]._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        for sub in self.sub_references:
            sub.perform_skills()
        line_ids = [sub.obj_id for sub in self.sub_references if isinstance(sub, LineLow)]
        if line_ids:
            print(f"GroupLine => Rectangle#{self.obj_id} from lineIDs={line_ids}")
        print(f"RecognizeInstanceRectangle => Rectangle#{self.obj_id}")
        print(f"LocalizeRectangle => Rectangle#{self.obj_id} (W={self.width:.1f}, H={self.height:.1f}, Angle={self.angle:.1f})")
        area = self.width * self.height
        perimeter = 2.0 * (self.width + self.height)
        print(f"MeasureRectangle => Rectangle#{self.obj_id} (Area={area:.1f}, Perimeter={perimeter:.1f})")

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
        return (self.center[0]-self.width/2, self.center[1]-self.height/2,
                self.center[0]+self.width/2, self.center[1]+self.height/2)

##############################################################################
# Triangle
##############################################################################
class TriangleObj(PlotObject):
    ALIAS = "Triangle"

    def __init__(self, vertices=None):
        super().__init__()
        if vertices is not None and len(vertices) == 3:
            self.vertices = vertices
            self._geometry_locked = True
        else:
            self.vertices = [(0, 0), (0, 0), (0, 0)]
            self._geometry_locked = False
        for _ in range(3):
            line = LineLow()
            self.sub_references.append(line)

    def assign_geometry(self):
        if not hasattr(self, "_geometry_locked") or not self._geometry_locked:
            x1, y1 = random.uniform(20, 80), random.uniform(20, 80)
            x2, y2 = x1 + random.uniform(10, 30), y1 + random.uniform(-20, 20)
            x3, y3 = x1 + random.uniform(-20, 20), y1 + random.uniform(10, 30)
            self.vertices = [(x1, y1), (x2, y2), (x3, y3)]
        lines = [ln for ln in self.sub_references if isinstance(ln, LineLow)]
        if len(lines) == 3:
            for i in range(3):
                lines[i].p1 = self.vertices[i]
                lines[i].p2 = self.vertices[(i + 1) % 3]
                lines[i]._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        for sub in self.sub_references:
            sub.perform_skills()
        line_ids = [line.obj_id for line in self.sub_references if isinstance(line, LineLow)]
        if line_ids:
            print(f"GroupLine => Triangle#{self.obj_id} from lineIDs={line_ids}")
        print(f"RecognizeInstanceTriangle => Triangle#{self.obj_id}")
        print(f"LocalizeTriangle => Triangle#{self.obj_id} (Vertices={self.vertices})")
        x1, y1 = self.vertices[0]
        x2, y2 = self.vertices[1]
        x3, y3 = self.vertices[2]
        area = abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2.0
        print(f"MeasureTriangle => Triangle#{self.obj_id} (Area={area:.1f})")

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

##############################################################################
# Polygon
##############################################################################
class PolygonObj(PlotObject):
    ALIAS = "Polygon"

    def __init__(self, center=None, sides=None, radius=None, angle=None):
        super().__init__()
        if center is not None and sides is not None and radius is not None and angle is not None:
            self.center = center
            self.sides = sides
            self.radius = radius
            self.angle = angle
            self._geometry_locked = True
        else:
            self.center = (0, 0)
            self.sides = 3
            self.radius = 0
            self.angle = 0
        for _ in range(10):
            line = LineLow()
            self.sub_references.append(line)

    def assign_geometry(self):
        if not hasattr(self, "_geometry_locked") or not self._geometry_locked:
            self.center = (random.uniform(30, 70), random.uniform(30, 70))
            self.sides = random.randint(3, 6)
            self.radius = random.uniform(10, 20)
            self.angle = random.uniform(0, 180)
        angle_step = 360.0 / self.sides
        corners = []
        for i in range(self.sides):
            theta = math.radians(self.angle + i * angle_step)
            px = self.center[0] + self.radius * math.cos(theta)
            py = self.center[1] + self.radius * math.sin(theta)
            corners.append((px, py))
        lines = [ln for ln in self.sub_references if isinstance(ln, LineLow)]
        if len(lines) >= self.sides:
            for i in range(self.sides):
                lines[i].p1 = corners[i]
                lines[i].p2 = corners[(i + 1) % self.sides]
                lines[i]._geometry_locked = True
            for j in range(self.sides, len(lines)):
                lines[j].p1 = (0, 0)
                lines[j].p2 = (0, 0)
                lines[j]._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        used_lines = [ln for ln in self.sub_references[:self.sides] if isinstance(ln, LineLow)]
        for ln in used_lines:
            ln.perform_skills()
        line_ids = [ln.obj_id for ln in used_lines]
        if line_ids:
            print(f"GroupLine => Polygon#{self.obj_id} from lineIDs={line_ids}")
        print(f"RecognizeInstancePolygon => Polygon#{self.obj_id}")
        print(f"LocalizePolygon => Polygon#{self.obj_id} (Sides={self.sides}, Angle={self.angle:.1f})")
        area = 0.5 * self.sides * (self.radius**2) * math.sin(2*math.pi/self.sides)
        print(f"MeasurePolygon => Polygon#{self.obj_id} (Area={area:.1f})")

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
        self._geometry_locked = True

    def get_bbox(self):
        angle_step = 360.0 / self.sides
        xs = []
        ys = []
        for i in range(self.sides):
            theta = math.radians(self.angle + i * angle_step)
            xs.append(self.center[0] + self.radius * math.cos(theta))
            ys.append(self.center[1] + self.radius * math.sin(theta))
        return (min(xs), min(ys), max(xs), max(ys))

##############################################################################
# Arrow
##############################################################################
class ArrowObj(PlotObject):
    ALIAS = "Arrow"

    def __init__(self, start=None, length=None, angle=None):
        super().__init__()
        # Accept parameters from constructor if provided.
        if start is not None and length is not None and angle is not None:
            self.start = start
            self.length = length
            self.angle = angle
            self._geometry_locked = True
        else:
            self.start = (0, 0)
            self.length = 0
            self.angle = 0
        for _ in range(3):
            line = LineLow()
            self.sub_references.append(line)

    def assign_geometry(self):
        if not hasattr(self, "_geometry_locked") or not self._geometry_locked:
            self.start = (random.uniform(20, 30), random.uniform(20, 30))
            self.length = random.uniform(20, 40)
            self.angle = random.uniform(0, 180)
        rad = math.radians(self.angle)
        x1, y1 = self.start
        x2 = x1 + self.length * math.cos(rad)
        y2 = y1 + self.length * math.sin(rad)
        lines = [ln for ln in self.sub_references if isinstance(ln, LineLow)]
        if len(lines) == 3:
            lines[0].p1 = (x1, y1)
            lines[0].p2 = (x2, y2)
            lines[0]._geometry_locked = True
            head_size = self.length * 0.2
            arrow_angle = 30
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

    def perform_skills(self):
        for sub in self.sub_references:
            sub.perform_skills()
        line_ids = [ln.obj_id for ln in self.sub_references if isinstance(ln, LineLow)]
        if line_ids:
            print(f"GroupLine => Arrow#{self.obj_id} from lineIDs={line_ids}")
        print(f"RecognizeInstanceArrow => Arrow#{self.obj_id}")
        print(f"LocalizeArrow => Arrow#{self.obj_id} (Length={self.length:.1f}, Angle={self.angle:.1f})")
        print(f"MeasureArrow => Arrow#{self.obj_id} (ShaftLength={self.length:.1f})")
        rad = math.radians(self.angle)
        dx = math.cos(rad)
        dy = math.sin(rad)
        print(f"ArrowDirection => Arrow#{self.obj_id} (Vector=({dx:.2f}, {dy:.2f}))")

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
        return (self.start[0], self.start[1], self.start[0]+self.length, self.start[1]+self.length)

##############################################################################
# Bars (multiple rectangles)
##############################################################################
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
                 base_position=None):
        super().__init__()
        self.num_bars = num_bars if num_bars else random.randint(2, 5)
        self.angle = angle
        self.min_width = min_width
        self.max_width = max_width
        self.spacing = spacing if spacing is not None else random.uniform(5, 10)
        self.min_height = min_height
        self.max_height = max_height
        self.base_position = base_position
        self._geometry_locked = False
        self.bars_list = []
        for _ in range(self.num_bars):
            rect = RectangleObj()
            self.bars_list.append(rect)
            self.sub_references.append(rect)

    def assign_geometry(self):
        if not self._geometry_locked:
            if self.base_position is not None:
                base_x, base_y = self.base_position
            else:
                base_x = random.uniform(10, 30)
                base_y = random.uniform(50, 80)
            angle_rad = math.radians(self.angle)
            delta_x = (self.max_width + self.spacing) * math.cos(angle_rad)
            delta_y = (self.max_width + self.spacing) * math.sin(angle_rad)
            current_x = base_x
            current_y = base_y
            for rect in self.bars_list:
                rect.width = random.uniform(self.min_width, self.max_width)
                rect.height = random.uniform(self.min_height, self.max_height)
                rect.angle = self.angle
                rect.set_bottom_left(current_x, current_y, angle=self.angle, width=rect.width, height=rect.height)
                current_x += delta_x
                current_y += delta_y
            self._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        for sub in self.sub_references:
            sub.perform_skills()
        rect_ids = [sub.obj_id for sub in self.sub_references if isinstance(sub, RectangleObj)]
        if rect_ids:
            print(f"GroupRectangle => Bars#{self.obj_id} from rectangleIDs={rect_ids}")
        print(f"RecognizeInstanceBars => Bars#{self.obj_id}")
        print(f"LocalizeBars => Bars#{self.obj_id} (Positions for each rectangle)")
        print(f"MeasureBars => Bars#{self.obj_id} (Heights, widths, spacing, etc.)")

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

##############################################################################
# Axis
##############################################################################
class AxisObj(PlotObject):
    ALIAS = "Axis"

    def __init__(self,
                 axis_length=50,
                 axis_angle=30,
                 min_tick_spacing=5,
                 max_tick_spacing=10,
                 min_tick_length=2,
                 max_tick_length=4,
                 start_position=None):
        super().__init__()
        self.axis_length = axis_length
        self.axis_angle = axis_angle
        self.min_tick_spacing = min_tick_spacing
        self.max_tick_spacing = max_tick_spacing
        self.min_tick_length = min_tick_length
        self.max_tick_length = max_tick_length
        self.start_position = start_position
        self.line = LineLow()
        self.sub_references.append(self.line)
        self.ticks = []
        self.p1 = (0, 0)
        self.p2 = (0, 0)
        self._geometry_locked = False

    def assign_geometry(self):
        if not self._geometry_locked:
            if self.start_position is not None:
                x1, y1 = self.start_position
            else:
                x1 = random.uniform(10, 20)
                y1 = random.uniform(60, 80)
            rad = math.radians(self.axis_angle)
            dx = self.axis_length * math.cos(rad)
            dy = self.axis_length * math.sin(rad)
            x2 = x1 + dx
            y2 = y1 + dy
            self.p1 = (x1, y1)
            self.p2 = (x2, y2)
            self.line.p1 = self.p1
            self.line.p2 = self.p2
            self.line._geometry_locked = True
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
                rx = half_t * math.cos(rad + math.pi/2)
                ry = half_t * math.sin(rad + math.pi/2)
                tick_line = LineLow((cx - rx, cy - ry), (cx + rx, cy + ry))
                self.ticks.append(tick_line)
                self.sub_references.append(tick_line)
            self._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        self.line.perform_skills()
        for tline in self.ticks:
            tline.perform_skills()
        print(f"GroupLine => Axis#{self.obj_id} from lineIDs=[{self.line.obj_id}" +
              "".join(f", {t.obj_id}" for t in self.ticks) + "]")
        print(f"RecognizeInstanceAxis => Axis#{self.obj_id}")
        print(f"LocalizeAxis => Axis#{self.obj_id} (Endpoints={self.p1}, {self.p2})")
        length, angle = get_line_length_and_angle(self.p1, self.p2)
        print(f"MeasureAxis => Axis#{self.obj_id} (Length={length:.1f}, Angle={angle:.1f})")

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

##############################################################################
# BarGraph
##############################################################################
class BarGraphObj(PlotObject):
    ALIAS = "BarGraph"

    def __init__(self,
                 base_position=None,
                 axis_length=None,
                 bars_num=None,
                 bars_angle=0,
                 with_y_axis=True,
                 axis_margin=0,
                 **kwargs):
        super().__init__()
        if base_position is None:
            base_position = (random.uniform(10, 30), random.uniform(50, 80))
        if axis_length is None:
            axis_length = random.uniform(40, 60)
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
        self.bars_obj = BarsObj(num_bars=self.bars_num,
                                angle=self.bars_angle,
                                base_position=self.base_position,
                                **kwargs)
        self.sub_references.append(self.bars_obj)
        rad_offset = math.radians(self.bars_angle - 90)
        ax_start_x = self.base_position[0] + self.axis_margin * math.cos(rad_offset)
        ax_start_y = self.base_position[1] + self.axis_margin * math.sin(rad_offset)
        self.axis_obj_x = AxisObj(start_position=(ax_start_x, ax_start_y),
                                  axis_length=self.axis_length,
                                  axis_angle=self.bars_angle)
        self.sub_references.append(self.axis_obj_x)
        if self.with_y_axis:
            self.axis_obj_y = AxisObj(start_position=(ax_start_x, ax_start_y),
                                      axis_length=self.axis_length,
                                      axis_angle=((self.bars_angle + 90) % 360))
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

    def perform_skills(self):
        self.axis_obj_x.perform_skills()
        if self.axis_obj_y:
            self.axis_obj_y.perform_skills()
            print(f"GroupAxis => BarGraph#{self.obj_id} from AxisIDs=[{self.axis_obj_x.obj_id}, {self.axis_obj_y.obj_id}]")
        else:
            print(f"GroupAxis => BarGraph#{self.obj_id} from AxisIDs=[{self.axis_obj_x.obj_id}]")
        self.bars_obj.perform_skills()
        print(f"GroupBars => BarGraph#{self.obj_id} from BarsIDs=[{self.bars_obj.obj_id}]")
        print(f"RecognizeInstanceBarGraph => BarGraph#{self.obj_id}")
        print(f"LocalizeBarGraph => BarGraph#{self.obj_id} (Overall bounding region, etc.)")
        print(f"MeasureBarGraph => BarGraph#{self.obj_id} (Number of bars, axis length, etc.)")

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

##############################################################################
# Scene Adjustment: Scale & Translate scene to fully fit within canvas.
##############################################################################
def adjust_scene(scene, canvas=(0, 100, 0, 100)):
    # canvas: (x_min, x_max, y_min, y_max)
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
# Build a scene from a plan.
##############################################################################
# Modified to allow the plan to specify parameters for each object instance.
# If the value is an int, that many default instances are created;
# if it is a list, each dictionary in the list will be passed as keyword arguments.
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
# New Function: Create Scene (scene construction without display/saving)
##############################################################################
def create_scene(plan, avoid_types=None, canvas=(0,100,0,100), allow_partial=False):
    if avoid_types is None:
        avoid_types = []
    scene = build_scene_from_plan(plan)
    # Add extra distractor objects if scene is too small, avoiding types in avoid_types.
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

    for obj in scene:
        obj.perform_skills()

    if not allow_partial:
        adjust_scene(scene, canvas=canvas)
    return scene

##############################################################################
# New Function: Display Scene and Save Structure
##############################################################################
def display_and_save_scene(scene, outdir="output", question=None, answer=None, canvas=(0,100,0,100)):
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    fig, ax = plt.subplots(figsize=(5, 5))
    x_min, x_max, y_min, y_max = canvas
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")
    for obj in scene:
        obj.render(ax)
    # Add noise.
    xs = sorted(ax.get_xlim())
    ys = sorted(ax.get_ylim())
    total_pixels = abs((xs[1] - xs[0]) * (ys[1] - ys[0]))
    noise_level = 0.01
    nn = int(total_pixels * noise_level)
    for _ in range(nn):
        xx = random.randint(int(xs[0]), int(xs[1]) - 1)
        yy = random.randint(int(ys[0]), int(ys[1]) - 1)
        ax.plot(xx, yy, 'ks', markersize=1)
    image_out = os.path.join(outdir, "scene.png")
    plt.savefig(image_out, dpi=120)
    plt.close()
    print(f"\nScene saved to {image_out}\n")
    scene_structure = [obj.to_dict() for obj in scene]
    json_out = os.path.join(outdir, "scene_structure.json")
    with open(json_out, "w") as json_file:
        json.dump(scene_structure, json_file, indent=2)
    print(f"Object structure saved to {json_out}\n")
    annotation = {"question": question, "answer": answer, "scene_structure": scene_structure}
    ann_out = os.path.join(outdir, "scene_annotation.json")
    with open(ann_out, "w") as ann_file:
        json.dump(annotation, ann_file, indent=2)
    print(f"Annotation saved to {ann_out}\n")

##############################################################################
# Modified run_scene_demo: Integrates scene creation and display.
##############################################################################
def run_scene_demo(plan, outdir="output", distractor_skills=None, allow_partial=False,
                   question=None, answer=None, avoid_types=None, canvas=(0,100,0,100)):
    scene = create_scene(plan, avoid_types=avoid_types, canvas=canvas, allow_partial=allow_partial)
    display_and_save_scene(scene, outdir=outdir, question=question, answer=answer, canvas=canvas)

##############################################################################
# Selected Question Demo Functions (Robust Versions)
##############################################################################

# 1. "Is there an <object type> in the image?"
def demo_question_object(answer=True, outdir="demo_output/question_object", canvas_size=(100,100)):
    width, height = canvas_size
    canvas = (0, width, 0, height)
    obj_type = random.choice(["Line", "Oval", "Rectangle", "Triangle", "Arrow"])
    if answer:
        plan = {obj_type: random.randint(1, 2)}
    else:
        plan = {obj_type: 0}
    scene = create_scene(plan, canvas=canvas, avoid_types=[] if answer else [obj_type])
    if not answer:
        for obj in scene:
            if obj.ALIAS == obj_type:
                raise Exception(f"Error: {obj_type} instance found when answer should be false.")
    question_text = f"Is there a {obj_type} in the image?"
    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)
# 2 "Are there any parallel/perpendicular lines in the image?"
def demo_question_parallel_perp_lines(answer=True,
                                      outdir="demo_output/question_parallel_perp_lines",
                                      canvas_size=(100, 100)):
    width, height = canvas_size
    canvas = (0, width, 0, height)
    epsilon = 4
    MAX_RETRY = 50
    margin = 5
    test_parallel = random.choice([True, False])
    relation_text = "parallel" if test_parallel else "perpendicular"
    question_text = f"Are there any {relation_text} lines in the image?"

    # New option: if answer is True, with 2% chance each, generate a rectangle, bars, or axis.
    if answer:
        r = random.random()
        if r < 0.02:
            plan = {"Rectangle": 1}
            scene = create_scene(plan, canvas=canvas, avoid_types=[])
            display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)
            return
        elif r < 0.04:
            plan = {"Bars": 1}
            scene = create_scene(plan, canvas=canvas, avoid_types=[])
            display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)
            return
        elif r < 0.06:
            plan = {"Axis": 1}
            scene = create_scene(plan, canvas=canvas, avoid_types=[])
            display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)
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

    # Iterative method to robustly gather all lines in the scene.
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
        scene = create_scene(plan, canvas=canvas, avoid_types=[])

        # Gather all lines from the generated scene using the iterative approach.
        all_lines = []
        for obj in scene:
            all_lines.extend(gather_all_lines(obj))
        if len(all_lines) < 2:
            continue

        print(all_lines)

        # Extract angles and sort them for efficient searching.
        angles = [get_line_length_and_angle(ln.p1, ln.p2)[1] for ln in all_lines]
        angles.sort()
        relation_found = False

        if test_parallel:
            # Check for any consecutive pair with a small difference (accounting for wrap-around).
            for i in range(len(angles) - 1):
                if abs(angles[i+1] - angles[i]) <= epsilon:
                    relation_found = True
                    break
            # Also check the wrap-around difference.
            if not relation_found and (360 - angles[-1] + angles[0]) <= epsilon:
                relation_found = True
        else:
            # For perpendicular lines, use binary search.
            for angle in angles:
                target = angle + 90
                # Since angles are in [0,360), adjust target if needed.
                if target > 360:
                    target -= 360
                    # Because of wrap-around, check both ends.
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

        # If answer should be True, ensure relation is found; if False, ensure none is found.
        if (answer and relation_found) or (not answer and not relation_found):
            break

    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)

# 3. "Are there any arrows pointing <upward | downward | leftward | rightward>?"
def demo_question_arrow_direction(answer=True, outdir="demo_output/question_arrow_direction", canvas_size=(100,100)):
    MAX_RETRY = 5
    width, height = canvas_size
    canvas = (0, width, 0, height)
    direction = random.choice(["upward", "downward", "leftward", "rightward"])
    tol_adjust = 30
    direction_angles = {"upward": 270, "downward": 90, "leftward": 180, "rightward": 0}

    NO_ARROW_PROB_FALSE = 0.15  # probability to generate scene with no arrow

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
            # For false answer, with some probability generate scene without any arrow.
            if random.random() < NO_ARROW_PROB_FALSE:
                plan = {}  # no objects
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
        scene = create_scene(plan, canvas=canvas)
        if not answer:
            # If scene is empty or there is no arrow, it's acceptable.
            arrow_objs = [obj for obj in scene if obj.ALIAS == "Arrow"]
            if not arrow_objs:
                break
            # Check that no arrow is pointing the target direction.
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
    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)

# 4. Does a <shape 1> intersect with a <shape 2>?
def demo_question_intersect_objects(answer=True,
                                    outdir="demo_output/question_intersect_objects",
                                    canvas_size=(100, 100)):
    import math, random
    width, height = canvas_size
    canvas = (0, width, 0, height)
    
    # Candidate types; note that "Circle" is treated as an oval,
    # and "Square", "Rectangle", "Triangle" and "Polygon" are treated as polygons.
    candidate_types = ["Line", "Oval", "Circle", "Rectangle", "Square", "Triangle", "Polygon"]
    type1 = random.choice(candidate_types)
    type2 = random.choice(candidate_types)
    question_text = f"Does an {type1} intersect with an {type2}?"
    
    # ------------------------
    # Helper: Return a string representing the geometric category.
    def geom_type(shape):
        if shape == "Line":
            return "line"
        elif shape in ["Oval", "Circle"]:
            return "oval"
        else:
            return "polygon"
    
    # ------------------------
    # Helper: Generate random parameters for a shape.
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
            # Use a center point and generate three vertices with small random offsets.
            center = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            pts = []
            for _ in range(3):
                pts.append((center[0] + random.uniform(-10, 10),
                            center[1] + random.uniform(-10, 10)))
            return {"vertices": pts}
        elif shape == "Polygon":
            # Generate a 5-vertex polygon by perturbing points around a circle.
            center = (random.uniform(margin, width - margin), random.uniform(margin, height - margin))
            pts = []
            count = 5
            for i in range(count):
                ang = 2 * math.pi * i / count + random.uniform(-0.2, 0.2)
                r = random.uniform(10, 30)
                pts.append((center[0] + r * math.cos(ang),
                            center[1] + r * math.sin(ang)))
            return {"vertices": pts}
    
    # ------------------------
    # Helper: Slightly perturb ("wiggle") the parameters of an object.
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
            # Optionally wiggle width/height if desired.
        elif shape in ["Triangle", "Polygon"]:
            new_vertices = []
            for (x, y) in params["vertices"]:
                new_vertices.append((x + random.uniform(-delta, delta),
                                     y + random.uniform(-delta, delta)))
            new_params["vertices"] = new_vertices
        return new_params

    # =========================================================================
    # Intersection routines – adapted to the object representations used here.
    #
    # All objects are represented as dummy objects with attributes.
    # A Line has attributes: p1, p2.
    # An Oval (or Circle) has attributes: center, width, height, angle.
    # A Polygon (Triangle, Rectangle, Square, Polygon) is represented by vertices.
    # =========================================================================
    
    # --- Helper: Line-line intersection.
    def _line_line_intersect(p1, p2, p3, p4):
        def orientation(a, b, c):
            val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
            if abs(val) < 1e-9:
                return 0
            return 1 if val > 0 else 2
        def on_segment(a, b, c):
            return (min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and
                    min(a[1], c[1]) <= b[1] <= max(a[1], c[1]))
        o1 = orientation(p1, p2, p3)
        o2 = orientation(p1, p2, p4)
        o3 = orientation(p3, p4, p1)
        o4 = orientation(p3, p4, p2)
        if o1 != o2 and o3 != o4:
            return True
        if o1 == 0 and on_segment(p1, p3, p2):
            return True
        if o2 == 0 and on_segment(p1, p4, p2):
            return True
        if o3 == 0 and on_segment(p3, p1, p4):
            return True
        if o4 == 0 and on_segment(p3, p2, p4):
            return True
        return False
    
    def doesLineLineIntersect(line1, line2):
        return _line_line_intersect(line1.p1, line1.p2, line2.p1, line2.p2)
    
    # --- Helper: Check if a point is inside a polygon.
    def _point_in_polygon(px, py, polygon_dict):
        inside = False
        vertices = polygon_dict["vertices"]
        n = len(vertices)
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi):
                inside = not inside
            j = i
        return inside
    
    # --- Helper: Rotate a point about a center.
    def _rotate_point(point, center, angle_deg):
        rad = math.radians(angle_deg)
        x, y = point
        cx, cy = center
        x -= cx
        y -= cy
        xr = x * math.cos(rad) - y * math.sin(rad)
        yr = x * math.sin(rad) + y * math.cos(rad)
        return (xr + cx, yr + cy)
    
    # --- Intersection: Line-Oval.
    def doesLineOvalIntersect(line, oval):
        cx, cy = oval.center
        ang = oval.angle
        w2, h2 = oval.width / 2.0, oval.height / 2.0
        def transform(pt):
            x, y = pt[0] - cx, pt[1] - cy
            rad = math.radians(-ang)
            xr = x * math.cos(rad) - y * math.sin(rad)
            yr = x * math.sin(rad) + y * math.cos(rad)
            return (xr, yr)
        p1_local = transform(line.p1)
        p2_local = transform(line.p2)
        dx = p2_local[0] - p1_local[0]
        dy = p2_local[1] - p1_local[1]
        A = (dx**2)/(w2**2) + (dy**2)/(h2**2)
        B = 2 * (p1_local[0]*dx/(w2**2) + p1_local[1]*dy/(h2**2))
        C = (p1_local[0]**2)/(w2**2) + (p1_local[1]**2)/(h2**2) - 1
        disc = B*B - 4*A*C
        if disc < 0:
            return False
        sqrt_disc = math.sqrt(disc)
        t1 = (-B + sqrt_disc) / (2*A)
        t2 = (-B - sqrt_disc) / (2*A)
        return (0 <= t1 <= 1) or (0 <= t2 <= 1)
    
    # --- Intersection: Line-Polygon.
    def doesLinePolygonIntersect(line, polygon_obj):
        if _point_in_polygon(line.p1[0], line.p1[1], {"vertices": polygon_obj.vertices}):
            return True
        if _point_in_polygon(line.p2[0], line.p2[1], {"vertices": polygon_obj.vertices}):
            return True
        verts = polygon_obj.vertices
        n = len(verts)
        for i in range(n):
            p3 = verts[i]
            p4 = verts[(i+1) % n]
            if _line_line_intersect(line.p1, line.p2, p3, p4):
                return True
        return False
    
    # --- Intersection: Oval-Oval.
    def doesOvalOvalIntersect(oval1, oval2):
        def sample_oval(ov, count=36):
            pts = []
            cx, cy = ov.center
            w2, h2 = ov.width / 2.0, ov.height / 2.0
            for i in range(count):
                theta = 2 * math.pi * i / count
                x = cx + w2 * math.cos(theta)
                y = cy + h2 * math.sin(theta)
                pts.append(_rotate_point((x, y), ov.center, ov.angle))
            return pts
        pts1 = sample_oval(oval1)
        pts2 = sample_oval(oval2)
        def point_in_oval(pt, ov):
            cx, cy = ov.center
            rad = math.radians(-ov.angle)
            x, y = pt[0] - cx, pt[1] - cy
            xr = x * math.cos(rad) - y * math.sin(rad)
            yr = x * math.sin(rad) + y * math.cos(rad)
            w2, h2 = ov.width/2.0, ov.height/2.0
            return (xr**2)/(w2**2) + (yr**2)/(h2**2) <= 1.0
        for pt in pts1:
            if point_in_oval(pt, oval2):
                return True
        for pt in pts2:
            if point_in_oval(pt, oval1):
                return True
        return False
    
    # --- Intersection: Polygon-Polygon.
    def doesPolyPolyIntersect(poly1, poly2):
        if any(_point_in_polygon(x, y, {"vertices": poly2.vertices}) for (x, y) in poly1.vertices):
            return True
        if any(_point_in_polygon(x, y, {"vertices": poly1.vertices}) for (x, y) in poly2.vertices):
            return True
        def edges(vertices):
            return [(vertices[i], vertices[(i+1) % len(vertices)]) for i in range(len(vertices))]
        for e1 in edges(poly1.vertices):
            for e2 in edges(poly2.vertices):
                if _line_line_intersect(e1[0], e1[1], e2[0], e2[1]):
                    return True
        return False
    
    # --- Intersection: Oval-Polygon.
    def doesOvalPolygonIntersect(oval, polygon_obj):
        for (x, y) in polygon_obj.vertices:
            cx, cy = oval.center
            rad = math.radians(-oval.angle)
            dx, dy = x - cx, y - cy
            xr = dx * math.cos(rad) - dy * math.sin(rad)
            yr = dx * math.sin(rad) + dy * math.cos(rad)
            w2, h2 = oval.width/2.0, oval.height/2.0
            if (xr**2)/(w2**2) + (yr**2)/(h2**2) <= 1:
                return True
        if _point_in_polygon(oval.center[0], oval.center[1], {"vertices": polygon_obj.vertices}):
            return True
        class DummyLine:
            pass
        verts = polygon_obj.vertices
        n = len(verts)
        for i in range(n):
            dummy = DummyLine()
            dummy.p1 = verts[i]
            dummy.p2 = verts[(i+1) % n]
            if doesLineOvalIntersect(dummy, oval):
                return True
        return False
    
    # --- Helper: Convert our parameter dictionary into a dummy object.
    def create_dummy(params, shape):
        class Dummy:
            pass
        dummy = Dummy()
        g = geom_type(shape)
        if g == "line":
            dummy.p1 = params["p1"]
            dummy.p2 = params["p2"]
        elif g == "oval":
            dummy.center = params["center"]
            dummy.width = params["width"]
            dummy.height = params["height"]
            dummy.angle = params["angle"]
        elif g == "polygon":
            # If the params already include vertices, use them.
            if "vertices" in params:
                dummy.vertices = params["vertices"]
            else:
                # Otherwise, assume the object was specified by center, width, height, angle
                # and convert it to a rectangle polygon.
                cx, cy = params["center"]
                w, h, angle = params["width"], params["height"], params["angle"]
                dx, dy = w / 2.0, h / 2.0
                pts = [
                    _rotate_point((cx - dx, cy - dy), (cx, cy), angle),
                    _rotate_point((cx + dx, cy - dy), (cx, cy), angle),
                    _rotate_point((cx + dx, cy + dy), (cx, cy), angle),
                    _rotate_point((cx - dx, cy + dy), (cx, cy), angle)
                ]
                dummy.vertices = pts
        return dummy
    
    # --- Main intersection dispatch.
    def intersect(params1, shape1, params2, shape2):
        obj1 = create_dummy(params1, shape1)
        obj2 = create_dummy(params2, shape2)
        g1 = geom_type(shape1)
        g2 = geom_type(shape2)
        if g1 == "line" and g2 == "line":
            return doesLineLineIntersect(obj1, obj2)
        elif g1 == "line" and g2 == "oval":
            return doesLineOvalIntersect(obj1, obj2)
        elif g1 == "oval" and g2 == "line":
            return doesLineOvalIntersect(obj2, obj1)
        elif g1 == "line" and g2 == "polygon":
            return doesLinePolygonIntersect(obj1, obj2)
        elif g1 == "polygon" and g2 == "line":
            return doesLinePolygonIntersect(obj2, obj1)
        elif g1 == "oval" and g2 == "oval":
            return doesOvalOvalIntersect(obj1, obj2)
        elif g1 == "polygon" and g2 == "polygon":
            return doesPolyPolyIntersect(obj1, obj2)
        elif g1 == "oval" and g2 == "polygon":
            return doesOvalPolygonIntersect(obj1, obj2)
        elif g1 == "polygon" and g2 == "oval":
            return doesOvalPolygonIntersect(obj2, obj1)
        else:
            return False

    # ------------------------
    # Generate initial parameters that satisfy the required relation.
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
    
    # ------------------------
    # "Wiggle" the parameters so the scene isn’t too static.
    WIGGLE_ATTEMPTS = 10
    if answer:
        # For a true answer, keep small changes that preserve intersection.
        for _ in range(WIGGLE_ATTEMPTS):
            new_p1 = wiggle_params(params1, type1)
            if intersect(new_p1, type1, params2, type2):
                params1 = new_p1
            new_p2 = wiggle_params(params2, type2)
            if intersect(params1, type1, new_p2, type2):
                params2 = new_p2
    else:
        # For a false answer, keep changes that preserve non-intersection.
        for _ in range(WIGGLE_ATTEMPTS):
            new_p1 = wiggle_params(params1, type1)
            if not intersect(new_p1, type1, params2, type2):
                params1 = new_p1
            new_p2 = wiggle_params(params2, type2)
            if not intersect(params1, type1, new_p2, type2):
                params2 = new_p2
    
    # ------------------------
    # Build the plan. We follow the same plan format as used in other demos:
    # a dictionary mapping object type to a list of parameter dictionaries.
    plan = {type1: [params1], type2: [params2]}
    
    # Generate and display the scene.
    scene = create_scene(plan, canvas=canvas)
    display_and_save_scene(scene, outdir=outdir, question=question_text, answer=answer, canvas=canvas)

##############################################################################
# Main Demo: Run one demo per question.
##############################################################################
if __name__ == "__main__":
    CANVAS_SIZE = (100, 100)  # width, height
    # Uncomment any of the following to test:
    #demo_question_object(answer=random.choice([True, False]), canvas_size=CANVAS_SIZE)
    #demo_question_parallel_perp_lines(answer=random.choice([True, False]), canvas_size=CANVAS_SIZE)
    #demo_question_arrow_direction(answer=random.choice([True, False]), canvas_size=CANVAS_SIZE)
    demo_question_intersect_objects(answer=random.choice([True, False]), canvas_size=CANVAS_SIZE)
