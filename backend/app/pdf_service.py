# -*- coding: utf-8 -*-
"""
Generation de la fiche de decision de credit au format PDF.

A partir d'une analyse enregistree, produit une fiche d'une page :
identite BSIC (bleu du logo), reference du dossier, client et credit,
decision avec jauge de risque a trois zones, indicateurs cles (taux
d'endettement, quotite de financement, nombre d'echeances), motivation,
facteurs determinants avec leur poids, conditions ou recommandations
adaptees au dossier, signatures, QR code et code d'authenticite.

Regles de couleur :
- le bleu BSIC sert a l'identite et aux titres ;
- le vert, le rouge et l'ambre sont reserves a leur sens (favorable /
  refus / vigilance) et sont toujours doubles d'un symbole et d'un mot,
  pour rester lisibles en noir et blanc et pour les daltoniens.

Le genre n'est jamais presente comme un facteur de decision sur la fiche.
"""

import os
import io
import json
import hmac
import hashlib
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

from .model_service import SEUIL_DECISION, SEUIL_RISQUE_FAIBLE

# ---------------------------------------------------------------------------
# Palette (alignee sur le logo BSIC)
# ---------------------------------------------------------------------------
BLEU = colors.HexColor("#0055A8")        # identite BSIC
BLEU_PALE = colors.HexColor("#EAF1FA")
INK = colors.HexColor("#1B2A41")         # texte principal
GRIS = colors.HexColor("#5A6B82")        # texte secondaire (contraste 5,4:1)
TRAIT = colors.HexColor("#D5DBE3")
FOND = colors.HexColor("#F5F7FA")
VERT = colors.HexColor("#0F6E56")        # accorde / favorable
VERT_PALE = colors.HexColor("#E6F3EE")
ROUGE = colors.HexColor("#B42318")       # refuse
ROUGE_PALE = colors.HexColor("#FCEBEA")
AMBRE = colors.HexColor("#B45309")       # vigilance (contraste 5:1)
AMBRE_PALE = colors.HexColor("#FDF1E1")
# Zones de la jauge (memes seuils que l'application)
ZONE_FAIBLE = colors.HexColor("#BFE3D3")
ZONE_MOYEN = colors.HexColor("#F6D9A8")
ZONE_ELEVE = colors.HexColor("#F2B8B2")

CHEMIN_LOGO = os.path.join(os.path.dirname(__file__), "logo_bsic.png")
NORME_ENDETTEMENT = 0.33

# ---------------------------------------------------------------------------
# Polices avec accents (DejaVu ou Arial si disponibles, sinon Helvetica)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Libelles et valeurs lisibles
# ---------------------------------------------------------------------------
LIBELLES_NUM = {
    "EXT_SOURCE_1": "Score externe 1",
    "EXT_SOURCE_2": "Score externe 2",
    "EXT_SOURCE_3": "Score externe 3",
    "AMT_INCOME_TOTAL": "Revenu",
    "AMT_CREDIT": "Montant du crédit",
    "AMT_ANNUITY": "Montant de l'échéance",
    "AMT_GOODS_PRICE": "Prix du bien financé",
    "AGE_ANNEES": "Âge",
    "ANCIENNETE_EMPLOI_ANNEES": "Ancienneté d'emploi",
    "CNT_CHILDREN": "Nombre d'enfants",
    "CNT_FAM_MEMBERS": "Taille du foyer",
    "EMPLOI_ANORMAL": "Sans emploi salarié",
}
LIBELLES_CAT = {
    "NAME_FAMILY_STATUS": "Situation familiale",
    "NAME_EDUCATION_TYPE": "Niveau d'études",
    "OCCUPATION_TYPE": "Profession",
    "ORGANIZATION_TYPE": "Type d'employeur",
    "NAME_INCOME_TYPE": "Type de revenu",
    "NAME_CONTRACT_TYPE": "Type de crédit",
}
CATEGORIES = {
    "Married": "Marié(e)", "Single / not married": "Célibataire",
    "Civil marriage": "Union libre", "Separated": "Séparé(e)", "Widow": "Veuf / veuve",
    "Secondary / secondary special": "Secondaire", "Higher education": "Supérieur",
    "Incomplete higher": "Supérieur incomplet", "Lower secondary": "Premier cycle",
    "Academic degree": "Diplôme universitaire",
    "Working": "Salarié", "Commercial associate": "Associé commercial",
    "Pensioner": "Retraité", "State servant": "Fonctionnaire",
    "Unemployed": "Sans emploi", "Student": "Étudiant", "Businessman": "Entrepreneur",
    "Cash loans": "Crédit de trésorerie", "Revolving loans": "Crédit renouvelable",
    "Laborers": "Ouvrier", "Government": "Administration publique",
}
# Variables jamais presentees comme facteur de decision sur la fiche
VARIABLES_EXCLUES = ("CODE_GENDER",)


