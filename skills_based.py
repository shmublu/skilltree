import math
import random
import os
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

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


##############################################################################
# Base PlotObject
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

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, **kwargs):
        """
        Default implementation does nothing, overridden by subclasses.
        `x` and `y` define the bottom-left position for angle=0,
        and `angle` is in degrees.
        """
        pass



##############################################################################
# Low-Level: Line
##############################################################################
def get_line_length_and_angle(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx))
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
        print(f"MeasureLine => Line#{self.obj_id} (Length={length:.1f},Angle={angle:.1f})")

    def render(self, ax):
        ax.plot([self.p1[0], self.p2[0]],
                [self.p1[1], self.p2[1]],
                color='k', lw=2)

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, length=10, **kwargs):
        """
        For a line, interpret (x, y) as the bottom-left endpoint when angle=0.
        Then rotate this line by `angle` degrees and use `length`.
        """
        rad = math.radians(angle)
        self.p1 = (x, y)
        # The 'bottom-left' for angle=0 means the line goes horizontally to the right
        self.p2 = (x + length * math.cos(rad), y + length * math.sin(rad))
        self._geometry_locked = True


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
        print(f"LocalizeOval => Oval#{self.obj_id} (Center={self.center},W={self.width},H={self.height},Angle={self.angle:.1f})")
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

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, width=10, height=10, **kwargs):
        """
        Interprets (x, y) as the bottom-left corner if angle=0.
        Then sets the center accordingly and applies rotation `angle`.
        """
        # Bottom-left corner -> center is offset by half-width, half-height
        rad = math.radians(angle)
        # The offset for the center when angle=0
        offset_x = width / 2.0
        offset_y = height / 2.0
        # Rotate that offset around the bottom-left corner
        rotated_cx = x + offset_x * math.cos(rad) - offset_y * math.sin(rad)
        rotated_cy = y + offset_x * math.sin(rad) + offset_y * math.cos(rad)
        self.center = (rotated_cx, rotated_cy)
        self.width = width
        self.height = height
        self.angle = angle
        self._geometry_locked = True


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
        print(f"LocalizeRectangle => Rectangle#{self.obj_id} (W={self.width:.1f},H={self.height:.1f},Angle={self.angle:.1f})")
        area = self.width * self.height
        perimeter = 2.0 * (self.width + self.height)
        print(f"MeasureRectangle => Rectangle#{self.obj_id} (Area={area:.1f},Perimeter={perimeter:.1f})")

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, width=10, height=10, **kwargs):
        """
        Interprets (x, y) as the bottom-left corner when angle=0.
        Sets center, width, height, and angle.
        """
        self.width = width
        self.height = height
        self.angle = angle
        rad = math.radians(angle)
        # Offset from bottom-left to center
        offset_x = width / 2.0
        offset_y = height / 2.0
        rotated_cx = x + offset_x * math.cos(rad) - offset_y * math.sin(rad)
        rotated_cy = y + offset_x * math.sin(rad) + offset_y * math.cos(rad)
        self.center = (rotated_cx, rotated_cy)
        self._geometry_locked = True

##############################################################################
# Bars (multiple rectangles)
##############################################################################
class BarsObj(PlotObject):
    ALIAS = "Bars"

    def __init__(
        self,
        num_bars=None,
        angle=30,
        min_width=5,
        max_width=6,
        spacing=None,
        min_height=15,
        max_height=30,
        base_position=None
    ):
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
                # Instead of setting rect.center directly, we use set_bottom_left
                rect.set_bottom_left(
                    current_x, current_y,
                    angle=self.angle,
                    width=rect.width,
                    height=rect.height
                )
                current_x += delta_x
                current_y += delta_y

            self._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        for sub in self.sub_references:
            sub.perform_skills()
        rect_ids = [
            sub.obj_id for sub in self.sub_references if isinstance(sub, RectangleObj)
        ]
        if rect_ids:
            print(f"GroupRectangle => Bars#{self.obj_id} from rectangleIDs={rect_ids}")
        print(f"RecognizeInstanceBars => Bars#{self.obj_id}")
        print(f"LocalizeBars => Bars#{self.obj_id} (Positions for each rectangle)")
        print(f"MeasureBars => Bars#{self.obj_id} (Heights, widths, spacing, etc.)")

    def render(self, ax):
        for sub in self.sub_references:
            sub.render(ax)

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, **kwargs):
        """
        Interprets (x, y) as a reference for the bottom-left of this entire bars set.
        For demonstration, we'll shift base_position to (x, y) and reassign geometry.
        """
        self.base_position = (x, y)
        self.angle = angle
        self._geometry_locked = False

