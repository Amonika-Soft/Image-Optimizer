from PIL import Image
import os

def optimize_images(input_folder, output_folder, quality=85):
    """
    Optimizes all JPEG and PNG images in a folder by reducing their file size.
    
    Args:
        input_folder (str): Path to the folder with original images.
        output_folder (str): Path to save optimized images.
        quality (int): Quality of the saved images (1-100).
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('jpeg', 'jpg', 'png')):
            img_path = os.path.join(input_folder, filename)
            img = Image.open(img_path)
            img = img.convert("RGB")  # Ensure compatibility for JPEG
            output_path = os.path.join(output_folder, filename)
            img.save(output_path, optimize=True, quality=quality)
            print(f"Optimized: {filename}")

# Example usage
input_folder = "input_images"
output_folder = "optimized_images"
optimize_images(input_folder, output_folder)
