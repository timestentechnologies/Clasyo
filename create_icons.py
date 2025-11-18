from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, text, filename):
    # Create a new image with a cyan background
    img = Image.new('RGB', (size, size), color=(0, 180, 216))  # Cyan color
    d = ImageDraw.Draw(img)
    
    # Try to load a nice font, fallback to default if not available
    try:
        font_size = size // 3  # Adjusted for "Clasyo" text
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Get text bounding box
    try:
        bbox = d.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = d.textsize(text, font=font)
    
    # Calculate position to center the text
    position = ((size - text_width) // 2, (size - text_height) // 2)
    
    # Draw the text in white
    d.text(position, text, fill=(255, 255, 255), font=font)
    
    # Save the image
    img.save(filename)

# Create images directory if it doesn't exist
os.makedirs('static/images', exist_ok=True)

# Create icons with "Clasyo" text
create_icon(192, "Clasyo", "static/images/icon-192x192.png")
create_icon(512, "Clasyo", "static/images/icon-512x512.png")

print("Icons created successfully with Clasyo text!")