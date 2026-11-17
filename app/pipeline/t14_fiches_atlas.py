"""T14 - Fiches régionales (17, une page chacune) et atlas national. Dépôt 05_interpretation.

Usage : python t14_fiches_atlas.py [--racine CHEMIN_BF_DATA_CHALLENGE]
Entrées : 03_transformation (indicateurs), 04_analyse (prévision, SHAP, typologie, bilan), app/data (limites, grille d'actions).
Sorties : 05_interpretation/  fiche-region-<nom>_v1.pdf (x17), fiches-17-regions_v1.pdf, atlas-national_v1.pdf,
          prevision-abandon-primaire-2024-25-17-regions_v1.csv
"""
import argparse, json, unicodedata, io
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Patch
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether)
from reportlab.lib.styles import ParagraphStyle

ap = argparse.ArgumentParser()
ap.add_argument("--racine", type=Path, default=Path(__file__).resolve().parents[2])
ROOT = ap.parse_args().racine
OUT = ROOT / "05_interpretation"; OUT.mkdir(exist_ok=True)
TEAM = "VIGIE-Ecole-Team"
def op(role, desc, ext="pdf"):
    return OUT / f"{TEAM}_05-interpretation_D1_{role}_{desc}_v1.{ext}"
def latest(folder, pat):
    return sorted((ROOT / folder).glob(f"*{pat}*"))[-1]
def slug(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(" ", "-").replace("'", "")

for nm, f in [("DV", "DejaVuSans.ttf"), ("DVB", "DejaVuSans-Bold.ttf")]:
    for d in ["/usr/share/fonts/truetype/dejavu/", str(Path(matplotlib.get_data_path()) / "fonts/ttf") + "/"]:
        if Path(d + f).exists():
            pdfmetrics.registerFont(TTFont(nm, d + f)); break
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})

prev = pd.read_csv(latest("04_analyse", "prevision-abandon-primaire"), sep=";")
typo = pd.read_csv(latest("04_analyse", "typologie-17-regions"), sep=";")
imp = pd.read_csv(latest("04_analyse", "importance-globale-facteurs"), sep=";")
B = json.load(open(latest("04_analyse", "bilan-modele"), encoding="utf-8"))
r17 = pd.read_csv(latest("03_transformation", "indicateurs-decrochage-17-regions"), sep=";")
p47 = pd.read_csv(latest("03_transformation", "indicateurs-decrochage-47-provinces"), sep=";")
nat = pd.read_csv(latest("03_transformation", "indicateurs-decrochage-national"), sep=";")
geo2 = json.load(open(ROOT / "app/data/limites_admin2_simplifiees.geojson", encoding="utf-8"))
geo1 = json.load(open(ROOT / "app/data/limites_admin1_simplifiees.geojson", encoding="utf-8"))
actions = pd.read_csv(ROOT / "app/data/grille_actions.csv", sep=";")
ALERTE = {"rouge": "#c0392b", "orange": "#e67e22", "jaune": "#f1c40f"}
GRIS = "#dddddd"

# ---- agrégat régional de la prévision ----
reg = prev.groupby(["adm1_pcode", "adm1_name"]).apply(lambda g: pd.Series({
    "prevision": np.average(g.prevision, weights=g.effectif_cp1_cm1_2024),
    "effectif_cp1_cm1_2024": g.effectif_cp1_cm1_2024.sum(),
    "decrocheurs_attendus": g.decrocheurs_attendus.sum(),
    "provinces": len(g), "provinces_alerte_rouge": int((g.niveau_alerte == "rouge").sum()),
    "abandon_observe_2023_24": np.average(g.abandon_observe_2023_24.fillna(g.prevision), weights=g.effectif_cp1_cm1_2024),
    "cause_dominante_majoritaire": g.cause_dominante.value_counts().index[0]}), include_groups=False).reset_index()
reg = reg.merge(typo[["adm1_name", "profil_regional"]], on="adm1_name", how="left").sort_values("prevision", ascending=False)
reg["rang"] = range(1, len(reg) + 1)
reg.round(2).to_csv(op("analyst", "prevision-abandon-primaire-2024-25-17-regions", "csv"), sep=";", index=False)

