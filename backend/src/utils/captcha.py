"""Captcha generation utility."""

import random
import string
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import uuid


def generate_captcha_text(length: int = 4) -> str:
    """Generate random captcha text.

    Args:
        length: Length of captcha text

    Returns:
        Random captcha string (uppercase letters and digits)
    """
    # Use uppercase letters and digits, exclude confusing characters
    chars = ''.join([
        c for c in (string.ascii_uppercase + string.digits)
        if c not in 'O0I1'  # Exclude confusing characters
    ])
    return ''.join(random.choices(chars, k=length))


def generate_captcha_image(text: str, width: int = 120, height: int = 40) -> bytes:
    """Generate captcha image.

    Args:
        text: Captcha text to render
        width: Image width
        height: Image height

    Returns:
        PNG image bytes
    """
    # Create image with white background
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Try to use a font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        try:
            # Try Linux font path
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except:
            # Use default font as fallback
            font = ImageFont.load_default()

    # Draw background noise lines
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)

    # Draw text with random colors
    text_width = draw.textlength(text, font=font)
    text_x = (width - text_width) / 2

    for i, char in enumerate(text):
        # Random color for each character
        color = (
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 100)
        )

        # Random vertical offset
        y_offset = random.randint(-3, 3)
        char_x = text_x + i * (text_width / len(text))

        draw.text((char_x, 5 + y_offset), char, font=font, fill=color)

    # Add noise points
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(150, 150, 150))

    # Apply slight blur
    image = image.filter(ImageFilter.SMOOTH)

    # Convert to bytes
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def generate_captcha() -> tuple[str, str, bytes]:
    """Generate captcha with unique key, text, and image.

    Returns:
        Tuple of (captcha_key, captcha_text, image_bytes)
    """
    captcha_key = str(uuid.uuid4())
    captcha_text = generate_captcha_text()
    image_bytes = generate_captcha_image(captcha_text)

    return captcha_key, captcha_text, image_bytes


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string.

    Args:
        image_bytes: PNG image bytes

    Returns:
        Base64 encoded string
    """
    return base64.b64encode(image_bytes).decode('utf-8')
