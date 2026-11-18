"""Annexes communales du rapport RGPH2019 Cartographie de la pauvrete."""
from pathlib import Path
import argparse,hashlib,json,re
import fitz,numpy as np,pandas as pd
from extraire_secondaire import lines,norm,number

VARIABLES={
5:['emploi_7_14ans','emploi_15_24ans','emploi_25_64ans','chomage_15_24ans','chomage_25_64ans'],
6:['travailleurs_autonomes_15_24ans','travailleurs_autonomes_25_64ans','frequentation_nette_postprimaire','frequentation_nette_lycee','parite_primaire'],
7:['parite_postprimaire','parite_secondaire','hors_ecole_6_11ans','hors_ecole_12_15ans','hors_ecole_16_18ans'],
8:['ni_ecole_ni_travail_15_24ans','alphabetisation_15_64ans','dependance_demographique','filles_17ans_deja_mariees','acte_naissance'],
9:['sanitaires_ameliores','eau_amelioree','electricite','energie_amelioree','telephone'],
}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--sortie',type=Path,required=True);a=ap.parse_args();a.sortie.mkdir(parents=True,exist_ok=True)
 f=next((a.source/'donnees').rglob('NADA275*.pdf'));doc=fitz.open(f);digest=hashlib.sha256(f.read_bytes()).hexdigest();geo=pd.read_csv(next((a.source/'livrables/01_collecte').glob('*referentiel-communes*')),sep=';');aliases=pd.read_csv(next((a.source/'livrables/01_collecte').glob('*alias-noms*')),sep=';')
 pa=aliases[(aliases.niveau=='province')&(aliases.decoupage=='ancien')];provs=dict(zip(pa.alias,pa.code));provs.update({'KOURITENGA':provs['KOURITTENGA'],'KOMANDJOARI':provs['KOMANDJARI']})
 regs=aliases[(aliases.niveau=='region')&(aliases.decoupage=='ancien')];regs=dict(zip(regs.alias,regs.code))
 commune={}
 for r in geo.itertuples():
  for name in [r.adm3_name,r.nom_rgph]:commune[(r.old_adm2_pcode,norm(name))]=r.adm3_pcode
 for province,alias,canon in [('BF5202','FADA N GOURMA','FADA NGOURMA'),('BF5301','KARANKASSO SAMBLA','KARANGASSO SAMBLA'),('BF5302','N DOROLA','NDOROLA')]:
  if (province,canon) in commune:commune[(province,alias)]=commune[(province,canon)]
 allpoints=[];unresolved=[];rawrows=[];currentprov='';currentcommune=''
 for annex,(start,end) in {5:(130,166),6:(167,203),7:(204,240),8:(241,279),9:(280,316)}.items():
  anchors=None;currentprov='';currentcommune=''
  for pg in range(start,end+1):
   for text,ws in lines(doc[pg-1]):
    nums=[w for w in ws if re.fullmatch(r'\d+,\d+',w[4])]
    if not nums:continue
    first=nums[0];label=' '.join(w[4] for w in ws if w[2]<first[0]);n=norm(label)
    if n=='BURKINA FASO' and len(nums)==5:anchors=[(w[0]+w[2])/2 for w in nums]
    if anchors is None:continue
    # Le texte de la ligne permet d'identifier une ligne de donnees ; les blancs restent des manquants.
    values=[None]*5;valid=True
    if len(nums)==5:values=[number(w[4]) for w in nums]
    else:
     for w in nums:
      x=(w[0]+w[2])/2;k=min(range(5),key=lambda k:abs(anchors[k]-x))
      if values[k] is not None or abs(anchors[k]-x)>35:valid=False;break
      values[k]=number(w[4])
    if not valid:unresolved.append(dict(annexe=annex,page_pdf=pg,label=label,motif='colonnes_ambigues',ligne=text));continue
    rawrows.append(dict(annexe=annex,page_pdf=pg,label=label,**{f'col{k+1}':v for k,v in enumerate(values)}))
    level='';code='';method=''
    if n=='BURKINA FASO':level='national';code='BF';currentprov='';currentcommune=''
    elif label.upper()==label and n in regs:level='ancienne_region';code=regs[n];currentprov='';currentcommune=''
    elif n in provs and (label.upper()==label or (currentprov,n) not in commune):level='ancienne_province';code=provs[n];currentprov=code;currentcommune=''
    elif (currentprov,n) in commune:level='commune';code=commune[(currentprov,n)];currentcommune=code
    elif n.startswith('SECTEUR ') or n=='RURAL' or re.match(r'^(OUAGA|BOBO) (ARR|RURAL)',n):level='sous_communal';code='';method='parent_commune:'+currentcommune
    else:level='non_resolu';method='libelle_a_confirmer';unresolved.append(dict(annexe=annex,page_pdf=pg,label=label,motif='geographie_non_resolue',ligne=text))
    for k,var in enumerate(VARIABLES[annex]):
     val=values[k];ratio=var.startswith('parite');validval=val is not None and (val>=0 if ratio or var=='dependance_demographique' else 0<=val<=100)
     allpoints.append(dict(fichier=str(f.relative_to(a.source)),sha256=digest,annexe=annex,page_pdf=pg,annee_reference=2019,label_source=label,niveau_geo=level,code_geo=code,parent_ancienne_province=currentprov,parent_commune=currentcommune,variable=var,valeur=val,unite='ratio' if ratio else '%',methode_geo=method or 'nom_exact_dans_ancienne_province',eligible_analyse=bool(validval and code),statut='contexte_structurel_2019_pas_observation_annuelle'))
 df=pd.DataFrame(allpoints);df.to_csv(a.sortie/'rgph2019_vulnerabilites_tous_niveaux.csv',sep=';',index=False,encoding='utf-8-sig');pd.DataFrame(rawrows).to_csv(a.sortie/'rgph2019_annexes_lignes_source.csv',sep=';',index=False,encoding='utf-8-sig');pd.DataFrame(unresolved).to_csv(a.sortie/'rgph2019_a_confirmer.csv',sep=';',index=False,encoding='utf-8-sig')
 com=df[df.niveau_geo.eq('commune')].copy();com.to_csv(a.sortie/'rgph2019_vulnerabilites_communes_long.csv',sep=';',index=False,encoding='utf-8-sig');wide=com.pivot(index='code_geo',columns='variable',values='valeur').reset_index().rename(columns={'code_geo':'adm3_pcode'});wide=geo[['adm3_pcode','adm3_name','adm2_pcode','adm2_name','adm1_pcode','adm1_name']].merge(wide,how='left');wide['annee_reference']=2019;wide.to_csv(a.sortie/'rgph2019_vulnerabilites_351_communes.csv',sep=';',index=False,encoding='utf-8-sig')
 # Pauvrete monetaire communale, avec code INSD hierarchique : pages 97 a 129.
 poverty=[];povertybad=[];currentprov=''
 for pg in range(97,130):
  for text,ws in lines(doc[pg-1]):
   m=re.match(r'^(\d{1,2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+',text)
   if not m:continue
   rest=text[m.end():];cells=[c.strip() for c in re.split(r'\s{2,}',rest) if c.strip()]
   if len(cells)!=6:povertybad.append(dict(page_pdf=pg,motif='6_cellules_attendues',ligne=text));continue
   label=cells[0];vals=[number(v) for v in cells[1:]];n=norm(label);level='';code=''
   r,pr,co,se=m.groups()
   if pr=='00':level='ancienne_region';code=regs.get(n,'')
   elif co=='00':level='ancienne_province';code=provs.get(n,'');currentprov=code
   elif se=='00':level='commune';code=commune.get((currentprov,n),'')
   else:level='sous_communal'
   poverty.append(dict(fichier=str(f.relative_to(a.source)),sha256=digest,page_pdf=pg,code_insd_source=' '.join(m.groups()),label_source=label,niveau_geo=level,code_geo=code,ancienne_province=currentprov,population_2019=vals[0],menages_2019=vals[1],incidence_pauvrete_estimee=vals[2],profondeur_pauvrete_estimee=vals[3],nombre_pauvres_estime=vals[4],annee_reference=2019,nature='estimation_petits_domaines_EHCVM2018_RGPH2019'))
 pv=pd.DataFrame(poverty);pv.to_csv(a.sortie/'rgph2019_pauvrete_monetaire_tous_niveaux.csv',sep=';',index=False,encoding='utf-8-sig');pd.DataFrame(povertybad).to_csv(a.sortie/'rgph2019_pauvrete_lignes_a_reprendre.csv',sep=';',index=False,encoding='utf-8-sig')
 cov=com.groupby('variable').agg(communes=('code_geo','nunique'),valeurs=('valeur','count')).reset_index();cov.to_csv(a.sortie/'rgph2019_couverture_variables.csv',sep=';',index=False,encoding='utf-8-sig')
 defs=[]
 for pg in [93,94,95]:defs.append(f'PAGE PDF {pg}\n'+doc[pg-1].get_text(sort=True))
 (a.sortie/'definitions_indicateurs_source.txt').write_text('\n\n'.join(defs),encoding='utf8')
 summary=dict(points=len(df),communes=com.code_geo.nunique(),variables=com.variable.nunique(),geographies_non_resolues=len(unresolved),pauvrete_lignes=len(pv),pauvrete_communes=int(pv[pv.niveau_geo.eq('commune') & pv.code_geo.ne('')].code_geo.nunique()),pauvrete_lignes_a_reprendre=len(povertybad));(a.sortie/'bilan_pauvrete.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(summary)

if __name__=='__main__':main()