# ---- outils cartes ----
def polys(ft):
    g = ft["geometry"]
    return g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]

def dessiner(ax, geo, key, couleur, contour="white", lw=0.5, labels=None):
    for ft in geo["features"]:
        c = couleur(ft["properties"][key])
        for p in polys(ft):
            ax.add_patch(MPoly(np.array(p[0]), closed=True, fc=c, ec=contour, lw=lw))
    ax.autoscale_view(); ax.set_aspect("equal"); ax.axis("off")

def centroide(ft):
    p = max(polys(ft), key=lambda q: len(q[0]))[0]
    a = np.array(p); return a[:, 0].mean(), a[:, 1].mean()

def fig_png(fig, dpi=200):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=dpi, bbox_inches="tight"); plt.close(fig); b.seek(0); return b

pcol = prev.set_index("adm2_pcode")
def couleur_alerte(code):
    return ALERTE.get(pcol.niveau_alerte.get(code), GRIS)

# ---- styles ----
S = {k: ParagraphStyle(k, fontName="DV", fontSize=v[0], leading=v[1], textColor=colors.HexColor(v[2]))
     for k, v in {"t": (16, 19, "#1f2d3d"), "st": (8.5, 11, "#555555"), "h": (10, 13, "#1f2d3d"), "p": (8, 10.5, "#222222"),
                  "s": (6.5, 8.5, "#666666"), "k": (15, 17, "#1f2d3d"), "kl": (7, 9, "#555555"), "cell": (7, 8.6, "#222222")}.items()}
S["t"].fontName = S["h"].fontName = S["k"].fontName = "DVB"
def P(t, s="p"):
    return Paragraph(t, S[s])
def fmt(x, d=1):
    return "n.d." if pd.isna(x) else f"{x:,.{d}f}".replace(",", " ").replace(".", ",")

SOURCES = ("Sources : annuaires statistiques MEBAPLN-DGESS (primaire, 2008-09 à 2024-25) et MESFPT-DGESS (post-primaire) ; "
           "INSD, RGPH 2019 ; ACLED (événements jusqu'à septembre 2025) ; CONASUR (personnes déplacées) ; limites IGB/OCHA COD-AB. "
           "Traitement : VIGIE-Ecole-Team, Data Challenge Burkina 2026.")
em = B["erreur_mediane_points_par_zone_gbm"]
LECTURE = (f"Prévision faite à la rentrée 2025 pour l'abandon de l'année 2024-25 (CP1-CM1, convention DGESS). Erreur typique : "
           f"{em['faible']:.0f} pts en zone à faible défi sécuritaire, {em['fort']:.0f} pts en zone à fort défi sécuritaire, où la "
           "fermeture d'écoles peut provoquer des sorties massives imprévisibles. Les facteurs indiquent des associations, pas des "
           "causes prouvées. Les actions sont des propositions à valider par l'équipe éducative.")

