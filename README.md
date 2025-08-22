# Image Optimizer Pro

A Python tool for batch image optimization with detailed reporting.  
Supports JPEG, PNG, WebP, and AVIF formats, generates CSV and HTML reports with visual charts.

## Features
- Reduces image size up to 70% without visible quality loss.  
- Batch processing with multithreading.  
- Input formats: JPEG, PNG, WebP, AVIF.  
- Output formats: Original / JPEG / PNG / WebP / AVIF.  
- Configurable quality, resize, and metadata preservation.  
- CSV and HTML reports with file-by-file statistics.  
- Visual charts: per-file savings (bar) and total before/after (pie).  
- Progress bar for better visibility during optimization.  

## Usage
1. Place your images in the `input_images` folder.  
2. Run the script:  
   ```bash
   python image_optimizer.py input_images optimized_images \
     --quality 85 --resize 1920x1080 --threads 8 --target-format webp \
     --report-prefix report
