import random
import math
from demo.demos import (
    demo_question_object,
    demo_question_parallel_perp_lines,
    demo_question_arrow_direction,
    demo_question_intersect_objects
)

if __name__ == "__main__":
    dataset_size = 10  # Change this to the desired number of scenes
    funcs = [
        demo_question_object,
        demo_question_parallel_perp_lines,
        demo_question_arrow_direction,
        demo_question_intersect_objects
    ]
    CANVAS_SIZE = (100, 100)

    for i in range(dataset_size):
        width = random.randint(100, 500)
        height_lower = max(100, math.ceil(width / 3))
        height_upper = min(400, 3 * width)
        height = random.randint(height_lower, height_upper)
        CANVAS_SIZE = (width, height)
        func = random.choice(funcs)
        func(answer=random.choice([True, False]), canvas_size=CANVAS_SIZE)
