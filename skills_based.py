import math
import random
import os
import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

plt.ioff()
matplotlib.use("TkAgg", force=True)


##############################################################################
# 1) SKILL GRAPH BUILD
##############################################################################
def build_skill_graph():
    """
    Builds a directed graph describing skills and their dependencies.
    Node labels like "RecognizeInstanceLine", "LocalizeLine", etc.
    Each node has its dependencies, which represent required steps.
    """
    G = nx.DiGraph()
    skill_info = {}

    def add_skill(obj, skill, deps=None):
        lbl = skill + obj
        skill_info[lbl] = dict(object=obj, skill=skill, deps=deps or [])
        G.add_node(lbl)

    def link_deps(lbl):
        for d in skill_info[lbl]["deps"]:
            G.add_edge(d, lbl)

    # Base objects
    add_skill("Line", "RecognizeInstance")
    add_skill("Line", "Localize", ["RecognizeInstanceLine"])
    add_skill("Line", "Measure", ["LocalizeLine"])
    add_skill("Line", "Group", ["MeasureLine"])
    add_skill("Line", "Count", ["GroupLine"])

    add_skill("Oval", "RecognizeInstance")
    add_skill("Oval", "Localize", ["RecognizeInstanceOval"])
    add_skill("Oval", "Measure", ["LocalizeOval"])
    add_skill("Oval", "Group", ["MeasureOval"])
    add_skill("Oval", "Count", ["GroupOval"])

    # Marker depends on grouped lines & grouped ovals
    add_skill("Marker", "RecognizeInstance", ["GroupLine", "GroupOval"])
    add_skill("Marker", "Localize", ["RecognizeInstanceMarker"])
    add_skill("Marker", "Measure", ["LocalizeMarker"])
    add_skill("Marker", "Group", ["MeasureMarker"])
    add_skill("Marker", "Count", ["GroupMarker"])

    # Rectangle depends on grouped lines
    add_skill("Rectangle", "RecognizeInstance", ["GroupLine"])
    add_skill("Rectangle", "Localize", ["RecognizeInstanceRectangle"])
    add_skill("Rectangle", "Measure", ["LocalizeRectangle"])
    add_skill("Rectangle", "Group", ["MeasureRectangle"])
    add_skill("Rectangle", "Count", ["GroupRectangle"])

    # Bars depends on grouped rectangles (in turn from lines)
    add_skill("Bars", "RecognizeInstance", ["GroupRectangle"])
    add_skill("Bars", "Localize", ["RecognizeInstanceBars"])
    add_skill("Bars", "Measure", ["LocalizeBars"])
    add_skill("Bars", "Group", ["MeasureBars"])
    add_skill("Bars", "Count", ["GroupBars"])

    # Axis depends on grouped lines
    add_skill("Axis", "RecognizeInstance", ["GroupLine"])
    add_skill("Axis", "Localize", ["RecognizeInstanceAxis"])
    add_skill("Axis", "Measure", ["LocalizeAxis"])
    add_skill("Axis", "Group", ["MeasureAxis"])
    add_skill("Axis", "Count", ["GroupAxis"])

    # AxesPair depends on grouped axis
    add_skill("AxesPair", "RecognizeInstance", ["GroupAxis"])
    add_skill("AxesPair", "Localize", ["RecognizeInstanceAxesPair"])
    add_skill("AxesPair", "Measure", ["LocalizeAxesPair"])
    add_skill("AxesPair", "Group", ["MeasureAxesPair"])
    add_skill("AxesPair", "Count", ["GroupAxesPair"])

    # NodeGraph depends on grouped ovals + grouped lines
    add_skill("NodeGraph", "RecognizeInstance", ["GroupOval", "GroupLine"])
    add_skill("NodeGraph", "Localize", ["RecognizeInstanceNodeGraph"])
    add_skill("NodeGraph", "Measure", ["LocalizeNodeGraph"])
    add_skill("NodeGraph", "Group", ["MeasureNodeGraph"])
    add_skill("NodeGraph", "Count", ["GroupNodeGraph"])

    # BarGraph depends on grouped bars & grouped axis
    add_skill("BarGraph", "RecognizeInstance", ["GroupBars", "GroupAxis"])
    add_skill("BarGraph", "Localize", ["RecognizeInstanceBarGraph"])
    add_skill("BarGraph", "Measure", ["LocalizeBarGraph"])
    add_skill("BarGraph", "Group", ["MeasureBarGraph"])
    add_skill("BarGraph", "Count", ["GroupBarGraph"])

    # Scatterplot depends on grouped axis + grouped markers
    add_skill("Scatterplot", "RecognizeInstance", ["GroupAxis", "GroupMarker"])
    add_skill("Scatterplot", "Localize", ["RecognizeInstanceScatterplot"])
    add_skill("Scatterplot", "Measure", ["LocalizeScatterplot"])
    add_skill("Scatterplot", "Group", ["MeasureScatterplot"])
    add_skill("Scatterplot", "Count", ["GroupScatterplot"])

    # PieChart depends on grouped ovals + grouped lines
    add_skill("PieChart", "RecognizeInstance", ["GroupOval", "GroupLine"])
    add_skill("PieChart", "Localize", ["RecognizeInstancePieChart"])
    add_skill("PieChart", "Measure", ["LocalizePieChart"])
    add_skill("PieChart", "Group", ["MeasurePieChart"])
    add_skill("PieChart", "Count", ["GroupPieChart"])

    # LineGraph depends on grouped axis + grouped lines
    add_skill("LineGraph", "RecognizeInstance", ["GroupAxis", "GroupLine"])
    add_skill("LineGraph", "Localize", ["RecognizeInstanceLineGraph"])
    add_skill("LineGraph", "Measure", ["LocalizeLineGraph"])
    add_skill("LineGraph", "Group", ["MeasureLineGraph"])
    add_skill("LineGraph", "Count", ["GroupLineGraph"])

    # Link all dependencies
    for lbl in skill_info:
        link_deps(lbl)

    return G, skill_info


