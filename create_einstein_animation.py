#!/usr/bin/env python3
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import random

# Configuration
INPUT_IMAGE = "e0302fc6-22ab-4e90-a879-4a684f931366.jpg"
OUTPUT_VIDEO = "einstein_papers_animation.mp4"
FPS = 30
PULL_OUT_DURATION = 2.0  # seconds for paper to come out
DISPLAY_DURATION = 2.5   # seconds to display
RETURN_DURATION = 1.5    # seconds to return

FRAMES_PULL_OUT = int(FPS * PULL_OUT_DURATION)
FRAMES_DISPLAY = int(FPS * DISPLAY_DURATION)
FRAMES_RETURN = int(FPS * RETURN_DURATION)

# Paper definitions
PAPERS = [
    {
        "name": "left",
        "title": "On the Electrodynamics\nof Moving Bodies",
        "bbox": (45, 275, 280, 215),
    },
    {
        "name": "right",
        "title": "On a Heuristic Viewpoint Concerning\nthe Production and Transformation of Light",
        "bbox": (665, 275, 305, 215),
    },
    {
        "name": "middle",
        "title": "Does the Inertia of a Body\nDepend Upon Its Energy Content?",
        "bbox": (345, 275, 310, 215),
    }
]

class Particle:
    def __init__(self, x, y, vx, vy, size, color, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.lifetime = lifetime
        self.age = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05  # gravity
        self.age += 1

    def is_alive(self):
        return self.age < self.lifetime

    def draw(self, frame):
        alpha = 1.0 - (self.age / self.lifetime)
        color = tuple([int(c * alpha) for c in self.color])
        cv2.circle(frame, (int(self.x), int(self.y)), int(self.size), color, -1)

class ParticleSystem:
    def __init__(self, img_shape):
        self.particles = []
        self.img_h, self.img_w = img_shape[:2]

    def add_ambient_particles(self, count=5):
        """Add floating ambient particles"""
        for _ in range(count):
            x = random.randint(0, self.img_w)
            y = random.randint(0, self.img_h)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-0.8, 0.2)
            size = random.uniform(1, 3)
            color = (200, 180, 100)  # Golden color
            lifetime = random.randint(60, 120)
            self.particles.append(Particle(x, y, vx, vy, size, color, lifetime))

    def add_sparkle(self, x, y):
        """Add sparkle effect at position"""
        for _ in range(10):
            angle = random.uniform(0, 2 * np.pi)
            speed = random.uniform(1, 3)
            vx = np.cos(angle) * speed
            vy = np.sin(angle) * speed
            size = random.uniform(1, 2)
            color = (255, 255, 200)
            lifetime = random.randint(15, 30)
            self.particles.append(Particle(x, y, vx, vy, size, color, lifetime))

    def update(self):
        """Update all particles"""
        self.particles = [p for p in self.particles if p.is_alive()]
        for p in self.particles:
            p.update()

    def draw(self, frame):
        """Draw all particles"""
        for p in self.particles:
            p.draw(frame)

def ease_in_out(t):
    """Smooth easing function"""
    return t * t * (3 - 2 * t)

def add_glow_effect(frame, intensity=0.3):
    """Add glowing effect to frame"""
    blurred = cv2.GaussianBlur(frame, (15, 15), 0)
    return cv2.addWeighted(frame, 1.0, blurred, intensity, 0)

def add_text_overlay(frame, text):
    """Add text overlay with nice styling"""
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img, 'RGBA')

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
    except:
        font = ImageFont.load_default()

    lines = text.split('\n')
    line_heights = []
    line_widths = []

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    max_width = max(line_widths)
    total_height = sum(line_heights) + (len(lines) - 1) * 12

    x = (frame.shape[1] - max_width) // 2
    y = frame.shape[0] - total_height - 100

    padding = 35
    bg_rect = [x - padding, y - padding,
               x + max_width + padding, y + total_height + padding]

    # Draw glowing background
    draw.rectangle(bg_rect, fill=(30, 25, 20, 230))
    draw.rectangle([r + 3 for r in bg_rect], outline=(150, 120, 50, 200), width=4)
    draw.rectangle(bg_rect, outline=(220, 180, 80, 255), width=2)

    current_y = y
    for i, line in enumerate(lines):
        line_x = x + (max_width - line_widths[i]) // 2
        # Draw shadow
        draw.text((line_x + 2, current_y + 2), line, font=font, fill=(0, 0, 0, 180))
        # Draw text
        draw.text((line_x, current_y), line, font=font, fill=(255, 230, 120, 255))
        current_y += line_heights[i] + 12

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def extract_paper_region(img, bbox):
    """Extract paper region"""
    x, y, w, h = bbox
    return img[y:y+h, x:x+w].copy()

