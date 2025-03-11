import math
import bisect
import random
from .utilities import rotate_point

##############################################################################
# Intersection routines – adapted to the object representations used here.
#
# All objects are represented as dummy objects with attributes.
# A Line has attributes: p1, p2.
# An Oval (or Circle) has attributes: center, width, height, angle.
# A Polygon (Triangle, Rectangle, Square, Polygon) is represented by vertices.
##############################################################################

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
            pts.append(rotate_point((x, y), ov.center, ov.angle))
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

# --- Helper: Convert parameter dictionary into a dummy object.
def create_dummy(params, shape):
    class Dummy:
        pass
    dummy = Dummy()
    # Determine geometric category.
    if shape == "Line":
        dummy.p1 = params["p1"]
        dummy.p2 = params["p2"]
    elif shape in ["Oval", "Circle"]:
        dummy.center = params["center"]
        dummy.width = params["width"]
        dummy.height = params["height"]
        dummy.angle = params["angle"]
    else:
        # For polygons (Triangle, Rectangle, Square, Polygon)
        if "vertices" in params:
            dummy.vertices = params["vertices"]
        else:
            cx, cy = params["center"]
            w, h, angle = params["width"], params["height"], params["angle"]
            dx, dy = w / 2.0, h / 2.0
            pts = [
                rotate_point((cx - dx, cy - dy), (cx, cy), angle),
                rotate_point((cx + dx, cy - dy), (cx, cy), angle),
                rotate_point((cx + dx, cy + dy), (cx, cy), angle),
                rotate_point((cx - dx, cy + dy), (cx, cy), angle)
            ]
            dummy.vertices = pts
    return dummy

# --- Main intersection dispatch.
def intersect(params1, shape1, params2, shape2):
    obj1 = create_dummy(params1, shape1)
    obj2 = create_dummy(params2, shape2)
    def geom_type(shape):
        if shape == "Line":
            return "line"
        elif shape in ["Oval", "Circle"]:
            return "oval"
        else:
            return "polygon"
    g1 = geom_type(shape1)
    g2 = geom_type(shape2)
    if g1 == "line" and g2 == "line":
        return _line_line_intersect(obj1.p1, obj1.p2, obj2.p1, obj2.p2)
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