##############################################################################
# 2) OPTIONAL VISUALIZATION: DRAW SKILL GRAPH
##############################################################################
def draw_skill_graph(G, skill_info, highlight_object=None):
    import matplotlib.pyplot as plt
    import networkx as nx

    if highlight_object:
        target_nodes = [n for n in G.nodes() if skill_info[n]["object"] == highlight_object]
        anc = set()
        for tn in target_nodes:
            anc |= nx.ancestors(G, tn)
        sub_nodes = set(target_nodes) | anc
        subG = G.subgraph(sub_nodes).copy()
    else:
        subG = G

    objects = sorted({skill_info[n]["object"] for n in subG.nodes()})
    palette = ["red", "blue", "green", "orange", "purple", "brown", "cyan", "magenta","olive", "grey"]
    color_map = {}
    for i, o in enumerate(objects):
        color_map[o] = palette[i % len(palette)]

    pos = nx.kamada_kawai_layout(subG, scale=2)
    plt.figure(figsize=(12, 9))
    nx.draw_networkx_edges(subG, pos, arrows=True, arrowstyle='-|>', arrowsize=16)
    node_colors = [color_map[skill_info[n]["object"]] for n in subG.nodes()]
    nx.draw_networkx_nodes(subG, pos, node_color=node_colors, node_size=2100)
    for n, (x, y) in pos.items():
        plt.text(x, y, n, fontsize=8, ha='center', va='center', fontweight='bold')

    used_colors = set()
    patches = []
    from matplotlib.patches import Patch
    for o in objects:
        c = color_map[o]
        if c not in used_colors:
            used_colors.add(c)
            patches.append(Patch(color=c, label=o))

    plt.title(
        "Skill Dependency Graph" + (f" (object={highlight_object})" if highlight_object else "")
    )
    plt.axis('off')
    if patches:
        plt.legend(handles=patches, loc='best')
    plt.tight_layout()
    plt.show()


##############################################################################
# 3) BASIC GEOMETRY + DRAWING UTILS
##############################################################################
def rotate_points(pts, center, angle_deg):
    cx, cy = center
    r = math.radians(angle_deg)
    out = []
    for (x, y) in pts:
        dx = x - cx
        dy = y - cy
        out.append((
            cx + dx * math.cos(r) - dy * math.sin(r),
            cy + dx * math.sin(r) + dy * math.cos(r)
        ))
    return out

def bounding_box(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))

def boxes_overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    if ax2 < bx1 or bx2 < ax1:
        return False
    if ay2 < by1 or by2 < ay1:
        return False
    return True

def in_bounds(pts, margin=2, size=100):
    """
    Checks if all points are within [margin, size-margin].
    """
    for x, y in pts:
        if x < margin or x > size - margin or y < margin or y > size - margin:
            return False
    return True