##############################################################################
# Axis
##############################################################################
class AxisObj(PlotObject):
    ALIAS = "Axis"

    def __init__(
        self,
        axis_length=50,
        axis_angle=30,
        min_tick_spacing=5,
        max_tick_spacing=10,
        min_tick_length=2,
        max_tick_length=4,
        start_position=None
    ):
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
                rx = half_t * math.cos(rad + math.pi / 2.0)
                ry = half_t * math.sin(rad + math.pi / 2.0)
                tick_line = LineLow((cx - rx, cy - ry), (cx + rx, cy + ry))
                self.ticks.append(tick_line)
                self.sub_references.append(tick_line)

            self._geometry_locked = True
        super().assign_geometry()

    def perform_skills(self):
        self.line.perform_skills()
        for tline in self.ticks:
            tline.perform_skills()
        print(f"GroupLine => Axis#{self.obj_id} from lineIDs=[{self.line.obj_id}" + "".join(f",{t.obj_id}" for t in self.ticks) + "]")
        print(f"RecognizeInstanceAxis => Axis#{self.obj_id}")
        print(f"LocalizeAxis => Axis#{self.obj_id} (Endpoints={self.p1},{self.p2})")
        length, angle = get_line_length_and_angle(self.p1, self.p2)
        print(f"MeasureAxis => Axis#{self.obj_id} (Length={length:.1f},Angle={angle:.1f})")

    def render(self, ax):
        self.line.render(ax)
        for tline in self.ticks:
            tline.render(ax)

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, axis_length=50, **kwargs):
        """
        Interprets (x, y) as the bottom-left start of the axis (when angle=0, the axis extends horizontally).
        """
        self.start_position = (x, y)
        self.axis_angle = angle
        self.axis_length = axis_length
        self._geometry_locked = False


##############################################################################
# BarGraph
##############################################################################
class BarGraphObj(PlotObject):
    ALIAS = "BarGraph"

    def __init__(
        self,
        base_position=None,
        axis_length=None,
        bars_num=None,
        bars_angle=0,
        with_y_axis=True,
        axis_margin=0,
        **kwargs
    ):
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

        self.bars_obj = BarsObj(
            num_bars=self.bars_num,
            angle=self.bars_angle,
            base_position=self.base_position,
            **kwargs
        )
        self.sub_references.append(self.bars_obj)

        rad_offset = math.radians(self.bars_angle - 90)
        ax_start_x = self.base_position[0] + self.axis_margin * math.cos(rad_offset)
        ax_start_y = self.base_position[1] + self.axis_margin * math.sin(rad_offset)

        self.axis_obj_x = AxisObj(
            start_position=(ax_start_x, ax_start_y),
            axis_length=self.axis_length,
            axis_angle=self.bars_angle
        )
        self.sub_references.append(self.axis_obj_x)

        if self.with_y_axis:
            self.axis_obj_y = AxisObj(
                start_position=(ax_start_x, ax_start_y),
                axis_length=self.axis_length,
                axis_angle=((self.bars_angle + 90) % 360)
            )
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
            print(f"GroupAxis => BarGraph#{self.obj_id} from AxisIDs=[{self.axis_obj_x.obj_id},{self.axis_obj_y.obj_id}]")
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

    # ---------------------------
    # New standardized positioning
    # ---------------------------
    def set_bottom_left(self, x, y, angle=0, axis_length=50, bars_num=2, **kwargs):
        """
        Interprets (x, y) as the bottom-left of the bar graph (with angle=0 meaning bars go horizontal).
        """
        self.base_position = (x, y)
        self.bars_angle = angle
        self.axis_length = axis_length
        self.bars_num = bars_num
        self._geometry_locked = False

##############################################################################
# Build a scene from skill graph plan
##############################################################################
OBJECT_TYPES = {
    "Line": LineLow,
    "Oval": OvalLow,
    "Rectangle": RectangleObj,
    "Bars": BarsObj,
    "Axis": AxisObj,
    "BarGraph": BarGraphObj,
}

SKILL_SYNONYMS = {
    "GroupRectangles": "GroupRectangle",
    "MeasureRectangles": "MeasureRectangle",
    "CountRectangles": "CountRectangle",
    "LocalizeRectangles": "LocalizeRectangle",
    "RecognizeRectangles": "RecognizeInstanceRectangle",
}

