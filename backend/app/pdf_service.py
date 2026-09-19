# -*- coding: utf-8 -*-
"""
Generation de la fiche de decision de credit au format PDF.

A partir d'une analyse enregistree, produit un document PDF propre reprenant
l'identite de la BSIC, les informations du client, la decision, l'explication
et les facteurs determinants. Ce document est destine a l'archivage physique
du dossier de credit.
"""

import os
import io
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader

# Couleurs
INK = colors.HexColor("#1B2A41")
ACCENT = colors.HexColor("#0F6E56")
RED = colors.HexColor("#C0392B")
GRAY = colors.HexColor("#5A6B82")
LIGHTGRAY = colors.HexColor("#DDDDDD")

# Chemin du logo (dans le dossier app/)
CHEMIN_LOGO = os.path.join(os.path.dirname(__file__), "logo_bsic.png")

# Libelles lisibles des variables (pour les facteurs)
LIBELLES = {
    "EXT_SOURCE_1": "Score de solvabilite", "EXT_SOURCE_2": "Score de solvabilite",
    "EXT_SOURCE_3": "Score de solvabilite", "AMT_INCOME_TOTAL": "Revenu",
    "AMT_CREDIT": "Montant du credit", "AMT_ANNUITY": "Montant de l'echeance",
    "AMT_GOODS_PRICE": "Prix du bien finance", "AGE_ANNEES": "Age",
    "ANCIENNETE_EMPLOI_ANNEES": "Anciennete d'emploi",
    "CNT_CHILDREN": "Nombre d'enfants", "CNT_FAM_MEMBERS": "Taille de la famille",
    "EMPLOI_ANORMAL": "Situation d'emploi", "CODE_GENDER": "Genre",
    "NAME_FAMILY_STATUS": "Situation familiale",
    "NAME_EDUCATION_TYPE": "Niveau d'education", "OCCUPATION_TYPE": "Profession",
    "ORGANIZATION_TYPE": "Type d'employeur", "NAME_INCOME_TYPE": "Type de revenu",
    "NAME_CONTRACT_TYPE": "Type de credit",
}


def _libelle(variable: str) -> str:
    for cle, lib in LIBELLES.items():
        if variable.startswith(cle):
            return lib
    return variable


