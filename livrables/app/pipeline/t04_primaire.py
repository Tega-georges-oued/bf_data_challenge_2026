"""T04 - Primaire : effectifs et redoublants par province, niveau, sexe et année scolaire.

Source : MEBAPLN/DGESS, Annuaires statistiques de l'enseignement primaire, éditions 2017/2018 à
2024/2025 (CNS 521 à 530, Data Pack), tableau VIII.3 « Historique des effectifs et des redoublants
par niveau et par province » (chaque édition couvre environ dix années).
Lecture : texte du PDF avec mise en page (cache historique ou PyMuPDF) ; la version CSV du Data Pack mélange
l'ordre des lignes sur certaines pages.
Règle de choix : pour chaque province-année-niveau-sexe, la valeur de l'édition la plus récente ;
les écarts entre éditions sont gardés et comptés (révisions).
Sorties :
  - 02_nettoyage : effectifs-primaire-provinces (valeur retenue + édition source + nb d'éditions)
  - 02_nettoyage : effectifs-primaire-provinces-toutes-editions (toutes les lectures, pour contrôle)
  - 02_nettoyage : journal-T04-primaire
"""
import sys, re
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from utils import PACK, norm, num, out_path, ROOT
from lecture_pdf import texte_pdf, OutilManquant

ANN = PACK / "01_Education_MENAPLN_DGESS/CNS_DGESS/Annuaires"
EDITIONS = {  # fichier -> édition (année scolaire de l'annuaire)
    "CNS521": "2017/2018", "CNS522": "2018/2019", "CNS523": "2019/2020", "CNS524": "2020/2021",
    "CNS525": "2021/2022", "CNS526": "2022/2023", "CNS529": "2023/2024", "CNS530": "2024/2025"}
NIV = ["CP1", "CP2", "CE1", "CE2", "CM1", "CM2", "TOTAL"]
SEXE = {"GARCONS": "G", "FILLES": "F", "TOTAL": "T"}
TITRE = "HISTORIQUE DES EFFECTIFS ET DES REDOUBLANTS PAR NIVEAU ET PAR PROVINCE"

alias = pd.read_csv(next((ROOT / "livrables" / "01_collecte").glob("*alias-noms-geographiques*")), sep=";")
old = alias[(alias.niveau == "province") & (alias.decoupage == "ancien")]
prov_alias = dict(zip(old.alias, old.code))
prov_alias.update({"LES BALE": prov_alias["BALE"], "ZOUNWEOGO": prov_alias["ZOUNDWEOGO"],
                   "KOURITENGA": prov_alias["KOURITTENGA"], "KOMONDJARI": prov_alias["KOMANDJARI"],
                   "KOMANDJOARI": prov_alias["KOMANDJARI"]})
regions_anciennes = set(alias[(alias.niveau == "region") & (alias.decoupage == "ancien")].alias)
journal = []

def yr(lbl):  # '2023/2024' -> 2023
    return int(lbl[:4])

def parse_edition(code, edition):
    pdf = next(ANN.glob(code + "_*.pdf"))
    txt = texte_pdf(pdf)
    blocks = []                     # [province, étiquette lue (ou None), page, [(sexe, valeurs)]]
    prov = None
    for page_no, page in enumerate(txt.split("\f"), start=1):
        if TITRE not in page:
            continue
        for line in page.splitlines():
            cells = [c for c in re.split(r"\s{2,}", line.strip()) if c]
            if not cells:
                continue
            n0 = norm(cells[0])
            if len(cells) == 1:
                if re.fullmatch(r"\d{4}/\d{4}", cells[0]):
                    if prov:
                        if blocks and blocks[-1][0] == prov and blocks[-1][1] is None and not blocks[-1][3]:
                            blocks[-1][1] = cells[0]          # étiquette du bloc ouvert par l'en-tête
                        else:
                            blocks.append([prov, cells[0], page_no, []])
                    continue
                if n0 in prov_alias:
                    if norm(n0) != prov:
                        prov = n0
                        blocks.append([prov, None, page_no, []])  # bloc ouvert, étiquette à venir
                    continue
                if n0 in regions_anciennes or n0.startswith("TOTAL") or n0 == "BURKINA FASO":
                    prov = None; continue
                continue
            if n0 in SEXE and prov and blocks and blocks[-1][0] == prov and len(cells) > 1 and num(cells[1]) is not None:
                if SEXE[n0] in {x[0] for x in blocks[-1][3]}:     # 2e jeu G/F/T sans étiquette : nouveau bloc
                    blocks.append([prov, None, page_no, []])
                blocks[-1][3].append((SEXE[n0], [num(c) for c in cells[1:]]))
    blocks = [b for b in blocks if b[3]]
    return blocks

