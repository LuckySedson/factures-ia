import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

output_dir = "data/tests"
os.makedirs(output_dir, exist_ok=True)

print(f"Génération des fichiers de test dans {output_dir}...")

# 1. PDF Propre
pdf_path = os.path.join(output_dir, "facture_propre_001.pdf")
c = canvas.Canvas(pdf_path, pagesize=letter)
c.drawString(100, 750, "FACTURE N° FAC-2026-001")
c.drawString(100, 730, "Fournisseur: Tech Solutions SARL")
c.drawString(100, 710, "Date: 15/11/2026")
c.drawString(100, 670, "Description                          Quantité    Prix Unitaire    Total")
c.drawString(100, 650, "PC Portable Acer Nitro 5                1        3500000 Ar      3500000 Ar")
c.drawString(100, 630, "Souris Gamer RGB                        2         75000 Ar       150000 Ar")
c.drawString(100, 590, "TOTAL HT: 3650000 Ar")
c.drawString(100, 570, "TVA (20%): 730000 Ar")
c.drawString(100, 550, "TOTAL TTC: 4380000 Ar")
c.save()
print(f"-> PDF créé : {pdf_path}")

# 2. Image scannée nette (Format A4 - 150 DPI)
img_path = os.path.join(output_dir, "facture_scan_002.jpg")
img = Image.new('RGB', (1240, 1754), color='white')
d = ImageDraw.Draw(img)

try:
    font_title = ImageFont.truetype("arial.ttf", 40)
    font_body = ImageFont.truetype("arial.ttf", 30)
except IOError:
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()

d.text((100, 100), "FACTURE N° FAC-2026-002", fill='black', font=font_title)
d.text((100, 180), "Fournisseur: Librairie Universitaire", fill='black', font=font_body)
d.text((100, 230), "Date: 16/11/2026", fill='black', font=font_body)

d.text((100, 350), "Description", fill='black', font=font_body)
d.text((900, 350), "Montant", fill='black', font=font_body)
d.line((100, 400, 1140, 400), fill='black', width=3)

d.text((100, 460), "1x Livre Algorithmique Avancée", fill='black', font=font_body)
d.text((900, 460), "45000 Ar", fill='black', font=font_body)

d.text((100, 530), "1x Cahier de notes spiralé", fill='black', font=font_body)
d.text((900, 530), "5000 Ar", fill='black', font=font_body)

d.line((100, 620, 1140, 620), fill='black', width=2)
d.text((750, 680), "TOTAL TTC: 50000 Ar", fill='black', font=font_title)

img.save(img_path)
print(f"-> Image scannée créée : {img_path}")
print("\nGénération terminée avec succès !")