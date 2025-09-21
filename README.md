# Image Optimizer Pro

A Python tool for batch image optimization with detailed reporting.  
Supports JPEG, PNG, WebP, and AVIF formats. Generates CSV and HTML reports with visual charts and quality metrics.

## ✨ Features
- Reduces image size up to 70% without visible quality loss.  
- Batch processing with multithreading.  
- Input formats: **JPEG, PNG, WebP, AVIF**.  
- Output formats: **Original / JPEG / PNG / WebP / AVIF**.  
- Configurable quality, resize, and metadata preservation.  
- **CSV and HTML reports** with per-file statistics.  
- **Visual charts**: per-file savings (bar), total before/after (pie).  
- **New: PSNR & SSIM quality metrics** for each optimized image.  
- **SSIM distribution chart** to easily detect potential quality degradation.  
- Progress bar for better visibility during optimization.  

## 📊 Example Reports
- CSV: size before/after, reduction %, PSNR, SSIM.  
- HTML: interactive charts + detailed table with quality metrics.  

## 🔧 Usage
1. Place your images in the `input_images` folder.  
2. Run the script:

```bash
python image_optimizer.py input_images optimized_images \
    --quality 85 --resize 1920x1080 --threads 8 --target-format webp \
    --report-prefix report