def total_T(lines):
    for sx, v in lines:
        if sx == "T" and len(v) == 14:
            return v[12]
    g = next((v for sx, v in lines if sx == "G" and len(v) == 14), None)
    f = next((v for sx, v in lines if sx == "F" and len(v) == 14), None)
    return g[12] + f[12] if g and f else None

def fiable(lbl, prev_lbl, ed_y):
    return (lbl is not None and int(lbl[5:]) == int(lbl[:4]) + 1 and yr(lbl) <= ed_y
            and (prev_lbl is None or yr(lbl) == yr(prev_lbl) - 1))

def to_rows(edition, p, lbl, pg, lines, statut):
    out, got = [], {}
    for sx, v in lines:
        if len(v) != 14:
            journal.append({"etape": "T04", "edition": edition, "province": p, "annee": lbl, "page_pdf": pg,
                            "objet": f"ligne {sx} incomplète ou cellules fusionnées ({len(v)} valeurs) : écartée",
                            "detail": " ".join(str(x) for x in v)})
        else:
            got[sx] = v
    if "T" not in got and "G" in got and "F" in got:
        got["T"] = [got["G"][k] + got["F"][k] for k in range(14)]
        journal.append({"etape": "T04", "edition": edition, "province": p, "annee": lbl, "page_pdf": pg,
                        "objet": "ligne T recalculée (garçons + filles)", "detail": ""})
    for sx, o in (("F", "G"), ("G", "F")):
        if sx not in got and "T" in got and o in got:
            got[sx] = [got["T"][k] - got[o][k] for k in range(14)]
            journal.append({"etape": "T04", "edition": edition, "province": p, "annee": lbl, "page_pdf": pg,
                            "objet": f"ligne {sx} recalculée (total - autre sexe)", "detail": ""})
    for sx, v in got.items():
        for k, niv in enumerate(NIV):
            out.append({"edition": edition, "old_adm2_pcode": prov_alias[p], "province_annuaire": p,
                        "annee_scolaire": lbl, "niveau": niv, "sexe": sx, "effectif": v[2 * k],
                        "redoublants": v[2 * k + 1], "page_pdf": pg, "statut_annee": statut})
    return out

# Passe 1 : lecture de toutes les éditions ; une étiquette est fiable si elle est bien formée et suit
# exactement l'année précédente lue (ou ouvre la série) ; référentiel (province, total) -> année.
try:
    parsed = {ed: parse_edition(code, ed) for code, ed in EDITIONS.items()}
except OutilManquant as e:
    sys.exit(str(e))
ref = {}
for ed, blocks in parsed.items():
    prev = {}
    for b in blocks:
        p, lbl, lines = b[0], b[1], b[3]
        ok = fiable(lbl, prev.get(p), yr(ed))
        b.append(ok)
        if lbl is not None:
            prev[p] = lbl
        t = total_T(lines)
        if ok and t is not None:
            ref.setdefault((p, t), set()).add(lbl)
