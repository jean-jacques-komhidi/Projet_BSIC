# -*- coding: utf-8 -*-
"""
Routes de l'export des donnees (reserve a l'administrateur).

  - GET  /export/options       : groupes de colonnes, destinataires, nombre de lignes par jeu
  - POST /export/apercu        : 5 premieres lignes et nombre total, selon les options
  - POST /export/telecharger   : fichier CSV (zip avec le dictionnaire) ou Excel ; l'export est journalise
  - GET  /export/journal       : derniers exports (qui, quand, quoi, pour qui, pourquoi)
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .security import administrateur_courant
from . import export_service as ex
from .logging_config import logger

router = APIRouter(prefix="/export", tags=["Export"])


class OptionsExport(BaseModel):
    jeu: str = "analyses"
    groupes: List[str] = Field(default_factory=lambda: list(ex.GROUPES_PAR_DEFAUT))
    anonymiser: bool = True
    du: Optional[date] = None
    au: Optional[date] = None


class DemandeExport(OptionsExport):
    destinataire: str
    motif: str
    format: str = "csv"


def _verifier(o: OptionsExport):
    if o.jeu not in ex.JEUX:
        raise HTTPException(status_code=422, detail="Jeu de données inconnu.")
    groupes = [g for g in o.groupes if g in ex.GROUPES]
    if not ex.colonnes(o.jeu, groupes):
        raise HTTPException(status_code=422, detail="Choisissez au moins un groupe de colonnes.")
    if o.du and o.au and o.du > o.au:
        raise HTTPException(status_code=422, detail="La date de début est après la date de fin.")
    return groupes


@router.get("/options")
def options(db: Session = Depends(get_db), admin: models.User = Depends(administrateur_courant)):
    return {
        "groupes": [{"cle": k, "libelle": v, "defaut": k in ex.GROUPES_PAR_DEFAUT} for k, v in ex.GROUPES.items()],
        "groupes_par_jeu": {jeu: sorted({c[1] for c in cols}, key=list(ex.GROUPES).index)
                            for jeu, cols in ex.COLONNES.items()},
        "destinataires": list(ex.DESTINATAIRES),
        "totaux": {"analyses": db.query(models.Analyse).count(), "clients": db.query(models.Client).count(),
                   "versions": db.query(models.ModelVersion).count()},
    }


@router.post("/apercu")
def apercu(o: OptionsExport, db: Session = Depends(get_db), admin: models.User = Depends(administrateur_courant)):
    groupes = _verifier(o)
    lignes = ex.lignes(db, o.jeu, groupes, o.anonymiser, o.du, o.au)
    return {"colonnes": ex.colonnes(o.jeu, groupes), "lignes": lignes[:5], "total": len(lignes)}


@router.post("/telecharger")
def telecharger(d: DemandeExport, db: Session = Depends(get_db), admin: models.User = Depends(administrateur_courant)):
    groupes = _verifier(d)
    if d.destinataire not in ex.DESTINATAIRES:
        raise HTTPException(status_code=422, detail="Choisissez un destinataire.")
    if len(d.motif.strip()) < 5:
        raise HTTPException(status_code=422, detail="Indiquez le motif de l'export.")
    if d.format not in ("csv", "xlsx"):
        raise HTTPException(status_code=422, detail="Format inconnu.")

    lignes = ex.lignes(db, d.jeu, groupes, d.anonymiser, d.du, d.au)
    entetes = ex.colonnes(d.jeu, groupes)
    dico = ex.dictionnaire(d.jeu, groupes)
    debut, fin = ex._periode(d.du, d.au)
    db.add(models.ExportDonnees(
        user_id=admin.id, auteur=admin.nom, jeu=d.jeu, groupes=",".join(groupes), destinataire=d.destinataire,
        motif=d.motif.strip()[:300], anonymise=d.anonymiser, format=d.format,
        periode_debut=debut if d.jeu != "versions" else None, periode_fin=fin if d.jeu != "versions" else None,
        nb_lignes=len(lignes)))
    db.commit()
    logger.info(f"Export {d.jeu} ({len(lignes)} lignes, {d.format}) par {admin.nom} pour {d.destinataire}.")

    horodatage = datetime.utcnow().strftime("%Y%m%d")
    if d.format == "csv":
        contenu, type_mime, nom = ex.fichier_zip_csv(d.jeu, lignes, entetes, dico), "application/zip", \
            f"crediscore_{d.jeu}_{horodatage}.zip"
    else:
        contenu = ex.fichier_xlsx(d.jeu, lignes, entetes, dico)
        type_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        nom = f"crediscore_{d.jeu}_{horodatage}.xlsx"
    return Response(content=contenu, media_type=type_mime,
                    headers={"Content-Disposition": f'attachment; filename="{nom}"',
                             "Access-Control-Expose-Headers": "Content-Disposition"})


@router.get("/journal")
def journal(db: Session = Depends(get_db), admin: models.User = Depends(administrateur_courant)):
    noms = {"analyses": "Analyses de crédit", "clients": "Clients", "versions": "Versions du modèle"}
    exports = db.query(models.ExportDonnees).order_by(models.ExportDonnees.date_export.desc()).limit(20).all()
    return [{
        "id": e.id, "date": ex._locale(e.date_export).strftime("%d/%m/%Y %H:%M") if e.date_export else "", "auteur": e.auteur,
        "donnees": noms.get(e.jeu, e.jeu), "destinataire": e.destinataire, "motif": e.motif,
        "anonymise": e.anonymise, "format": e.format, "nb_lignes": e.nb_lignes,
        "genre_inclus": "genre" in (e.groupes or "").split(","),
    } for e in exports]
