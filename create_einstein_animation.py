#!/usr/bin/env python3
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
INPUT_IMAGE = "e0302fc6-22ab-4e90-a879-4a684f931366.jpg"
OUTPUT_VIDEO = "einstein_papers_animation.mp4"
FPS = 30
MOVE_DURATION = 1.5  # seconds for paper to move to center
DISPLAY_DURATION = 2.5  # seconds to display in center
RETURN_DURATION = 1.5  # seconds to return to position

FRAMES_MOVE = int(FPS * MOVE_DURATION)
FRAMES_DISPLAY = int(FPS * DISPLAY_DURATION)
FRAMES_RETURN = int(FPS * RETURN_DURATION)

# Paper definitions with more precise coordinates
# Format: (x, y, width, height, title)
PAPERS = [
    {
        "name": "left",
        "title": "On the Electrodynamics\nof Moving Bodies",
        "bbox": (45, 275, 280, 215),  # x, y, width, height
        "center_offset": (140, 360)  # center point of paper in original position
    },
    {
        "name": "right",
        "title": "On a Heuristic Viewpoint Concerning\nthe Production and Transformation of Light",
        "bbox": (665, 275, 305, 215),
        "center_offset": (815, 360)
    },
    {
        "name": "middle",
        "title": "Does the Inertia of a Body\nDepend Upon Its Energy Content?",
        "bbox": (345, 275, 310, 215),
        "center_offset": (500, 360)
    }
]

def ease_in_out(t):
    """Smooth easing function"""
    return t * t * (3 - 2 * t)

def add_text_overlay(frame, text):
    """Add text overlay to frame with better formatting"""
    # Convert to PIL Image for better text rendering
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img, 'RGBA')

    # Try to use a nice font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 48)
        except:
            font = ImageFont.load_default()

    # Calculate text bounding box
    lines = text.split('\n')
    line_heights = []
    line_widths = []

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    max_width = max(line_widths)
    total_height = sum(line_heights) + (len(lines) - 1) * 10  # 10px spacing

    # Position at bottom center
    x = (frame.shape[1] - max_width) // 2
    y = frame.shape[0] - total_height - 80

    # Draw semi-transparent background
    padding = 30
    bg_rect = [x - padding, y - padding,
               x + max_width + padding, y + total_height + padding]
    draw.rectangle(bg_rect, fill=(20, 20, 20, 220))

    # Draw border
    draw.rectangle(bg_rect, outline=(200, 150, 50, 255), width=3)

    # Draw text lines
    current_y = y
    for i, line in enumerate(lines):
        line_x = x + (max_width - line_widths[i]) // 2  # Center each line
        draw.text((line_x, current_y), line, font=font, fill=(255, 220, 100, 255))
        current_y += line_heights[i] + 10

    # Convert back to OpenCV format
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def extract_paper_with_mask(img, bbox):
    """Extract paper region and create a simple mask"""
    x, y, w, h = bbox

    # Extract the paper region
    paper = img[y:y+h, x:x+w].copy()

    # Create a mask (simple rectangle for now, but with soft edges)
    mask = np.ones((h, w), dtype=np.uint8) * 255

    # Feather the edges slightly
    feather = 5
    mask[:feather, :] = np.linspace(0, 255, feather)[:, np.newaxis]
    mask[-feather:, :] = np.linspace(255, 0, feather)[:, np.newaxis]
    mask[:, :feather] = np.minimum(mask[:, :feather], np.linspace(0, 255, feather)[np.newaxis, :])
    mask[:, -feather:] = np.minimum(mask[:, -feather:], np.linspace(255, 0, feather)[np.newaxis, :])

    return paper, mask

def create_background_without_paper(img, bbox):
    """Create background with paper region darkened/blurred"""
    bg = img.copy()
    x, y, w, h = bbox

    # Darken the paper region
    bg[y:y+h, x:x+w] = (bg[y:y+h, x:x+w] * 0.3).astype(np.uint8)

    # Blur it slightly
    bg[y:y+h, x:x+w] = cv2.GaussianBlur(bg[y:y+h, x:x+w], (21, 21), 0)

    return bg

