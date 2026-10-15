# -*- coding: utf-8 -*-
"""
Tests de CrediBot, sans appel reel a Groq : un faux modele de langage capture
ce qui lui serait envoye.

Verifie : seuils reels, createur, utilisateur connecte, recherche des clients
au-dela de l'apercu, et surtout qu'aucun nom de client n'est envoye a Groq.
"""

import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_base = os.path.join(tempfile.mkdtemp(), "test_chatbot.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_base}"

import pytest

from app.database import Base, engine, SessionLocal
from app import models, chatbot_service
from app.chatbot_service import (
    Pseudonymes, PROMPT_SYSTEME, construire_contexte, repondre, DemasqueurFlux,
)


class FauxGroq:
    """Imite client_groq.chat.completions.create et garde les messages recus.
    Si 'morceaux' est fourni, imite aussi le mode stream=True."""
    def __init__(self, reponse, morceaux=None):
        self.reponse = reponse
        self.morceaux = morceaux
        self.messages = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._creer))

    def _creer(self, model, messages, stream=False, **kwargs):
        self.messages = messages
        if stream:
            return iter(
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=m))])
                for m in self.morceaux
            )
        message = SimpleNamespace(content=self.reponse)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _client(db, nom, profession="Commercant", age=40):
    c = models.Client(nom=nom, profession=profession, age=age, genre="M")
    db.add(c)
    db.commit()
    return c


def _analyse(db, client, proba, decision, risque):
    db.add(models.Analyse(client_id=client.id, probabilite_defaut=proba,
                          decision=decision, classe_risque=risque))
    db.commit()


def _agent():
    return SimpleNamespace(nom="Fatime Abakar", role="agent")


# --- Prompt -----------------------------------------------------------------

def test_prompt_utilise_les_seuils_reels_du_modele():
    assert "70 %" in PROMPT_SYSTEME
    assert "40 %" in PROMPT_SYSTEME
    assert "30 %" not in PROMPT_SYSTEME


def test_prompt_cite_le_createur():
    assert "Komhidi Jean Jacques" in PROMPT_SYSTEME
    assert "UCAO" in PROMPT_SYSTEME


# --- Pseudonymisation -------------------------------------------------------

def test_masquer_puis_demasquer():
    ps = Pseudonymes([(1, "Ali Mahamat"), (2, "Zara Oumar")])
    masque = ps.masquer("Compare Ali Mahamat et Zara Oumar")
    assert "Ali" not in masque and "Zara" not in masque
    assert "Client#1" in masque and "Client#2" in masque
    assert ps.demasquer("Client#1 est plus risque que Client #2") == \
        "Ali Mahamat est plus risque que Zara Oumar"


def test_nom_partiel_et_sans_accents_reconnu():
    ps = Pseudonymes([(7, "Hélène Ngarlem"), (8, "Moussa Ngarlem")])
    # "Hélène" est propre a un seul client : reconnu, meme ecrit sans accent
    assert ps.clients_cites("et pour helene ?") == [7]
    # "Ngarlem" est partage : ambigu, donc pas attribue au hasard
    assert ps.clients_cites("et Ngarlem ?") == []
    assert "Hélène" not in ps.masquer("Que penses-tu de Hélène ?")


# --- Contexte ---------------------------------------------------------------

def test_client_cite_trouve_au_dela_de_l_apercu(db):
    cible = _client(db, "Abdel Kerim Haroun")
    _analyse(db, cible, 0.82, "REFUSE", "eleve")
    for i in range(chatbot_service.NB_CLIENTS_APERCU + 5):
        _client(db, f"Client Recent {i}")   # plus recents que la cible
    ps = Pseudonymes(db.query(models.Client.id, models.Client.nom).all())

    contexte = construire_contexte(db, ps, "Pourquoi Abdel Kerim Haroun a ete refuse ?",
                                   utilisateur=_agent())

    assert f"Client#{cible.id}" in contexte
    assert "82.0 %" in contexte
    assert "FICHES DES CLIENTS CITES" in contexte
    assert "Fatime Abakar (agent de credit)" in contexte


def test_aucun_nom_de_client_dans_le_contexte(db):
    c = _client(db, "Achta Mahamat")
    _analyse(db, c, 0.25, "ACCORDE", "faible")
    ps = Pseudonymes(db.query(models.Client.id, models.Client.nom).all())
    contexte = construire_contexte(db, ps, "Parle-moi de Achta Mahamat")
    assert "Achta" not in contexte and "Mahamat" not in contexte


# --- Reponse complete (faux Groq) -------------------------------------------

def test_rien_de_nominatif_n_est_envoye_a_groq(db, monkeypatch):
    c = _client(db, "Achta Mahamat")
    _analyse(db, c, 0.25, "ACCORDE", "faible")
    faux = FauxGroq(f"Client#{c.id} presente un risque faible.")
    monkeypatch.setattr(chatbot_service, "client_groq", faux)

    historique = [{"role": "user", "contenu": "Bonjour, je regarde Achta Mahamat"},
                  {"role": "assistant", "contenu": "Achta Mahamat a un dossier accorde."}]
    reponse = repondre(db, "Quel est le risque de Achta ?", historique=historique,
                       utilisateur=_agent())

    envoye = " ".join(m["content"] for m in faux.messages)
    assert "Achta" not in envoye and "Mahamat" not in envoye
    assert reponse == "Achta Mahamat presente un risque faible."


# --- Reponse progressive (streaming) ----------------------------------------

def test_flux_retablit_un_nom_coupe_entre_deux_morceaux():
    d = DemasqueurFlux(Pseudonymes([(12, "Achta Mahamat")]))
    morceaux = ["Le dossier de Cli", "ent", "#1", "2 est accord", "é.<b", "r>Fin"]
    sortie = "".join(d.ajouter(m) for m in morceaux) + d.terminer()
    assert sortie == "Le dossier de Achta Mahamat est accordé.\nFin"


def test_flux_n_envoie_jamais_d_identifiant_partiel():
    d = DemasqueurFlux(Pseudonymes([(12, "Achta Mahamat")]))
    for morceau in ["Voir Client", "#", "1"]:
        assert "Client" not in d.ajouter(morceau)


def test_route_flux_envoie_et_enregistre_la_reponse(db, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app import conversation_routes
    from app.security import utilisateur_courant

    c = _client(db, "Achta Mahamat")
    agent = models.User(nom="Fatime Abakar", email="agent@exemple.com", mot_de_passe="x", role="agent")
    db.add(agent)
    db.commit()
    conv = models.Conversation(titre="Nouvelle conversation", user_id=agent.id)
    db.add(conv)
    db.commit()

    faux = FauxGroq(None, morceaux=["Client#", f"{c.id} a un ", "risque faible."])
    monkeypatch.setattr(chatbot_service, "client_groq", faux)
    app = FastAPI()
    app.include_router(conversation_routes.router)
    app.dependency_overrides[utilisateur_courant] = lambda: SessionLocal().get(models.User, agent.id)

    r = TestClient(app).post(f"/conversations/{conv.id}/message/flux",
                             json={"question": "Et Achta Mahamat ?"})

    assert r.status_code == 200
    assert r.text == "Achta Mahamat a un risque faible."
    envoye = " ".join(m["content"] for m in faux.messages)
    assert "Achta" not in envoye
    db.expire_all()
    messages = db.query(models.Message).filter(models.Message.conversation_id == conv.id).all()
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].contenu == "Achta Mahamat a un risque faible."