# Passe 2 : attribution des années
allrows = []
for ed, blocks in parsed.items():
    by_p = {}
    for b in blocks:
        by_p.setdefault(b[0], []).append(b)
    for p, bl in by_p.items():
        seen_lines, used, last_y = [], set(), None
        for (pv, lbl, pg, lines, ok) in bl:
            if lines in seen_lines:
                journal.append({"etape": "T04", "edition": ed, "province": p, "annee": lbl, "page_pdf": pg,
                                "objet": "bloc en double (valeurs identiques) : supprimé", "detail": ""})
                continue
            seen_lines.append(lines)
            t = total_T(lines)
            cand = ref.get((p, t), set()) - used if t is not None else set()
            if ok and lbl not in used:
                statut = "étiquette lue"
            elif len(cand) == 1:
                new = next(iter(cand)); statut = "étiquette confirmée par une autre édition"
                journal.append({"etape": "T04", "edition": ed, "province": p, "annee": new, "page_pdf": pg,
                                "objet": "année identifiée par les valeurs d'une autre édition", "detail": f"étiquette lue : {lbl}"})
                lbl = new
            else:
                y = yr(ed) if last_y is None else last_y - 1
                new = f"{y}/{y + 1}"
                if new in used:
                    journal.append({"etape": "T04", "edition": ed, "province": p, "annee": new, "page_pdf": pg,
                                    "objet": "bloc sans année identifiable : écarté", "detail": f"étiquette lue : {lbl}"})
                    continue
                statut = "année déduite de l'ordre (non confirmée)"
                journal.append({"etape": "T04", "edition": ed, "province": p, "annee": new, "page_pdf": pg,
                                "objet": "année déduite de l'ordre des blocs, non confirmée", "detail": f"étiquette lue : {lbl}"})
                lbl = new
            used.add(lbl); last_y = yr(lbl)
            allrows += to_rows(ed, p, lbl, pg, lines, statut)
for ed in EDITIONS.values():
    r = [x for x in allrows if x["edition"] == ed]
    print(ed, len(r), "lignes,", len({x["old_adm2_pcode"] for x in r}), "provinces,", len({x["annee_scolaire"] for x in r}), "années")
alled = pd.DataFrame(allrows)

# --- Valeur retenue : édition la plus récente -------------------------------------
k = ["old_adm2_pcode", "annee_scolaire", "niveau", "sexe"]
alled["_rang"] = alled.statut_annee.map({"année déduite de l'ordre (non confirmée)": 0}).fillna(1)
alled = alled.sort_values(["_rang", "edition"])
nb = alled.groupby(k).size().rename("nb_editions")
rev = alled.groupby(k).effectif.agg(lambda s: s.max() - s.min()).rename("ecart_entre_editions")
best = alled.groupby(k).tail(1).set_index(k).join(nb).join(rev).reset_index()
best = best.rename(columns={"edition": "edition_source"}).drop(columns="_rang")
alled = alled.drop(columns="_rang")

contemp = alled[alled.edition == alled.annee_scolaire].set_index(k)[["effectif", "redoublants"]].rename(
    columns={"effectif": "effectif_edition_de_l_annee", "redoublants": "redoublants_edition_de_l_annee"})
contemp = contemp[~contemp.index.duplicated()]
best = best.set_index(k).join(contemp).reset_index()
best = best[best.annee_scolaire >= "2008/2009"]          # 2007/2008 : une seule province, hors période

# --- Validation externe : totaux par ancienne région contre la base principale du challenge
base = next((ROOT / "donnees").glob("DONNEES_STATISTQUES*.xlsx"))
f1 = pd.read_excel(base, sheet_name="Feuil1", header=None)
reg_rows, cur = [], None
for _, r in f1.iloc[2:].iterrows():
    if isinstance(r[0], str) and r[0].strip():
        cur = r[0].strip()
    if cur and isinstance(r[1], str) and r[1].strip().upper() == "TOTAL":
        for j, an in enumerate(range(2015, 2025)):
            reg_rows.append({"region": norm(cur), "annee_scolaire": f"{an}/{an + 1}", "effectif_base": r[2 + j]})
