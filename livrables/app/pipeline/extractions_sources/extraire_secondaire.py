"""Extraction geometrique des tableaux provinciaux MESFPT, six annuaires."""
from pathlib import Path
import argparse,collections,hashlib,math,re,statistics,unicodedata
import fitz
import pandas as pd

def norm(s):
 return re.sub(r'[^A-Z0-9]+',' ',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().upper()).strip()

def lines(page):
 directions=collections.Counter()
 for b in page.get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   directions[tuple(l['dir'])]+=sum(len(s['text']) for s in l['spans'])
 direction=directions.most_common(1)[0][0] if directions else (1,0)
 angle=-math.degrees(math.atan2(direction[1],direction[0]));mat=fitz.Matrix(angle)
 words=[]
 for w in page.get_text('words'):
  r=fitz.Rect(w[:4])*mat;words.append((r.x0,r.y0,r.x1,r.y1,w[4]))
 if not words:return []
 height=statistics.median(w[3]-w[1] for w in words);tol=max(.7,height*.3)
 groups=[]
 for w in sorted(words,key=lambda w:((w[1]+w[3])/2,w[0])):
  y=(w[1]+w[3])/2
  if not groups or abs(y-groups[-1][0])>tol:groups.append([y,[w]])
  else:groups[-1][1].append(w)
 result=[]
 for y,ws in groups:
  ws.sort(key=lambda w:w[0]);text=ws[0][4]
  for prev,w in zip(ws,ws[1:]):
   gap=w[0]-prev[2];text+=('  ' if gap>height*.55 else ' ')+w[4]
  result.append((text,ws))
 return result

