# utilities.py
import math, random
import numpy as np

import webcolors
from typing import Tuple, Optional

def replace_polygon(s):
    if s.lower() == 'polygon':
        return "non-rectangular, non-triangular Polygon"
    else:
        return s

def color_to_name(rgb_or_rgba: Tuple[float, ...]) -> Optional[str]:
    """
    Converts an RGB or RGBA color tuple to a color name.

    Args:
        rgb_or_rgba: A tuple representing the color, either (R, G, B) or (R, G, B, A),
                     where R, G, B, and A are floats in the range [0.0, 1.0].

    Returns:
        The name of the color, or None if no matching name is found.
    """
    if type(rgb_or_rgba) == str:
        return rgb_or_rgba
    if not (3 <= len(rgb_or_rgba) <= 4):
        raise ValueError("Input must be an RGB or RGBA tuple.")

    rgb = tuple(int(c * 255) for c in rgb_or_rgba[:3])  # Convert floats to integers in [0, 255]

    try:
        # Try to get the exact name first.
        return webcolors.rgb_to_name(rgb)
    except ValueError:
        # If exact name is not found, try to get the closest name.
        try:
            return webcolors.rgb_to_name(rgb, spec='css3') #use css3 for better support.
        except ValueError:
             try:
                return webcolors.rgb_to_name(rgb, spec='html4') #try html4 as a fallback.
             except ValueError:
                return None


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
    if angle < 0:
        angle += 360
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