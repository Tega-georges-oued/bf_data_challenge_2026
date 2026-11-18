"""T02 - Référentiel géographique VIGIE-École (17 régions, 47 provinces, 351 communes).

Entrées : COD-AB (IGB/OCHA, version v03 du 01/08/2025) ; population 2019 par commune
(INSD, RGPH 2019, synthèse des résultats définitifs, tableau 12, p. 124-133).
Sorties (01_collecte) :
  - referentiel-communes : une ligne par commune, nouveau et ancien découpage, population 2019
  - passage-anciennes-provinces : poids de répartition ancienne province -> nouvelle province
  - alias-noms : noms normalisés (nouveaux et anciens) -> codes, pour joindre les sources
  - journal T02 (02_nettoyage) : appariements de noms faits par similarité, à relire
"""
import sys, difflib
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from utils import PACK, PACK_CSV, norm, num, out_path

COD = PACK / "04_Cartographie_SIG/COD-AB_limites_administratives/bfa_admin_boundaries.xlsx"
SYN = PACK_CSV / "02_Demographie_INSD/CNS_RGPH2019_Synthese_resultats_definitifs.csv"

# --- 1. Découpage COD-AB -------------------------------------------------------------
a1 = pd.read_excel(COD, sheet_name="bfa_admin1")
a2 = pd.read_excel(COD, sheet_name="bfa_admin2")
a3 = pd.read_excel(COD, sheet_name="bfa_admin3")
old_reg = (a1[["adm1_pcode_old", "adm1_name_old"]].drop_duplicates()
           .rename(columns={"adm1_pcode_old": "old_adm1_pcode", "adm1_name_old": "old_adm1_name"}))
old_prov = (a2[["adm2_pcode_old", "adm2_name_old"]].drop_duplicates()
            .rename(columns={"adm2_pcode_old": "old_adm2_pcode", "adm2_name_old": "old_adm2_name"}))
com = a3[["adm3_pcode", "adm3_name1", "adm2_pcode", "adm2_name1", "adm1_pcode", "adm1_name1",
          "adm3_pcode_old", "area_sqkm"]].rename(columns={
    "adm3_name1": "adm3_name", "adm2_name1": "adm2_name", "adm1_name1": "adm1_name",
    "adm3_pcode_old": "old_adm3_pcode"})
com["old_adm2_pcode"] = com.old_adm3_pcode.str[:6]
com["old_adm1_pcode"] = com.old_adm3_pcode.str[:4]
com = com.merge(old_prov, on="old_adm2_pcode", how="left").merge(old_reg, on="old_adm1_pcode", how="left")
assert com.old_adm2_name.notna().all() and com.old_adm1_name.notna().all()
assert len(com) == 351 and com.adm1_pcode.nunique() == 17 and com.adm2_pcode.nunique() == 47

# --- 2. Population 2019 par commune (tableau région > province > commune) -----------
d = pd.read_csv(SYN, sep=";", dtype=str)
d["page"] = d.page.astype(int)
t = d[(d.page >= 124) & (d.page <= 133) & (d.nb_cellules.astype(int) >= 5)].copy()
t = t[t.c3.map(num).notna()]
t["nom"] = t.c1.str.replace("*", "", regex=False).str.strip()
t["n"] = t.nom.map(norm)
regs = {norm(x): x for x in old_reg.old_adm1_name}
provs = {norm(x): c for x, c in zip(old_prov.old_adm2_name, old_prov.old_adm2_pcode)}
cur_prov, rows, seen, journal = None, [], set(), []
commune_names = set(a3.adm3_name1.map(norm))  # un nom de commune n'est jamais pris pour une province par similarité
for _, r in t.iterrows():
    if r.n in ("BURKINA FASO",) or r.n in regs:
        continue
    # en-tête de province : nom de province (orthographe proche tolérée), différent de la province
    # en cours (une commune peut porter le nom de sa province, ex. Kompienga)
    hit = r.n if r.n in provs else (None if r.n in commune_names else next(iter(difflib.get_close_matches(r.n, list(provs), n=1, cutoff=0.85)), None))
    if hit and provs[hit] != cur_prov and provs[hit] not in seen:
        cur_prov = provs[hit]; seen.add(cur_prov)
        if hit != r.n:
            journal.append({"etape": "T02", "objet": "en-tête de province lu par similarité",
                            "commune_codab": "", "adm3_pcode": "", "nom_rgph_2019": r.nom,
                            "ancienne_province": cur_prov, "score": None})
        continue
    rows.append({"old_adm2_pcode": cur_prov, "nom_rgph": r.nom, "n": r.n,
                 "menages_2019": num(r.c2), "pop_2019": num(r.c3), "hommes_2019": num(r.c4),
                 "femmes_2019": num(r.c5), "page_source": r.page})
p = pd.DataFrame(rows)

# arrondissements de Ouagadougou (Kadiogo) et Bobo-Dioulasso (Houet) -> la commune
city = {"BF1300": "OUAGADOUGOU", "BF5301": "BOBO DIOULASSO"}
arr = p.n.str.startswith("ARRONDISSEMENT")
p.loc[arr, "n"] = p.loc[arr, "old_adm2_pcode"].map(city)
p.loc[arr, "nom_rgph"] = p.loc[arr, "n"].str.title() + " (somme des arrondissements)"
p = (p.groupby(["old_adm2_pcode", "n"], as_index=False)
       .agg(nom_rgph=("nom_rgph", "first"), menages_2019=("menages_2019", "sum"),
            pop_2019=("pop_2019", "sum"), hommes_2019=("hommes_2019", "sum"),
            femmes_2019=("femmes_2019", "sum"), page_source=("page_source", "first")))

