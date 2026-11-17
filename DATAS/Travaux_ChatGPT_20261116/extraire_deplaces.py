"""Stocks PDI : snapshots et archives multidates distingues, textes libres exclus."""
from pathlib import Path
import argparse,json,re
import pandas as pd,numpy as np
from extraire_secondaire import norm,number

MONTHS={'JANVIER':'01','FEVRIER':'02','MARS':'03','AVRIL':'04','MAI':'05','JUIN':'06','JUILLET':'07','AOUT':'08','SEPTEMBRE':'09','OCTOBRE':'10','NOVEMBRE':'11','DECEMBRE':'12'}
def datefile(name):
 n=norm(name);m=re.search(r'(\d{2}) (JANVIER|FEVRIER|MARS|AVRIL|MAI|JUIN|JUILLET|AOUT|SEPTEMBRE|OCTOBRE|NOVEMBRE|DECEMBRE) (20\d{2})',n)
 if m:return f'{m[3]}-{MONTHS[m[2]]}-{m[1]}'
 m=re.search(r'(20\d{2})(\d{2})(\d{2})',n)
 if m:return '-'.join(m.groups())
 m=re.search(r'(\d{2})(\d{2})(20\d{2})',n)
 if m:return f'{m[3]}-{m[2]}-{m[1]}'
 return ''

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--sortie',type=Path,required=True);a=ap.parse_args();a.sortie.mkdir(parents=True,exist_ok=True)
 g=pd.read_csv(next((a.source/'01_collecte').glob('*referentiel-communes*')),sep=';');al=pd.read_csv(next((a.source/'01_collecte').glob('*alias-noms*')),sep=';');pr=al[(al.niveau=='province')&(al.decoupage=='ancien')];pmap=dict(zip(pr.alias,pr.code));pmap.update({'KOMONDJOARI':pmap['KOMANDJARI'],'KOMONDJARI':pmap['KOMANDJARI'],'KOURITENGA':pmap['KOURITTENGA'],'LORUM':pmap['LOROUM'],'ZANDOMA':pmap['ZONDOMA']})
 cm={}
 for r in g.itertuples():
  for n in [r.adm3_name,r.nom_rgph]:cm[(r.old_adm2_pcode,norm(n))]=(r.adm3_pcode,r.old_adm3_pcode)
 points=[];log=[];folder=a.source/'DATAS/DataPack_DCB_2026/DataPack_DCB_2026/data/03_Conditions_de_Vie_et_Emploi/PDI_CONASUR'
 for f in sorted(folder.glob('*.csv')):
  d=pd.read_csv(f,sep=';',dtype=str).drop(columns=['remarque_collecte'],errors='ignore');head=None;cols={}
  for ix,row in d.head(15).iterrows():
   names={c:norm(v) for c,v in row.items() if pd.notna(v)}
   com=[c for c,v in names.items() if re.fullmatch(r'COMMUNES?( DESTINATION)?',v)]
   total=[c for c,v in names.items() if v in ['TOTAL INDIVIDUS','TOTAL INDIVIDUS2','TOTAL PDIS','NOMBRE TOTAL DE PDI']]
   if com and total:
    cols={'commune':com[0],'total':total[0]};head=ix
    for kind,pat in [('province',r'^PROVINCES?( DESTINATION)?$'),('date',r'^DATE DON'),('code_commune',r'^(ADMIN 3 PCODE|ADMIN3PCOD|ADMIN 3 PCOD)$'),('enfants',r'^TOTAL ENFANTS$')]:
     got=[c for c,v in names.items() if re.search(pat,v)]
     if got:cols[kind]=got[0]
    break
  if head is None:log.append(dict(fichier=f.name,statut='table_speciale_non_normalisee',lignes=len(d)));continue
  count=0
  for ix,row in d.iloc[head+1:].iterrows():
   v=number(str(row[cols['total']]))
   if v is None or v<0:continue
   label=row[cols['commune']]
   if pd.isna(label) or norm(label).startswith('TOTAL'):continue
   province=row.get(cols.get('province',''),None);pc=pmap.get(norm(province),'');new,old=cm.get((pc,norm(label)),('',''))
   rawdate=row.get(cols.get('date',''),None)
   if pd.notna(rawdate):
    dt=pd.to_datetime(rawdate,errors='coerce');date=dt.strftime('%Y-%m-%d') if pd.notna(dt) else '';method='date_ligne_source'
   else:date=datefile(f.name);method='date_nom_fichier'
   rawcode=row.get(cols.get('code_commune',''),'');contradiction=bool(old and pd.notna(rawcode) and str(rawcode).startswith('BF') and rawcode!=old)
   points.append(dict(fichier=str(f.relative_to(a.source)),ligne_source=ix+2,date=date,methode_date=method,province_source=province,commune_source=label,old_adm2_pcode=pc,adm3_pcode=new,code_commune_source=rawcode,code_source_incoherent_nom=contradiction,pdi_total=v,pdi_enfants=number(str(row.get(cols.get('enfants',''),''))),nature='archive_multidates' if 'date' in cols else 'snapshot_communal',eligible_agregation=False if 'date' in cols else bool(new and date and not contradiction)))
   count+=1
  log.append(dict(fichier=f.name,statut='normalise_archive_non_sommable' if 'date' in cols else 'snapshot_normalise',lignes=len(d),observations=count))
 df=pd.DataFrame(points);df.to_csv(a.sortie/'pdi_observations_provenance.csv',sep=';',index=False,encoding='utf-8-sig')
 snap=df[df.nature.eq('snapshot_communal')].copy();key=['date','adm3_pcode'];snap['doublon_cle']=snap.duplicated(key,False);snap.loc[snap.doublon_cle,'eligible_agregation']=False;snap=snap.merge(g[['adm3_pcode','adm2_pcode','adm2_name','adm1_pcode','adm1_name']],how='left',on='adm3_pcode',validate='many_to_one');snap.to_csv(a.sortie/'pdi_snapshots_communes.csv',sep=';',index=False,encoding='utf-8-sig')
 ag=snap[snap.eligible_agregation].groupby(['date','adm2_pcode','adm2_name','adm1_pcode','adm1_name'],as_index=False).agg(pdi_dans_communes_renseignees=('pdi_total','sum'),communes_renseignees=('adm3_pcode','nunique'))
 expected=g.groupby('adm2_pcode').size().rename('communes_attendues');ag=ag.merge(expected,on='adm2_pcode');ag['couverture_communes']=ag.communes_renseignees/ag.communes_attendues;ag['total_province_complet']=ag.couverture_communes.eq(1);ag['interpretation']='somme_des_communes_publiees_absences_non_remplacees_par_zero';ag.to_csv(a.sortie/'pdi_47_provinces_couverture_explicitee.csv',sep=';',index=False,encoding='utf-8-sig')
 pd.DataFrame(log).to_csv(a.sortie/'pdi_statut_chaque_table.csv',sep=';',index=False,encoding='utf-8-sig');print('PDI',len(df),'observations',len(snap),'snapshots communaux',len(ag),'agregats avec couverture')

if __name__=='__main__':main()
