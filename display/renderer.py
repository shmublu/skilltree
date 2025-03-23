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
def display_and_save_scene(scene, outdir="output/output", question=None, reasoning=None, final_answer=None,
                           canvas=(0, 100, 0, 100), huggingface_dataset=True, visualize=False):
    # Determine output file/directory settings based on the dataset type.
    if huggingface_dataset:
        outdir = "output-fix"
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
    
    # Add noise to the image 70% of the time to make it more realistic.
    if random.random() < 0.33:
        xs = sorted(ax.get_xlim())
        ys = sorted(ax.get_ylim())
        total_pixels = abs((xs[1] - xs[0]) * (ys[1] - ys[0]))
        max_noise_level = 0.001
        # Randomize the noise level (current noise level is the max it can be)
        noise_level = random.uniform(0, max_noise_level)
        nn = int(total_pixels * noise_level)
        
        # 50% chance: only multicolored noise; 50% chance: only uniformly colored noise.
        if random.random() < 0.5:
            # Multicolored noise: each dot gets its own random color.
            for _ in range(nn):
                xx = random.randint(int(xs[0]), int(xs[1]) - 1)
                yy = random.randint(int(ys[0]), int(ys[1]) - 1)
                marker_size = random.uniform(0.01, 0.3)
                random_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
                ax.plot(xx, yy, marker='s', color=random_color, markersize=marker_size)
        else:
            # Uniformly colored noise: all dots share one random color.
            uniform_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            for _ in range(nn):
                xx = random.randint(int(xs[0]), int(xs[1]) - 1)
                yy = random.randint(int(ys[0]), int(ys[1]) - 1)
                marker_size = random.uniform(0.1, 0.9)
                ax.plot(xx, yy, marker='s', color=uniform_color, markersize=marker_size)
        
        # 20% chance to add random letters as noise (at a much lower density).
        if random.random() < 0.2:
            letter_count = max(1, int(nn * 0.2))
            multilang_letters = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                                 "αβγδεζηθικλμνξοπρστυφχψω"
                                 "абвгдежзийклмнопрстуфхцчшщъыьэюя"
                                 "あいうえおかきくけこ"
                                 "אבגדהוזחט")
            for _ in range(letter_count):
                xx = random.randint(int(xs[0]), int(xs[1]) - 1)
                yy = random.randint(int(ys[0]), int(ys[1]) - 1)
                random_letter = random.choice(multilang_letters)
                font_size = random.uniform(2, 6)
                letter_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
                # Specify fontname to fix text rendering issues.
                ax.text(xx, yy, random_letter, fontsize=font_size, color=letter_color, fontname='DejaVu Sans')
    
    # If visualize flag is true, display the image with a title before saving.
    if visualize:
        title_text = ""
        if question:
            title_text += f"Question: {question}"
        if reasoning:
            if title_text:
                title_text += " | "
            title_text += f"Reasoning: {reasoning}"
        if final_answer:
            if title_text:
                title_text += " | "
            title_text += f"Final Answer: {final_answer}"
        if title_text:
            ax.set_title(title_text, fontname='DejaVu Sans')
        plt.show()  # This call will block until the window is closed.
    
    # Save the scene image.
    fig.savefig(image_out, dpi=400, bbox_inches='tight', pad_inches=0)
    print(f"Scene image saved to {image_out}")
    
    # Function for word-level synonym substitution.
    def synonym_substitution(s):
        substitutions = {
            "reason": ["contemplate", "consider", "reflect on", "deliberate"],
            "looks like": ["appears to be", "looks like", "is"],
            "consider": ["regard", "view", "examine", "assess"],
            "think": ["think", "believe", "suspect", "see that"],
            "image": ["picture", "image", "scene"],
            "picture": ["picture", "image", "scene"],
        }
        for word, alternatives in substitutions.items():
            pattern = r'\b' + word + r'\b'
            if re.search(pattern, s, flags=re.IGNORECASE):
                replacement = random.choice(alternatives)
                s = re.sub(pattern, replacement, s, count=1, flags=re.IGNORECASE)
        return s

    # Neutral introduction sentences.
    neutral_intros = [
        "I think there is geometry in the image. Let me decompose it and then return to the original question. ",
        "The image contains shapes. Before I answer the question, let me parse the geometric shapes. ",
        "This image has geometric data in it. I will analyze it visually and then go back to answer the question. ",
        "This looks like a 2D image. Let me decompose it and then return to the original question. ",
        "This is a two dimensional geometry scene. I will decompose it and then return to the original question. ",
    ]
    
    # Build the final output message.
    intro = random.choice(neutral_intros)
    if reasoning is None:
        reasoning = ""
    reasoning_text = synonym_substitution(reasoning) + " " if reasoning.strip() else ""
    
    final_answer = final_answer.lower()
    if final_answer == "true":
        final_decision = "yes"
    elif final_answer == "false":
        final_decision = "no"
    else:
        final_decision = final_answer
        
    if question is None:
        question = ""
    return_sentence = f"After analyzing, I will now return to the original question: '{question}' - the answer is {final_decision}."
    
    final_output = intro + reasoning_text + return_sentence
    final_output = synonym_substitution(final_output)
    
    # Handle annotation saving based on the dataset type.
    if huggingface_dataset:
        abs_image_path = os.path.abspath(image_out)
        conversation = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_path", "content": abs_image_path},
                        {"type": "text", "content": question}
                    ]
                },
                {
                    "role": "assistant",
                    "content": final_output
                }
            ]
        }
        hf_out = os.path.join(outdir, "huggingface_dataset.jsonl")
        file_mode = "a" if os.path.exists(hf_out) else "w"
        with open(hf_out, file_mode, encoding="utf-8") as jsonlfile:
            jsonlfile.write(json.dumps(conversation) + "\n")
        print(f"HuggingFace-style dataset row appended to {hf_out}")
    else:
        annotation = {"question": question, "answer": final_output}
        ann_out = os.path.join(outdir, "scene_annotation.json")
        with open(ann_out, "w") as ann_file:
            json.dump(annotation, ann_file, indent=2)
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