def number(s):
 t=s.replace(' ','').replace('\xa0','').replace(',','.').replace('%','')
 if t in ['','-','–','—']:return None
 try:
  value=float(t)
  return value if math.isfinite(value) else None
 except ValueError:return None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--sortie',type=Path,required=True);a=ap.parse_args();a.sortie.mkdir(parents=True,exist_ok=True)
 aliases=pd.read_csv(next((a.source/'livrables/01_collecte').glob('*alias-noms*')),sep=';');pa=aliases[(aliases.niveau=='province')&(aliases.decoupage=='ancien')];lookup=dict(zip(pa.alias,pa.code))
 for x,y in {'KOMONDJARI':'KOMANDJARI','KOMONDJOARI':'KOMANDJARI','KOMANDJOARI':'KOMANDJARI','KOURITENGA':'KOURITTENGA','ZOUNWEOGO':'ZOUNDWEOGO','ZANDOMA':'ZONDOMA','LORUM':'LOROUM','LES BALE':'BALE'}.items():lookup[x]=lookup[y]
 points=[];rejected=[];coverage=[];checks=[]
 folder=a.source/'donnees/Annuaires_et_tableaux_de_bord_DGESS_Education_Burkina_hors_superieur/MESFPT/Annuaires'
 for f in sorted(folder.glob('*Post_primaire*pdf')):
  year=re.search(r'(20\d{2})-(20\d{2})',f.name);year='/'.join(year.groups());digest=hashlib.sha256(f.read_bytes()).hexdigest();doc=fitz.open(f);before=len(points)
  for i,page in enumerate(doc):
   raw=page.get_text();nt=norm(raw)
   if i<20 or 'II 3' not in nt or 'PROVINCE' not in nt:continue
   ls=lines(page);joined=norm(' '.join(t for t,w in ls))
   table=re.search(r'II 3 (\d+)(?: (\d+))?',joined)
   if not table:continue
   tab=int(table[1]);sex=None
   if tab==11:
    st=re.search(r'II 3 11 ([123])',joined)
    if st:sex={'1':'G','2':'F','3':'T'}[st[1]]
    else:rejected.append(dict(fichier=f.name,page_pdf=i+1,motif='sexe_table_flux_non_identifie'));continue
    header=next((ws for t,ws in ls if sum(w[4] in ['Prom','Redoub','Aband'] for w in ws)==21),None)
    if header is None:rejected.append(dict(fichier=f.name,page_pdf=i+1,motif='entete_21_colonnes_flux_absente'));continue
    centers=[(w[0]+w[2])/2 for w in header if w[4] in ['Prom','Redoub','Aband']]
   elif not 1<=tab<=10:continue
   for text,ws in ls:
    # Le nom de province precede le premier nombre ou pourcentage.
    idx=next((k for k,w in enumerate(ws) if re.match(r'^\d|^[\-–—]$',w[4])),None)
    if idx is None:continue
    label=norm(' '.join(w[4] for w in ws[:idx]));code=lookup.get(label)
    if code is None:continue
    common=dict(fichier=str(f.relative_to(a.source)),sha256=digest,page_pdf=i+1,annee_scolaire=year,old_adm2_pcode=code,province_lue=label,table_source=f'II.3.{tab}',perimetre='general_sans_cours_du_soir' if tab==11 else 'general_technique_professionnel',methode='coordonnees_pdf_orientation_corrigee')
    if tab==11:
     tokens=['']*21;valid=True
     for w in ws[idx:]:
      if not re.fullmatch(r'\d+(?:[,.]\d+)?%|[-–—]',w[4]):continue
      x=(w[0]+w[2])/2;k=min(range(21),key=lambda j:abs(centers[j]-x))
      if tokens[k] or abs(centers[k]-x)>statistics.median([centers[j+1]-centers[j] for j in range(20)])*.48:valid=False;break
      tokens[k]=w[4]
     if not valid:rejected.append(dict(**common,motif='alignement_flux_ambigu',ligne=text));continue
     for k,token in enumerate(tokens):
      level=['6e','5e','4e','3e','2nde','1ere','Tle'][k//3];metric=['taux_promotion','taux_redoublement','taux_abandon'][k%3];v=number(token)
      points.append(dict(**common,sexe=sex,niveau=level,variable=metric,valeur=v,unite='%',valeur_source=token,statut_valeur='manquant_publie' if v is None else 'extraite_controle_automatique'))
    else:
     # Les espaces simples sont les separateurs de milliers ; les cellules sont separees geometriquement.
     numeric=ws[idx:];groups=[];height=statistics.median(w[3]-w[1] for w in ws)
     for w in numeric:
      if not groups or w[0]-groups[-1][-1][2]>height*.55:groups.append([w])
      else:groups[-1].append(w)
     vals=[' '.join(w[4] for w in g) for g in groups];nums=[number(t) for t in vals]
     if len(nums)!=10 or any(v is None for v in nums):rejected.append(dict(**common,motif=f'indicateur_{len(nums)}_cellules_au_lieu_10',ligne=text));continue
     cycle={1:'6e',2:'2nde',3:'postprimaire_secondaire',4:'postprimaire',5:'secondaire',6:'postprimaire_secondaire',7:'postprimaire',8:'secondaire',9:'3e',10:'Tle'}[tab]
     rate={1:'tba',2:'tba',3:'tbs',4:'tbs',5:'tbs',6:'tns',7:'tns',8:'tns',9:'taux_achevement',10:'taux_achevement'}[tab]
     countname='nouveaux_inscrits' if tab in (1,2) else ('eleves_non_redoublants_fin_cycle' if tab in (9,10) else ('eleves_scolarises_age_officiel' if tab in (6,7,8) else 'eleves_scolarises'))
     for k,v in enumerate(nums):
      var='population_age_reference' if k<3 else (countname if k<6 else (rate if k<9 else 'indice_parite_'+rate))
      points.append(dict(**common,sexe=['G','F','T'][k%3] if k<9 else 'F/G',niveau=cycle,variable=var,valeur=v,unite='personnes' if k<6 else ('%' if k<9 else 'ratio'),valeur_source=vals[k],statut_valeur='extraite_controle_automatique'))
     checks.append(dict(**common,controle='G_plus_F_population_et_eleves',reussi=nums[0]+nums[1]==nums[2] and nums[3]+nums[4]==nums[5],detail=f'population ecart {nums[0]+nums[1]-nums[2]}, eleves ecart {nums[3]+nums[4]-nums[5]}'))
     for k in range(3):
      if nums[k]>0:checks.append(dict(**common,controle='ratio_publie_vs_comptages_'+['G','F','T'][k],reussi=abs(nums[3+k]/nums[k]*100-nums[6+k])<=.16,detail=f'calcule {nums[3+k]/nums[k]*100:.4f}, publie {nums[6+k]}'))
  print(f.name,'points',len(points)-before,flush=True)
 df=pd.DataFrame(points)
 if df.empty:raise ValueError('Aucun point extrait')
 key=['annee_scolaire','old_adm2_pcode','table_source','sexe','niveau','variable']
 duplicates=df[df.duplicated(key,keep=False)]
 if len(duplicates):duplicates.to_csv(a.sortie/'secondaire_doublons_a_arbitrer.csv',sep=';',index=False,encoding='utf-8-sig')
 df['cle_dupliquee']=df.duplicated(key,keep=False)
 badchecks=pd.DataFrame(checks);badset=set((r.annee_scolaire,r.old_adm2_pcode,r.table_source) for r in badchecks[~badchecks.reussi].itertuples()) if not badchecks.empty else set()
 df['table_controles_coherents']=[(r.annee_scolaire,r.old_adm2_pcode,r.table_source) not in badset for r in df.itertuples()]
 df['eligible_analyse']=~df.cle_dupliquee & df.table_controles_coherents & df.valeur.notna()
 # Valeurs des taux hors domaine bloquees ; les taux bruts peuvent depasser 100.
 bad=df.variable.isin(['taux_promotion','taux_redoublement','taux_abandon','tns']) & ~df.valeur.between(0,100) & df.valeur.notna();df.loc[bad,'eligible_analyse']=False
 df.to_csv(a.sortie/'secondaire_provinces_long.csv',sep=';',index=False,encoding='utf-8-sig')
 pd.DataFrame(rejected).to_csv(a.sortie/'secondaire_lignes_a_reprendre.csv',sep=';',index=False,encoding='utf-8-sig')
 badchecks.to_csv(a.sortie/'secondaire_controles.csv',sep=';',index=False,encoding='utf-8-sig')
 cv=df.groupby(['annee_scolaire','table_source','sexe']).agg(provinces=('old_adm2_pcode','nunique'),points=('valeur','size'),valeurs_presentes=('valeur','count')).reset_index();cv.to_csv(a.sortie/'secondaire_couverture.csv',sep=';',index=False,encoding='utf-8-sig')
 print('BILAN',len(df),'points',df.old_adm2_pcode.nunique(),'provinces',len(rejected),'lignes a reprendre',len(duplicates),'doublons',flush=True)

if __name__=='__main__':main()
