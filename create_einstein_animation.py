#!/usr/bin/env python3
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
INPUT_IMAGE = "e0302fc6-22ab-4e90-a879-4a684f931366.jpg"
OUTPUT_VIDEO = "einstein_papers_animation.mp4"
FPS = 30
ANIMATION_DURATION = 1.0  # seconds for moving to center
DISPLAY_DURATION = 2.0     # seconds to display in center
FRAMES_TO_CENTER = int(FPS * ANIMATION_DURATION)
FRAMES_DISPLAY = int(FPS * DISPLAY_DURATION)

# Paper definitions (left, middle, right)
# Format: (x, y, width, height, title)
PAPERS = [
    {
        "name": "left",
        "title": "On the Electrodynamics of Moving Bodies",
        "bbox": (50, 280, 300, 200)  # Approximate bounding box
    },
    {
        "name": "right",
        "title": "On a Heuristic Viewpoint Concerning the\nProduction and Transformation of Light",
        "bbox": (670, 280, 300, 200)  # Approximate bounding box
    },
    {
        "name": "middle",
        "title": "Does the Inertia of a Body Depend\nUpon Its Energy Content?",
        "bbox": (350, 280, 320, 200)  # Approximate bounding box
    }
]

def add_text_overlay(frame, text, position="center"):
    """Add text overlay to frame"""
    # Convert to PIL Image for better text rendering
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()

    # Get text size
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Position text at bottom center
    x = (frame.shape[1] - text_width) // 2
    y = frame.shape[0] - text_height - 50

    # Draw semi-transparent background
    padding = 20
    draw.rectangle(
        [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
        fill=(0, 0, 0, 180)
    )

    # Draw text
    draw.text((x, y), text, font=font, fill=(255, 255, 255))

    # Convert back to OpenCV format
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def create_zoom_animation(base_img, paper_bbox, title, order):
    """Create animation for a single paper"""
    frames = []
    h, w = base_img.shape[:2]

    x, y, pw, ph = paper_bbox
    center_x = w // 2
    center_y = h // 2

    # Starting position (paper's current position)
    start_x, start_y = x + pw // 2, y + ph // 2

    # Calculate scale factor to make paper prominent in center
    scale_factor = 2.0

    # Animation: Move to center and scale up
    for i in range(FRAMES_TO_CENTER):
        t = i / FRAMES_TO_CENTER  # 0 to 1
        # Ease in-out
        t = t * t * (3 - 2 * t)

        # Current position
        curr_x = int(start_x + (center_x - start_x) * t)
        curr_y = int(start_y + (center_y - start_y) * t)
        curr_scale = 1.0 + (scale_factor - 1.0) * t

        # Create frame with highlighted paper
        frame = base_img.copy()

        # Extract paper region
        paper_region = base_img[y:y+ph, x:x+pw].copy()

        # Scale paper
        new_pw = int(pw * curr_scale)
        new_ph = int(ph * curr_scale)
        scaled_paper = cv2.resize(paper_region, (new_pw, new_ph))

        # Calculate position to paste
        paste_x = curr_x - new_pw // 2
        paste_y = curr_y - new_ph // 2

        # Ensure we don't go out of bounds
        paste_x = max(0, min(paste_x, w - new_pw))
        paste_y = max(0, min(paste_y, h - new_ph))

        # Darken the background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.3 + 0.7 * (1 - t), overlay, 0.7 * t, 0)

        # Paste scaled paper
        frame[paste_y:paste_y+new_ph, paste_x:paste_x+new_pw] = scaled_paper

        frames.append(frame)

    # Display in center with text
    for i in range(FRAMES_DISPLAY):
        # Create frame with paper centered and scaled
        frame = base_img.copy()

        # Darken background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.3, overlay, 0.7, 0)

        # Extract and scale paper
        paper_region = base_img[y:y+ph, x:x+pw].copy()
        new_pw = int(pw * scale_factor)
        new_ph = int(ph * scale_factor)
        scaled_paper = cv2.resize(paper_region, (new_pw, new_ph))

        # Center position
        paste_x = center_x - new_pw // 2
        paste_y = center_y - new_ph // 2

        # Ensure we don't go out of bounds
        paste_x = max(0, min(paste_x, w - new_pw))
        paste_y = max(0, min(paste_y, h - new_ph))

        # Paste paper
        frame[paste_y:paste_y+new_ph, paste_x:paste_x+new_pw] = scaled_paper

        # Add text overlay
        frame = add_text_overlay(frame, title)

        frames.append(frame)

    # Animation: Return to original position
    for i in range(FRAMES_TO_CENTER):
        t = i / FRAMES_TO_CENTER  # 0 to 1
        # Ease in-out
        t = t * t * (3 - 2 * t)

        # Current position (reversing the animation)
        curr_x = int(center_x + (start_x - center_x) * t)
        curr_y = int(center_y + (start_y - center_y) * t)
        curr_scale = scale_factor + (1.0 - scale_factor) * t

        # Create frame
        frame = base_img.copy()

        # Extract paper region
        paper_region = base_img[y:y+ph, x:x+pw].copy()

        # Scale paper
        new_pw = int(pw * curr_scale)
        new_ph = int(ph * curr_scale)
        scaled_paper = cv2.resize(paper_region, (new_pw, new_ph))

        # Calculate position to paste
        paste_x = curr_x - new_pw // 2
        paste_y = curr_y - new_ph // 2

        # Ensure we don't go out of bounds
        paste_x = max(0, min(paste_x, w - new_pw))
        paste_y = max(0, min(paste_y, h - new_ph))

        # Darken the background (fading back to normal)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.3 + 0.7 * t, overlay, 0.7 * (1 - t), 0)

        # Paste scaled paper
        frame[paste_y:paste_y+new_ph, paste_x:paste_x+new_pw] = scaled_paper

        frames.append(frame)

    return frames

def main():
    print("Loading image...")
    img = cv2.imread(INPUT_IMAGE)
    if img is None:
        print(f"Error: Could not load image {INPUT_IMAGE}")
        return

    h, w = img.shape[:2]
    print(f"Image dimensions: {w}x{h}")

    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, FPS, (w, h))

    # Add initial frames showing the base image
    print("Adding initial frames...")
    for _ in range(FPS * 2):  # 2 seconds
        out.write(img)

    # Animate each paper
    for i, paper in enumerate(PAPERS):
        print(f"Animating paper {i+1}/3: {paper['name']}...")
        frames = create_zoom_animation(img, paper['bbox'], paper['title'], i)
        for frame in frames:
            out.write(frame)

    # Add final frames showing the base image
    print("Adding final frames...")
    for _ in range(FPS * 2):  # 2 seconds
        out.write(img)

    out.release()
    print(f"Video created successfully: {OUTPUT_VIDEO}")
    print(f"Total duration: ~{(2 + len(PAPERS) * (2 * ANIMATION_DURATION + DISPLAY_DURATION) + 2):.1f} seconds")

if __name__ == "__main__":
    main()