def _traduire(valeur):
    if valeur in (None, ""):
        return "—"
    return CATEGORIES.get(str(valeur), str(valeur))


def _fcfa(valeur):
    try:
        return f"{int(round(float(valeur))):,}".replace(",", " ") + " FCFA"
    except (TypeError, ValueError):
        return "—"


def _pct(x, decimales=0):
    if x is None:
        return "—"
    return f"{x * 100:.{decimales}f}".replace(".", ",") + " %"


def _nombre(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _facteur(variable: str, dossier: dict):
    """(libelle, valeur du dossier) d'un facteur SHAP, ou None s'il est exclu."""
    if variable.startswith(VARIABLES_EXCLUES):
        return None
    for cle, libelle in LIBELLES_NUM.items():
        if variable == cle or variable.startswith(cle + "_") or variable.startswith(cle):
            v = _nombre(dossier.get(cle))
            if v is None:
                return libelle, "—"
            if cle.startswith("EXT_SOURCE"):
                return libelle, f"{v:.2f}".replace(".", ",") + " / 1"
            if cle.startswith("AMT_"):
                return libelle, _fcfa(v)
            if cle in ("AGE_ANNEES", "ANCIENNETE_EMPLOI_ANNEES"):
                return libelle, f"{v:.1f}".replace(".", ",").replace(",0", "") + " ans"
            if cle == "EMPLOI_ANORMAL":
                return libelle, "Oui" if v else "Non"
            return libelle, f"{int(v)}"
    for prefixe, libelle in LIBELLES_CAT.items():
        if variable.startswith(prefixe):
            return libelle, _traduire(dossier.get(prefixe))
    return variable, "—"


def _liste(elements):
    elements = list(elements)
    if len(elements) <= 1:
        return "".join(elements)
    return ", ".join(elements[:-1]) + " et " + elements[-1]


def _ratios(dossier: dict) -> dict:
    """Indicateurs cles calcules a partir du dossier (None si incalculable).
    Le revenu et l'echeance etant saisis sur la meme periode, leur rapport
    ne depend pas de la periode retenue."""
    def positif(cle):
        v = _nombre(dossier.get(cle))
        return v if v and v > 0 else None

    revenu, echeance = positif("AMT_INCOME_TOTAL"), positif("AMT_ANNUITY")
    credit, bien = positif("AMT_CREDIT"), positif("AMT_GOODS_PRICE")
    return {
        "endettement": echeance / revenu if echeance and revenu else None,
        "quotite": credit / bien if credit and bien else None,
        "echeances": round(credit / echeance) if credit and echeance else None,
    }


def code_authenticite(analyse) -> str:
    """Code d'authenticite de la fiche (HMAC-SHA256 des donnees de la decision,
    signe avec la cle secrete de l'API) : toute modification de la decision
    ou de la probabilite donne un autre code."""
    from .security import SECRET_KEY
    date = analyse.date_analyse.isoformat() if analyse.date_analyse else ""
    message = f"{analyse.id}|{analyse.probabilite_defaut:.6f}|{analyse.decision}|{date}"
    h = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest().upper()[:12]
    return "-".join(h[i:i + 4] for i in range(0, 12, 4))


# ---------------------------------------------------------------------------
# Elements graphiques
# ---------------------------------------------------------------------------
def _icone(c, x, y, r, sorte, couleur):
    """Pastille avec un symbole dessine (lisible sans couleur) :
    'ok' = coche, 'non' = croix, 'alerte' = point d'exclamation."""
    c.saveState()
    c.setFillColor(couleur)
    c.circle(x, y, r, fill=1, stroke=0)
    c.setStrokeColor(colors.white)
    c.setFillColor(colors.white)
    c.setLineWidth(max(r * 0.28, 0.9))
    c.setLineCap(1)
    c.setLineJoin(1)
    if sorte == "ok":
        p = c.beginPath()
        p.moveTo(x - 0.45 * r, y + 0.02 * r)
        p.lineTo(x - 0.12 * r, y - 0.32 * r)
        p.lineTo(x + 0.45 * r, y + 0.35 * r)
        c.drawPath(p, stroke=1, fill=0)
    elif sorte == "non":
        d = 0.33 * r
        c.line(x - d, y - d, x + d, y + d)
        c.line(x - d, y + d, x + d, y - d)
    else:
        c.line(x, y + 0.45 * r, x, y - 0.05 * r)
        c.circle(x, y - 0.38 * r, 0.09 * r, fill=1, stroke=0)
    c.restoreState()


def _titre_section(c, x, y, texte, largeur):
    c.setFillColor(BLEU)
    c.setFont(FONT_B, 9.5)
    c.drawString(x, y, texte)
    c.setStrokeColor(BLEU)
    c.setLineWidth(0.8)
    c.line(x, y - 0.18 * cm, x + largeur, y - 0.18 * cm)


def _qr(c, url, x, y, taille):
    widget = QrCodeWidget(url)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(taille, taille, transform=[taille / (x1 - x0), 0, 0, taille / (y1 - y0), 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def _paragraphe(texte, taille=9.5, interligne=13.5, couleur=INK, align=4):
    style = ParagraphStyle("p", fontName=FONT, fontSize=taille, leading=interligne,
                           textColor=couleur, alignment=align)
    return Paragraph(texte, style)


# ---------------------------------------------------------------------------
# Contenu calcule
# ---------------------------------------------------------------------------
def _facteurs_affiches(analyse, dossier, nombre=5):
    """Facteurs SHAP a afficher : sans le genre, sans doublon de libelle."""
    try:
        bruts = json.loads(analyse.facteurs_explicatifs or "[]")
    except (ValueError, TypeError):
        bruts = []
    facteurs, vus = [], set()
    for f in bruts:
        info = _facteur(str(f.get("variable", "")), dossier)
        if info is None or info[0] in vus:
            continue
        vus.add(info[0])
        facteurs.append({"libelle": info[0], "valeur": info[1],
                         "contribution": float(f.get("contribution", 0)),
                         "variable": str(f.get("variable", ""))})
    return facteurs[:nombre]


def _motivation(accorde, proba, facteurs):
    seuil = _pct(SEUIL_DECISION)
    favorables = [f["libelle"].lower() for f in facteurs if f["contribution"] < 0]
    risques = [f["libelle"].lower() for f in facteurs if f["contribution"] >= 0]
    if accorde:
        phrases = [f"Le crédit peut être accordé : la probabilité de défaut estimée ({_pct(proba)}) "
                   f"reste sous le seuil de refus de {seuil}."]
        if favorables:
            phrases.append(f"Principaux éléments favorables : {_liste(favorables[:3])}.")
        if risques:
            phrases.append(f"Point(s) de vigilance : {_liste(risques[:2])}, "
                           "sans remettre en cause la décision.")
    else:
        phrases = [f"Le crédit est refusé en l'état : la probabilité de défaut estimée ({_pct(proba)}) "
                   f"atteint ou dépasse le seuil de refus de {seuil}."]
        if risques:
            phrases.append(f"Principaux facteurs de risque : {_liste(risques[:3])}.")
        if favorables:
            phrases.append(f"Le dossier présente toutefois des atouts : {_liste(favorables[:2])}.")
    return " ".join(phrases)


_RECOS = [
    ("EXT_SOURCE", "Améliorer l'historique de crédit : régulariser les engagements en cours "
                   "et proposer des garanties (caution, nantissement)."),
    ("AMT_CREDIT", "Réduire le montant sollicité ou augmenter l'apport personnel."),
    ("AMT_GOODS_PRICE", "Réduire le montant sollicité ou augmenter l'apport personnel."),
    ("AMT_ANNUITY", "Allonger la durée du crédit pour réduire le montant de l'échéance."),
    ("AMT_INCOME_TOTAL", "Justifier de revenus complémentaires ou domicilier ses revenus à la BSIC."),
    ("ANCIENNETE_EMPLOI", "Consolider l'ancienneté professionnelle avant une nouvelle demande."),
]


def _conditions_ou_recommandations(accorde, facteurs, ratios):
    endet, quotite = ratios["endettement"], ratios["quotite"]
    if accorde:
        lignes = [
            "Décision valable 30 jours à compter de sa date d'émission.",
            "Octroi définitif subordonné à la constitution des garanties requises.",
            "Assurance décès-invalidité obligatoire avant le déblocage des fonds.",
        ]
        if endet is not None and endet > NORME_ENDETTEMENT:
            lignes.append(f"Taux d'endettement de {_pct(endet)}, supérieur à la norme de "
                          f"{_pct(NORME_ENDETTEMENT)} : dérogation à valider par le responsable des engagements.")
        elif endet is not None:
            lignes.append(f"Le taux d'endettement ({_pct(endet)}) respecte la norme de "
                          f"{_pct(NORME_ENDETTEMENT)} du revenu.")
        return "CONDITIONS ET ENGAGEMENTS", lignes

    lignes = []
    if endet is not None and endet > NORME_ENDETTEMENT:
        lignes.append(f"Ramener le taux d'endettement sous {_pct(NORME_ENDETTEMENT)} "
                      f"(actuellement {_pct(endet)}) en réduisant l'échéance.")
    if quotite is not None and quotite > 1:
        lignes.append("Limiter le financement au prix du bien (le montant demandé le dépasse).")
    for f in facteurs:
        if f["contribution"] <= 0:
            continue
        for prefixe, texte in _RECOS:
            if f["variable"].startswith(prefixe) and texte not in lignes:
                lignes.append(texte)
                break
    if len(lignes) < 3:
        for texte in ("Présenter un co-emprunteur ou une caution solidaire.",
                      "Constituer une épargne préalable témoignant d'une capacité de remboursement."):
            if len(lignes) < 3:
                lignes.append(texte)
    return "RECOMMANDATIONS POUR UNE NOUVELLE DEMANDE", lignes[:4]


def _version_modele(analyse) -> str:
    v = getattr(analyse, "version_modele", None)
    if not v:
        return "Modèle : Gradient Boosting"
    details = [f"version n°{v.id}"]
    if v.auc:
        details.append(f"AUC {v.auc:.3f}".replace(".", ","))
    if v.date_creation:
        details.append(f"en service depuis le {v.date_creation:%d/%m/%Y}")
    return f"Modèle : {v.algorithme} ({', '.join(details)})"


# ---------------------------------------------------------------------------
# La fiche
# ---------------------------------------------------------------------------
def generer_pdf_decision(analyse, client, agent_nom: str) -> bytes:
    """Genere la fiche de decision en PDF et renvoie les octets."""
    tampon = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(f"Fiche de décision de crédit - analyse {analyse.id}")
    c.setAuthor("CREDISCORE - BSIC Tchad")

    def Y(depuis_le_haut_cm):
        return H - depuis_le_haut_cm * cm

    G, D = 2 * cm, W - 2 * cm          # marges gauche et droite
    largeur = D - G
    accorde = analyse.decision == "ACCORDE"
    couleur_dec = VERT if accorde else ROUGE
    proba = float(analyse.probabilite_defaut or 0)

    try:
        dossier = json.loads(analyse.donnees_dossier) if analyse.donnees_dossier else {}
    except (ValueError, TypeError):
        dossier = {}
    facteurs = _facteurs_affiches(analyse, dossier)
    ratios = _ratios(dossier)

    # === EN-TETE =========================================================
    if os.path.exists(CHEMIN_LOGO):
        c.drawImage(ImageReader(CHEMIN_LOGO), D - 2.2 * cm, Y(3.05), width=2.2 * cm,
                    height=2.2 * cm, mask="auto", preserveAspectRatio=True)
    c.setFillColor(INK)
    c.setFont(FONT_B, 17)
    c.drawString(G, Y(1.75), "BSIC TCHAD S.A.")
    c.setFillColor(GRIS)
    c.setFont(FONT, 9)
    c.drawString(G, Y(2.25), "Banque Sahélo-Saharienne pour l'Investissement et le Commerce")
    etiquette = "CONFIDENTIEL · SECRET BANCAIRE"
    c.setFont(FONT_B, 6.5)
    le = c.stringWidth(etiquette, FONT_B, 6.5) + 0.4 * cm
    c.setFillColor(INK)
    c.roundRect(G, Y(2.95), le, 0.42 * cm, 2, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawString(G + 0.2 * cm, Y(2.8), etiquette)
    c.setStrokeColor(BLEU)
    c.setLineWidth(2)
    c.line(G, Y(3.3), D, Y(3.3))

    # === TITRE + REFERENCE ===============================================
    c.setFillColor(INK)
    c.setFont(FONT_B, 16)
    c.drawString(G, Y(4.15), "FICHE DE DÉCISION DE CRÉDIT")
    date_str = (analyse.date_analyse.strftime("%d/%m/%Y à %H:%M")
                if analyse.date_analyse else datetime.now().strftime("%d/%m/%Y"))
    c.setFillColor(GRIS)
    c.setFont(FONT, 9)
    c.drawString(G, Y(4.7), f"Émise le {date_str}  ·  Agent de crédit : {agent_nom}")
    annee = analyse.date_analyse.year if analyse.date_analyse else datetime.now().year
    reference = f"CRED-{annee}-{analyse.id:04d}"
    c.setFillColor(BLEU_PALE)
    c.roundRect(D - 5 * cm, Y(4.85), 5 * cm, 1.2 * cm, 4, fill=1, stroke=0)
    c.setFillColor(GRIS)
    c.setFont(FONT, 7.5)
    c.drawString(D - 4.7 * cm, Y(4.05), "RÉFÉRENCE DOSSIER")
    c.setFillColor(BLEU)
    c.setFont(FONT_B, 12.5)
    c.drawString(D - 4.7 * cm, Y(4.55), reference)

    # === CLIENT + CREDIT (deux colonnes) =================================
    col = (largeur - 0.8 * cm) / 2
    x2 = G + col + 0.8 * cm
    _titre_section(c, G, Y(5.55), "INFORMATIONS DU CLIENT", col)
    _titre_section(c, x2, Y(5.55), "CARACTÉRISTIQUES DU CRÉDIT", col)
    genre = {"F": "Féminin", "M": "Masculin"}.get(getattr(client, "genre", None), "—")
    infos_client = [
        ("Nom", client.nom if client else "—"),
        ("Genre", genre),
        ("Âge", f"{int(client.age)} ans" if client and client.age else "—"),
        ("Profession", client.profession if client and client.profession else "—"),
        ("Situation familiale", _traduire(client.situation_familiale) if client else "—"),
    ]
    infos_credit = [
        ("Type de crédit", _traduire(dossier.get("NAME_CONTRACT_TYPE"))),
        ("Montant demandé", _fcfa(dossier.get("AMT_CREDIT"))),
        ("Échéance", _fcfa(dossier.get("AMT_ANNUITY"))),
        ("Prix du bien", _fcfa(dossier.get("AMT_GOODS_PRICE"))),
        ("Revenu", _fcfa(dossier.get("AMT_INCOME_TOTAL"))),
    ]
    for x, infos in ((G, infos_client), (x2, infos_credit)):
        y = 6.15
        for libelle, valeur in infos:
            c.setFillColor(GRIS)
            c.setFont(FONT, 9)
            c.drawString(x, Y(y), libelle)
            c.setFillColor(INK)
            c.setFont(FONT_B, 9)
            c.drawString(x + 3.4 * cm, Y(y), str(valeur))
            y += 0.5

    # === DECISION + JAUGE ================================================
    haut, hauteur = 8.75, 2.45
    c.setFillColor(VERT_PALE if accorde else ROUGE_PALE)
    c.setStrokeColor(couleur_dec)
    c.setLineWidth(1.2)
    c.roundRect(G, Y(haut + hauteur), largeur, hauteur * cm, 6, fill=1, stroke=1)
    _icone(c, G + 0.85 * cm, Y(haut + 0.9), 0.38 * cm, "ok" if accorde else "non", couleur_dec)
    c.setFillColor(couleur_dec)
    c.setFont(FONT_B, 18)
    c.drawString(G + 1.5 * cm, Y(haut + 1.08), "CRÉDIT ACCORDÉ" if accorde else "CRÉDIT REFUSÉ")
    classe = (analyse.classe_risque or "—").capitalize().replace("Eleve", "Élevé")
    c.setFillColor(INK)
    c.setFont(FONT, 9)
    c.drawString(G + 1.5 * cm, Y(haut + 1.65), f"Classe de risque : {classe}")
    c.drawString(G + 1.5 * cm, Y(haut + 2.05), f"Seuil de refus : {_pct(SEUIL_DECISION)} de probabilité de défaut")

    # Jauge a trois zones, curseur sur la valeur du client
    gx, gw = G + 9.3 * cm, largeur - 9.8 * cm
    gy = Y(haut + 1.55)
    c.setFillColor(GRIS)
    c.setFont(FONT, 8)
    c.drawString(gx, Y(haut + 0.6), "Probabilité de défaut")
    c.setFillColor(couleur_dec)
    c.setFont(FONT_B, 18)
    c.drawRightString(gx + gw, Y(haut + 0.85), _pct(proba))
    zones = [(0, SEUIL_RISQUE_FAIBLE, ZONE_FAIBLE, "Faible"),
             (SEUIL_RISQUE_FAIBLE, SEUIL_DECISION, ZONE_MOYEN, "Moyen"),
             (SEUIL_DECISION, 1, ZONE_ELEVE, "Élevé")]
    for debut, fin, teinte, nom in zones:
        c.setFillColor(teinte)
        c.rect(gx + gw * debut, gy, gw * (fin - debut), 0.3 * cm, fill=1, stroke=0)
        c.setFillColor(GRIS)
        c.setFont(FONT, 6.5)
        c.drawCentredString(gx + gw * (debut + fin) / 2, gy - 0.38 * cm, nom)
    # Seuil de refus
    sx = gx + gw * SEUIL_DECISION
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.setDash(2, 1.5)
    c.line(sx, gy - 0.12 * cm, sx, gy + 0.42 * cm)
    c.setDash()
    # Curseur
    cx = gx + gw * min(max(proba, 0), 1)
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(cx - 0.13 * cm, gy + 0.55 * cm)
    p.lineTo(cx + 0.13 * cm, gy + 0.55 * cm)
    p.lineTo(cx, gy + 0.33 * cm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setLineWidth(1.6)
    c.line(cx, gy - 0.04 * cm, cx, gy + 0.34 * cm)

    # === INDICATEURS CLES ================================================
    _titre_section(c, G, Y(11.75), "INDICATEURS CLÉS DU DOSSIER", largeur)
    endet, quotite, nb = ratios["endettement"], ratios["quotite"], ratios["echeances"]
    if endet is None:
        t_endet = ("—", GRIS, None, "Données incomplètes")
    elif endet <= NORME_ENDETTEMENT:
        t_endet = (_pct(endet), VERT, "ok", "Conforme")
    elif endet <= 0.5:
        t_endet = (_pct(endet), AMBRE, "alerte", "Hors norme")
    else:
        t_endet = (_pct(endet), ROUGE, "non", "Très hors norme")
    if quotite is None:
        t_quot = ("—", GRIS, None, "Données incomplètes")
    elif quotite <= 1:
        t_quot = (_pct(quotite), VERT, "ok", "Couvert par le bien")
    else:
        t_quot = (_pct(quotite), AMBRE, "alerte", "Dépasse le prix du bien")
    t_nb = (f"env. {nb}" if nb else "—", INK, None, "Hors intérêts")
    tuiles = [("Taux d'endettement",
               f"Échéance ÷ revenu · norme {_pct(NORME_ENDETTEMENT)} max.", t_endet),
              ("Quotité de financement", "Montant du crédit ÷ prix du bien", t_quot),
              ("Nombre d'échéances", "Montant du crédit ÷ échéance", t_nb)]
    tw = (largeur - 2 * 0.4 * cm) / 3
    for i, (nom, formule, (valeur, coul, icone, note)) in enumerate(tuiles):
        tx = G + i * (tw + 0.4 * cm)
        c.setFillColor(FOND)
        c.roundRect(tx, Y(13.65), tw, 1.5 * cm, 4, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT_B, 8.5)
        c.drawString(tx + 0.3 * cm, Y(12.6), nom)
        c.setFillColor(GRIS)
        c.setFont(FONT, 6.5)
        c.drawString(tx + 0.3 * cm, Y(12.92), formule)
        c.setFillColor(coul)
        c.setFont(FONT_B, 13)
        c.drawString(tx + 0.3 * cm, Y(13.43), valeur)
        vx = tx + 0.3 * cm + c.stringWidth(valeur, FONT_B, 13) + 0.25 * cm
        if icone:
            _icone(c, vx + 0.14 * cm, Y(13.53), 0.14 * cm, icone, coul)
            vx += 0.4 * cm
        c.setFillColor(GRIS)
        c.setFont(FONT, 6.5)
        c.drawString(vx, Y(13.48), note)

    # === MOTIVATION ======================================================
    _titre_section(c, G, Y(14.4), "MOTIVATION DE LA DÉCISION", largeur)
    para = _paragraphe(_motivation(accorde, proba, facteurs))
    _, ph = para.wrap(largeur, 5 * cm)
    para.drawOn(c, G, Y(14.75) - ph)
    y = 14.75 + ph / cm + 0.7

    # === FACTEURS ========================================================
    _titre_section(c, G, Y(y), "FACTEURS DÉTERMINANTS DE L'ÉVALUATION", largeur)
    y += 0.55
    col_val, col_barre, barre_max = G + 6.2 * cm, G + 11.2 * cm, 3.2 * cm
    c.setFillColor(GRIS)
    c.setFont(FONT, 7)
    c.drawString(G + 0.6 * cm, Y(y), "Facteur")
    c.drawString(col_val, Y(y), "Valeur du dossier")
    c.drawString(col_barre, Y(y), "Poids dans la décision")
    c.drawRightString(D, Y(y), "Effet")
    y += 0.5
    poids_max = max((abs(f["contribution"]) for f in facteurs), default=0) or 1
    for f in facteurs:
        favorable = f["contribution"] < 0
        coul = VERT if favorable else AMBRE
        _icone(c, G + 0.2 * cm, Y(y) + 0.1 * cm, 0.17 * cm, "ok" if favorable else "alerte", coul)
        c.setFillColor(INK)
        c.setFont(FONT, 9)
        c.drawString(G + 0.6 * cm, Y(y), f["libelle"])
        c.drawString(col_val, Y(y), f["valeur"])
        c.setFillColor(TRAIT)
        c.rect(col_barre, Y(y) - 0.02 * cm, barre_max, 0.24 * cm, fill=1, stroke=0)
        c.setFillColor(coul)
        c.rect(col_barre, Y(y) - 0.02 * cm, barre_max * abs(f["contribution"]) / poids_max,
               0.24 * cm, fill=1, stroke=0)
        c.setFont(FONT_B, 8.5)
        c.drawRightString(D, Y(y), "Favorable" if favorable else "Vigilance")
        y += 0.52

    # === CONDITIONS / RECOMMANDATIONS ====================================
    y += 0.3
    titre_bloc, lignes = _conditions_ou_recommandations(accorde, facteurs, ratios)
    paras = [_paragraphe(l, taille=8.5, interligne=11.5, couleur=INK, align=0) for l in lignes]
    hauteurs = [p.wrap(largeur - 1.2 * cm, 3 * cm)[1] for p in paras]
    h_bloc = 0.75 * cm + sum(hauteurs) + 0.12 * cm * len(paras) + 0.25 * cm
    c.setFillColor(FOND)
    c.roundRect(G, Y(y) - h_bloc, largeur, h_bloc, 5, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(FONT_B, 9)
    c.drawString(G + 0.4 * cm, Y(y) - 0.5 * cm, titre_bloc)
    yy = Y(y) - 0.75 * cm
    for p, h in zip(paras, hauteurs):
        c.setFillColor(BLEU)
        c.circle(G + 0.5 * cm, yy - 0.2 * cm, 0.05 * cm, fill=1, stroke=0)
        p.drawOn(c, G + 0.8 * cm, yy - h)
        yy -= h + 0.12 * cm

    # === SIGNATURES + AUTHENTICITE =======================================
    bas, h_sign = 2.6 * cm, 2.9 * cm
    blocs = [("Agent de crédit", f"Nom : {agent_nom}", "Signature :"),
             ("Responsable des engagements", "Nom :", "Visa et cachet de l'agence :")]
    lb = 5.6 * cm
    for i, (titre, nom, champ) in enumerate(blocs):
        bx = G + i * (lb + 0.35 * cm)
        c.setStrokeColor(TRAIT)
        c.setLineWidth(0.8)
        c.roundRect(bx, bas, lb, h_sign, 4, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont(FONT_B, 8.5)
        c.drawString(bx + 0.3 * cm, bas + h_sign - 0.5 * cm, titre)
        c.setFillColor(GRIS)
        c.setFont(FONT, 8)
        c.drawString(bx + 0.3 * cm, bas + h_sign - 1.0 * cm, nom)
        c.drawString(bx + 0.3 * cm, bas + h_sign - 1.45 * cm, "Date :")
        c.drawString(bx + 0.3 * cm, bas + h_sign - 1.9 * cm, champ)

    qr_taille = 2.1 * cm
    ax = G + 2 * (lb + 0.35 * cm) + 0.15 * cm
    url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/") + f"/analyse/{analyse.id}"
    _qr(c, url, D - qr_taille, bas + 0.3 * cm, qr_taille)
    c.setFillColor(INK)
    c.setFont(FONT_B, 8)
    c.drawString(ax, bas + h_sign - 0.5 * cm, "Authenticité")
    c.setFillColor(GRIS)
    c.setFont(FONT, 7)
    c.drawString(ax, bas + h_sign - 0.95 * cm, "Code de la fiche :")
    c.setFillColor(BLEU)
    c.setFont(FONT_B, 7.5)
    c.drawString(ax, bas + h_sign - 1.4 * cm, code_authenticite(analyse))
    c.setFillColor(GRIS)
    c.setFont(FONT, 6.5)
    c.drawString(ax, bas + h_sign - 1.9 * cm, "Scannez le QR code pour")
    c.drawString(ax, bas + h_sign - 2.2 * cm, "consulter l'analyse dans")
    c.drawString(ax, bas + h_sign - 2.5 * cm, "CREDISCORE.")

    # === PIED DE PAGE ====================================================
    c.setStrokeColor(BLEU)
    c.setLineWidth(1.2)
    c.line(G, 2.15 * cm, D, 2.15 * cm)
    c.setFillColor(GRIS)
    c.setFont(FONT, 7)
    c.drawString(G, 1.8 * cm, "Document confidentiel couvert par le secret bancaire · "
                              "Conforme aux exigences de traçabilité de la COBAC.")
    c.drawString(G, 1.48 * cm, "Aide à la décision générée par CREDISCORE, "
                               "engageant la responsabilité de l'agent signataire.")
    c.drawString(G, 1.16 * cm, _version_modele(analyse))
    c.setFillColor(BLEU)
    c.setFont(FONT_B, 7.5)
    c.drawRightString(D, 1.8 * cm, "Page 1/1")

    c.save()
    tampon.seek(0)
    return tampon.read()
