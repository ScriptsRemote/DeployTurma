##pre processamento 
import pandas as pd 
import geopandas as gpd

##Elaborar função
def load_data():
    df = pd.read_csv('https://dados.agricultura.gov.br/dataset/baefdc68-9bad-4204-83e8-f2888b79ab48/resource/ac7e4351-974f-4958-9294-627c5cbf289a/download/psrdadosabertos2024csv.csv',
                 encoding='latin1', sep=';', low_memory=False)
    return df

df = load_data()

df.drop(columns=['CD_PROCESSO_SUSEP', 'NR_PROPOSTA', 'ID_PROPOSTA',
                 'DT_PROPOSTA', 'DT_INICIO_VIGENCIA', 'DT_FIM_VIGENCIA', 'NM_SEGURADO',
                 'NR_DOCUMENTO_SEGURADO', 'LATITUDE', 'NR_GRAU_LAT', 'NR_MIN_LAT',
                 'NR_SEG_LAT', 'LONGITUDE', 'NR_GRAU_LONG', 'NR_MIN_LONG', 'NR_SEG_LONG',
                 'NR_DECIMAL_LATITUDE', 'NR_DECIMAL_LONGITUDE',
       'NivelDeCobertura','DT_APOLICE',
       'ANO_APOLICE', 'CD_GEOCMU'], inplace=True)

df.columns

df.to_parquet('assets/dados_filtrado.parquet')


##Elaborar função
def load_geodata(): 
    return gpd.read_file('datasets/BR_UF_2022.shp')

gdf = load_geodata()

tolerancia =0.01

gdf['geometry'] = gdf['geometry'].simplify(tolerance=tolerancia,
                                           preserve_topology=True)

gdf.to_file('assets/BR_UF_2022_filtrado.geojson', driver='GeoJSON')

