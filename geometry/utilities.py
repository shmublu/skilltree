import math

def get_line_length_and_angle(p1, p2):
    """Return the length and angle (in degrees) of the line defined by p1 and p2."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx)) % 360
    return (length, angle)

def rotate_point(pt, center, ang_deg):
    """Rotate a point around a center by a given angle in degrees."""
    r = math.radians(ang_deg)
    (x, y) = pt
    (cx, cy) = center
    dx, dy = x - cx, y - cy
    rx = cx + dx * math.cos(r) - dy * math.sin(r)
    ry = cy + dx * math.sin(r) + dy * math.cos(r)
    return (rx, ry)