def build_skill_graph():
    import networkx as nx
    G = nx.DiGraph()
    skill_info = {}

    def add_skill(obj, skill, deps=None):
        lbl = skill + obj
        skill_info[lbl] = dict(object=obj, skill=skill, deps=deps or [])
        G.add_node(lbl)

    def link_deps(lbl):
        for d in skill_info[lbl]["deps"]:
            G.add_edge(d, lbl)

    # Lines

    add_skill("Line", "RecognizeInstance")
    add_skill("Line", "Localize", ["RecognizeInstanceLine"])
    add_skill("Line", "Measure", ["LocalizeLine"])
    add_skill("Line", "Group", ["MeasureLine"])
    add_skill("Line", "Count", ["GroupLine"])

    

    # Ovals

    add_skill("Oval", "RecognizeInstance")
    add_skill("Oval", "Localize", ["RecognizeInstanceOval"])
    add_skill("Oval", "Measure", ["LocalizeOval"])
    add_skill("Oval", "Group", ["MeasureOval"])
    add_skill("Oval", "Count", ["GroupOval"])

    

    # Rectangle
    add_skill("Rectangle", "RecognizeInstance", ["GroupLine"])
    add_skill("Rectangle", "Localize", ["RecognizeInstanceRectangle"])
    add_skill("Rectangle", "Measure", ["LocalizeRectangle"])
    add_skill("Rectangle", "Group", ["MeasureRectangle"])
    add_skill("Rectangle", "Count", ["GroupRectangle"])

    

    # Bars

    add_skill("Bars", "RecognizeInstance", ["GroupRectangle"])
    add_skill("Bars", "Localize", ["RecognizeInstanceBars"])
    add_skill("Bars", "Measure", ["LocalizeBars"])
    add_skill("Bars", "Group", ["MeasureBars"])
    add_skill("Bars", "Count", ["GroupBars"])

    

    # Axis

    add_skill("Axis", "RecognizeInstance", ["GroupLine"])
    add_skill("Axis", "Localize", ["RecognizeInstanceAxis"])
    add_skill("Axis", "Measure", ["LocalizeAxis"])
    add_skill("Axis", "Group", ["MeasureAxis"])
    add_skill("Axis", "Count", ["GroupAxis"])

    

    # BarGraph

    add_skill("BarGraph", "RecognizeInstance", ["GroupBars", "GroupAxis"])
    add_skill("BarGraph", "Localize", ["RecognizeInstanceBarGraph"])
    add_skill("BarGraph", "Measure", ["LocalizeBarGraph"])
    add_skill("BarGraph", "Group", ["MeasureBarGraph"])
    add_skill("BarGraph", "Count", ["GroupBarGraph"])

    

    # AxesPair

    add_skill("AxesPair", "RecognizeInstance", ["GroupAxis"])
    add_skill("AxesPair", "Localize", ["RecognizeInstanceAxesPair"])
    add_skill("AxesPair", "Measure", ["LocalizeAxesPair"])
    add_skill("AxesPair", "Group", ["MeasureAxesPair"])
    add_skill("AxesPair", "Count", ["GroupAxesPair"])

    

    # NodeGraph

    add_skill("NodeGraph", "RecognizeInstance", ["GroupOval", "GroupLine"])
    add_skill("NodeGraph", "Localize", ["RecognizeInstanceNodeGraph"])
    add_skill("NodeGraph", "Measure", ["LocalizeNodeGraph"])
    add_skill("NodeGraph", "Group", ["MeasureNodeGraph"])
    add_skill("NodeGraph", "Count", ["GroupNodeGraph"])


    

    # Scatterplot

    add_skill("Scatterplot", "RecognizeInstance", ["GroupAxis", "GroupMarker"])
    add_skill("Scatterplot", "Localize", ["RecognizeInstanceScatterplot"])
    add_skill("Scatterplot", "Measure", ["LocalizeScatterplot"])
    add_skill("Scatterplot", "Group", ["MeasureScatterplot"])
    add_skill("Scatterplot", "Count", ["GroupScatterplot"])

    

    # PieChart

    add_skill("PieChart", "RecognizeInstance", ["GroupOval", "GroupLine"])
    add_skill("PieChart", "Localize", ["RecognizeInstancePieChart"])
    add_skill("PieChart", "Measure", ["LocalizePieChart"])
    add_skill("PieChart", "Group", ["MeasurePieChart"])
    add_skill("PieChart", "Count", ["GroupPieChart"])

    

    # LineGraph

    add_skill("LineGraph", "RecognizeInstance", ["GroupAxis", "GroupLine"])
    add_skill("LineGraph", "Localize", ["RecognizeInstanceLineGraph"])
    add_skill("LineGraph", "Measure", ["LocalizeLineGraph"])
    add_skill("LineGraph", "Group", ["MeasureLineGraph"])
    add_skill("LineGraph", "Count", ["GroupLineGraph"])

    for lbl in list(skill_info.keys()):
        link_deps(lbl)

    return G, skill_info

