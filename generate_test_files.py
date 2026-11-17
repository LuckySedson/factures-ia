import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

#dossier de test dédié
output_dir = "data/tests"
os.makedirs(output_dir, exist_ok=True)

print(f"Génération des fichiers de test dans {output_dir}...")

# Générer un PDF Propre (Texte natif)
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

# Générer une image de facture (Scan / JPG)
img_path = os.path.join(output_dir, "facture_scan_002.jpg")
img = Image.new('RGB', (900, 1200), color='white')
d = ImageDraw.Draw(img)

# Chargement d'une police système Windows standard (Arial ou Segoe UI)
font_path = "C:/Windows/Fonts/arial.ttf"
try:
    font_title = ImageFont.truetype(font_path, 24)
    font_body = ImageFont.truetype(font_path, 18)
except IOError:
    # Fallback de secours si la police n'est pas trouvée
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()

# Dessiner du texte net et lisible pour Tesseract
d.text((60, 60), "FACTURE N° FAC-2026-002", fill='black', font=font_title)
d.text((60, 110), "Fournisseur: Librairie Universitaire", fill='black', font=font_body)
d.text((60, 140), "Date: 16/11/2026", fill='black', font=font_body)

d.text((60, 220), "Description", fill='black', font=font_body)
d.text((650, 220), "Montant", fill='black', font=font_body)
d.line((60, 250, 840, 250), fill='black', width=2)

d.text((60, 280), "1x Livre Algorithmique Avancée", fill='black', font=font_body)
d.text((650, 280), "45000 Ar", fill='black', font=font_body)

d.text((60, 320), "1x Cahier de notes spiralé", fill='black', font=font_body)
d.text((650, 320), "5000 Ar", fill='black', font=font_body)

d.line((60, 380, 840, 380), fill='black', width=1)
d.text((500, 410), "TOTAL TTC: 50000 Ar", fill='black', font=font_title)

# Sauvegarder l'image
img.save(img_path)
print(f"-> Image scannée créée : {img_path}")

print("\nGénération propre terminée avec succès dans data/tests/ !")