# appariement nom par nom, à l'intérieur de chaque ancienne province
com["n"] = com.adm3_name.map(norm)
match = {}
for prov, g in com.groupby("old_adm2_pcode"):
    cand = p[p.old_adm2_pcode == prov]
    libres = dict(zip(cand.n, cand.index))
    for _, c in g.iterrows():
        if c.n in libres:
            match[c.adm3_pcode] = libres.pop(c.n); continue
        best = difflib.get_close_matches(c.n, list(libres), n=1, cutoff=0.6)
        if best:
            match[c.adm3_pcode] = libres.pop(best[0])
            journal.append({"etape": "T02", "objet": "appariement de nom (similarité)",
                            "commune_codab": c.adm3_name, "adm3_pcode": c.adm3_pcode,
                            "nom_rgph_2019": p.loc[match[c.adm3_pcode], "nom_rgph"],
                            "ancienne_province": c.old_adm2_name,
                            "score": round(difflib.SequenceMatcher(None, c.n, best[0]).ratio(), 2)})
        else:
            journal.append({"etape": "T02", "objet": "commune sans population 2019",
                            "commune_codab": c.adm3_name, "adm3_pcode": c.adm3_pcode,
                            "nom_rgph_2019": "", "ancienne_province": c.old_adm2_name, "score": None})
    for n_rest, i in libres.items():
        journal.append({"etape": "T02", "objet": "ligne RGPH non rattachée",
                        "commune_codab": "", "adm3_pcode": "", "nom_rgph_2019": p.loc[i, "nom_rgph"],
                        "ancienne_province": prov, "score": None})
pm = p.loc[list(match.values()), ["nom_rgph", "menages_2019", "pop_2019", "hommes_2019",
                                  "femmes_2019", "page_source"]].copy()
pm.index = list(match.keys())
com = com.drop(columns="n").merge(pm, left_on="adm3_pcode", right_index=True, how="left")

# --- 3. Poids ancienne province -> nouvelle province (population 2019) ---------------
w = (com.groupby(["old_adm2_pcode", "old_adm2_name", "adm2_pcode", "adm2_name", "adm1_pcode", "adm1_name"],
                 as_index=False).pop_2019.sum())
w["poids_pop_2019"] = w.pop_2019 / w.groupby("old_adm2_pcode").pop_2019.transform("sum")

# --- 4. Alias de noms pour les jointures ---------------------------------------------
al = []
for _, r in com.drop_duplicates("adm2_pcode").iterrows():
    al.append({"niveau": "province", "alias": norm(r.adm2_name), "code": r.adm2_pcode, "decoupage": "nouveau"})
for _, r in old_prov.iterrows():
    al.append({"niveau": "province", "alias": norm(r.old_adm2_name), "code": r.old_adm2_pcode, "decoupage": "ancien"})
for _, r in a1.iterrows():
    al.append({"niveau": "region", "alias": norm(r.adm1_name1), "code": r.adm1_pcode, "decoupage": "nouveau"})
for _, r in old_reg.iterrows():
    al.append({"niveau": "region", "alias": norm(r.old_adm1_name), "code": r.old_adm1_pcode, "decoupage": "ancien"})
for _, r in com.iterrows():
    al.append({"niveau": "commune", "alias": norm(r.adm3_name), "code": r.adm3_pcode, "decoupage": "nouveau"})
    if isinstance(r.nom_rgph, str) and norm(r.nom_rgph) != norm(r.adm3_name):
        al.append({"niveau": "commune", "alias": norm(r.nom_rgph), "code": r.adm3_pcode, "decoupage": "nom RGPH 2019"})
al = pd.DataFrame(al).drop_duplicates()

# --- 5. Écriture ---------------------------------------------------------------------
com = com.sort_values(["adm1_pcode", "adm2_pcode", "adm3_pcode"])
f1 = out_path("01-collecte", "architect", "referentiel-communes-17-regions")
f2 = out_path("01-collecte", "architect", "passage-anciennes-provinces-47-provinces")
f3 = out_path("01-collecte", "architect", "alias-noms-geographiques")
f4 = out_path("02-nettoyage", "engineer", "journal-T02-referentiel")
com.to_csv(f1, sep=";", index=False, encoding="utf-8")
w.to_csv(f2, sep=";", index=False, encoding="utf-8")
al.to_csv(f3, sep=";", index=False, encoding="utf-8")
pd.DataFrame(journal).to_csv(f4, sep=";", index=False, encoding="utf-8")

print("communes", len(com), "| avec population", com.pop_2019.notna().sum(),
      "| population totale", int(com.pop_2019.sum()), "(RGPH : 20 505 155)")
print("journal :", pd.DataFrame(journal).objet.value_counts().to_dict() if journal else {})
print("provinces scindées :", w[w.poids_pop_2019 < 1][["old_adm2_name", "adm2_name", "poids_pop_2019"]].to_string(index=False))