eff23 = p47[(p47.annee_depart == "2023/2024") & (p47.sexe == "T")].set_index("adm2_pcode").taux_effet_fermetures.to_dict()
# ---- fiche régionale ----
def fiche(rr):
    region = rr.adm1_name
    pr = prev[prev.adm1_name == region].sort_values("prevision", ascending=False)
    els = [P(f"Région {region} : risque de décrochage scolaire", "t"),
           P(f"Fiche VIGIE-École 2024-2025 · rang {rr.rang} sur 17 · {int(rr.provinces)} province(s) · profil : {rr.profil_regional}", "st"),
           Spacer(1, 4 * mm)]
    k = [[P(fmt(rr.prevision) + " %", "k"), P(fmt(rr.decrocheurs_attendus, 0), "k"),
          P(f"{int(rr.provinces_alerte_rouge)} / {int(rr.provinces)}", "k"), P(fmt(rr.abandon_observe_2023_24) + " %", "k")],
         [P("abandon prévu au primaire, 2024-25", "kl"), P("élèves CP1-CM1 qui risquent d'abandonner", "kl"),
          P("provinces en alerte rouge", "kl"), P("abandon observé en 2023-24", "kl")]]
    kt = Table(k, colWidths=[45 * mm] * 4)
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f5f7")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LINEAFTER", (0, 0), (2, -1), 0.5, colors.white), ("TOPPADDING", (0, 0), (-1, 0), 5)]))
    els += [kt, Spacer(1, 3 * mm)]
    # carte (région mise en évidence) + historique
    fig, ax = plt.subplots(figsize=(3.3, 2.9))
    codes = set(pr.adm2_pcode)
    dessiner(ax, geo2, "adm2_pcode", lambda c: couleur_alerte(c) if c in codes else "#eeeeee", lw=0.3)
    for ft in geo1["features"]:
        if ft["properties"]["adm1_name"] == region:
            for p in polys(ft):
                ax.add_patch(MPoly(np.array(p[0]), closed=True, fc="none", ec="#1f2d3d", lw=1.2))
    for ft in geo2["features"]:
        if ft["properties"]["adm2_pcode"] in codes:
            x, y = centroide(ft); ax.text(x, y, ft["properties"]["adm2_name"], fontsize=5.5, ha="center", va="center")
    bx = np.vstack([np.array(p[0]) for ft in geo1["features"] if ft["properties"]["adm1_name"] == region for p in polys(ft)])
    (x0, y0), (x1, y1) = bx.min(0), bx.max(0); m = max(x1 - x0, y1 - y0) * 0.25 + 0.2
    ax.set_xlim(x0 - m, x1 + m); ax.set_ylim(y0 - m, y1 + m)
    ins = ax.inset_axes([0.0, 0.0, 0.3, 0.3])
    dessiner(ins, geo1, "adm1_name", lambda n: "#1f2d3d" if n == region else "#dddddd", lw=0.2)
    ax.legend(handles=[Patch(fc=v, label=k.capitalize()) for k, v in ALERTE.items()], loc="upper right", fontsize=5.5, frameon=False)
    img1 = Image(fig_png(fig), width=72 * mm, height=63 * mm)
    h = r17[(r17.adm1_name == region) & (r17.sexe == "T")].sort_values("annee_depart")
    hf = r17[(r17.adm1_name == region) & (r17.sexe == "F")].sort_values("annee_depart")
    fig, ax = plt.subplots(figsize=(4.1, 2.9))
    x = h.annee_depart.str[:4].astype(int) + 1
    ax.plot(x, h.taux_abandon_dgess, "-o", ms=2.5, color="#c0392b", label="Abandon publié (DGESS)")
    ax.plot(hf.annee_depart.str[:4].astype(int) + 1, hf.taux_abandon_dgess, ":", color="#c0392b", lw=1, label="dont filles")
    ax.plot(x, h.taux_abandon_corrige, "-", color="#2c3e50", label="Abandon corrigé des fermetures")
    fragile = h.taux_effet_fermetures.abs() > 10
    ax.plot(x[~fragile], h.taux_abandon_corrige[~fragile], "o", ms=2.5, color="#2c3e50")
    if fragile.any():
        ax.plot(x[fragile], h.taux_abandon_corrige[fragile], "o", ms=4, mfc="white", color="#2c3e50",
                label="correction fragile (écoles : variation > 10 %)")
    ax.plot(x, h.taux_abandon_post_primaire, "-s", ms=2.5, color="#16a085", label="Post-primaire (publié)")
    ax.scatter([2025], [rr.prevision], s=40, color="#c0392b", marker="*", zorder=5, label="Prévision 2024-25")
    ax.set_ylabel("% des élèves"); ax.set_title("Évolution de l'abandon (année de fin)", fontsize=8)
    ax.grid(alpha=0.3); ax.spines[["top", "right"]].set_visible(False); ax.legend(fontsize=5.5, frameon=False)
    img2 = Image(fig_png(fig), width=95 * mm, height=67 * mm)
    els += [Table([[img1, img2]], colWidths=[78 * mm, 102 * mm])]
    # tableau des provinces
    rows = [[P("<b>Province</b>", "cell"), P("<b>Prévu 2024-25</b>", "cell"), P("<b>Fourchette 80 %</b>", "cell"),
             P("<b>Observé 2023-24</b>", "cell"), P("<b>Corrigé 2023-24</b>", "cell"), P("<b>Principaux facteurs du risque</b>", "cell")]]
    for _, p in pr.iterrows():
        rows.append([P(f"<font color='{ALERTE[p.niveau_alerte]}'>■</font> {p.adm2_name}", "cell"), P(fmt(p.prevision) + " %", "cell"),
                     P(f"{p.intervalle_80_bas:.0f} à {p.intervalle_80_haut:.0f} %", "cell"), P(fmt(p.abandon_observe_2023_24) + " %", "cell"),
                     P(fmt(p.abandon_corrige_2023_24) + " %" + (" *" if abs(eff23.get(p.adm2_pcode, 0)) > 10 else ""), "cell"),
                     P(str(p.trois_facteurs_principaux), "cell")])
    tt = Table(rows, colWidths=[27 * mm, 18 * mm, 21 * mm, 19 * mm, 19 * mm, 76 * mm], repeatRows=1)
    tt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#1f2d3d")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")])]))
    els += [Spacer(1, 2 * mm), P("Provinces", "h"), tt]
    if any(abs(eff23.get(c, 0)) > 10 for c in pr.adm2_pcode):
        els.append(P("* Correction fragile : le nombre d'écoles a varié de plus de 10 % (fermetures ou réouvertures massives).", "s"))
    els.append(Spacer(1, 3 * mm))
    # pistes d'action
    causes = pr.cause_dominante.value_counts().index.tolist()[:2]
    act = actions[actions.cause.isin(causes)]
    els.append(P("Pistes d'action (à valider par l'équipe éducative)", "h"))
    for c in causes:
        a = act[act.cause == c]
        if len(a):
            els.append(P(f"<b>{c}</b> : " + " · ".join(f"{n} : {t[0].lower() + t[1:]}" for n, t in zip(a.niveau, a.action)), "p"))
    els += [Spacer(1, 3 * mm), P(LECTURE, "s"), Spacer(1, 1 * mm), P(SOURCES, "s")]
    return els