def draw_line(ax, pts, color='k', lw=2, jitter=0.0):
    """
    Draws a segmented line with optional jitter for a natural look.
    This is the ONLY place that physically draws lines.
    All shapes that have "lines" must eventually call draw_line.
    """
    if len(pts) < 2:
        return
    x0, y0 = pts[0]
    for i in range(1, len(pts)):
        x1, y1 = pts[i]
        steps = max(2, int((abs(x1 - x0) + abs(y1 - y0)) * 0.4))
        xarr, yarr = [], []
        for s in range(steps + 1):
            t = s / steps
            xx = x0 + t * (x1 - x0)
            yy = y0 + t * (y1 - y0)
            if jitter > 0:
                amt = jitter * 0.01
                xx += random.uniform(-amt, amt) * (steps / 2)
                yy += random.uniform(-amt, amt) * (steps / 2)
            xarr.append(xx)
            yarr.append(yy)
        ax.plot(xarr, yarr, color=color, lw=lw)
        x0, y0 = x1, y1


##############################################################################
# 4) BASE OBJECT GENERATION: LINES & OVALS (Lowest-level rendering)
##############################################################################
def gen_line(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    Generates (and draws) a line that meets constraints.
    If we cannot place one after multiple tries, picks a fallback.
    """
    if used_bboxes is None:
        used_bboxes = []
    for _ in range(100):
        length = random.uniform(10, 30)
        angle = random.uniform(0, 180)
        cx = random.uniform(20, 80)
        cy = random.uniform(20, 80)
        dx = (length / 2) * math.cos(math.radians(angle))
        dy = (length / 2) * math.sin(math.radians(angle))
        p1 = (cx - dx, cy - dy)
        p2 = (cx + dx, cy + dy)
        pts = [p1, p2]
        bb = bounding_box(pts)
        if must_in_bounds and not in_bounds(pts, margin=2, size=100):
            continue
        if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
            continue
        draw_line(ax, pts, jitter=jitter)
        used_bboxes.append(bb)
        return {"type": "Line", "points": pts, "bbox": bb, "meta": {"angle": angle, "length": length}}

    # fallback
    p1, p2 = (40, 40), (60, 40)
    pts = [p1, p2]
    bb = bounding_box(pts)
    draw_line(ax, pts, jitter=jitter)
    used_bboxes.append(bb)
    return {"type": "Line", "points": pts, "bbox": bb, "meta": {"angle": 0, "length": 20}}


def gen_oval(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    Generates (and draws) an oval in the 100x100 area.
    Physically drawn by approximating the perimeter with draw_line calls.
    """
    if used_bboxes is None:
        used_bboxes = []
    for _ in range(100):
        w = random.uniform(10, 35)
        h = random.uniform(10, 35)
        angle = random.uniform(0, 180)
        cx = random.uniform(20, 80)
        cy = random.uniform(20, 80)
        segs = 12
        pts = []
        for s in range(segs + 1):
            th = 2 * math.pi * (s / segs)
            xx = cx + (w / 2) * math.cos(th)
            yy = cy + (h / 2) * math.sin(th)
            pts.append((xx, yy))
        if angle != 0:
            pts = rotate_points(pts, (cx, cy), angle)
        bb = bounding_box(pts)
        if must_in_bounds and not in_bounds(pts, margin=2, size=100):
            continue
        if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
            continue
        # connect the perimeter
        draw_line(ax, pts, jitter=jitter)
        used_bboxes.append(bb)
        return {"type": "Oval", "points": pts, "bbox": bb, "meta": {"angle": angle, "width": w, "height": h}}

    # fallback
    pts = [(40, 40), (60, 40), (60, 60), (40, 60), (40, 40)]
    bb = bounding_box(pts)
    draw_line(ax, pts, jitter=jitter)
    used_bboxes.append(bb)
    return {"type": "Oval", "points": pts, "bbox": bb, "meta": {"angle": 0, "width": 20, "height": 20}}


##############################################################################
# 5) HIGHER-LEVEL COMPOSITIONS (But we define constraints first, then place)
##############################################################################

def compose_marker(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """A marker can be a small oval or two perpendicular short lines."""
    if used_bboxes is None:
        used_bboxes = []

    if random.random() < 0.5:
        # small oval approach
        result_ov = gen_oval(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
        return {
            "type": "Marker",
            "points": result_ov["points"],
            "bbox": result_ov["bbox"],
            "meta": {"mode": "small_oval"}
        }
    else:
        # short lines approach
        # We'll pick a center, angle, length
        for _ in range(100):
            length = random.uniform(3, 8)
            angle = random.uniform(0, 180)
            cx = random.uniform(20, 80)
            cy = random.uniform(20, 80)

            dx = (length / 2) * math.cos(math.radians(angle))
            dy = (length / 2) * math.sin(math.radians(angle))
            p1, p2 = (cx - dx, cy - dy), (cx + dx, cy + dy)

            angle_perp = angle + 90
            dx2 = (length / 2) * math.cos(math.radians(angle_perp))
            dy2 = (length / 2) * math.sin(math.radians(angle_perp))
            p3, p4 = (cx - dx2, cy - dy2), (cx + dx2, cy + dy2)

            # Check each line's bounding box
            pts1 = [p1, p2]
            bb1 = bounding_box(pts1)
            pts2 = [p3, p4]
            bb2 = bounding_box(pts2)
            if must_in_bounds and (not in_bounds(pts1) or not in_bounds(pts2)):
                continue
            if no_overlap and (
                any(boxes_overlap(bb1, u) for u in used_bboxes) or
                any(boxes_overlap(bb2, u) for u in used_bboxes)
            ):
                continue
            # OK, let's draw them
            draw_line(ax, pts1, jitter=jitter)
            draw_line(ax, pts2, jitter=jitter)
            used_bboxes.append(bb1)
            used_bboxes.append(bb2)
            allpts = pts1 + pts2
            b = bounding_box(allpts)
            return {
                "type": "Marker",
                "points": allpts,
                "bbox": b,
                "meta": {"mode": "two_perp_lines"}
            }

        # fallback
        # small lines forming a cross
        p1, p2, p3, p4 = (40, 40), (44, 40), (40, 44), (44, 44)
        pts1 = [p1, p2]
        pts2 = [p3, p4]
        bb1 = bounding_box(pts1)
        bb2 = bounding_box(pts2)
        draw_line(ax, pts1, jitter=jitter)
        draw_line(ax, pts2, jitter=jitter)
        used_bboxes.append(bb1)
        used_bboxes.append(bb2)
        b = bounding_box(pts1 + pts2)
        return {
            "type": "Marker",
            "points": pts1 + pts2,
            "bbox": b,
            "meta": {"mode": "fallback_cross"}
        }

def compose_rectangle(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """A rectangle is 4 lines at right angles. We'll define w,h,angle, then place lines."""
    if used_bboxes is None:
        used_bboxes = []
    for _ in range(100):
        w = random.uniform(10, 30)
        h = random.uniform(10, 30)
        angle = random.uniform(0, 180)
        cx = random.uniform(20, 80)
        cy = random.uniform(20, 80)
        corners = [(cx - w/2, cy - h/2), (cx + w/2, cy - h/2), 
                   (cx + w/2, cy + h/2), (cx - w/2, cy + h/2)]
        if angle != 0:
            corners = rotate_points(corners, (cx, cy), angle)

        # Try to draw 4 lines. If any fails, revert.
        lines_data = []
        success = True
        for i in range(4):
            p1 = corners[i]
            p2 = corners[(i + 1) % 4]
            bb = bounding_box([p1, p2])
            if must_in_bounds and not in_bounds([p1, p2]):
                success = False
                break
            if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
                success = False
                break
            # if success, draw
            draw_line(ax, [p1, p2], jitter=jitter)
            used_bboxes.append(bb)
            lines_data.append({"bbox": bb, "points": [p1, p2]})
        if success:
            allpts = []
            for ld in lines_data:
                allpts.extend(ld["points"])
            b = bounding_box(allpts)
            return {
                "type": "Rectangle",
                "points": allpts,
                "bbox": b,
                "meta": {"angle": angle, "width": w, "height": h}
            }
        else:
            # revert what we drew
            for ld in lines_data:
                if ld["bbox"] in used_bboxes:
                    used_bboxes.remove(ld["bbox"])

    # fallback
    # forced small rectangle
    c = [(40, 40), (50, 40), (50, 48), (40, 48)]
    lines_data = []
    success = True
    for i in range(4):
        p1 = c[i]
        p2 = c[(i + 1) % 4]
        bb = bounding_box([p1, p2])
        if must_in_bounds and not in_bounds([p1, p2]):
            success = False
            break
        if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
            success = False
            break
        draw_line(ax, [p1, p2], jitter=jitter)
        used_bboxes.append(bb)
        lines_data.append({"bbox": bb, "points": [p1, p2]})
    if success:
        allpts = []
        for ld in lines_data:
            allpts.extend(ld["points"])
        b = bounding_box(allpts)
        return {
            "type": "Rectangle",
            "points": allpts,
            "bbox": b,
            "meta": {"angle": 0, "width": 10, "height": 8}
        }
    else:
        # If we can't even do fallback?
        return {"type": "Rectangle", "points": [], "bbox": (0,0,0,0), "meta": {}}

def compose_bars(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    Bars = multiple rectangles in a row, same angle, aligned bottom.
    We'll define num_bars, bar_w, spacing, angle, etc. Then place each rectangle.
    """
    if used_bboxes is None:
        used_bboxes = []
    angle = random.uniform(0, 180)
    num_bars = random.randint(2, 5)
    bar_w = random.uniform(5, 12)
    spacing = bar_w * 0.3
    # anchor at a random center
    cx = random.uniform(30, 70)
    cy = random.uniform(30, 70)
    tot_w = num_bars * (bar_w + spacing) - spacing
    left = -tot_w / 2
    allpts = []
    for i in range(num_bars):
        local_x = left + i * (bar_w + spacing)
        bar_h = random.uniform(15, 50)
        # corners local
        corners_local = [
            (local_x, 0),
            (local_x + bar_w, 0),
            (local_x + bar_w, bar_h),
            (local_x, bar_h)
        ]
        if angle != 0:
            corners_local = rotate_points(corners_local, (0,0), angle)
        corners_global = [(p[0]+cx, p[1]+cy) for p in corners_local]

        # draw 4 lines => rectangle
        lines_data = []
        success = True
        for k in range(4):
            p1 = corners_global[k]
            p2 = corners_global[(k+1)%4]
            bb = bounding_box([p1, p2])
            if must_in_bounds and not in_bounds([p1,p2]):
                success = False
                break
            if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
                success = False
                break
            draw_line(ax, [p1, p2], jitter=jitter)
            used_bboxes.append(bb)
            lines_data.append({"points":[p1,p2], "bbox":bb})
        if not success:
            for ld in lines_data:
                used_bboxes.remove(ld["bbox"])
        else:
            for ld in lines_data:
                allpts.extend(ld["points"])
    if not allpts:
        # fallback => just a single rectangle
        rect_data = compose_rectangle(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
        return {"type": "Bars", "points": rect_data["points"], "bbox": rect_data["bbox"], "meta": {"fallback": True}}

    b = bounding_box(allpts)
    return {"type": "Bars", "points": allpts, "bbox": b, "meta": {"angle": angle, "num_bars": num_bars}}

def compose_axis(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    Axis = a single line on the plane.
    """
    return gen_line(ax, jitter, must_in_bounds, no_overlap, used_bboxes)

def compose_axespair(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    AxesPair = 2 axes that share a common endpoint.
    We'll do 2 lines and force them to share an endpoint. 
    We'll define them first, then shift the second.
    """
    if used_bboxes is None:
        used_bboxes = []
    ax1 = compose_axis(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    if not ax1["points"]:
        return ax1
    p1, p2 = ax1["points"]
    pick_end = random.choice([p1, p2])

    # second axis
    ax2 = compose_axis(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    if not ax2["points"]:
        return ax1
    used_bboxes.remove(ax2["bbox"])  # remove old bounding box, we'll re-draw with shift
    # shift ax2 so that its midpoint is pick_end
    midx = (ax2["points"][0][0] + ax2["points"][1][0]) / 2
    midy = (ax2["points"][0][1] + ax2["points"][1][1]) / 2
    dx = pick_end[0] - midx
    dy = pick_end[1] - midy

    shifted_pts = []
    for p in ax2["points"]:
        shifted_pts.append((p[0]+dx, p[1]+dy))

    # now see if shifted is valid
    bb = bounding_box(shifted_pts)
    if must_in_bounds and not in_bounds(shifted_pts):
        # revert
        return ax1
    if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
        return ax1
    # draw them
    draw_line(ax, shifted_pts, jitter=jitter)
    used_bboxes.append(bb)
    allpts = ax1["points"] + shifted_pts
    bigBB = bounding_box(allpts)
    return {"type": "AxesPair", "points": allpts, "bbox": bigBB, "meta": {}}

def compose_nodegraph(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    NodeGraph = 3-6 ovals, and random lines connecting their centers.
    """
    n_nodes = random.randint(3, 6)
    node_list = []
    for _ in range(n_nodes):
        ov = gen_oval(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
        node_list.append(ov)
    edges = []
    allpts = []
    for n in node_list:
        allpts.extend(n["points"])
    # random edges
    n_edges = random.randint(n_nodes-1, min(n_nodes*(n_nodes-1)//2, n_nodes+3))
    used_pairs = set()
    for _ in range(n_edges):
        i1 = random.randint(0, n_nodes-1)
        i2 = random.randint(0, n_nodes-1)
        if i1 != i2 and (i1, i2) not in used_pairs and (i2, i1) not in used_pairs:
            used_pairs.add((i1, i2))
            bb1 = node_list[i1]["bbox"]
            bb2 = node_list[i2]["bbox"]
            x1, y1 = (bb1[0]+bb1[2])/2, (bb1[1]+bb1[3])/2
            x2, y2 = (bb2[0]+bb2[2])/2, (bb2[1]+bb2[3])/2
            # check line
            new_bb = bounding_box([(x1,y1),(x2,y2)])
            if must_in_bounds and not in_bounds([(x1,y1),(x2,y2)]):
                continue
            if no_overlap and any(boxes_overlap(new_bb, u) for u in used_bboxes):
                continue
            draw_line(ax, [(x1, y1), (x2, y2)], jitter=jitter)
            used_bboxes.append(new_bb)
            edges.append(new_bb)
            allpts.append((x1,y1))
            allpts.append((x2,y2))
    bb = bounding_box(allpts)
    return {"type": "NodeGraph", "points": allpts, "bbox": bb, "meta": {"nodes": len(node_list)}}

def compose_bargraph(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    BarGraph = single axis + a bars set. 
    """
    axdata = compose_axis(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    barsdata = compose_bars(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    allpts = axdata["points"] + barsdata["points"]
    b1, b2 = axdata["bbox"], barsdata["bbox"]
    bigBB = (min(b1[0],b2[0]), min(b1[1],b2[1]), max(b1[2],b2[2]), max(b1[3],b2[3]))
    return {"type": "BarGraph", "points": allpts, "bbox": bigBB, "meta": {}}

def compose_scatterplot(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    Scatterplot = single axis + multiple markers around.
    """
    axis_data = compose_axis(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    n_marks = random.randint(3, 10)
    allpts = list(axis_data["points"])
    for _ in range(n_marks):
        mk = compose_marker(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
        allpts.extend(mk["points"])
    bb = bounding_box(allpts)
    return {"type": "Scatterplot", "points": allpts, "bbox": bb, "meta": {"markers": n_marks}}

def compose_piechart(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    PieChart = single oval + lines from center for wedges.
    """
    if used_bboxes is None:
        used_bboxes = []
    ov = gen_oval(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    b = ov["bbox"]
    cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
    n_wedges = random.randint(2, 6)
    wedge_pts = []
    allpts = list(ov["points"])
    for _ in range(n_wedges):
        angle = random.uniform(0,360)
        rx = (b[2]-b[0])/2
        ry = (b[3]-b[1])/2
        r = max(rx, ry)
        x2 = cx + r * math.cos(math.radians(angle))
        y2 = cy + r * math.sin(math.radians(angle))
        wbb = bounding_box([(cx,cy),(x2,y2)])
        if must_in_bounds and not in_bounds([(cx,cy),(x2,y2)]):
            continue
        if no_overlap and any(boxes_overlap(wbb, u) for u in used_bboxes):
            continue
        draw_line(ax, [(cx, cy), (x2, y2)], jitter=jitter)
        used_bboxes.append(wbb)
        wedge_pts.extend([(cx, cy), (x2, y2)])
    allpts.extend(wedge_pts)
    bigBB = bounding_box(allpts)
    return {"type": "PieChart", "points": allpts, "bbox": bigBB, "meta": {"wedges": n_wedges}}

def compose_linegraph(ax, jitter=0.0, must_in_bounds=True, no_overlap=False, used_bboxes=None):
    """
    LineGraph = single axis + a polyline offset from the axis.
    """
    axis_obj = compose_axis(ax, jitter, must_in_bounds, no_overlap, used_bboxes)
    if len(axis_obj["points"]) < 2:
        return axis_obj
    p1, p2 = axis_obj["points"]
    n_points = random.randint(4, 8)
    step = 1/(n_points - 1)
    polypoints = []
    # pick offset
    allpts = list(axis_obj["points"])
    for i in range(n_points):
        t = i*step
        xx = p1[0] + t*(p2[0]-p1[0])
        yy = p1[1] + t*(p2[1]-p1[1])
        angle = math.atan2((p2[1]-p1[1]),(p2[0]-p1[0])) + math.pi/2
        dist = random.uniform(-20,20)
        sx = dist*math.cos(angle)
        sy = dist*math.sin(angle)
        polypoints.append((xx+sx, yy+sy))

    for i in range(len(polypoints)-1):
        seg = [polypoints[i], polypoints[i+1]]
        bb = bounding_box(seg)
        if must_in_bounds and not in_bounds(seg):
            continue
        if no_overlap and any(boxes_overlap(bb, u) for u in used_bboxes):
            continue
        draw_line(ax, seg, jitter=jitter)
        used_bboxes.append(bb)
        allpts.extend(seg)

    bb = bounding_box(allpts)
    return {"type": "LineGraph", "points": allpts, "bbox": bb, "meta": {"num_points": n_points}}


##############################################################################
# DISPATCH TABLE FOR GENERATION
##############################################################################
OBJECT_GENERATORS = {
    "Line": gen_line,
    "Oval": gen_oval,
    "Marker": compose_marker,
    "Rectangle": compose_rectangle,
    "Bars": compose_bars,
    "Axis": compose_axis,
    "AxesPair": compose_axespair,
    "NodeGraph": compose_nodegraph,
    "BarGraph": compose_bargraph,
    "Scatterplot": compose_scatterplot,
    "PieChart": compose_piechart,
    "LineGraph": compose_linegraph,
}


##############################################################################
# 6) MAIN PROCEDURAL GENERATION LOGIC
##############################################################################
def procedural_generate(
    skill_label,
    outdir="tree_procedural_output",
    jitter=2.0,
    noise_level=0.02,
    must_in_bounds=True,
    no_overlap=False,
    verbose=True
):
    """
    Creates a single image that satisfies the skill_label using the skill graph.
    We plan from the "top" skill but also print from the "bottom up" as we do everything:
      e.g. RecognizeInstanceLine -> ...
           LocalizeLine -> ...
           ...
           GroupLine -> ...
           RecognizeInstanceRectangle -> ...
    Then we physically generate the objects in a final pass. 
    """
    G, skill_info = build_skill_graph()
    if skill_label not in G.nodes():
        raise ValueError(f"Skill label {skill_label} not in skill graph.")

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # We'll build a plan of steps
    final_plan = []
    object_records = {}
    object_id_counters = {}
    used_bboxes = []

    fig, ax = plt.subplots(figsize=(5,5))
    ax.set_xlim(0,100)
    ax.set_ylim(0,100)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.gca().invert_yaxis()

    def get_next_id(obj_type):
        if obj_type not in object_id_counters:
            object_id_counters[obj_type] = 0
        object_id_counters[obj_type] += 1
        return object_id_counters[obj_type]

    def group_objects(obj_type):
        """Generates a plan step grouping all ungrouped objects of that type."""
        if obj_type not in object_records:
            return
        ungrouped = [x for x in object_records[obj_type] if not x["grouped"]]
        if ungrouped:
            ids_ungrouped = [u["id"] for u in ungrouped]
            for u in ungrouped:
                u["grouped"] = True
            final_plan.append(f"Group{obj_type} -> grouped {obj_type} objects {ids_ungrouped}")

    def ensure_base_objects(obj_type, n_needed):
        """
        For each object type, we ensure we have at least n_needed recognized+localized+measured.
        We'll record it in object_records but won't physically draw them yet.
        """
        if obj_type not in object_records:
            object_records[obj_type] = []
        existing_count = len(object_records[obj_type])
        to_make = n_needed - existing_count
        for _ in range(to_make):
            new_id = get_next_id(obj_type)
            object_records[obj_type].append({
                "id": new_id,
                "recognized": True,
                "localized": True,
                "measured": True,
                "grouped": False,
                "shape_data": None
            })
            final_plan.append(f"RecognizeInstance{obj_type}{new_id} -> Created {obj_type}#{new_id}")
            final_plan.append(f"Localize{obj_type}{new_id} -> assigned position for {obj_type}#{new_id}")
            final_plan.append(f"Measure{obj_type}{new_id} -> measured geometry for {obj_type}#{new_id}")

    def ensure_deps_for_object(obj_type):
        """
        Recursively ensure dependencies for object (like grouping lines if needed).
        """
        rec_lbl = f"RecognizeInstance{obj_type}"
        if rec_lbl not in skill_info:
            return
        for dep_skill in skill_info[rec_lbl]["deps"]:
            dep_obj = skill_info[dep_skill]["object"]
            dep_act = skill_info[dep_skill]["skill"]
            ensure_deps_for_object(dep_obj)
            if dep_act == "RecognizeInstance":
                ensure_base_objects(dep_obj, 1)
            elif dep_act == "Group":
                ensure_base_objects(dep_obj, 2)
                group_objects(dep_obj)
            # measure/localize is implied in ensure_base_objects

    # Figure out what we want to do for skill_label
    skill_obj = skill_info[skill_label]["object"]
    skill_act = skill_info[skill_label]["skill"]

    # Build up dependencies
    ensure_deps_for_object(skill_obj)

    # If we need more objects for final step, e.g. grouping or counting
    needed_count = 2 if skill_act in ["Group","Count"] else 1
    ensure_base_objects(skill_obj, needed_count)

    # group or count if needed
    if skill_act == "Group":
        group_objects(skill_obj)
    elif skill_act == "Count":
        group_objects(skill_obj)
        grouped_objs = [x for x in object_records[skill_obj] if x["grouped"]]
        final_plan.append(f"Count{skill_obj} -> found {len(grouped_objs)} grouped {skill_obj}(s)")
    elif skill_act in ["Localize","Measure"]:
        # They were already marked localized/measured in ensure_base_objects
        for o in object_records[skill_obj]:
            final_plan.append(f"(Note) {skill_obj}#{o['id']} was {skill_act.lower()}d earlier.")

    # Physically generate/draw each recognized object exactly once
    for obj_type, rec_list in object_records.items():
        gen_fn = OBJECT_GENERATORS.get(obj_type, None)
        if gen_fn:
            for obj_rec in rec_list:
                if obj_rec["shape_data"] is None:
                    shape_data = gen_fn(
                        ax,
                        jitter=jitter,
                        must_in_bounds=must_in_bounds,
                        no_overlap=no_overlap,
                        used_bboxes=used_bboxes
                    )
                    obj_rec["shape_data"] = shape_data

    # Add random noise
    totpix = 100*100
    nn = int(totpix * noise_level)
    for _ in range(nn):
        xx = random.randint(0,99)
        yy = random.randint(0,99)
        ax.plot([xx],[yy],'ks',markersize=1)

    title_text = f"Single-Image skill={skill_label}"
    fig.suptitle(title_text, fontsize=9)
    outpath = os.path.join(outdir, f"{skill_label}_single.png")
    plt.savefig(outpath, dpi=120)
    plt.close(fig)

    if verbose:
        print(f"Saved {outpath}")
        print("===== Detailed Plan (Bottom-Up) =====")
        for line in final_plan:
            print(line)


##############################################################################
# 7) MAIN DEMO
##############################################################################
def main():
    # If you want to visualize the graph, uncomment:
    # G, skill_info = build_skill_graph()
    # draw_skill_graph(G, skill_info)
    # draw_skill_graph(G, skill_info, highlight_object="Rectangle")

    # Example usage:
    skill = "CountBars"
    procedural_generate(
        skill_label=skill,
        outdir="tree_procedural_output",
        jitter=1.5,
        noise_level=0.02,
        must_in_bounds=True,
        no_overlap=True,
        verbose=True
    )

    # You can try more:
    # procedural_generate("CountLine", outdir="tree_procedural_output", verbose=True)
    # procedural_generate("LineGraph", outdir="tree_procedural_output", verbose=True)
    # procedural_generate("Scatterplot", outdir="tree_procedural_output", verbose=True)
    # etc.

if __name__ == "__main__":
    main()
