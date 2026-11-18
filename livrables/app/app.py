"""VIGIE-École - application d'aide à la décision (Défi 1, Data Challenge Burkina 2026).

Lancement depuis la racine : python -m streamlit run livrables/app/app.py
Fonctionne sans connexion. Lit les dépôts 03_transformation, 04_analyse et 05_interpretation.
"""
import json
import re
from pathlib import Path
import traceback
import streamlit as st

st.set_page_config(page_title="VIGIE-École", page_icon="🧭", layout="wide")
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] {padding-top: 3rem; max-width: 1440px;}
[data-testid="stMain"] h1 {font-size: clamp(1.85rem, 3.4vw, 2.65rem); letter-spacing: -.035em; line-height: 1.13;}
[data-testid="stMain"] h2, [data-testid="stMain"] h3 {letter-spacing: -.018em;}
[data-testid="stSidebarContent"] h1 {font-size: 1.6rem; letter-spacing: -.03em;}
[data-testid="stMetric"] {
    border: 1px solid var(--border-color, rgba(128,128,128,.3));
    border-top: 3px solid var(--primary-color, currentColor);
    border-radius: .4rem;
    padding: .85rem 1rem;
    background: var(--secondary-background-color, transparent);
    height: 100%;
}
[data-testid="stMetricValue"] {font-variant-numeric: tabular-nums;}
.st-key-perspective_tableau [data-testid="stMarkdownContainer"] {overflow-x: auto;}
.st-key-perspective_tableau table {min-width: 760px;}
.st-key-perspective_tableau th:nth-child(2) {min-width: 260px;}
.vigie-legende {display:flex; flex-wrap:wrap; gap:.5rem 1.25rem; margin:.25rem 0 .75rem;}
.vigie-legende span {display:inline-flex; align-items:center; gap:.45rem; font-size:.88rem;}
.vigie-legende i {display:inline-block; width:.8rem; height:.8rem; border-radius:.18rem;}
</style>
""", unsafe_allow_html=True)

try:
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
except Exception as e:  # bibliothèque absente : message clair au lieu d'une erreur technique
    st.error(f"Bibliothèque manquante ou défectueuse : {e}. Dans un terminal, depuis le dossier BF_DATA_CHALLENGE : "
             "pip install -r livrables/app/requirements.txt, puis relancer l'application.")
    st.stop()

APP = Path(__file__).resolve().parent
ROOT = APP.parent.parent
ALERTE = {"rouge": "#c0392b", "orange": "#e67e22", "jaune": "#f1c40f"}

def latest(folder, pattern, extension):
    candidates = (ROOT / "livrables" / folder).glob(f"*{pattern}*_v*.{extension}")
    def version(path):
        match = re.search(r"_v(\d+)$", path.stem)
        return int(match[1]) if match else -1
    return max((p for p in candidates if p.is_file() and version(p) >= 0),
               key=lambda p: (version(p), p.name), default=None)

FICHIERS = {  # clé -> (dépôt, motif du nom, type)
    "prev": ("04_analyse", "prevision-abandon-primaire-2024-25-47-provinces", "csv"),
    "shap": ("04_analyse", "explication-facteurs-shap", "csv"),
    "imp": ("04_analyse", "importance-globale-facteurs", "csv"),
    "fiab": ("04_analyse", "fiabilite-par-annee-test", "csv"),
    "synth": ("04_analyse", "fiabilite-synthese-modeles", "csv"),
    "equite": ("04_analyse", "equite-erreurs-par-groupe", "csv"),
    "calib": ("04_analyse", "calibration-deciles", "csv"),
    "typo": ("04_analyse", "typologie-17-regions", "csv"),
    "bilan": ("04_analyse", "bilan-modele", "json"),
    "p47": ("03_transformation", "indicateurs-decrochage-47-provinces", "csv"),
    "r17": ("03_transformation", "indicateurs-decrochage-17-regions", "csv"),
    "nat": ("03_transformation", "indicateurs-decrochage-national", "csv"),
}
LOCAUX = {"geo2": "data/limites_admin2_simplifiees.geojson", "geo1": "data/limites_admin1_simplifiees.geojson",
          "actions": "data/grille_actions.csv"}
COLONNES = {"prev": ["adm1_pcode", "adm1_name", "adm2_pcode", "adm2_name", "prevision", "intervalle_80_bas", "intervalle_80_haut",
                     "niveau_alerte", "effectif_cp1_cm1_2024", "decrocheurs_attendus", "cause_dominante"],
            "actions": ["cause", "niveau", "action", "unite_de_mesure", "eleves_par_unite_indicatif", "statut"]}

def lire_csv(chemin):
    for enc in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return pd.read_csv(chemin, sep=";", encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(chemin, sep=";", encoding="latin-1")

def empreinte(path):
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@st.cache_data(show_spinner=False, max_entries=64)
def lire_donnee(path, version):
    if empreinte(path) != version:
        raise OSError("Fichier modifié pendant le chargement")
    if path.suffix in {".json", ".geojson"}:
        valeur = json.loads(path.read_text(encoding="utf-8-sig"))
    else:
        valeur = lire_csv(path)
        if valeur.empty:
            raise ValueError("Table sans données")
    if empreinte(path) != version:
        raise OSError("Fichier modifié pendant le chargement")
    return valeur


def charger():
    D, manquants, erreurs = {}, [], []
    fichiers = [(k, latest(dossier, motif, typ), f"{dossier}/{motif} (*.{typ})")
                for k, (dossier, motif, typ) in FICHIERS.items()]
    fichiers += [(k, APP / rel, rel) for k, rel in LOCAUX.items()]
    for k, chemin, libelle in fichiers:
        try:
            if chemin is None:
                manquants.append(libelle)
                continue
            D[k] = lire_donnee(chemin, empreinte(chemin))
        except FileNotFoundError:
            manquants.append(libelle)
        except (OSError, ValueError) as exc:
            erreurs.append(f"{libelle} : {exc}")
    for k in ("geo1", "geo2"):
        if k in D and (not isinstance(D[k], dict) or not isinstance(D[k].get("features"), list)
                       or not D[k]["features"]):
            erreurs.append(f"{k} : collection geographique vide ou invalide")
    if "bilan" in D and not isinstance(D["bilan"], dict):
        erreurs.append("bilan : objet JSON attendu")
    if "typo" in D and D["typo"].get("adm1_name", pd.Series(dtype=str)).duplicated().any():
        erreurs.append("typo : regions en double")
    if "prev" in D:
        for col in ("prevision", "intervalle_80_bas", "intervalle_80_haut",
                    "effectif_cp1_cm1_2024", "decrocheurs_attendus"):
            if col in D["prev"] and not np.isfinite(pd.to_numeric(D["prev"][col], errors="coerce")).all():
                erreurs.append(f"prev : valeurs numeriques invalides dans {col}")
        if "niveau_alerte" in D["prev"] and not D["prev"]["niveau_alerte"].isin(ALERTE).all():
            erreurs.append("prev : niveau d'alerte inconnu")
        if "adm2_pcode" in D["prev"] and D["prev"]["adm2_pcode"].duplicated().any():
            erreurs.append("prev : provinces en double")
        if "effectif_cp1_cm1_2024" in D["prev"]:
            effectifs = pd.to_numeric(D["prev"]["effectif_cp1_cm1_2024"], errors="coerce")
            if (effectifs < 0).any() or effectifs.sum() <= 0:
                erreurs.append("prev : effectifs incompatibles avec une moyenne ponderee")
    COLONNES["typo"] = ["adm1_name", "profil_regional"]
    for k, cols in COLONNES.items():
        if k in D:
            absentes = [c for c in cols if c not in D[k].columns]
            if absentes:
                erreurs.append(f"{k} : colonnes absentes {absentes}")
    if manquants or erreurs:
        return None, manquants, erreurs
    p = D["prev"].copy()
    p["effectif_cp1_cm1_2024"] = pd.to_numeric(p.effectif_cp1_cm1_2024, errors="coerce").fillna(0)
    p["_pond"] = p.prevision * p.effectif_cp1_cm1_2024
    reg = p.groupby(["adm1_pcode", "adm1_name"], as_index=False).agg(
        _pond=("_pond", "sum"), effectif_cp1_cm1_2024=("effectif_cp1_cm1_2024", "sum"),
        decrocheurs_attendus=("decrocheurs_attendus", "sum"), provinces=("adm2_pcode", "count"),
        provinces_rouges=("niveau_alerte", lambda s: int((s == "rouge").sum())))
    reg["prevision"] = reg._pond / reg.effectif_cp1_cm1_2024.where(reg.effectif_cp1_cm1_2024 > 0)
    reg["decrocheurs_attendus"] = reg.decrocheurs_attendus.round()
    D["prev"] = p.drop(columns="_pond")
    D["reg"] = reg.drop(columns="_pond").merge(D["typo"][["adm1_name", "profil_regional"]], on="adm1_name", how="left")
    D["reg"]["profil_regional"] = D["reg"].profil_regional.fillna("non déterminé")
    return D, [], []

try:
    D, manquants, erreurs = charger()
except (OSError, ValueError, KeyError, TypeError) as exc:
    D, manquants, erreurs = None, [], [str(exc)]
if D is None:
    st.title("VIGIE-École")
    st.error("Les données de l'application sont incomplètes.")
    if manquants:
        st.markdown("**Fichiers introuvables :**\n" + "\n".join(f"- {m}" for m in manquants))
    if erreurs:
        st.markdown("**Fichiers illisibles :**\n" + "\n".join(f"- {m}" for m in erreurs))
    st.info("Verifiez que le ZIP Code a ete entierement extrait, avec les dossiers livrables. "
            "Si une regeneration est en cours, attendez sa fin, puis reessayez.")
    st.button("Reessayer le chargement", key="reessayer_chargement")
    st.stop()

prev, reg = D["prev"], D["reg"]
B = D["bilan"]

st.sidebar.title("VIGIE-École")
st.sidebar.caption("Prévoir le décrochage scolaire, de la province à la région, pour agir à temps.")
page = st.sidebar.radio("Navigation", ["Carte d'alerte", "Fiche région", "Fiche province", "Comprendre l'abandon",
                                       "Où agir et comment", "Fiabilité du modèle", "Perspective", "Données et méthode"])
st.sidebar.markdown("---")
st.sidebar.caption("Découpage : 17 régions, 47 provinces (2025). Sources : DGESS (MEBAPLN, MESFPT), INSD (RGPH 2019), "
                   "ACLED, CONASUR, IGB/OCHA. Équipe VIGIE-Ecole-Team.")

def tableau(ou, df, *, key, hide_index=True, width="stretch"):
    return ou.dataframe(df, hide_index=hide_index, width=width, key=key)


def graphique(ou, fig, *, key, width="stretch"):
    return ou.plotly_chart(fig, width=width, key=key)


def f1(x, d=1, suffixe=""):
    try:
        if x is None or pd.isna(x):
            return "n.d."
        return f"{x:,.{d}f}".replace(",", " ") + suffixe
    except Exception:
        return "n.d."

def carte(df, geo, key, couleur_de, titre, survol, legende=None):
    """Carte hors connexion : polygones tracés dans un repère simple (aucun fond de carte téléchargé)."""
    fig = go.Figure()
    vus = set()
    idx = df.set_index(key)
    for ft in geo["features"]:
        code = ft["properties"][key]
        if code not in idx.index:
            continue
        ligne = idx.loc[code]
        coul, groupe = couleur_de(ligne)
        polys = ft["geometry"]["coordinates"] if ft["geometry"]["type"] == "MultiPolygon" else [ft["geometry"]["coordinates"]]
        for k, poly in enumerate(polys):
            xs, ys = zip(*poly[0])
            fig.add_scatter(x=xs, y=ys, fill="toself", fillcolor=coul, mode="lines", line=dict(color="white", width=0.8),
                            name=groupe, legendgroup=groupe, showlegend=(legende is not None and groupe not in vus and k == 0),
                            hoverinfo="text", text=survol(ligne))
            vus.add(groupe)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=30, b=0), title=titre, plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.02), hoverlabel=dict(bgcolor="white"))
    return fig

def survol_prov(l):
    return (f"<b>{l.adm2_name}</b> ({l.adm1_name})<br>Abandon prévu : {l.prevision:.1f} %<br>"
            f"Cause dominante : {l.cause_dominante}")

try:
    if page == "Carte d'alerte":
        st.title("Carte d'alerte du décrochage scolaire")
        st.caption("Burkina Faso · Primaire (CP1–CM1) · Année scolaire 2024–2025")
        st.caption("Prévision faite à la rentrée 2025 avec les données disponibles à cette date ; la mesure officielle "
                   "arrivera avec l'annuaire 2025-2026. Taux d'abandon CP1-CM1 (convention DGESS).")
        nat_prev = np.average(prev.prevision, weights=prev.effectif_cp1_cm1_2024)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Abandon prévu (national)", f"{nat_prev:.1f} %")
        c2.metric("Décrocheurs attendus (CP1-CM1)", f"{prev.decrocheurs_attendus.sum():,.0f}".replace(",", " "))
        c3.metric("Provinces en alerte rouge", int((prev.niveau_alerte == "rouge").sum()))
        em = B["erreur_mediane_points_par_zone_gbm"]
        c4.metric("Erreur typique (médiane)", f"{em['faible']:.0f} pts / {em['fort']:.0f} pts",
                  help="Zones à faible défi sécuritaire / zones à fort défi sécuritaire (validation 2015-2023).")
        st.info("**Comment lire.** Dans les zones calmes, la prévision par province est précise (erreur typique d'environ "
                f"{em['faible']:.0f} points). Dans les zones à fort défi sécuritaire, une fermeture massive d'écoles peut faire sortir "
                "la moitié des élèves en un an ; aucune donnée publique ne permet de la prévoir. Là, la carte sert surtout à "
                "**classer** les provinces par niveau de risque, pas à donner un chiffre exact.")
        st.subheader("Niveaux d’alerte par province")
        st.markdown(
            '<div class="vigie-legende" aria-label="Légende des niveaux d’alerte">'
            + "".join(f'<span><i aria-hidden="true" style="background:{ALERTE[niveau]}"></i>{libelle}</span>'
                      for niveau, libelle in (("rouge", "Rouge · risque le plus élevé"),
                                              ("orange", "Orange"), ("jaune", "Jaune")))
            + '</div>', unsafe_allow_html=True,
        )
        a, b = st.columns([3, 2])
        ordre = {"rouge": "Rouge (risque le plus élevé)", "orange": "Orange", "jaune": "Jaune"}
        pv = prev.sort_values("niveau_alerte", key=lambda c: c.map({"rouge": 0, "orange": 1, "jaune": 2}))
        graphique(a, carte(pv, D["geo2"], "adm2_pcode", lambda l: (ALERTE[l.niveau_alerte], ordre[l.niveau_alerte]),
                             "Niveau d'alerte par province", survol_prov, legende=None), width="stretch", key="carte_provinces")
        with b:
            st.subheader("Provinces les plus exposées")
            t = prev.sort_values("prevision", ascending=False).head(12).copy()
            t["fourchette"] = t.intervalle_80_bas.round().astype(int).astype(str) + " à " + t.intervalle_80_haut.round().astype(int).astype(str)
            t = t[["adm2_name", "adm1_name", "prevision", "fourchette", "cause_dominante"]]
            t.columns = ["Province", "Région", "Prévu (%)", "Fourchette 80 % (%)", "Cause dominante"]
            tableau(st, t.round(1), hide_index=True, width="stretch", key="provinces_prioritaires")
            st.caption(f"Seuils : rouge ≥ {B['seuils_alerte']['rouge']} % (20 % les plus exposées), orange ≥ {B['seuils_alerte']['orange']} %.")
        st.subheader("Par région")
        r = reg.sort_values("prevision", ascending=False)[["adm1_name", "prevision", "decrocheurs_attendus", "provinces_rouges", "provinces", "profil_regional"]]
        r.columns = ["Région", "Abandon prévu (%)", "Décrocheurs attendus", "Provinces rouges", "Provinces", "Profil des facteurs"]
        r["Décrocheurs attendus"] = r["Décrocheurs attendus"].round(-1).astype(int)
        tableau(st, r.round(1), hide_index=True, width="stretch", key="synthese_regions")

    elif page == "Fiche région":
        st.title("Fiche region")
        st.caption("Primaire · Année scolaire 2024–2025")
        region = st.selectbox("Région", sorted(reg.adm1_name))
        rr = reg[reg.adm1_name == region].iloc[0]
        st.subheader(region)
        c1, c2, c3 = st.columns(3)
        c1.metric("Abandon prévu 2024-25", f"{rr.prevision:.1f} %")
        c2.metric("Décrocheurs attendus", f"{rr.decrocheurs_attendus:,.0f}".replace(",", " "))
        c3.metric("Provinces en alerte rouge", f"{rr.provinces_rouges} / {rr.provinces}")
        st.info(f"Profil des facteurs : **{rr.profil_regional}**")
        pr = prev[prev.adm1_name == region].sort_values("prevision", ascending=False)
        t = pr[["adm2_name", "prevision", "intervalle_80_bas", "intervalle_80_haut", "abandon_observe_2023_24", "abandon_corrige_2023_24",
                "ecart_au_risque_attendu", "niveau_alerte", "trois_facteurs_principaux"]]
        t.columns = ["Province", "Prévu 2024-25 (%)", "Bas", "Haut", "Observé 2023-24 (%)", "Corrigé 2023-24 (%)", "Écart au risque attendu (pts)", "Alerte", "Principaux facteurs"]
        # Ce petit tableau est consultatif : un rendu statique suffit et évite
        # de remonter une grille interactive après le changement de page.
        st.subheader("Niveaux d’alerte des provinces")
        def couleur_alerte(valeur):
            couleur = ALERTE.get(str(valeur), "transparent")
            return f"border-left: 4px solid {couleur}; font-weight: 600"
        st.table(t.round(1).style.map(couleur_alerte, subset=["Alerte"]), hide_index=True)
        st.subheader("Évolution des taux d’abandon")
        h = D["r17"][(D["r17"].adm1_name == region) & (D["r17"].sexe == "T")].sort_values("annee_depart")
        fig = go.Figure()
        fig.add_scatter(x=h.annee_depart, y=h.taux_abandon_dgess, name="Abandon primaire (DGESS)", mode="lines+markers")
        fig.add_scatter(x=h.annee_depart, y=h.taux_abandon_corrige, name="Abandon primaire corrigé des fermetures", mode="lines+markers")
        if "taux_abandon_post_primaire" in h:
            fig.add_scatter(x=h.annee_depart, y=h.taux_abandon_post_primaire, name="Abandon post-primaire (publié)", mode="lines+markers")
        fig.update_layout(height=380, yaxis_title="%", xaxis_title="Année scolaire", margin=dict(t=30))
        graphique(st, fig, width="stretch", key="region_evolution")
        st.subheader("Pistes d'action")
        causes = pr.cause_dominante.value_counts().index.tolist()
        tableau(st, D["actions"][D["actions"].cause.isin(causes)][["cause", "niveau", "action", "statut"]], hide_index=True, width="stretch", key="region_actions")
        pdf = sorted((ROOT / "livrables" / "05_interpretation").glob(f"*fiche-region-{region.lower().replace(' ', '-')}*.pdf"))
        if not pdf:
            import unicodedata
            slug = unicodedata.normalize("NFKD", region).encode("ascii", "ignore").decode().lower().replace(" ", "-")
            pdf = sorted((ROOT / "livrables" / "05_interpretation").glob(f"*fiche-region-{slug}*.pdf"))
        if pdf:
            st.download_button("Télécharger la fiche régionale (PDF)", pdf[-1].read_bytes(), file_name=pdf[-1].name)

    elif page == "Fiche province":
        st.title("Fiche province")
        st.caption("Primaire · Année scolaire 2024–2025")
        province = st.selectbox("Province", sorted(prev.adm2_name))
        pp = prev[prev.adm2_name == province].iloc[0]
        st.subheader(f"{province} · {pp.adm1_name}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Abandon prévu 2024-25", f"{pp.prevision:.1f} %", help=f"Intervalle à 80 % : {pp.intervalle_80_bas:.1f} à {pp.intervalle_80_haut:.1f} %")
        c2.metric("Observé 2023-24", f"{pp.abandon_observe_2023_24:.1f} %" if pd.notna(pp.abandon_observe_2023_24) else "n.d.")
        c3.metric("Corrigé 2023-24", f"{pp.abandon_corrige_2023_24:.1f} %" if pd.notna(pp.abandon_corrige_2023_24) else "n.d.")
        c4.metric("Alerte", pp.niveau_alerte)
        st.subheader("Facteurs associés à la prévision")
        s = D["shap"][D["shap"].adm2_name == province].sort_values("contribution_points")
        s = pd.concat([s.head(5), s.tail(7)]).drop_duplicates("facteur")
        fig = px.bar(s, x="contribution_points", y="libelle", color="famille", orientation="h",
                     labels={"contribution_points": "Contribution à la prévision (points de %)", "libelle": ""})
        fig.update_layout(height=460, margin=dict(t=30), title="Ce qui pèse dans la prévision (au-dessus ou en dessous de la moyenne)")
        graphique(st, fig, width="stretch", key="province_facteurs")
        st.caption("Une contribution indique une association dans le modèle, pas une cause prouvée. À confronter au terrain.")
        h = D["p47"][(D["p47"].adm2_name == province)].pivot_table(index="annee_depart", columns="sexe", values="taux_abandon_dgess").reset_index()
        fig2 = go.Figure()
        for sx, nm in [("F", "Filles"), ("G", "Garçons"), ("T", "Ensemble")]:
            if sx in h:
                fig2.add_scatter(x=h.annee_depart, y=h[sx], name=nm, mode="lines+markers")
        fig2.update_layout(height=340, yaxis_title="Abandon primaire (%)", margin=dict(t=30), title="Évolution par sexe")
        graphique(st, fig2, width="stretch", key="province_evolution")

    elif page == "Comprendre l'abandon":
        st.title("Ce que mesure vraiment le taux d'abandon")
        st.markdown("Le taux d'abandon publié mélange les **vrais abandons**, les **sorties forcées** par la fermeture d'écoles "
                    "et, en sens inverse, les **retours** d'élèves dans les écoles rouvertes. VIGIE-École les sépare.")
        n = D["nat"][D["nat"].sexe == "T"].sort_values("annee_depart")
        fig = go.Figure()
        fig.add_bar(x=n.annee_depart, y=n.taux_effet_fermetures, name="Effet des fermetures (+) / réouvertures (−)", marker_color="#95a5a6")
        fig.add_scatter(x=n.annee_depart, y=n.taux_abandon_dgess, name="Abandon publié (convention DGESS)", mode="lines+markers", line_color="#c0392b")
        fig.add_scatter(x=n.annee_depart, y=n.taux_abandon_corrige, name="Abandon corrigé (estimation)", mode="lines+markers", line_color="#2c3e50")
        fig.update_layout(height=430, yaxis_title="% des élèves CP1-CM1", xaxis_title="Année scolaire", margin=dict(t=30))
        graphique(st, fig, width="stretch", key="abandon_national")
        st.markdown("**Lecture.** En 2021-22, l'abandon publié bondit à 20,5 % ; plus de la moitié s'explique par les fermetures "
                    "d'écoles. En 2022-23 et 2023-24, les réouvertures font revenir des élèves et masquent des abandons réels : "
                    "la mesure corrigée est plus élevée que la mesure publiée.")
        st.caption("Correction approchée : une école fermée retire une part proportionnelle des élèves de la province. "
                   "Disponible depuis 2017-18 (nombre d'écoles publié par province).")

    elif page == "Où agir et comment":
        st.title("Où agir et comment : simulateur de ciblage")
        st.warning("Outil d'aide à la décision. L'efficacité d'une action n'est pas mesurée par ces données : "
                   "elle est une hypothèse que vous renseignez. Les actions proposées sont à valider par le terrain.")
        cause = st.selectbox("Type de réponse", D["actions"].cause.unique())
        act = D["actions"][D["actions"].cause == cause]
        action = st.selectbox("Action", act.action)
        row = act[act.action == action].iloc[0]
        c1, c2, c3 = st.columns(3)
        n_unites = c1.number_input(f"Nombre d'unités ({row.unite_de_mesure})", min_value=1, value=50, step=10)
        par_unite = c2.number_input("Élèves touchés par unité", min_value=1, value=int(row.eleves_par_unite_indicatif))
        eff = c3.slider("Efficacité supposée : baisse relative du risque d'abandon (%)", 0, 50, 10)
        seul_cause = st.checkbox("Cibler seulement les provinces où cette cause domine", value=True)
        cand = prev.copy()
        if seul_cause:
            cand = cand[cand.cause_dominante == cause]
        cand = cand.sort_values("prevision", ascending=False)
        budget, alloc = n_unites * par_unite, []
        for _, p in cand.iterrows():
            if budget <= 0:
                break
            eleves = min(budget, p.effectif_cp1_cm1_2024)
            alloc.append({"Province": p.adm2_name, "Région": p.adm1_name, "Abandon prévu (%)": round(p.prevision, 1),
                          "Élèves couverts": int(eleves), "Abandons évités (selon l'hypothèse)": round(eleves * p.prevision / 100 * eff / 100)})
            budget -= eleves
        al = pd.DataFrame(alloc)
        if al.empty:
            st.info("Aucune province ne correspond à ce critère.")
        else:
            tableau(st, al, hide_index=True, width="stretch", key="simulation_resultats")
            col_evites = "Abandons évités (selon l'hypothèse)"
            st.metric("Abandons évités (selon l'hypothèse d'efficacité)", f1(al[col_evites].sum(), 0))
            st.caption("Règle d'allocation : les moyens vont d'abord aux provinces au risque prévu le plus élevé.")

    elif page == "Fiabilité du modèle":
        st.title("Fiabilité : ce que vaut la prévision")
        st.metric("Réduction de l’erreur par rapport à la reconduction",
                  f"{B['gain_mae_vs_reconduction_pct']} %")
        st.caption("Validation temporelle · 2015–2023")
        st.subheader("Comparaison des modèles")
        s = D["synth"].copy()
        s.columns = ["Modèle", "Erreur absolue moyenne (pts)", "RMSE (pts)", "Corrélation de rang", "Part des abandons captée (top 10 %)", "Rappel du top 10 %"]
        tableau(st, s.round(3), hide_index=True, width="stretch", key="fiabilite_modeles")
        st.markdown(f"Le modèle retenu (**{B['modele_retenu']}**) réduit l'erreur de **{B['gain_mae_vs_reconduction_pct']} %** par rapport à la "
                    f"simple reconduction du taux de l'année précédente. Validation temporelle : chaque année de 2015 à 2023 est prévue "
                    f"avec les seules années antérieures.")
        em, mm = B["erreur_mediane_points_par_zone_gbm"], B["erreur_moyenne_points_par_zone_gbm"]
        st.markdown(f"**Erreur selon le contexte** : zones à faible défi sécuritaire, médiane {em['faible']} pts (moyenne {mm['faible']}) ; "
                    f"zones à fort défi sécuritaire, médiane {em['fort']} pts (moyenne {mm['fort']}). Pondérée par les effectifs, l'erreur "
                    f"moyenne est de {B['mae_ponderee_effectifs_gbm']} pts. Les grandes erreurs viennent des fermetures massives d'écoles "
                    "(2017-18 au Sahel, 2020-21 et 2021-22), imprévisibles avec les données publiques.")
        f = D["fiab"].pivot(index="annee_test", columns="modele", values="mae").reset_index()
        fig = px.line(f, x="annee_test", y=[c for c in f.columns if c != "annee_test"], markers=True,
                      labels={"value": "Erreur absolue moyenne (pts)", "annee_test": "Année prévue", "variable": "Modèle"})
        graphique(st, fig, width="stretch", key="fiabilite_evolution")
        a, b = st.columns(2)
        e = D["equite"].copy(); e.columns = ["Groupe", "Erreur moyenne (pts)", "Biais moyen (pts)", "Observations"]
        a.subheader("Équité"); tableau(a, e.round(2), hide_index=True, width="stretch", key="fiabilite_equite")
        c = D["calib"]
        fig3 = px.scatter(c, x="prevision_moyenne", y="observe_moyen", labels={"prevision_moyenne": "Prévu (%)", "observe_moyen": "Observé (%)"})
        fig3.add_shape(type="line", x0=0, y0=0, x1=c.prevision_moyenne.max(), y1=c.prevision_moyenne.max(), line=dict(dash="dash"))
        b.subheader("Calibration (déciles)"); graphique(b, fig3, width="stretch", key="fiabilite_calibration")
        r = B["test_retrospectif_2021_22"]
        st.subheader("Test rétrospectif : l'année de crise 2021-22")
        st.markdown(f"Abandon observé : **{r['abandon_national_observe']:.1f} %** ; prévu par le modèle : **{r['abandon_national_prevu_modele']:.1f} %** ; "
                    f"par reconduction : {r['abandon_national_prevu_reconduction']:.1f} %. Le modèle retrouve **{int(r['rappel_modele']*100)} %** des provinces "
                    f"du top 10 % contre {int(r['rappel_reconduction']*100)} % pour la reconduction. Il sous-estime le pic national, en grande partie "
                    f"dû aux fermetures d'écoles (abandon corrigé 2021-22 : environ 8,6 %).")
        st.caption(f"Intervalles à 80 % : ± {B['intervalle_80_demi_largeur_points_par_zone']['faible']} pts (défi sécuritaire faible), "
                   f"± {B['intervalle_80_demi_largeur_points_par_zone']['fort']} pts (fort). Couverture observée : {B['couverture_80_moyenne']*100:.0f} %.")

    elif page == "Perspective":
        st.title("Perspective : de VIGIE-École à FASO SCHOOL TRACKER")
        st.container(key="perspective_tableau").markdown("""
    | Horizon | Description | Données | Alerte | Délai |
    |---|---|---|---|---|
    | **Aujourd'hui** · VIGIE-École | Tableau de bord qui estime le décrochage au primaire et aide à repérer les provinces où approfondir le diagnostic. | Annuaires DGESS et signaux de contexte (ACLED, CONASUR) | Par province | Cycle annuel, avec des signaux de contexte mensuels |
    | **Demain** · VIGIE-École + base de la DGESS | Connecter le tableau de bord au recensement scolaire pour passer du diagnostic provincial à un repérage plus fin des établissements à accompagner. | Accès direct aux données du recensement scolaire | Par établissement | Dès la rentrée, selon la disponibilité des données |
    | **Après-demain** · FASO SCHOOL TRACKER | Plateforme nationale centralisée de suivi des parcours et de pilotage de l’éducation et de la formation, de la maternelle à l’université, y compris l’enseignement technique et les formations professionnelles formelles ou non formelles. Elle s’appuierait sur School Tracker, le MVP existant de suivi en établissement, pour relier les inscriptions, transferts, interruptions et reprises, et éclairer la répartition des ressources. | Identifiant unique de l’apprenant, inscriptions, absences, notes et événements de parcours | Au niveau choisi selon les besoins et les données disponibles. Par apprenant, classe ou niveau d’enseignement, établissement, commune, province, région ou au niveau national. | Au trimestre |

    Seul un identifiant unique de l'apprenant permet de savoir si un élève « disparu » a abandonné, a été transféré ou a été déplacé.
    VIGIE-École est conçu pour recevoir ces données sans être refait : chaîne élève → établissement → commune → province → région.

    **Garde-fous** : infrastructure publique hébergée au Burkina Faso, avis de la CIL, loi n° 001-2021/AN, aucune publication de score individuel,
    la décision revient toujours à l'équipe éducative.
    """)

    else:
        st.title("Données et méthode")
        st.markdown("""
    **Mesure.** Cohorte reconstituée (méthode ISU/DGESS) : pour chaque niveau CP1-CM1, abandon = effectif t − promus − redoublants en t+1.
    Vérifiée contre les taux publiés (tableau I.8 des annuaires). Post-primaire : taux publiés par le MESFPT (tableau II.3.11).

    **Série primaire** : 45 anciennes provinces, 2008-09 à 2024-25 ; détail de l'année (2017-18 à 2024-25) et tableau historique
    (2008-09 à 2016-17), contrôlés contre la base principale (387 cases sur 390 identiques).

    **Découpage** : report sur 47 provinces et 17 régions par les codes des communes (COD-AB) ; Soum et Tapoa répartis par la
    population 2019 des communes.

    **Prévision** : gradient boosting, validation temporelle 2015-2023, intervalles conformes par zone de sécurité, explication SHAP.
    Toutes les variables sont celles connues à la rentrée de l'année prévue.

    Le détail est dans la documentation et les dépôts 01 à 05.
    """)
except Exception as e:
    st.error(f"Cette page n'a pas pu s'afficher ({type(e).__name__} : {e}). Les autres pages restent utilisables.")
    with st.expander("Détail technique (à transmettre à l'équipe)"):
        st.code(traceback.format_exc())