def doc(path):
    return SimpleDocTemplate(str(path), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=10 * mm,
                             title="VIGIE-École", author=TEAM)

tous = []
for _, rr in reg.iterrows():
    e = fiche(rr)
    doc(op("analyst", f"fiche-region-{slug(rr.adm1_name)}")).build(e)
    tous += fiche(rr) + [PageBreak()]
doc(op("analyst", "fiches-17-regions")).build(tous[:-1])

# ---- atlas national ----
def carte_continue(valeurs, titre, cmap="OrRd", fmtv="{:.0f}", vmin=None, vmax=None, unite="%"):
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    v = pd.Series(valeurs); vmin = v.min() if vmin is None else vmin; vmax = v.quantile(0.95) if vmax is None else vmax
    cm = plt.get_cmap(cmap); norm = matplotlib.colors.Normalize(vmin, vmax)
    dessiner(ax, geo2, "adm2_pcode", lambda c: cm(norm(v[c])) if c in v and pd.notna(v[c]) else GRIS, lw=0.3)
    dessiner(ax, geo1, "adm1_pcode", lambda c: "none", contour="#333333", lw=0.8)
    for ft in geo1["features"]:
        x, y = centroide(ft); ax.text(x, y, ft["properties"]["adm1_name"], fontsize=6.5, ha="center", color="#111111",
                                      bbox=dict(fc="white", alpha=0.6, lw=0, pad=0.5))
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cm); cb = fig.colorbar(sm, ax=ax, shrink=0.6, pad=0.01); cb.set_label(unite)
    ax.set_title(titre, fontsize=10)
    return fig_png(fig)

def T(t):
    return ParagraphStyle("x", parent=S["t"], fontSize=13, leading=16)

pages = []
def page(titre, img, texte, w=175):
    pages.extend([Paragraph(titre, T(titre)), Spacer(1, 2 * mm), Image(img, width=w * mm, height=w * 0.78 * mm), Spacer(1, 2 * mm),
                  P(texte), Spacer(1, 2 * mm), P(SOURCES, "s"), PageBreak()])

pages += [Spacer(1, 50 * mm), P("Atlas national du décrochage scolaire", "t"), Spacer(1, 3 * mm),
          P("Burkina Faso · 17 régions · 47 provinces · VIGIE-École, édition 2024-2025", "st"), Spacer(1, 8 * mm),
          P("Cet atlas rassemble, sur le découpage territorial de 2025, la mesure de l'abandon scolaire corrigée des fermetures "
            "d'écoles, la prévision pour 2024-25, les facteurs de risque et les profils régionaux. Chaque carte indique sa source.")]