def generer_pdf_decision(analyse, client, agent_nom: str) -> bytes:
    """Genere la fiche de decision en PDF et renvoie les octets du fichier.

    - analyse : l'objet Analyse (de la base)
    - client  : l'objet Client concerne
    - agent_nom : le nom de l'agent qui a realise l'analyse
    """
    tampon = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(tampon, pagesize=A4)

    # --- En-tete avec logo ---
    if os.path.exists(CHEMIN_LOGO):
        logo = ImageReader(CHEMIN_LOGO)
        c.drawImage(logo, W-5*cm, H-3.3*cm, width=3*cm, height=3*cm,
                    mask='auto', preserveAspectRatio=True)

    c.setFillColor(INK); c.setFont("Times-Bold", 15)
    c.drawString(2*cm, H-2.3*cm, "BSIC TCHAD S.A.")
    c.setFont("Times-Roman", 9.5); c.setFillColor(GRAY)
    c.drawString(2*cm, H-2.8*cm,
                 "Banque Sahelo-Saharienne pour l'Investissement et le Commerce")

    c.setStrokeColor(LIGHTGRAY); c.setLineWidth(0.7); c.setDash(1, 2)
    c.line(2*cm, H-3.6*cm, W-2*cm, H-3.6*cm); c.setDash()

    # --- Titre ---
    c.setFillColor(INK); c.setFont("Times-Bold", 16)
    c.drawString(2*cm, H-4.6*cm, "FICHE DE DECISION DE CREDIT")
    c.setFont("Times-Roman", 10); c.setFillColor(GRAY)
    date_str = analyse.date_analyse.strftime("%d/%m/%Y") if analyse.date_analyse else datetime.now().strftime("%d/%m/%Y")
    c.drawString(2*cm, H-5.1*cm,
                 f"Analyse N {analyse.id}   |   Date : {date_str}   |   Agent : {agent_nom}")

    # --- Informations du client ---
    y = H-6.1*cm
    c.setFillColor(INK); c.setFont("Times-Bold", 12)
    c.drawString(2*cm, y, "Informations du client")
    c.setStrokeColor(LIGHTGRAY); c.setDash(1, 2)
    c.line(2*cm, y-0.25*cm, W-2*cm, y-0.25*cm); c.setDash()
    y -= 0.9*cm
    infos = [
        ("Nom", client.nom or "-"),
        ("Genre", client.genre or "-"),
        ("Age", f"{int(client.age)} ans" if client.age else "-"),
        ("Profession", client.profession or "-"),
        ("Situation familiale", client.situation_familiale or "-"),
    ]
    for label, val in infos:
        c.setFillColor(INK); c.setFont("Times-Bold", 10.5); c.drawString(2*cm, y, label + " :")
        c.setFont("Times-Roman", 10.5); c.drawString(6.5*cm, y, str(val))
        y -= 0.6*cm

    # --- Resultat de l'analyse ---
    y -= 0.3*cm
    c.setFillColor(INK); c.setFont("Times-Bold", 12)
    c.drawString(2*cm, y, "Resultat de l'analyse")
    c.setStrokeColor(LIGHTGRAY); c.setDash(1, 2)
    c.line(2*cm, y-0.25*cm, W-2*cm, y-0.25*cm); c.setDash()
    y -= 1.1*cm

    accorde = (analyse.decision == "ACCORDE")
    couleur_dec = ACCENT if accorde else RED
    texte_dec = "DECISION : CREDIT ACCORDE" if accorde else "DECISION : CREDIT REFUSE"

    c.setStrokeColor(couleur_dec); c.setLineWidth(1.5)
    c.roundRect(2*cm, y-1.2*cm, W-4*cm, 1.5*cm, 6, fill=0, stroke=1)
    c.setFillColor(couleur_dec); c.setFont("Times-Bold", 17)
    c.drawString(2.5*cm, y-0.5*cm, texte_dec)
    c.setFillColor(INK); c.setFont("Times-Roman", 10.5)
    proba = analyse.probabilite_defaut * 100
    c.drawString(2.5*cm, y-1*cm,
                 f"Probabilite de defaut : {proba:.1f} %      Classe de risque : {analyse.classe_risque}")
    y -= 2*cm

    # --- Explication ---
    c.setFillColor(INK); c.setFont("Times-Bold", 12)
    c.drawString(2*cm, y, "Explication")
    c.setStrokeColor(LIGHTGRAY); c.setDash(1, 2)
    c.line(2*cm, y-0.25*cm, W-2*cm, y-0.25*cm); c.setDash()
    y -= 0.7*cm
    styles = getSampleStyleSheet()
    style_e = ParagraphStyle('e', parent=styles['Normal'], fontName='Times-Roman',
                             fontSize=10, leading=15, textColor=INK, alignment=4)
    texte_expl = analyse.explication or "Explication non disponible."
    p = Paragraph(texte_expl, style_e)
    fw, fh = p.wrap(W-4*cm, 5*cm)
    p.drawOn(c, 2*cm, y-fh)
    y -= fh + 0.6*cm

    # --- Facteurs determinants ---
    c.setFillColor(INK); c.setFont("Times-Bold", 12)
    c.drawString(2*cm, y, "Facteurs determinants")
    c.setStrokeColor(LIGHTGRAY); c.setDash(1, 2)
    c.line(2*cm, y-0.25*cm, W-2*cm, y-0.25*cm); c.setDash()
    y -= 0.8*cm
    if analyse.facteurs_explicatifs:
        facteurs = json.loads(analyse.facteurs_explicatifs)
        for f in facteurs[:5]:
            favorable = f["contribution"] < 0
            col = ACCENT if favorable else RED
            effet = "Favorable" if favorable else "Facteur de risque"
            c.setFillColor(col); c.circle(2.2*cm, y+0.08*cm, 0.07*cm, fill=1)
            c.setFillColor(INK); c.setFont("Times-Roman", 10.5)
            c.drawString(2.5*cm, y, _libelle(f["variable"]))
            c.setFillColor(col); c.drawString(10*cm, y, effet)
            y -= 0.55*cm

    # --- Signatures ---
    y -= 1.2*cm
    if y < 3*cm:  # securite si le contenu est long
        y = 3.5*cm
    c.setStrokeColor(GRAY); c.setLineWidth(0.5)
    c.line(2.5*cm, y, 7.5*cm, y); c.line(W-7.5*cm, y, W-2.5*cm, y)
    c.setFillColor(GRAY); c.setFont("Times-Italic", 9.5)
    c.drawCentredString(5*cm, y-0.5*cm, "Signature de l'agent")
    c.drawCentredString(W-5*cm, y-0.5*cm, "Signature du responsable")

    # --- Pied de page ---
    c.setStrokeColor(LIGHTGRAY); c.setDash(1, 2)
    c.line(2*cm, 2*cm, W-2*cm, 2*cm); c.setDash()
    c.setFont("Times-Italic", 8); c.setFillColor(GRAY)
    c.drawCentredString(W/2, 1.5*cm,
                        "Document genere par CREDISCORE  -  A titre d'aide a la decision")

    c.save()
    tampon.seek(0)
    return tampon.read()