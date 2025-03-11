import math
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from .base import PlotObject, skills_tree_to_text
from .utilities import get_line_length_and_angle, rotate_point

##############################################################################
# Low-Level: Line
##############################################################################
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

    def perform_skills(self, verbose=False):
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

    def perform_skills(self, verbose=False):
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

    def perform_skills(self, verbose=False):
        # First, get children skills from the four line sub-references.
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

    def perform_skills(self, verbose=False):
        children_trees = [child.perform_skills(verbose=verbose) for child in self.sub_references]
        line_ids = [child.obj_id for child in self.sub_references if isinstance(child, LineLow)]
        x1, y1 = self.vertices[0]
        x2, y2 = self.vertices[1]
        x3, y3 = self.vertices[2]
        area = abs(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2.0
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
    def perform_skills(self, verbose=False):
        used_lines = [child.perform_skills(verbose=verbose) for child in self.sub_references[:self.sides] if isinstance(child, LineLow)]
        line_ids = [child.obj_id for child in self.sub_references[:self.sides] if isinstance(child, LineLow)]
        area = 0.5 * self.sides * (self.radius ** 2) * math.sin(2 * math.pi / self.sides)
        tree = {
            "action": "GroupLine",
            "object": f"Polygon#{self.obj_id}",
            "details": f"from lineIDs={line_ids}",
            "children": used_lines + [
                {"action": "RecognizeInstancePolygon", "object": f"Polygon#{self.obj_id}"},
                {"action": "LocalizePolygon", "object": f"Polygon#{self.obj_id}", "details": f"(Sides={self.sides}, Angle={self.angle:.1f})"},
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

    def perform_skills(self, verbose=False):
        axis_x_tree = self.axis_obj_x.perform_skills(verbose=verbose)
        children = [axis_x_tree]
        if self.axis_obj_y:
            axis_y_tree = self.axis_obj_y.perform_skills(verbose=verbose)
            children.append(axis_y_tree)
            children.append({"action": "GroupAxis", "object": f"BarGraph#{self.obj_id}", "details": f"from AxisIDs=[{self.axis_obj_x.obj_id}, {self.axis_obj_y.obj_id}]"})
        else:
            children.append({"action": "GroupAxis", "object": f"BarGraph#{self.obj_id}", "details": f"from AxisIDs=[{self.axis_obj_x.obj_id}]"})
        bars_tree = self.bars_obj.perform_skills(verbose=verbose)
        children.append(bars_tree)
        children.append({"action": "GroupBars", "object": f"BarGraph#{self.obj_id}", "details": f"from BarsIDs=[{self.bars_obj.obj_id}]"})
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
