from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


root = Path(__file__).resolve().parents[1]
target = root / "examples" / "demo-paper" / "figures" / "workflow.png"
target.parent.mkdir(parents=True, exist_ok=True)
image = Image.new("RGB", (1200, 360), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.load_default(size=24)
labels = ["Semantic Markdown", "Journal Profile", "DOCX", "Compliance"]
for index, label in enumerate(labels):
    x = 35 + index * 295
    draw.rounded_rectangle((x, 115, x + 230, 235), radius=18, fill="#edf3f8", outline="#24445c", width=4)
    box = draw.textbbox((0, 0), label, font=font)
    draw.text((x + (230 - (box[2] - box[0])) / 2, 165), label, fill="#172b3a", font=font)
    if index < len(labels) - 1:
        draw.line((x + 235, 175, x + 285, 175), fill="#24445c", width=5)
        draw.polygon(((x + 285, 175), (x + 270, 165), (x + 270, 185)), fill="#24445c")
image.save(target)
print(target)
