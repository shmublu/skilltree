import json
import sys
import argparse

def convert_line(line):
    """
    Convert a single JSON line from the old format to the new format.
    
    For each message:
      - If role is "user" and content is a list:
          - For each item, if the type is:
              - "image_path": append "<image>" to the content and record the file path.
              - "audio_path": append "<audio>" and record the file path.
              - "video_path": append "<video>" and record the file path.
              - "text": append the text.
      - If role is "assistant":
          - If content is a string, use it as-is.
    
    The resulting JSON object contains:
      - "messages": a list of message objects with proper role tags.
      - Additional keys ("images", "audios", "videos") if media items are found.
    """
    data = json.loads(line)
    new_messages = []
    images = []
    audios = []
    videos = []
    
    for message in data.get("messages", []):
        role = message.get("role")
        content = message.get("content")
        new_content = ""
        
        if isinstance(content, list):
            for item in content:
                item_type = item.get("type")
                item_content = item.get("content", "")
                if item_type == "image_path":
                    new_content += "<image>"
                    images.append(item_content)
                elif item_type == "audio_path":
                    new_content += "<audio>"
                    audios.append(item_content)
                elif item_type == "video_path":
                    new_content += "<video>"
                    videos.append(item_content)
                elif item_type == "text":
                    new_content += item_content
                else:
                    new_content += item_content if item_content else ""
        elif isinstance(content, str):
            new_content = content
        else:
            new_content = str(content)
        
        # Preserve the role for each message.
        new_messages.append({"role": role, "content": new_content.replace("<image>", "")})
    
    result = {"messages": new_messages}
    if images:
        result["images"] = images
    if audios:
        result["audios"] = audios
    if videos:
        result["videos"] = videos
    return result

def main():
    parser = argparse.ArgumentParser(
        description="Convert a file of JSON lines from the old format to the new format."
    )
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("output_file", help="Path to the output file")
    args = parser.parse_args()
    
    with open(args.input_file, "r", encoding="utf-8") as fin, \
         open(args.output_file, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue  # skip empty lines
            try:
                new_obj = convert_line(line)
                fout.write(json.dumps(new_obj) + "\n")
            except Exception as e:
                print("Error processing line:", line, file=sys.stderr)
                print("Error:", e, file=sys.stderr)

if __name__ == "__main__":
    main()