def create_3d_perspective_paper(paper, progress, coming_out=True):
    """
    Create 3D perspective effect - paper coming OUT toward viewer
    progress: 0 to 1 (0 = flat on surface, 1 = fully out toward viewer)
    """
    h, w = paper.shape[:2]

    if coming_out:
        t = progress
    else:
        t = 1 - progress

    # Scale factor - paper gets bigger as it comes toward viewer
    scale = 1.0 + t * 1.8

    # Calculate new size
    new_w = int(w * scale)
    new_h = int(h * scale)

    # Perspective warp parameters
    # Create trapezoid effect (bottom wider than top when coming out)
    perspective_factor = t * 0.15

    src_points = np.float32([
        [0, 0],
        [w, 0],
        [w, h],
        [0, h]
    ])

    # Destination points for perspective (paper tilting toward viewer)
    offset_x = int(new_w * perspective_factor)
    offset_y = int(new_h * perspective_factor * 0.3)

    dst_points = np.float32([
        [offset_x, offset_y],
        [new_w - offset_x, offset_y],
        [new_w, new_h],
        [0, new_h]
    ])

    # Get perspective transform matrix
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)

    # Apply perspective warp
    warped = cv2.warpPerspective(paper, matrix, (new_w, new_h),
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(0, 0, 0))

    # Add shadow for depth
    shadow = np.zeros((new_h + 20, new_w + 20, 3), dtype=np.uint8)
    shadow_alpha = int(t * 150)
    cv2.rectangle(shadow, (10, 10), (new_w + 10, new_h + 10),
                  (0, 0, 0), -1)
    shadow = cv2.GaussianBlur(shadow, (31, 31), 0)

    return warped, shadow, (new_w, new_h)

