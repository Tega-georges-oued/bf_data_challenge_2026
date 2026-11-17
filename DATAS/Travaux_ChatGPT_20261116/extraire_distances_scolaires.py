"""Distances declarees des eleves, plus pertinentes que le seul proxy OSM."""
from pathlib import Path
import argparse,hashlib,re,sqlite3
import pandas as pd,numpy as np,fitz
from extraire_secondaire import lines,norm
from extraire_primaire import numeric_cells

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--travail',type=Path,required=True);a=ap.parse_args();out=a.travail/'02_nettoyage/distances_scolaires';out.mkdir(parents=True,exist_ok=True);index=a.travail/'01_collecte';cat=pd.read_csv(index/'catalogue_pdf.csv',sep=';');db=sqlite3.connect(index/'index_documentaire.sqlite');al=pd.read_csv(next((a.source/'01_collecte').glob('*alias-noms*')),sep=';');p=al[(al.niveau=='province')&(al.decoupage=='ancien')];lookup=dict(zip(p.alias,p.code))
 for alias,canon in {'LES BALE':'BALE','KOMONDJARI':'KOMANDJARI','KOMONDJOARI':'KOMANDJARI','KOMANDJOARI':'KOMANDJARI','KOURITENGA':'KOURITTENGA','ZOUNWEOGO':'ZOUNDWEOGO'}.items():lookup[alias]=lookup[canon]
 points=[];bad=[]
 for code,year in {'CNS521':'2017/2018','CNS522':'2018/2019','CNS523':'2019/2020','CNS524':'2020/2021','CNS525':'2021/2022','CNS526':'2022/2023','CNS529':'2023/2024','CNS530':'2024/2025'}.items():
  f=cat[cat.fichier.str.contains(code+'_',regex=False)].iloc[0];doc=fitz.open(a.source/f.fichier)
  for pg,text in db.execute("SELECT page,texte FROM pages WHERE sha256=? AND texte LIKE '%DISTANCE PARCOURUE%'",(f.sha256,)):
   if pg<=10:continue
   n=norm(text);m=re.search(r'(?:VI|V) 5 ([1-5])',n)
   if not m:continue
   kind={'1':'public','2':'prive','3':'public_prive','4':'urbain','5':'rural'}[m[1]]
   for text,ws in lines(doc[pg-1]):
    idx=next((i for i,w in enumerate(ws) if re.match(r'^\d',w[4])),None)
    if idx is None:continue
    label=norm(' '.join(w[4] for w in ws[:idx]));province=lookup.get(label)
    if province is None:continue
    tokens,vals=numeric_cells(ws,idx)
    if len(vals)!=4 or any(v is None for v in vals):bad.append(dict(fichier=f.fichier,page_pdf=pg,ligne=text,motif='4_valeurs_attendues'));continue
    eligible=vals[3]>0 and abs(sum(vals[:3])-100)<=.031 and all(0<=v<=100 for v in vals[:3])
    for var,v in zip(['part_trajet_moins_3km','part_trajet_3_a_5km','part_trajet_plus_5km','eleves_denominateur'],vals):points.append(dict(fichier=f.fichier,sha256=f.sha256,page_pdf=pg,annee_scolaire=year,old_adm2_pcode=province,perimetre=kind,variable=var,valeur=v,unite='eleves' if var=='eleves_denominateur' else '%',controle_somme_pct=sum(vals[:3]),eligible_analyse=bool(eligible if var!='eleves_denominateur' else v>=0),nature='distance_declaree_dans_annuaire_pas_distance_OSM'))
 df=pd.DataFrame(points);df.to_csv(out/'distances_eleves_provinces_long.csv',sep=';',index=False,encoding='utf-8-sig');pd.DataFrame(bad).to_csv(out/'distances_lignes_a_reprendre.csv',sep=';',index=False,encoding='utf-8-sig');df.groupby(['annee_scolaire','perimetre']).agg(provinces=('old_adm2_pcode','nunique'),cellules=('valeur','size')).reset_index().to_csv(out/'distances_couverture.csv',sep=';',index=False,encoding='utf-8-sig');print('DISTANCES',len(df),'cellules',len(bad),'lignes a reprendre')

if __name__=='__main__':main()
