#!/usr/bin/env python3
import os
import json
import shutil
from datasets import load_dataset
from PIL import Image

def save_image(sample, index, output_dir="./outputs/mathvista_images"):
    """
    Saves the decoded image from the sample to output_dir using a unique filename based on index.
    The decoded_image field may be a PIL image or a dict with a 'path' key.
    Returns the path to the saved image.
    """
    os.makedirs(output_dir, exist_ok=True)
    image = sample["decoded_image"]
    
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
    Loads the AI4Math/MathVista dataset split and transforms each sample into a JSONL record.
    Only samples whose metadata field (when converted to a string) contains "math" or "geometry"
    are stored.
    
    Each record follows the structure:
    
    {
      "messages": [
         {
           "role": "user",
           "content": [
               {"type": "image_path", "content": <absolute_image_path>},
               {"type": "text", "content": <query>}
           ]
         },
         {
           "role": "assistant",
           "content": <answer>
         }
      ]
    }
    
    The "query" field populates the prompt, the "answer" field becomes the groundtruth,
    and the image is saved from the "decoded_image" field.
    """
    dataset = load_dataset("AI4Math/MathVista", split=split)
    output_image_dir = "./outputs/mathvista_images"
    os.makedirs(output_image_dir, exist_ok=True)
    
    with open(output_file, "w") as f:
        for idx, sample in enumerate(dataset):
            # Convert metadata to a lowercase string and check for keywords.
            metadata = sample.get("metadata", {})
            metadata_str = json.dumps(metadata).lower()
            if "math" not in metadata_str and "geometry" not in metadata_str:
                continue  # Skip this sample if neither keyword is found.
            
            # Save the decoded image locally.
            local_image_path = save_image(sample, idx, output_image_dir)
            
            # Use the "query" field for the prompt and "answer" for the groundtruth.
            prompt = sample.get("query", "No query provided")
            prompt += " Please put your final answer in {}, like {Up} or {3}"
            groundtruth = sample.get("answer", "No answer provided")
            
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
    split = "testmini"  # Change to "validation" or another split if needed.
    output_file = "mathvista_transformed.jsonl"
    transform_dataset(split, output_file)
    print(f"Transformed dataset has been saved to {output_file}")