def composite_with_shadow(frame, paper, shadow, position):
    """Composite paper with shadow onto frame"""
    h, w = frame.shape[:2]
    px, py = position

    # Composite shadow first
    sh, sw = shadow.shape[:2]
    sx1 = max(0, px - sw // 2)
    sy1 = max(0, py - sh // 2)
    sx2 = min(w, sx1 + sw)
    sy2 = min(h, sy1 + sh)

    if sx2 > sx1 and sy2 > sy1:
        shadow_region = shadow[0:sy2-sy1, 0:sx2-sx1]
        shadow_mask = shadow_region.astype(float) / 255.0
        frame[sy1:sy2, sx1:sx2] = (
            frame[sy1:sy2, sx1:sx2] * (1 - shadow_mask * 0.5) +
            shadow_region * shadow_mask * 0.5
        ).astype(np.uint8)

    # Composite paper
    ph, pw = paper.shape[:2]
    px1 = max(0, px - pw // 2)
    py1 = max(0, py - ph // 2)
    px2 = min(w, px1 + pw)
    py2 = min(h, py1 + ph)

    if px2 > px1 and py2 > py1:
        # Create mask for paper (non-black pixels)
        gray = cv2.cvtColor(paper, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        paper_region = paper[0:py2-py1, 0:px2-px1]
        mask_region = mask[0:py2-py1, 0:px2-px1]
        mask_3ch = cv2.cvtColor(mask_region, cv2.COLOR_GRAY2BGR).astype(float) / 255.0

        frame[py1:py2, px1:px2] = (
            paper_region * mask_3ch +
            frame[py1:py2, px1:px2] * (1 - mask_3ch)
        ).astype(np.uint8)

    return frame

def animate_paper(base_img, paper_info, particle_system):
    """Animate paper coming out, displaying, and returning"""
    frames = []
    bbox = paper_info['bbox']
    x, y, w, h = bbox
    title = paper_info['title']

    # Extract paper
    paper = extract_paper_region(base_img, bbox)

    # Original position (center of paper)
    orig_x = x + w // 2
    orig_y = y + h // 2

    # Target position (center of frame)
    frame_h, frame_w = base_img.shape[:2]
    target_x = frame_w // 2
    target_y = frame_h // 2 - 50  # Slightly higher

    # PHASE 1: Paper comes OUT toward viewer
    for i in range(FRAMES_PULL_OUT):
        t = ease_in_out(i / FRAMES_PULL_OUT)

        # Create base frame with particles
        frame = base_img.copy()
        particle_system.add_ambient_particles(2)

        if i % 10 == 0:  # Add sparkles occasionally
            spark_x = random.randint(orig_x - 50, orig_x + 50)
            spark_y = random.randint(orig_y - 50, orig_y + 50)
            particle_system.add_sparkle(spark_x, spark_y)

        particle_system.update()
        particle_system.draw(frame)

        # Darken background
        overlay = np.zeros_like(frame)
        frame = cv2.addWeighted(frame, 1 - t * 0.6, overlay, t * 0.6, 0)

        # Darken original paper position
        frame[y:y+h, x:x+w] = (frame[y:y+h, x:x+w] * (1 - t * 0.8)).astype(np.uint8)

        # Create 3D paper coming out
        warped_paper, shadow, (pw, ph) = create_3d_perspective_paper(paper, t, coming_out=True)

        # Interpolate position
        curr_x = int(orig_x + (target_x - orig_x) * t)
        curr_y = int(orig_y + (target_y - orig_y) * t)

        # Composite paper with shadow
        frame = composite_with_shadow(frame, warped_paper, shadow, (curr_x, curr_y))

        # Add glow effect
        frame = add_glow_effect(frame, 0.1 + t * 0.2)

        frames.append(frame)

    # PHASE 2: Display with text
    for i in range(FRAMES_DISPLAY):
        frame = base_img.copy()
        particle_system.add_ambient_particles(3)
        particle_system.update()
        particle_system.draw(frame)

        # Darken background
        overlay = np.zeros_like(frame)
        frame = cv2.addWeighted(frame, 0.4, overlay, 0.6, 0)
        frame[y:y+h, x:x+w] = (frame[y:y+h, x:x+w] * 0.2).astype(np.uint8)

        # Paper fully out
        warped_paper, shadow, _ = create_3d_perspective_paper(paper, 1.0, coming_out=True)
        frame = composite_with_shadow(frame, warped_paper, shadow, (target_x, target_y))

        # Add text
        frame = add_text_overlay(frame, title)
        frame = add_glow_effect(frame, 0.3)

        frames.append(frame)

    # PHASE 3: Return
    for i in range(FRAMES_RETURN):
        t = ease_in_out(i / FRAMES_RETURN)

        frame = base_img.copy()
        particle_system.add_ambient_particles(2)
        particle_system.update()
        particle_system.draw(frame)

        # Lighten background
        overlay = np.zeros_like(frame)
        frame = cv2.addWeighted(frame, 0.4 + t * 0.6, overlay, 0.6 - t * 0.6, 0)
        frame[y:y+h, x:x+w] = (frame[y:y+h, x:x+w] * (0.2 + t * 0.8)).astype(np.uint8)

        # Paper going back
        warped_paper, shadow, _ = create_3d_perspective_paper(paper, 1.0 - t, coming_out=True)

        # Interpolate position back
        curr_x = int(target_x + (orig_x - target_x) * t)
        curr_y = int(target_y + (orig_y - target_y) * t)

        frame = composite_with_shadow(frame, warped_paper, shadow, (curr_x, curr_y))
        frame = add_glow_effect(frame, 0.3 - t * 0.2)

        frames.append(frame)

    return frames

def main():
    print("Loading image...")
    img = cv2.imread(INPUT_IMAGE)
    if img is None:
        print(f"Error: Could not load {INPUT_IMAGE}")
        return

    h, w = img.shape[:2]
    print(f"Image dimensions: {w}x{h}")

    # Initialize particle system
    particle_system = ParticleSystem(img.shape)

    # Video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, FPS, (w, h))

    # Initial frames with animated background
    print("Adding animated intro (2 seconds)...")
    for i in range(FPS * 2):
        frame = img.copy()
        particle_system.add_ambient_particles(3)
        particle_system.update()
        particle_system.draw(frame)
        frame = add_glow_effect(frame, 0.1)
        out.write(frame)

    # Animate each paper
    for idx in [0, 1, 2]:  # left, right, middle
        paper = PAPERS[idx]
        print(f"Animating {paper['name']} paper...")
        frames = animate_paper(img, paper, particle_system)
        print(f"  Generated {len(frames)} frames")
        for frame in frames:
            out.write(frame)

    # Final animated frames
    print("Adding animated outro (2 seconds)...")
    for i in range(FPS * 2):
        frame = img.copy()
        particle_system.add_ambient_particles(3)
        particle_system.update()
        particle_system.draw(frame)
        frame = add_glow_effect(frame, 0.1)
        out.write(frame)

    out.release()

    total_duration = 4 + len(PAPERS) * (PULL_OUT_DURATION + DISPLAY_DURATION + RETURN_DURATION)
    print(f"\n✓ Fully animated video created: {OUTPUT_VIDEO}")
    print(f"✓ Duration: ~{total_duration:.1f} seconds")
    print(f"✓ Resolution: {w}x{h} @ {FPS}fps")

if __name__ == "__main__":
    main()
