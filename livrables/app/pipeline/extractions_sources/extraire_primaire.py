"""Tables contemporaines du primaire : niveaux, sexe, ressources et milieu."""
from pathlib import Path
import argparse,hashlib,json,re,statistics
import fitz,numpy as np,pandas as pd
from extraire_secondaire import lines,norm,number

def numeric_cells(ws,start):
 groups=[];height=statistics.median(w[3]-w[1] for w in ws)
 for w in ws[start:]:
  if not groups or w[0]-groups[-1][-1][2]>height*.4:groups.append([w])
  else:groups[-1].append(w)
 tokens=[' '.join(w[4] for w in group) for group in groups]
 return tokens,[number(t) for t in tokens]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--sortie',type=Path,required=True);ap.add_argument('--skip-stage',action='store_true');a=ap.parse_args();a.sortie.mkdir(parents=True,exist_ok=True)
 al=pd.read_csv(next((a.source/'livrables/01_collecte').glob('*alias-noms*')),sep=';');p=al[(al.niveau=='province')&(al.decoupage=='ancien')];lookup=dict(zip(p.alias,p.code))
 for alias,canon in {'LES BALE':'BALE','KOMONDJARI':'KOMANDJARI','KOMONDJOARI':'KOMANDJARI','KOURITENGA':'KOURITTENGA','ZOUNWEOGO':'ZOUNDWEOGO'}.items():lookup[alias]=lookup[canon]
 folder=a.source/'donnees/DataPack_DCB_2026/DataPack_DCB_2026/01_Education_MENAPLN_DGESS/CNS_DGESS/Annuaires';points=[];stage=[];reject=[]
 editions={'CNS521':'2017/2018','CNS522':'2018/2019','CNS523':'2019/2020','CNS524':'2020/2021','CNS525':'2021/2022','CNS526':'2022/2023','CNS529':'2023/2024','CNS530':'2024/2025'}
 for code,year in editions.items():
  f=next(folder.glob(code+'*.pdf'));doc=fitz.open(f);sha=hashlib.sha256(f.read_bytes()).hexdigest();n0=len(points)
  for pg,page in enumerate(doc,1):
   if pg<=10:continue
   raw=page.get_text();nt=norm(raw)
   if 'HISTORIQUE' in nt:continue
   target=''
   if re.search(r'(?:III|IV) 3 3 PUBLIC PRIVE',nt):target='III.3.3'
   elif re.search(r'\bI{1,2} 1 NOMBRE D ECOLES',nt) and 'GROUPES PEDAGOGIQUES' in nt[:800] and 'COMMUNES PRIORITAIRES' not in nt[:800]:target='I.1'
   elif re.search(r'\bI{1,2} 2 NOMBRE D ELEVES',nt) and 'COMMUNES PRIORITAIRES' not in nt[:800]:target='I.2'
   if not target and a.skip_stage:continue
   # Toutes les lignes provinciales des autres tableaux restent reperables, sans inventer leur semantique.
   ls=lines(page);currentprov=None;statut=''
   for text,ws in ls:
    n=norm(text)
    idx=next((k for k,w in enumerate(ws) if re.match(r'^\d|^[\-–—]$',w[4])),None)
    prefix=norm(' '.join(w[4] for w in ws[:idx])) if idx is not None else n
    if n in lookup:currentprov=lookup[n];continue
    province_prefix=re.sub(r' (PUBLIC|PRIVE|TOTAL)$','',prefix) if target=='I.1' else prefix
    if province_prefix in lookup:currentprov=lookup[province_prefix]
    elif prefix.startswith('TOTAL REGION') or n.startswith('TOTAL NATIONAL') or n.startswith('TOTAL REGION'):currentprov=None
    if not target:
     if prefix in lookup and idx is not None:
      tokens,vals=numeric_cells(ws,idx)
      if sum(v is not None for v in vals)>=2:stage.append(dict(fichier=str(f.relative_to(a.source)),sha256=sha,page_pdf=pg,annee_scolaire=year,old_adm2_pcode=lookup[prefix],ligne_source=text,cellules=json.dumps(tokens,ensure_ascii=False),entete_page=' '.join(t for t,w in ls[:12])[:2000],statut='cellules_brutes_semantique_non_validee'))
     continue
    if currentprov is None:continue
    common=dict(fichier=str(f.relative_to(a.source)),sha256=sha,page_pdf=pg,annee_scolaire=year,old_adm2_pcode=currentprov,table_source=target)
    if target=='III.3.3':
     if idx is None:continue
     sx={'GARCONS':'G','FILLES':'F','TOTAL':'T'}.get(prefix)
     if not sx:continue
     tok,vals=numeric_cells(ws,idx)
     if len(vals)!=14 or any(v is None for v in vals):reject.append(dict(**common,motif=f'{len(vals)}_cellules_au_lieu_14',ligne=text));continue
     for k,level in enumerate(['CP1','CP2','CE1','CE2','CM1','CM2','TOTAL']):
      points.append(dict(**common,sexe=sx,niveau=level,statut_etablissement='public_prive',milieu='ensemble',variable='effectif',valeur=vals[2*k],unite='eleves'))
      points.append(dict(**common,sexe=sx,niveau=level,statut_etablissement='public_prive',milieu='ensemble',variable='redoublants',valeur=vals[2*k+1],unite='eleves'))
    elif target=='I.1':
     st=next((w[4] for w in ws if norm(w[4]) in ['PUBLIC','PRIVE','TOTAL']),None)
     if st is None or idx is None:continue
     tok,vals=numeric_cells(ws,idx)
     if len(vals)!=6 or any(v is None for v in vals):reject.append(dict(**common,motif=f'{len(vals)}_cellules_au_lieu_6',ligne=text));continue
     for var,v in zip(['ecoles','salles_classe','groupes_pedagogiques','maitres_charges_cours','effectif','ratio_eleves_maitre'],vals):points.append(dict(**common,sexe='T',niveau='TOTAL',statut_etablissement=norm(st).lower(),milieu='ensemble',variable=var,valeur=v,unite='ratio' if var.startswith('ratio') else 'nombre'))
    elif target=='I.2' and prefix in lookup and idx is not None:
     tok,vals=numeric_cells(ws,idx)
     if len(vals)!=9 or any(v is None for v in vals):reject.append(dict(**common,motif=f'{len(vals)}_cellules_au_lieu_9',ligne=text));continue
     for k,v in enumerate(vals):points.append(dict(**common,sexe='F' if k%3==1 else 'T',niveau='TOTAL',statut_etablissement='public_prive',milieu=['urbain','rural','ensemble'][k//3],variable='pourcentage_filles' if k%3==2 else 'effectif',valeur=v,unite='%' if k%3==2 else 'eleves'))
  print(code,year,len(points)-n0,'points',flush=True)
 df=pd.DataFrame(points);key=['annee_scolaire','old_adm2_pcode','table_source','sexe','niveau','statut_etablissement','milieu','variable'];df['cle_dupliquee']=df.duplicated(key,False);df['eligible_structure']=~df.cle_dupliquee & df.valeur.ge(0)
 df.to_csv(a.sortie/'primaire_tables_contemporaines_long.csv',sep=';',index=False,encoding='utf-8-sig')
 if not a.skip_stage:pd.DataFrame(stage).to_csv(a.sortie/'primaire_autres_tableaux_cellules_a_documenter.csv',sep=';',index=False,encoding='utf-8-sig')
 pd.DataFrame(reject).to_csv(a.sortie/'primaire_lignes_a_reprendre.csv',sep=';',index=False,encoding='utf-8-sig')
 df.groupby(['annee_scolaire','table_source','variable']).agg(provinces=('old_adm2_pcode','nunique'),points=('valeur','size')).reset_index().to_csv(a.sortie/'primaire_couverture.csv',sep=';',index=False,encoding='utf-8-sig')
 # Comparaison directe des effectifs par sexe avec les historiques retenus precedemment.
 history=pd.read_csv(next((a.source/'livrables/02_nettoyage').glob('*effectifs-primaire-provinces_v1.csv')),sep=';');current=df[df.table_source.eq('III.3.3')].pivot(index=['annee_scolaire','old_adm2_pcode','sexe','niveau'],columns='variable',values='valeur').reset_index();comp=current.merge(history,on=['annee_scolaire','old_adm2_pcode','sexe','niveau'],suffixes=('_contemporain','_historique'),validate='one_to_one')
 for var in ['effectif','redoublants']:comp['ecart_'+var]=comp[var+'_contemporain']-comp[var+'_historique']
 comp.to_csv(a.sortie/'primaire_contemporain_vs_historique.csv',sep=';',index=False,encoding='utf-8-sig')
 print('BILAN',len(df),'points',len(stage),'lignes autres tableaux',len(reject),'rejets',df.cle_dupliquee.sum(),'doublons',flush=True)

if __name__=='__main__':main()
