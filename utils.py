import os
import subprocess
import tempfile
from io import BytesIO
from PIL import Image

def process_image(image_data: BytesIO, is_emoji: bool = False) -> BytesIO:
    with Image.open(image_data) as img:
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if is_emoji:
            img.thumbnail((100, 100), Image.Resampling.LANCZOS)
            
            canvas = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            
            x = (100 - img.width) // 2
            y = (100 - img.height) // 2
            canvas.paste(img, (x, y))
            img = canvas
        else:
            width, height = img.size
            if width >= height:
                new_width = 512
                new_height = int(height * (512 / width))
            else:
                new_height = 512
                new_width = int(width * (512 / height))
            
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output

def process_video(video_data: BytesIO) -> BytesIO:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_input:
        temp_input.write(video_data.read())
        input_path = temp_input.name

    output_path = input_path + ".webm"

    try:
        command = [
            "ffmpeg",
            "-i", input_path,
            "-t", "3",
            "-vf", "scale=512:512:force_original_aspect_ratio=decrease",
            "-c:v", "libvpx-vp9",
            "-b:v", "256k",
            "-an",
            "-f", "webm",
            "-y",
            output_path
        ]
        
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        with open(output_path, "rb") as f:
            output_data = BytesIO(f.read())
            
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg conversion failed: {e}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
            
    return output_data
