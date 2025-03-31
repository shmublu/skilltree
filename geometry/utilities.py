# utilities.py
import math, random
import numpy as np

def handwritten_path(p1, p2, steps=20, jitter=5):
    """
    Generate a momentum-based jittered path from p1 to p2.
    p1, p2: tuples
    steps: number of segments
    jitter: controls how "handwritten" the path is (0 = perfect)
    Returns a list of (x,y) points.
    """
    p1 = np.array(p1, dtype=float)
    p2 = np.array(p2, dtype=float)
    dt = 1.0 / steps
    velocity = np.zeros(2)
    path = [p1.copy()]
    for i in range(steps):
        desired = p1 + (i+1)/steps*(p2-p1)
        accel = np.random.uniform(-jitter, jitter, size=2)
        velocity = 0.8 * velocity + accel * dt
        new_point = path[-1] + (desired - path[-1]) + velocity * dt
        path.append(new_point)
    return [tuple(pt) for pt in path]

def jitter_coords(coords, jitter=2):
    """Jitter each (x,y) coordinate by ±jitter."""
    return [(x + random.uniform(-jitter, jitter), y + random.uniform(-jitter, jitter)) for (x, y) in coords]

def clamp_point(point, canvas=(0,800,0,600)):
    xmin, xmax, ymin, ymax = canvas
    x = max(xmin, min(point[0], xmax))
    y = max(ymin, min(point[1], ymax))
    return (x, y)

def draw_momentum_line(ax, p1, p2, color, thickness, handwritten=0, steps=20):
    """
    Draw a line from p1 to p2 on axis ax using a momentum-based handwritten simulation.
    """
    pts = handwritten_path(p1, p2, steps=steps, jitter=handwritten) if handwritten > 0 else [p1, p2]
    xs = [pt[0] for pt in pts]
    ys = [pt[1] for pt in pts]
    ax.plot(xs, ys, color=color, lw=thickness)



def get_line_length_and_angle(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx))
    return length, angle

def rotate_point(point, center, angle):
    # Rotate a point around a center by angle (degrees)
    rad = math.radians(angle)
    x, y = point
    cx, cy = center
    x -= cx
    y -= cy
    x_new = x * math.cos(rad) - y * math.sin(rad)
    y_new = x * math.sin(rad) + y * math.cos(rad)
    return (x_new + cx, y_new + cy)


def propagate_style(parent):
    """Force every child to use parent's color and thickness."""
    for child in parent.sub_references:
        child.color = parent.border_color
        child.thickness = parent.thickness
        if hasattr(child, "sub_references") and child.sub_references:
            propagate_style(child)