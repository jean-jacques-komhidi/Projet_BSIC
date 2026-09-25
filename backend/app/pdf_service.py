# -*- coding: utf-8 -*-
"""
Generation de la fiche de decision de credit au format PDF (version enrichie).

A partir d'une analyse enregistree, produit un document PDF professionnel :
identite BSIC, reference du dossier, informations du client ET caracteristiques
du credit, decision avec jauge de risque, motivation, facteurs determinants,
conditions/recommandations, signatures et pied de page reglementaire.
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Couleurs ---
INK = colors.HexColor("#1B2A41")
BLEU = colors.HexColor("#2E86C1")
VERT = colors.HexColor("#0F6E56")
ROUGE = colors.HexColor("#C0392B")
ORANGE = colors.HexColor("#D97706")
GRAY = colors.HexColor("#5A6B82")
LIGHTGRAY = colors.HexColor("#DDDDDD")
FONDCLAIR = colors.HexColor("#F7F8FA")

CHEMIN_LOGO = os.path.join(os.path.dirname(__file__), "logo_bsic.png")

# --- Polices avec accents (DejaVu si disponible, sinon Helvetica) ---
# On cherche la police a plusieurs emplacements (Linux et Windows)
_CHEMINS_POLICE = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
]
_CHEMINS_POLICE_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
]

def _enregistrer_polices():
    """Enregistre une police gerant les accents. Renvoie (normale, grasse)."""
    normale, grasse = "Helvetica", "Helvetica-Bold"
    for chemin in _CHEMINS_POLICE:
        if os.path.exists(chemin):
            try:
                pdfmetrics.registerFont(TTFont("Police", chemin))
                normale = "Police"
                break
            except Exception:
                pass
    for chemin in _CHEMINS_POLICE_BOLD:
        if os.path.exists(chemin):
            try:
                pdfmetrics.registerFont(TTFont("Police-Bold", chemin))
                grasse = "Police-Bold"
                break
            except Exception:
                pass
    return normale, grasse

FONT, FONT_B = _enregistrer_polices()

# Libelles lisibles des variables (facteurs)
LIBELLES = {
    "EXT_SOURCE_1": "Score de solvabilite externe", "EXT_SOURCE_2": "Score de solvabilite externe",
    "EXT_SOURCE_3": "Score de solvabilite externe", "AMT_INCOME_TOTAL": "Revenu",
    "AMT_CREDIT": "Montant du credit", "AMT_ANNUITY": "Montant de l'echeance",
    "AMT_GOODS_PRICE": "Prix du bien finance", "AGE_ANNEES": "Age",
    "ANCIENNETE_EMPLOI_ANNEES": "Anciennete d'emploi", "CNT_CHILDREN": "Nombre d'enfants",
    "CNT_FAM_MEMBERS": "Taille de la famille", "CODE_GENDER": "Genre",
    "NAME_FAMILY_STATUS": "Situation familiale", "NAME_EDUCATION_TYPE": "Niveau d'education",
    "OCCUPATION_TYPE": "Profession", "ORGANIZATION_TYPE": "Type d'employeur",
    "NAME_INCOME_TYPE": "Type de revenu", "NAME_CONTRACT_TYPE": "Type de credit",
}

TYPES_CREDIT = {
    "Cash loans": "Credit tresorerie", "Revolving loans": "Credit renouvelable",
}


def _libelle(variable: str) -> str:
    for cle, lib in LIBELLES.items():
        if variable.startswith(cle):
            return lib
    return variable


def _fmt_fcfa(valeur):
    """Formate un montant en FCFA avec separateurs de milliers."""
    try:
        return f"{int(float(valeur)):,}".replace(",", " ") + " FCFA"
    except Exception:
        return "-"


def generer_pdf_decision(analyse, client, agent_nom: str) -> bytes:
    """Genere la fiche de decision enrichie en PDF et renvoie les octets."""
    tampon = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(tampon, pagesize=A4)

    accorde = (analyse.decision == "ACCORDE")
    couleur_dec = VERT if accorde else ROUGE

    # Donnees du dossier (JSON stocke)
    dossier = {}
    if analyse.donnees_dossier:
        try:
            dossier = json.loads(analyse.donnees_dossier)
        except Exception:
            dossier = {}

    # === EN-TETE ===
    if os.path.exists(CHEMIN_LOGO):
        c.drawImage(ImageReader(CHEMIN_LOGO), W-5.2*cm, H-3.1*cm, width=2.8*cm, height=2.8*cm,
                    mask='auto', preserveAspectRatio=True)
    c.setFillColor(INK); c.setFont(FONT_B, 17)
    c.drawString(2*cm, H-2.2*cm, "BSIC TCHAD S.A.")
    c.setFont(FONT, 9.5); c.setFillColor(GRAY)
    c.drawString(2*cm, H-2.7*cm, "Banque Sahelo-Saharienne pour l'Investissement et le Commerce")
    c.setStrokeColor(BLEU); c.setLineWidth(2.5)
    c.line(2*cm, H-3.1*cm, W-2*cm, H-3.1*cm)

    # === TITRE + REFERENCE ===
    c.setFillColor(INK); c.setFont(FONT_B, 17)
    c.drawString(2*cm, H-4.1*cm, "FICHE DE DECISION DE CREDIT")
    c.setFillColor(FONDCLAIR)
    c.roundRect(W-6.8*cm, H-4.5*cm, 4.8*cm, 1*cm, 4, fill=1, stroke=0)
    c.setFillColor(GRAY); c.setFont(FONT, 8)
    c.drawString(W-6.5*cm, H-3.95*cm, "REFERENCE DOSSIER")
    annee = analyse.date_analyse.year if analyse.date_analyse else datetime.now().year
    reference = f"CRED-{annee}-{analyse.id:04d}"
    c.setFillColor(BLEU); c.setFont(FONT_B, 12)
    c.drawString(W-6.5*cm, H-4.4*cm, reference)
    date_str = analyse.date_analyse.strftime("%d/%m/%Y a %H:%M") if analyse.date_analyse else datetime.now().strftime("%d/%m/%Y")
    c.setFillColor(GRAY); c.setFont(FONT, 9)
    c.drawString(2*cm, H-4.6*cm, f"Emise le {date_str}   -   Agent : {agent_nom}")

    # === CLIENT + CREDIT (deux colonnes) ===
    y = H-5.6*cm
    col_w = (W - 4*cm - 0.8*cm) / 2

    def section_titre(x, yy, texte, couleur):
        c.setFillColor(couleur); c.setFont(FONT_B, 11)
        c.drawString(x, yy, texte)
        c.setStrokeColor(couleur); c.setLineWidth(1.2)
        c.line(x, yy-0.2*cm, x+col_w, yy-0.2*cm)

    # Client
    section_titre(2*cm, y, "INFORMATIONS DU CLIENT", BLEU)
    genre_lisible = "Feminin" if client and client.genre == "F" else "Masculin" if client and client.genre == "M" else "-"
    infos_client = [
        ("Nom", client.nom if client else "-"),
        ("Genre", genre_lisible),
        ("Age", f"{int(client.age)} ans" if client and client.age else "-"),
        ("Profession", client.profession if client and client.profession else "-"),
        ("Situation familiale", client.situation_familiale if client and client.situation_familiale else "-"),
    ]
    yy = y - 0.75*cm
    for label, val in infos_client:
        c.setFillColor(GRAY); c.setFont(FONT, 9.5); c.drawString(2*cm, yy, label)
        c.setFillColor(INK); c.setFont(FONT_B, 9.5); c.drawString(2*cm+3.4*cm, yy, str(val))
        yy -= 0.62*cm

    # Credit
    x2 = 2*cm + col_w + 0.8*cm
    section_titre(x2, y, "CARACTERISTIQUES DU CREDIT", VERT)
    type_credit = dossier.get("NAME_CONTRACT_TYPE", "")
    type_lisible = TYPES_CREDIT.get(type_credit, type_credit or "-")
    infos_credit = [
        ("Type de credit", type_lisible),
        ("Montant demande", _fmt_fcfa(dossier.get("AMT_CREDIT"))),
        ("Echeance mensuelle", _fmt_fcfa(dossier.get("AMT_ANNUITY"))),
        ("Prix du bien", _fmt_fcfa(dossier.get("AMT_GOODS_PRICE"))),
        ("Revenu mensuel", _fmt_fcfa(dossier.get("AMT_INCOME_TOTAL"))),
    ]
    yy = y - 0.75*cm
    for label, val in infos_credit:
        c.setFillColor(GRAY); c.setFont(FONT, 9.5); c.drawString(x2, yy, label)
        c.setFillColor(INK); c.setFont(FONT_B, 9.5); c.drawString(x2+3.6*cm, yy, str(val))
        yy -= 0.62*cm

    # === DECISION + JAUGE ===
    y = yy - 0.5*cm
    texte_dec = "DECISION : CREDIT ACCORDE" if accorde else "DECISION : CREDIT REFUSE"
    c.setStrokeColor(couleur_dec); c.setLineWidth(2)
    c.roundRect(2*cm, y-2*cm, W-4*cm, 2.2*cm, 7, fill=0, stroke=1)
    c.setFillColor(couleur_dec); c.setFont(FONT_B, 17)
    c.drawString(2.5*cm, y-0.8*cm, texte_dec)
    c.setFillColor(INK); c.setFont(FONT, 10)
    classe = (analyse.classe_risque or "").upper()
    c.drawString(2.5*cm, y-1.4*cm, f"Classe de risque : {classe}")
    version_modele = "Gradient Boosting"
    if analyse.version_modele:
        version_modele = analyse.version_modele.algorithme
    c.drawString(2.5*cm, y-1.8*cm, f"Modele : {version_modele}")

    # Jauge (positionnee pour rester dans l'encadre)
    proba = analyse.probabilite_defaut
    pct_x = W - 3.2*cm
    jw = 3.8*cm
    jx = pct_x - jw - 0.3*cm
    jy = y - 1.5*cm
    c.setFillColor(GRAY); c.setFont(FONT, 9)
    c.drawString(jx, jy+0.75*cm, "Probabilite de defaut")
    c.setFillColor(LIGHTGRAY); c.roundRect(jx, jy+0.1*cm, jw, 0.35*cm, 2, fill=1, stroke=0)
    c.setFillColor(couleur_dec); c.roundRect(jx, jy+0.1*cm, jw*proba, 0.35*cm, 2, fill=1, stroke=0)
    c.setFillColor(couleur_dec); c.setFont(FONT_B, 15)
    c.drawString(pct_x, jy+0.08*cm, f"{round(proba*100)}%")

    # === MOTIVATION ===
    y = y - 2.7*cm
    c.setFillColor(BLEU); c.setFont(FONT_B, 11)
    c.drawString(2*cm, y, "MOTIVATION DE LA DECISION")
    c.setStrokeColor(LIGHTGRAY); c.setLineWidth(0.6); c.line(2*cm, y-0.2*cm, W-2*cm, y-0.2*cm)
    y -= 0.65*cm
    styles = getSampleStyleSheet()
    style_e = ParagraphStyle('e', parent=styles['Normal'], fontName=FONT, fontSize=10,
                             leading=15, textColor=INK, alignment=4)
    texte_expl = analyse.explication or "Explication non disponible."
    p = Paragraph(texte_expl, style_e)
    fw, fh = p.wrap(W-4*cm, 4*cm); p.drawOn(c, 2*cm, y-fh)
    y -= fh + 0.7*cm

    # === FACTEURS ===
    c.setFillColor(BLEU); c.setFont(FONT_B, 11)
    c.drawString(2*cm, y, "FACTEURS DETERMINANTS DE L'EVALUATION")
    c.setStrokeColor(LIGHTGRAY); c.line(2*cm, y-0.2*cm, W-2*cm, y-0.2*cm)
    y -= 0.75*cm
    if analyse.facteurs_explicatifs:
        try:
            facteurs = json.loads(analyse.facteurs_explicatifs)
        except Exception:
            facteurs = []
        for f in facteurs[:5]:
            favorable = f["contribution"] < 0
            col = VERT if favorable else ORANGE
            effet = "Favorable" if favorable else "Point de vigilance"
            c.setFillColor(col); c.circle(2.25*cm, y+0.09*cm, 0.08*cm, fill=1)
            c.setFillColor(INK); c.setFont(FONT, 10); c.drawString(2.6*cm, y, _libelle(f["variable"]))
            c.setFillColor(col); c.setFont(FONT_B, 9.5); c.drawString(12*cm, y, effet)
            y -= 0.55*cm

    # === CONDITIONS (accorde) ou RECOMMANDATIONS (refuse) ===
    y -= 0.4*cm
    c.setFillColor(FONDCLAIR)
    c.roundRect(2*cm, y-2*cm, W-4*cm, 2*cm, 6, fill=1, stroke=0)
    c.setFillColor(INK); c.setFont(FONT_B, 10)
    if accorde:
        c.drawString(2.4*cm, y-0.5*cm, "CONDITIONS ET ENGAGEMENTS")
        lignes = [
            "La presente decision est valable 30 jours a compter de sa date d'emission.",
            "L'octroi definitif est subordonne a la constitution des garanties requises.",
            "La souscription d'une assurance deces-invalidite est obligatoire avant le deblocage des fonds.",
            "Le taux d'endettement du demandeur ne devra pas exceder 33% du revenu net cessible.",
        ]
    else:
        c.drawString(2.4*cm, y-0.5*cm, "RECOMMANDATIONS POUR UNE FUTURE DEMANDE")
        lignes = [
            "Reduire le montant sollicite ou augmenter l'apport personnel pour ameliorer la quotite.",
            "Consolider la stabilite des revenus et l'anciennete professionnelle.",
            "Reduire l'endettement existant avant de soumettre une nouvelle demande.",
            "Constituer une epargne prealable temoignant d'une capacite de remboursement.",
        ]
    c.setFillColor(GRAY); c.setFont(FONT, 9)
    yy = y - 1*cm
    for ligne in lignes:
        c.setFillColor(couleur_dec); c.drawString(2.4*cm, yy, "-")
        c.setFillColor(GRAY); c.drawString(2.7*cm, yy, ligne)
        yy -= 0.4*cm

    # === SIGNATURES ===
    y_sign = 3.6*cm
    c.setStrokeColor(GRAY); c.setLineWidth(0.6)
    c.line(2.5*cm, y_sign, 7.5*cm, y_sign); c.line(W-7.5*cm, y_sign, W-2.5*cm, y_sign)
    c.setFillColor(GRAY); c.setFont(FONT, 9)
    c.drawCentredString(5*cm, y_sign-0.45*cm, "Signature de l'agent de credit")
    c.drawCentredString(W-5*cm, y_sign-0.45*cm, "Visa du responsable des engagements")

    # === PIED DE PAGE ===
    c.setStrokeColor(BLEU); c.setLineWidth(1.5); c.line(2*cm, 2*cm, W-2*cm, 2*cm)
    c.setFillColor(GRAY); c.setFont(FONT, 7.5)
    c.drawString(2*cm, 1.6*cm, "Document conforme aux exigences de tracabilite de la COBAC.")
    c.drawString(2*cm, 1.25*cm, "CREDISCORE - BSIC Tchad  -  Support d'aide a la decision engageant la responsabilite de l'agent signataire.")
    c.setFont(FONT_B, 8); c.setFillColor(BLEU)
    c.drawRightString(W-2*cm, 1.6*cm, "Page 1/1")

    c.save()
    tampon.seek(0)
    return tampon.read()