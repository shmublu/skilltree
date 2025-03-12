import os
import json
import random
import uuid
import math
import re
import matplotlib.pyplot as plt

from geometry.utilities import get_line_length_and_angle

##############################################################################
# Display Scene and Save Structure (Direct New Format)
##############################################################################
def display_and_save_scene(scene, outdir="output", question=None, answer=None,
                           canvas=(0, 100, 0, 100), huggingface_dataset=True, visualize=False):
    # Set up output directories.
    if huggingface_dataset:
        outdir = "output"
        image_folder = os.path.join(outdir, "images")
        os.makedirs(outdir, exist_ok=True)
        os.makedirs(image_folder, exist_ok=True)
        unique_id = uuid.uuid4().hex
        image_filename = f"scene_{unique_id}.png"
        image_out = os.path.join(image_folder, image_filename)
    else:
        os.makedirs(outdir, exist_ok=True)
        image_out = os.path.join(outdir, "scene.png")
    
    # Create figure and render the scene.
    fig, ax = plt.subplots(figsize=(5, 5))
    x_min, x_max, y_min, y_max = canvas
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")
    
    for obj in scene:
        obj.render(ax)
    
    # Add noise to the image 70% of the time.
    if random.random() < 0.7:
        xs = sorted(ax.get_xlim())
        ys = sorted(ax.get_ylim())
        total_pixels = abs((xs[1] - xs[0]) * (ys[1] - ys[0]))
        noise_level = 0.002
        nn = int(total_pixels * noise_level)
        for _ in range(nn):
            xx = random.randint(int(xs[0]), int(xs[1]) - 1)
            yy = random.randint(int(ys[0]), int(ys[1]) - 1)
            ax.plot(xx, yy, 'ks', markersize=1)
    
    # Optionally visualize the image with a title.
    if visualize:
        title_text = ""
        if question:
            title_text += f"Question: {question}"
        if answer is not None:
            if title_text:
                title_text += " | "
            title_text += f"Answer: {answer}"
        if title_text:
            ax.set_title(title_text)
        plt.show()
    
    # Save the scene image.
    fig.savefig(image_out, dpi=120, bbox_inches='tight', pad_inches=0)
    print(f"Scene image saved to {image_out}")
    
    # --- Build the conversation in the new format directly ---
    # Instead of embedding media info inside message content, record it separately.
    abs_image_path = os.path.abspath(image_out)
    # Build user message: if a question is provided, use it; also, record the image.
    user_text = question if question else ""
    images = [abs_image_path]  # In this case, we always have one image.
    # Build conversation with messages and media keys.
    conversation = {
        "messages": [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": answer if answer is not None else ""}
        ]
    }
    if images:
        conversation["images"] = images
    # (Similarly, you could add "audios" and "videos" keys if needed.)
    
    # Write conversation to a jsonl file.
    if huggingface_dataset:
        hf_out = os.path.join(outdir, "huggingface_dataset.jsonl")
        file_mode = "a" if os.path.exists(hf_out) else "w"
        with open(hf_out, file_mode, encoding="utf-8") as jsonlfile:
            jsonlfile.write(json.dumps(conversation) + "\n")
        print(f"HuggingFace-style dataset row appended to {hf_out}")
    else:
        ann_out = os.path.join(outdir, "scene_annotation.json")
        with open(ann_out, "w", encoding="utf-8") as ann_file:
            json.dump(conversation, ann_file, indent=2)
        print(f"Annotation saved to {ann_out}")
    
    plt.close(fig)
    
##############################################################################
# Modified run_scene_demo: Integrates scene creation and display.
##############################################################################
def run_scene_demo(plan, outdir="output", distractor_skills=None, allow_partial=False,
                   question=None, answer=None, avoid_types=None, canvas=(0,100,0,100)):
    from scene.builder import create_scene
    scene, _ = create_scene(plan, avoid_types=avoid_types, canvas=canvas, allow_partial=allow_partial)
    display_and_save_scene(scene, outdir=outdir, question=question, answer=answer, canvas=canvas)