pages += [PageBreak()]
# 1 alerte
fig, ax = plt.subplots(figsize=(6.6, 5.2))
dessiner(ax, geo2, "adm2_pcode", couleur_alerte, lw=0.3); dessiner(ax, geo1, "adm1_pcode", lambda c: "none", contour="#333333", lw=0.8)
for ft in geo2["features"]:
    c = ft["properties"]["adm2_pcode"]
    if pcol.niveau_alerte.get(c) == "rouge":
        x, y = centroide(ft); ax.text(x, y, ft["properties"]["adm2_name"], fontsize=5.5, ha="center", color="white", weight="bold")
ax.legend(handles=[Patch(fc=v, label=k.capitalize()) for k, v in ALERTE.items()], loc="lower right", frameon=False)
ax.set_title("Niveau d'alerte 2024-25 (abandon prévu au primaire)", fontsize=10)
top = prev.head(10)
page("1. Où le risque d'abandon est le plus élevé en 2024-25", fig_png(fig),
     f"Abandon prévu au niveau national : {fmt(np.average(prev.prevision, weights=prev.effectif_cp1_cm1_2024))} %, soit environ "
     f"{fmt(prev.decrocheurs_attendus.sum(), 0)} élèves de CP1 à CM1. Rouge : les 20 % de provinces au risque le plus élevé "
     f"(≥ {B['seuils_alerte']['rouge']:.1f} %). Les plus exposées : " + ", ".join(f"{a} ({fmt(b)} %)" for a, b in zip(top.adm2_name, top.prevision)) + ".")
# 2 abandon corrigé 2023-24
t23 = p47[(p47.annee_depart == "2023/2024") & (p47.sexe == "T")].set_index("adm2_pcode")
page("2. Abandon réel estimé en 2023-24 (corrigé des fermetures et réouvertures d'écoles)",
     carte_continue(t23.taux_abandon_corrige, "Abandon corrigé 2023-24, primaire (%)"),
     "Le taux publié soustrait les élèves revenus dans les écoles rouvertes et masque ainsi des abandons. La correction retire "
     "l'effet de la variation du nombre d'écoles. Au niveau national : " +
     f"{fmt(nat[(nat.annee_depart=='2023/2024')&(nat.sexe=='T')].taux_abandon_corrige.iloc[0])} % corrigé contre "
     f"{fmt(nat[(nat.annee_depart=='2023/2024')&(nat.sexe=='T')].taux_abandon_dgess.iloc[0])} % publié.")
# 3 effet fermetures 2021-22
t21 = p47[(p47.annee_depart == "2021/2022") & (p47.sexe == "T")].set_index("adm2_pcode")
page("3. L'année de crise 2021-22 : la part des fermetures d'écoles",
     carte_continue(t21.taux_effet_fermetures, "Sorties dues aux fermetures d'écoles, 2021-22 (points de %)", cmap="Greys", vmin=0),
     "En 2021-22, l'abandon publié atteint 20,5 % au niveau national, dont environ 11 points liés aux fermetures d'écoles. "
     "Les provinces sombres sont celles où la fermeture d'écoles explique l'essentiel des sorties.")
# 4 écart filles-garçons
tF = p47[(p47.annee_depart == "2023/2024") & (p47.sexe == "F")].set_index("adm2_pcode").taux_abandon_dgess
tG = p47[(p47.annee_depart == "2023/2024") & (p47.sexe == "G")].set_index("adm2_pcode").taux_abandon_dgess
page("4. Les filles abandonnent-elles plus que les garçons ? (2023-24)",
     carte_continue(tF - tG, "Écart d'abandon filles moins garçons, 2023-24 (points)", cmap="RdBu_r", vmin=-5, vmax=5, unite="points"),
     "Rouge : les filles abandonnent plus que les garçons ; bleu : moins. Au primaire, les filles abandonnent plus que les garçons "
     f"dans {int(((tF - tG) > 0).sum())} provinces sur {int((tF - tG).notna().sum())} ; l'écart dépasse 2 points dans "
     f"{int(((tF - tG) > 2).sum())} d'entre elles. Le risque propre aux filles (mariage précoce, distance) pèse surtout après le primaire.")
