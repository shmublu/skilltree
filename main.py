import random
import math
import argparse
from demo.demos import (
    demo_question_object,
    demo_question_parallel_perp_lines,
    demo_question_arrow_direction,
    demo_question_intersect_objects
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate scenes with skill trees.")
    parser.add_argument("--num-scenes", type=int, default=10, help="Number of scenes to generate")
    parser.add_argument("--sigfigs", type=int, default=1, help="Number of significant figures for numeric outputs")
    parser.add_argument("--json-skill-graph", action="store_true", help="Output the skill graph in JSON format per image")
    args = parser.parse_args()

    funcs = [
        demo_question_object,
        demo_question_parallel_perp_lines,
        demo_question_arrow_direction,
        demo_question_intersect_objects
    ]
    CANVAS_SIZE = (100, 100)

    for i in range(args.num_scenes):
        width = random.randint(100, 500)
        height_lower = max(100, math.ceil(width / 3))
        height_upper = min(400, 3 * width)
        height = random.randint(height_lower, height_upper)
        CANVAS_SIZE = (width, height)
        func = random.choice(funcs)
        # Pass the sigfigs parameter to the demo function.
        skill_trees = func(answer=random.choice([True, False]), canvas_size=CANVAS_SIZE, sigfigs=args.sigfigs)
        # If the json-skill-graph flag is set, write the raw skill trees to a JSON file.
        if args.json_skill_graph:
            json_out = f"skill_graph_{i}.json"
            with open(json_out, "w", encoding="utf-8") as f:
                import json
                json.dump(skill_trees, f, indent=2)
            print(f"Skill graph JSON saved to {json_out}")