def gather_dependencies(skill_label, skill_info, G):
    import networkx as nx
    needed = set()
    stack = [skill_label]
    while stack:
        cur = stack.pop()
        if cur not in needed:
            needed.add(cur)
            for dep in skill_info[cur]["deps"]:
                if dep not in needed:
                    stack.append(dep)
    subg = G.subgraph(needed)
    topo_list = list(nx.topological_sort(subg))
    return topo_list



def build_scene_from_plan(high_level_objects):
    """
    We only create top-level objects according to plan.
    Sub-objects are created in their constructors.
    """

    scene = []
    for alias, cnt in high_level_objects.items():
        cls_ = OBJECT_TYPES.get(alias, None)
        if cls_ and cnt > 0:
            for _ in range(cnt):
                scene.append(cls_())
    return scene

def build_scene_from_plan1(deps, skill_info):
    """
    We only create top-level objects according to plan.
    Sub-objects are created in their constructors.
    """
    needed_counts = {}
    for alias in OBJECT_TYPES:
        needed_counts[alias] = 0

    for lbl in deps:
        obj_type = skill_info[lbl]["object"]
        action = skill_info[lbl]["skill"]
        if action == "RecognizeInstance":
            needed_counts[obj_type] = max(needed_counts[obj_type], 1)
        elif action in ["Group", "Count"]:
            needed_counts[obj_type] = max(needed_counts[obj_type], 2)

    scene = []
    for alias, cnt in needed_counts.items():
        cls_ = OBJECT_TYPES.get(alias, None)
        if cls_ and cnt > 0:
            for _ in range(cnt):
                scene.append(cls_())
    return scene

##############################################################################
# Putting it all together
##############################################################################
def run_skill_demo(skill_label, outdir="output", distractor_skills=None):
    # Apply synonyms
    if skill_label in SKILL_SYNONYMS:
        skill_label = SKILL_SYNONYMS[skill_label]

    import networkx as nx
    import random

    G, skill_info = build_skill_graph()
    if skill_label not in G.nodes():
        raise ValueError(f"Skill '{skill_label}' not found in graph")

    high_level_objects = {}

    # Add the main object
    main_obj_type = skill_info[skill_label]["object"]
    high_level_objects[main_obj_type] = 1  # Always include the main object

    # Handle distractor skills
    if distractor_skills:
        for ds_label, max_count, probability in distractor_skills:
            if ds_label in SKILL_SYNONYMS:
                ds_label = SKILL_SYNONYMS[ds_label]
            for c in range(max_count):
                print(c)
                if ds_label in G.nodes() and random.random() < probability:
                    ds_obj_type = skill_info[ds_label]["object"]
                    high_level_objects[ds_obj_type] = high_level_objects.get(ds_obj_type, 0) + 1

    scene = build_scene_from_plan(high_level_objects)
    # 1) Assign geometry
    for obj in scene:
        obj.assign_geometry()

    # 2) Perform skill logic
    for obj in scene:
        obj.perform_skills()

    # 3) Render
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")

    for obj in scene:
        obj.render(ax)

    # Optional noise
    total_pixels = 100 * 100
    noise_level = 0.01
    nn = int(total_pixels * noise_level)
    for _ in range(nn):
        xx = random.randint(0, 99)
        yy = random.randint(0, 99)
        ax.plot(xx, yy, 'ks', markersize=1)

    outpath = os.path.join(outdir, "scene.png")
    plt.savefig(outpath, dpi=120)
    plt.close()
    print(f"\nScene saved to {outpath}\n")

##############################################################################
# Demo
##############################################################################
if __name__ == "__main__":
    # Example skill
    test_skill = "RecognizeInstanceBarGraph"
    run_skill_demo(test_skill, outdir="demo_output", distractor_skills=[("RecognizeInstanceLine", 10, 0.003)])