def composite_paper_on_frame(frame, paper, mask, position, scale=1.0, rotation=0):
    """Composite paper onto frame at given position with scale and rotation"""
    h, w = paper.shape[:2]

    # Scale the paper
    new_w = int(w * scale)
    new_h = int(h * scale)

    if new_w <= 0 or new_h <= 0:
        return frame

    scaled_paper = cv2.resize(paper, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    scaled_mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Apply rotation if needed
    if rotation != 0:
        center = (new_w // 2, new_h // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, rotation, 1.0)
        scaled_paper = cv2.warpAffine(scaled_paper, rot_matrix, (new_w, new_h),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        scaled_mask = cv2.warpAffine(scaled_mask, rot_matrix, (new_w, new_h),
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    # Calculate paste position (position is the center point)
    paste_x = int(position[0] - new_w // 2)
    paste_y = int(position[1] - new_h // 2)

    # Ensure we don't go out of bounds
    frame_h, frame_w = frame.shape[:2]

    # Calculate valid region
    src_x1 = max(0, -paste_x)
    src_y1 = max(0, -paste_y)
    src_x2 = min(new_w, frame_w - paste_x)
    src_y2 = min(new_h, frame_h - paste_y)

    dst_x1 = max(0, paste_x)
    dst_y1 = max(0, paste_y)
    dst_x2 = min(frame_w, paste_x + new_w)
    dst_y2 = min(frame_h, paste_y + new_h)

    if src_x2 <= src_x1 or src_y2 <= src_y1:
        return frame

    # Extract regions
    paper_region = scaled_paper[src_y1:src_y2, src_x1:src_x2]
    mask_region = scaled_mask[src_y1:src_y2, src_x1:src_x2]

    # Normalize mask
    mask_3ch = cv2.cvtColor(mask_region, cv2.COLOR_GRAY2BGR) / 255.0

    # Composite
    bg_region = frame[dst_y1:dst_y2, dst_x1:dst_x2]
    blended = (paper_region * mask_3ch + bg_region * (1 - mask_3ch)).astype(np.uint8)

    # Paste back
    result = frame.copy()
    result[dst_y1:dst_y2, dst_x1:dst_x2] = blended

    return result

def animate_paper(base_img, paper_info):
    """Create animation for one paper moving to center and back"""
    frames = []

    bbox = paper_info['bbox']
    x, y, w, h = bbox
    title = paper_info['title']

    # Extract paper and create mask
    paper, mask = extract_paper_with_mask(base_img, bbox)

    # Create background without this paper
    bg_without_paper = create_background_without_paper(base_img, bbox)

    # Original center position of paper
    orig_center = (x + w // 2, y + h // 2)

    # Target center position (center of frame)
    frame_h, frame_w = base_img.shape[:2]
    target_center = (frame_w // 2, frame_h // 2)

    # Scaling parameters
    original_scale = 1.0
    target_scale = 2.5  # Make it bigger when centered

    # === PHASE 1: Move to center ===
    for i in range(FRAMES_MOVE):
        t = ease_in_out(i / FRAMES_MOVE)

        # Interpolate position
        curr_x = orig_center[0] + (target_center[0] - orig_center[0]) * t
        curr_y = orig_center[1] + (target_center[1] - orig_center[1]) * t

        # Interpolate scale
        curr_scale = original_scale + (target_scale - original_scale) * t

        # Add slight rotation for effect
        curr_rotation = 0  # Can add rotation: np.sin(t * np.pi) * 5

        # Darken background progressively
        frame = cv2.addWeighted(base_img, 1 - t * 0.7, bg_without_paper, t * 0.7, 0)

        # Composite paper at current position
        frame = composite_paper_on_frame(frame, paper, mask, (curr_x, curr_y),
                                         curr_scale, curr_rotation)

        frames.append(frame)

    # === PHASE 2: Display in center ===
    for i in range(FRAMES_DISPLAY):
        # Fully darkened background
        frame = cv2.addWeighted(base_img, 0.3, bg_without_paper, 0.7, 0)

        # Paper at center, full scale
        frame = composite_paper_on_frame(frame, paper, mask, target_center, target_scale, 0)

        # Add text overlay
        frame = add_text_overlay(frame, title)

        frames.append(frame)

    # === PHASE 3: Return to original position ===
    for i in range(FRAMES_RETURN):
        t = ease_in_out(i / FRAMES_RETURN)

        # Interpolate position (reverse)
        curr_x = target_center[0] + (orig_center[0] - target_center[0]) * t
        curr_y = target_center[1] + (orig_center[1] - target_center[1]) * t

        # Interpolate scale (reverse)
        curr_scale = target_scale + (original_scale - target_scale) * t

        # Lighten background progressively
        frame = cv2.addWeighted(base_img, 0.3 + t * 0.7, bg_without_paper, 0.7 - t * 0.7, 0)

        # Composite paper
        frame = composite_paper_on_frame(frame, paper, mask, (curr_x, curr_y), curr_scale, 0)

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
    print("Adding initial frames (2 seconds)...")
    for _ in range(FPS * 2):
        out.write(img)

    # Animate each paper
    paper_order = [0, 1, 2]  # left, right, middle
    for idx in paper_order:
        paper = PAPERS[idx]
        print(f"Animating {paper['name']} paper: {paper['title'].split()[0]}...")
        frames = animate_paper(img, paper)
        print(f"  Generated {len(frames)} frames")
        for frame in frames:
            out.write(frame)

    # Add final frames showing the base image
    print("Adding final frames (2 seconds)...")
    for _ in range(FPS * 2):
        out.write(img)

    out.release()

    total_duration = 4 + len(PAPERS) * (MOVE_DURATION + DISPLAY_DURATION + RETURN_DURATION)
    print(f"\n✓ Video created successfully: {OUTPUT_VIDEO}")
    print(f"✓ Total duration: ~{total_duration:.1f} seconds")
    print(f"✓ Resolution: {w}x{h}")
    print(f"✓ Frame rate: {FPS} fps")

if __name__ == "__main__":
    main()
