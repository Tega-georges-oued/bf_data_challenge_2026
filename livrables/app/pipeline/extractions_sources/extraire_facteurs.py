"""Normalisation exhaustive ODA/HDX et facteurs observes, avec geographie explicite."""
from pathlib import Path
import argparse,json,re,unicodedata
import numpy as np
import pandas as pd

def norm(s):
 return re.sub(r'[^A-Z0-9]+',' ',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().upper()).strip()

def read(f):
 first=f.open(encoding='utf-8-sig').readline();return pd.read_csv(f,sep=';' if first.count(';')>first.count(',') else ',',encoding='utf-8-sig',low_memory=False).drop(columns=['remarque_collecte'],errors='ignore')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--sortie',type=Path,required=True);a=ap.parse_args();out=a.sortie;out.mkdir(parents=True,exist_ok=True)
 src=a.source;ext=src/'donnees/Sources_externes';geo=read(next((src/'livrables/01_collecte').glob('*referentiel-communes*')));al=read(next((src/'livrables/01_collecte').glob('*alias-noms*')))
 lookup={}
 for r in al.itertuples():
  if r.niveau!='commune' and r.decoupage!='ancien':continue
  lookup.setdefault(r.alias,set()).add((r.niveau,r.code))
 for alias,canon in {'KOMONDJOARI':'KOMANDJARI','KOMONDJARI':'KOMANDJARI','KOURITENGA':'KOURITTENGA','LORUM':'LOROUM','ZANDOMA':'ZONDOMA','PLATEAUCENTRAL':'PLATEAU CENTRAL','LES BALE':'BALE','UPPER BASINS':'HAUTS BASSINS','CENTRAL NORTH':'CENTRE NORD','CENTRAL EAST':'CENTRE EST','CENTRAL WEST':'CENTRE OUEST','CENTRAL SOUTH':'CENTRE SUD','SOUTH WEST':'SUD OUEST','NORTH':'NORD','EAST':'EST','CENTRAL PLATEAU':'PLATEAU CENTRAL'}.items():
  if canon in lookup:lookup[alias]=lookup[canon]
 def resolve(value,kind=None):
  n=norm(value);n=re.sub(r'^(TOTAL |REGION DU |REGION DE LA |REGION DES |REGION )','',n)
  candidates=lookup.get(n,set())
  if kind and any(x[0]==kind for x in candidates):candidates={x for x in candidates if x[0]==kind}
  if len(candidates)==1:
   level,code=next(iter(candidates));return code,level,'exact_ou_alias_explicite'
  return '',('ambigu' if candidates else 'non_resolu'),'a_confirmer'
 # ODA : toutes les valeurs, toutes les dimensions, metadonnees des jeux.
 folder=ext/'OpenDataForAfrica_INSD';catalog=read(folder/'DCB_ext_ODA_catalogue-jeux-extraits.csv');alloda=[];summaries=[]
 for f in sorted(folder.glob('*.csv')):
  if 'catalogue' in f.name:continue
  d=read(f);d['fichier_source']=str(f.relative_to(src));d['ligne_source']=np.arange(len(d))+2
  d=d.merge(catalog[['dataset_id','theme','titre','source','publication','url','date_extraction']],on=['dataset_id','theme'],how='left',validate='many_to_one')
  # Le nom de dimension annonce parfois « province » alors que ses modalites incluent une region ou une classe.
  resolutions=[]
  for r in d.to_dict('records'):
   matches=[];unresolved=[]
   for i in range(1,6):
    kind=norm(r.get(f'dim{i}_nom',''));value=r.get(f'dim{i}')
    if pd.isna(value) or not re.search(r'COMMUNE|PROVINCE|REGION|ARRONDISSEMENT',kind):continue
    hint='commune' if 'COMMUNE' in kind else ('province' if 'PROVINCE' in kind else ('region' if 'REGION' in kind else None))
    code,level,method=resolve(value,hint)
    if code:matches.append((code,level,method,str(value)))
    else:unresolved.append(str(value))
   if matches:
    matches.sort(key=lambda x:{'commune':0,'province':1,'region':2}.get(x[1],3));code,level,method,label=matches[0]
   else:code,level,method,label='','non_resolu','a_confirmer','|'.join(unresolved)
   resolutions.append((code,level,method,label))
  d[['code_geo','niveau_geo','methode_geo','libelle_geo_lu']]=pd.DataFrame(resolutions,index=d.index)
  d['type_annee']='annee_source_non_qualifiee';d['unite_a_confirmer']=d.unite.eq('%') & ~pd.to_numeric(d.valeur,errors='coerce').between(0,100)
  d['statut_integration']=np.where(d.code_geo.ne('') & ~d.unite_a_confirmer,'normalise_periode_et_semantique_a_valider','quarantaine_geo_ou_unite')
  alloda.append(d)
  for key,g in d.groupby('dataset_id'):
   summaries.append(dict(dataset_id=key,theme=g.theme.iloc[0],titre=g.titre.iloc[0],source=g.source.iloc[0],publication=g.publication.iloc[0],url=g.url.iloc[0],points=len(g),annee_min=g.annee.min(),annee_max=g.annee.max(),points_geo_resolus=g.code_geo.ne('').sum(),codes_geo=g.loc[g.code_geo.ne(''),'code_geo'].nunique(),unites_a_confirmer=int(g.unite_a_confirmer.sum())))
  print('ODA',f.name,len(d),flush=True)
 oda=pd.concat(alloda,ignore_index=True)
 pointkeys=['dataset_id']+[c for c in oda.columns if c.startswith('dim')]+['annee','valeur','unite']
 oda_dups=int(oda.duplicated(pointkeys).sum());oda=oda.drop_duplicates(pointkeys).copy()
 memberships=catalog.groupby('dataset_id').theme.agg(lambda s:'|'.join(sorted(set(s))));oda['themes_catalogue']=oda.dataset_id.map(memberships)
 oda.to_csv(out/'oda_observations_dimensions_completes.csv',sep=';',index=False,encoding='utf-8-sig');pd.DataFrame(summaries).to_csv(out/'oda_catalogue_couverture.csv',sep=';',index=False,encoding='utf-8-sig')
 missing=catalog[~catalog.dataset_id.isin(oda.dataset_id)];missing.to_csv(out/'oda_jeux_sans_valeurs.csv',sep=';',index=False,encoding='utf-8-sig')
 # ACLED : categories separees, aucune addition de la violence politique et des violences contre civils.
 acled=[]
 for f in sorted((ext/'HDX').glob('*ACLED*.xlsx')):
  d=pd.read_excel(f,sheet_name='Data');d['categorie']='ciblage_civils' if 'civils' in f.name else 'violence_politique';d['fichier_source']=str(f.relative_to(src));d['ligne_source']=np.arange(len(d))+2
  d['mois']=pd.to_datetime(d.Year.astype(str)+'-'+d.Month.astype(str),format='%Y-%B').dt.strftime('%Y-%m');d=d.rename(columns={'Admin2 Pcode':'old_adm2_pcode','Events':'evenements','Fatalities':'deces'})
  d['statut_geographique']=np.where(d.old_adm2_pcode.isin(geo.old_adm2_pcode),'code_ancienne_province_reconnu','a_confirmer');d['millésime_extraction']='2026-11-11';d['retrospectif_disponibilite_historique_non_prouvee']=True
  d=d.sort_values(['old_adm2_pcode','mois'])
  for n in [3,6,12]:
   for metric in ['evenements','deces']:d[f'{metric}_{n}mois']=d.groupby('old_adm2_pcode')[metric].transform(lambda s:s.rolling(n,min_periods=n).sum())
  acled.append(d)
 ac=pd.concat(acled,ignore_index=True);ac.to_csv(out/'acled_provinces_mois_signaux.csv',sep=';',index=False,encoding='utf-8-sig')
 # DHS : conserver les sous-populations, intervalles et effectifs d'enquete.
 dhs=[]
 for f in sorted((ext/'HDX').glob('*DHS*.csv')):
  d=read(f);d['fichier_source']=str(f.relative_to(src));dhs.append(d)
 dh=pd.concat(dhs,ignore_index=True);dh=dh.drop_duplicates('DataId')
 rr=[resolve(x,'region') for x in dh.Location];dh[['code_geo','niveau_geo','methode_geo']]=pd.DataFrame(rr,index=dh.index)
 # Les regions des anciennes enquetes ne sont pas automatiquement celles du decoupage 2001.
 dh.loc[dh.SurveyYear.lt(2003),['code_geo','niveau_geo','methode_geo']]=['','ancien_decoupage_non_harmonise','a_confirmer']
 dh['usage']='contexte_enquete_pas_serie_annuelle';dh.to_csv(out/'dhs_vulnerabilites_avec_incertitude.csv',sep=';',index=False,encoding='utf-8-sig')
 op=read(next((ext/'HDX').glob('*OPHI*.csv')));rr=[resolve(x,'region') for x in op['Admin 1 Name']];op[['code_geo','niveau_geo','methode_geo']]=pd.DataFrame(rr,index=op.index);op['usage']='pauvrete_multidimensionnelle_2021_pas_pauvrete_monetaire';op.to_csv(out/'ophi_pauvrete_multidimensionnelle.csv',sep=';',index=False,encoding='utf-8-sig')
 dtm=read(next((ext/'HDX').glob('*OIM*.csv')));dtm['usage']='stock_a_date_ne_pas_sommer_les_dates';dtm.to_csv(out/'oim_dtm_stocks_source.csv',sep=';',index=False,encoding='utf-8-sig')
 views=read(next((ext/'HDX').glob('*VIEWS*.csv')));views['statut']='prevision_externe_hors_variables_historiques_sans_millesime_et_correspondance_grille';views.to_csv(out/'views_previsions_en_quarantaine.csv',sep=';',index=False,encoding='utf-8-sig')
 # Incidents ecoles : les trois extractions se recouvrent, dedoublonnage par identifiant d'evenement.
 incidents=[]
 for f in sorted((ext/'HDX').glob('*InsecurityInsight*.xlsx')):
  d=pd.read_excel(f);d=d[d['Country ISO'].eq('BFA')].copy();d['fichier_source']=str(f.relative_to(src));incidents.append(d)
 inc=pd.concat(incidents,ignore_index=True);inc['Date Event Modified']=pd.to_datetime(inc.get('Date Event Modified'),errors='coerce');inc=inc.sort_values('Date Event Modified',na_position='first').drop_duplicates('SiND Event ID',keep='last')
 inc[['code_geo','niveau_geo','methode_geo']]=pd.DataFrame([resolve(x,'region') for x in inc['Admin 1']],index=inc.index);inc['date_observation']=pd.to_datetime(inc.Date,errors='coerce');inc['mois']=inc.date_observation.dt.strftime('%Y-%m');inc['precision_geo_source']=inc['Geo Precision'];inc['usage']='incidents_signales_non_exhaustifs_localisation_parfois_masquee';inc.to_csv(out/'incidents_education_dedoublonnes.csv',sep=';',index=False,encoding='utf-8-sig')
 # Les etablissements publics 2016/17 restent une base historique distincte d'OSM.
 f=next((ext/'HDX').glob('*MENA*.xlsx'));schools=pd.read_excel(f,header=2);schools=schools.dropna(how='all');schools['fichier_source']=str(f.relative_to(src));schools.to_csv(out/'ecoles_publiques_2016_2017.csv',sep=';',index=False,encoding='utf-8-sig')
 # OSM : mapping communal exact ancien->nouveau ; couverture cartographique distincte des effectifs scolaires.
 osmfile=src/'donnees/DataPack_DCB_2026/DataPack_DCB_2026/data/04_Cartographie_SIG/Ecoles_OSM_HOTOSM/ecoles_osm_burkina.csv';osm=read(osmfile).drop_duplicates('id');osm=osm.rename(columns={'adm3_pcode':'old_adm3_pcode','adm2_pcode':'old_adm2_pcode_osm','adm1_pcode':'old_adm1_pcode_osm'})
 osm=osm.merge(geo[['old_adm3_pcode','adm3_pcode','adm2_pcode','adm2_name','adm1_pcode','adm1_name','pop_2019']],on='old_adm3_pcode',how='left',validate='many_to_one',suffixes=('_osm',''))
 osm['geographie_resolue']=osm.adm3_pcode.notna();osm['usage']='couverture_OSM_pas_recensement_exhaustif';osm.to_csv(out/'osm_etablissements_rattaches.csv',sep=';',index=False,encoding='utf-8-sig')
 school=osm[osm.amenity.eq('school') & osm.geographie_resolue].copy();school['nom_absent']=school.name.isna()
 osmag=school.groupby(['adm2_pcode','adm2_name','adm1_pcode','adm1_name'],as_index=False).agg(ecoles_osm=('id','nunique'),ecoles_sans_nom=('nom_absent','sum'))
 osmag=geo[['adm2_pcode','adm2_name','adm1_pcode','adm1_name']].drop_duplicates().merge(osmag,how='left');osmag['interpretation_absence']='manquant_ou_non_cartographie_ne_signifie_pas_absence_ecole';osmag.to_csv(out/'osm_couverture_47_provinces.csv',sep=';',index=False,encoding='utf-8-sig')
 # Distance indicative chef-lieu -> ecole OSM la plus proche, a vol d'oiseau, pas distance eleve-ecole.
 capitals=src/'donnees/DataPack_DCB_2026/DataPack_DCB_2026/04_Cartographie_SIG/COD-AB_limites_administratives/bfa_admin_boundaries.xlsx';cap=pd.read_excel(capitals,sheet_name='bfa_admincapitals');cap=cap[cap.adm_p_lvl.eq(3)].copy();coords=school[['latitude','longitude']].apply(pd.to_numeric,errors='coerce').dropna().to_numpy()
 distances=[]
 for row in cap.itertuples():
  la,lo=float(row.y_coord),float(row.x_coord);lat1=np.radians(la);lat2=np.radians(coords[:,0]);dl=np.radians(coords[:,1]-lo);dlat=lat2-lat1
  dist=6371*2*np.arcsin(np.sqrt(np.clip(np.sin(dlat/2)**2+np.cos(lat1)*np.cos(lat2)*np.sin(dl/2)**2,0,1)))
  distances.append(dict(adm3_pcode=row.adm3_pcode,chef_lieu=row.name,distance_km_chef_lieu_ecole_osm=float(dist.min()),definition='distance_a_vol_oiseau_chef_lieu_pas_distance_des_enfants',statut='proxy_couverture_OSM_non_exhaustive'))
 pd.DataFrame(distances).to_csv(out/'osm_distance_indicative_chefs_lieux.csv',sep=';',index=False,encoding='utf-8-sig')
 summary=dict(oda_points=len(oda),oda_doublons_retires=oda_dups,oda_jeux=int(oda.dataset_id.nunique()),catalogue_entrees=len(catalog),jeux_sans_valeurs=len(missing),oda_geo_resolus=int(oda.code_geo.ne('').sum()),oda_unite_a_confirmer=int(oda.unite_a_confirmer.sum()),acled_points=len(ac),dhs_points=len(dh),incidents_education=len(inc),ecoles_publiques_2016_2017=len(schools),osm_etablissements=len(osm),osm_geo_resolus=int(osm.geographie_resolue.sum()),chefs_lieux_distance=len(distances))
 (out/'bilan_facteurs.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