bref = pd.DataFrame(reg_rows)
oldreg = dict(zip(alias[(alias.niveau == "region") & (alias.decoupage == "ancien")].code,
                  alias[(alias.niveau == "region") & (alias.decoupage == "ancien")].alias))
tt = best[(best.niveau == "TOTAL") & (best.sexe == "T")].copy()
tt["region"] = tt.old_adm2_pcode.str[:4].map(oldreg)
agg = tt.groupby(["region", "annee_scolaire"], as_index=False).effectif.sum()
cmp_ = bref.merge(agg, on=["region", "annee_scolaire"], how="left")
cmp_["ecart"] = cmp_.effectif - cmp_.effectif_base
cmp_.to_csv(out_path("02-nettoyage", "engineer", "controle-T04-totaux-regions-vs-base-principale"), sep=";", index=False, encoding="utf-8")
journal.append({"etape": "T04", "objet": "contrôle des totaux régionaux contre la base principale",
                "detail": f"{(cmp_.ecart == 0).sum()} cas identiques sur {len(cmp_)} ; écart absolu max {cmp_.ecart.abs().max():.0f}"})
print("contrôle base principale :", (cmp_.ecart == 0).sum(), "/", len(cmp_), "identiques ; écarts non nuls :")
print(cmp_[cmp_.ecart != 0].to_string(index=False))

# --- Contrôles de cohérence sur la valeur retenue ----------------------------------
w = best.pivot_table(index=["old_adm2_pcode", "annee_scolaire", "niveau"], columns="sexe", values="effectif")
e = (w["G"] + w["F"] - w["T"]).abs()
for kk, v in e[e > 0].items():
    journal.append({"etape": "T04", "province": kk[0], "annee": kk[1], "objet": "garçons + filles différent du total",
                    "detail": f"{kk[2]} écart {v:.0f}"})
s_ = best[best.niveau != "TOTAL"].groupby(["old_adm2_pcode", "annee_scolaire", "sexe"])[["effectif", "redoublants"]].sum()
t_ = best[best.niveau == "TOTAL"].set_index(["old_adm2_pcode", "annee_scolaire", "sexe"])[["effectif", "redoublants"]]
d_ = (s_ - t_).abs()
for kk, row in d_[(d_ > 0).any(axis=1)].iterrows():
    journal.append({"etape": "T04", "province": kk[0], "annee": kk[1], "objet": "somme des niveaux différente du total publié",
                    "detail": f"sexe {kk[2]}, écart effectif {row.effectif:.0f}, redoublants {row.redoublants:.0f}"})
for _, b in best[best.redoublants > best.effectif].iterrows():
    journal.append({"etape": "T04", "province": b.old_adm2_pcode, "annee": b.annee_scolaire,
                    "objet": "redoublants supérieurs à l'effectif", "detail": f"{b.niveau} {b.sexe}"})
revs = best[(best.niveau == "TOTAL") & (best.sexe == "T") & (best.ecart_entre_editions > 0)]
journal.append({"etape": "T04", "objet": "révisions entre éditions (total province-année)",
                "detail": f"{len(revs)} cas ; écart médian {revs.ecart_entre_editions.median() if len(revs) else 0:.0f} élèves"})

alled.to_csv(out_path("02-nettoyage", "engineer", "effectifs-primaire-provinces-toutes-editions"), sep=";", index=False, encoding="utf-8")
f = out_path("02-nettoyage", "engineer", "effectifs-primaire-provinces")
best.to_csv(f, sep=";", index=False, encoding="utf-8")
pd.DataFrame(journal).to_csv(out_path("02-nettoyage", "engineer", "journal-T04-primaire"), sep=";", index=False, encoding="utf-8")
cov = best[(best.niveau == "TOTAL") & (best.sexe == "T")].groupby("annee_scolaire").old_adm2_pcode.nunique()
print(f.name, len(best), "lignes ; provinces par année :", cov.to_dict())
print("journal :", pd.DataFrame(journal).objet.value_counts().to_dict())
