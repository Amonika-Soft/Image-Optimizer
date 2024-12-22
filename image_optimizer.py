from PIL import Image
import os
import logging
from concurrent.futures import ThreadPoolExecutor

def optimize_image(file_path, output_path, quality=85, max_width=None, max_height=None, preserve_metadata=False):
    try:
        img = Image.open(file_path)
        img = img.convert("RGB")  # Ensure compatibility for JPEG

        # Resize image if max_width or max_height are provided
        if max_width or max_height:
            img.thumbnail((max_width or img.width, max_height or img.height))

        # Save with or without metadata
        save_kwargs = {"optimize": True, "quality": quality}
        if not preserve_metadata:
            save_kwargs["exif"] = None

        img.save(output_path, **save_kwargs)

        original_size = os.path.getsize(file_path)
        optimized_size = os.path.getsize(output_path)
        reduction = ((original_size - optimized_size) / original_size) * 100
        logging.info(f"Optimized: {os.path.basename(file_path)} | "
                     f"Original: {original_size / 1024:.2f} KB | Optimized: {optimized_size / 1024:.2f} KB "
                     f"({reduction:.2f}% reduction)")
    except Exception as e:
        logging.error(f"Failed to optimize {file_path}: {e}")

def optimize_images(input_folder, output_folder, quality=85, max_width=None, max_height=None, preserve_metadata=False, threads=4):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info(f"Starting image optimization for folder: {input_folder}")

    image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('jpeg', 'jpg', 'png', 'webp'))]

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for filename in image_files:
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            executor.submit(optimize_image, input_path, output_path, quality, max_width, max_height, preserve_metadata)

    logging.info("Image optimization completed.")

# Example usage
input_folder = "input_images"
output_folder = "optimized_images"
optimize_images(
    input_folder,
    output_folder,
    quality=85,
    max_width=1920,
    max_height=1080,
    preserve_metadata=False,
    threads=4
)