# 5 insécurité
ac = prev.set_index("adm2_pcode").acled_evenements_violence_12m_p100k
page("5. Pression sécuritaire de l'année scolaire 2024-25",
     carte_continue(ac, "Événements violents pour 100 000 habitants, oct. 2024 à sept. 2025 (ACLED)", cmap="Purples", unite="pour 100 000"),
     "L'insécurité est le premier facteur de la prévision (importance SHAP). Les provinces les plus touchées cumulent fermetures "
     "d'écoles, déplacements de population et abandon.")
# 6 typologie
pal = dict(zip(sorted(typo.profil_regional.unique()), ["#2e86c1", "#c0392b", "#f39c12", "#27ae60", "#8e44ad"]))
fig, ax = plt.subplots(figsize=(6.6, 5.2))
tp = typo.set_index("adm1_name").profil_regional
dessiner(ax, geo1, "adm1_name", lambda n: pal.get(tp.get(n), GRIS), lw=0.8)
for ft in geo1["features"]:
    x, y = centroide(ft); ax.text(x, y, ft["properties"]["adm1_name"], fontsize=6.5, ha="center", color="white", weight="bold")
ax.legend(handles=[Patch(fc=v, label=k.replace("Dominante : ", "")) for k, v in pal.items()], loc="lower center",
          bbox_to_anchor=(0.5, -0.18), ncol=1, fontsize=6.5, frameon=False)
ax.set_title("Profils régionaux des facteurs de risque", fontsize=10)
page("6. Quatre profils de régions, quatre types de réponse", fig_png(fig),
     "Les régions sont regroupées selon le poids des grandes familles de facteurs dans leur prévision (insécurité et "
     "déplacements, offre scolaire et distance, pauvreté et travail des enfants, situation des filles, inertie scolaire). "
     "Le profil oriente le type d'action ; les fiches régionales détaillent les provinces.")
# 7 importance globale
fam = imp.groupby("famille").shap_moyen_absolu_points.sum().sort_values()
fig, ax = plt.subplots(figsize=(6.6, 3.2))
ax.barh(fam.index, fam.values, color="#2c3e50"); ax.set_xlabel("Contribution moyenne à la prévision (points de %)")
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Poids des familles de facteurs dans la prévision", fontsize=10)
pages.extend([Paragraph("7. Ce qui pèse dans le risque d'abandon", T("")), Spacer(1, 2 * mm), Image(fig_png(fig), width=170 * mm, height=82 * mm),
              P("Les 5 facteurs les plus influents : " + " ; ".join(imp.head(5).libelle) + ". Une forte contribution signale une "
                "association statistique, à confirmer sur le terrain."), Spacer(1, 4 * mm)])
# 8 tableau régional
rows = [[P("<b>Rang</b>", "cell"), P("<b>Région</b>", "cell"), P("<b>Abandon prévu</b>", "cell"), P("<b>Décrocheurs attendus</b>", "cell"),
         P("<b>Provinces rouges</b>", "cell"), P("<b>Profil</b>", "cell")]]
for _, r in reg.iterrows():
    rows.append([P(str(r.rang), "cell"), P(r.adm1_name, "cell"), P(fmt(r.prevision) + " %", "cell"), P(fmt(r.decrocheurs_attendus, 0), "cell"),
                 P(f"{int(r.provinces_alerte_rouge)} / {int(r.provinces)}", "cell"), P(r.profil_regional.replace("Dominante : ", ""), "cell")])
tt = Table(rows, colWidths=[12 * mm, 25 * mm, 22 * mm, 26 * mm, 22 * mm, 73 * mm], repeatRows=1)
tt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")])]))
pages.extend([P("8. Classement des 17 régions", "h"), Spacer(1, 2 * mm), tt, Spacer(1, 3 * mm), P(LECTURE, "s"), P(SOURCES, "s")])
doc(op("analyst", "atlas-national")).build(pages)
print(reg[["rang", "adm1_name", "prevision", "decrocheurs_attendus", "provinces_alerte_rouge"]].round(1).to_string(index=False))
print("fichiers :", len(list(OUT.glob("*.pdf"))))
