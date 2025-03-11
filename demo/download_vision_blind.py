#!/usr/bin/env python3
import os
import json
import shutil
from datasets import load_dataset
from PIL import Image

def save_image(sample, index, output_dir="./outputs/blind_images"):
    """
    Saves the image from the sample to output_dir using a unique filename based on index.
    The image field may be a PIL image or a dict with a 'path' key.
    Returns the path to the saved image.
    """
    os.makedirs(output_dir, exist_ok=True)
    image = sample["image"]
    
    # If the image is already a PIL image, save it.
    if hasattr(image, "save"):
        filename = f"image_{index}.png"
        dest_path = os.path.join(output_dir, filename)
        image.save(dest_path)
        return os.path.abspath(dest_path)
    # If the image is a dict with a 'path' key, copy the file.
    elif isinstance(image, dict) and "path" in image:
        src_path = image["path"]
        filename = os.path.basename(src_path)
        dest_path = os.path.join(output_dir, filename)
        if not os.path.exists(dest_path):
            shutil.copy(src_path, dest_path)
        return os.path.abspath(dest_path)
    else:
        return "UNKNOWN_IMAGE_PATH"

def transform_dataset(split: str, output_file: str):
    """
    Loads the given dataset split and transforms each sample into a JSONL record.
    Each record follows the structure:
    
    {"messages": [
         {"role": "user", "content": [
              {"type": "image_path", "content": <absolute_image_path>},
              {"type": "text", "content": <prompt>}
         ]},
         {"role": "assistant", "content": <groundtruth>}
     ]}
    
    The fields used are:
      - "prompt": for the question text
      - "groundtruth": for the answer
      - "image": for the image that is downloaded and saved locally
    """
    # Download the dataset split (e.g. "validation")
    dataset = load_dataset("XAI/vlmsareblind", split=split)
    output_image_dir = "./outputs/blind_images"
    os.makedirs(output_image_dir, exist_ok=True)
    
    with open(output_file, "w") as f:
        for idx, sample in enumerate(dataset):
            # Download and save the image locally.
            local_image_path = save_image(sample, idx, output_image_dir)
            prompt = sample.get("prompt", "No prompt provided")
            groundtruth = sample.get("groundtruth", "No groundtruth provided")
            
            record = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_path", "content": local_image_path},
                            {"type": "text", "content": prompt}
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": "{" + groundtruth + "}"
                    }
                ]
            }
            f.write(json.dumps(record) + "\n")

if __name__ == "__main__":
    split = "valid"  # Change to "train" if needed.
    output_file = "vlmsareblind_transformed.jsonl"
    transform_dataset(split, output_file)
    print(f"Transformed dataset has been saved to {output_file}")
