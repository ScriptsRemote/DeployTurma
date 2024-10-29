import streamlit as st 
import geopandas as gpd
import pandas as pd 
import plotly.express as px 
import mapclassify
import os 
import folium
from streamlit_folium import folium_static
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

##Configurar pagina
st.set_page_config(layout='wide')
st.sidebar.image('assets/Logo.png')

# Função para carregar o GeoDataFrame com cache, otimizando a velocidade de carregamento
@st.cache_data
def load_geodata():
    # Carregar o shapefile com os estados do Brasil
    return gpd.read_file('assets/BR_UF_2022_filtrado.geojson')

# Função para carregar o DataFrame de dados de seguros com cache
@st.cache_data
def load_data():
    url = 'assets/dados_filtrado.parquet'
    # Carregar os dados de seguros diretamente de uma URL e definir o encoding e separador
    df = pd.read_parquet(url)
    return df

# Carregar os dados geográficos usando a função cacheada
gdf = load_geodata()
# Carregar os dados de seguros usando a função cacheada
df = load_data()

# Limpar dados numéricos convertendo as colunas selecionadas para float
cols = ['NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO']
df[cols] = df[cols].replace(',', '.', regex=True).astype(float)

# Agrupar os dados de seguros por estado para obter área total, valor total e número de seguros por estado
df_estado = df.groupby('SG_UF_PROPRIEDADE').agg(
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
    numero_seguros=('NR_APOLICE', 'nunique')
).reset_index()

# Unir o GeoDataFrame (gdf) com os dados agregados por estado para mapeamento
gdf = gdf.merge(df_estado, left_on='SIGLA_UF', right_on='SG_UF_PROPRIEDADE', how='left')


# Agrupar os dados por razão social para cálculo de métricas específicas
df_razao_social = df.groupby('NM_RAZAO_SOCIAL').agg(
    numero_seguros=('NR_APOLICE', 'nunique'),
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
    estados=('SG_UF_PROPRIEDADE', 'unique') 
).reset_index()

df_razao_social_estado = df.groupby(['NM_RAZAO_SOCIAL', 'SG_UF_PROPRIEDADE']).agg(
    numero_seguros=('NR_APOLICE', 'nunique'),
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum') 
).reset_index()

# Contar o número de estados únicos associados a cada razão social
df_razao_social['contagem_estados'] = df_razao_social['estados'].apply(len)

# Calcular a matriz de correlação entre as variáveis selecionadas com arredondamento para 2 casas decimais
correlation_columns = ['NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO', 'VL_LIMITE_GARANTIA', 
                       'NR_PRODUTIVIDADE_ESTIMADA', 'NR_PRODUTIVIDADE_SEGURADA', 'VL_SUBVENCAO_FEDERAL']
for col in correlation_columns:
    df[col] = df[col].replace(',', '.', regex=True).astype(float)

# Gerar a matriz de correlação arredondada
correlation_matrix = df[correlation_columns].corr().round(2)

#####################################################################################

#####################################################################################
st.title('Análise de Seguros Agrícolas - Brasil')
st.markdown('''**Descrição da Base de Dados**: O SISSER é utilizado na operacionalização do PSR,Programa de Subvenção ao Prêmio do Seguro Rural, através de troca de informações
entre o MAPA e as seguradoras habilitadas no programa. Nele constam as informações referentes aos produtores que receberam a subvenção e os dados das apólices
recepcionadas.Acesse a base dados em [Dados.Gov](https://dados.gov.br/home') ou [Dados Agricultura](https://dados.agricultura.gov.br/dataset/sisser3/resource/ac7e4351-974f-4958-9294-627c5cbf289a).
O(a) usuário(a) deve selecionar qual a análise dejada, bem como se será em nível Estadual ou Federal.  
        ''')
st.divider()

with st.sidebar:
    st.subheader('''SISSER - Sistema de Subvenção Econômica ao Prêmio do Seguro Rural. Fonte:[SISSER](https://dados.agricultura.gov.br/dataset/sisser3)''')
    analise_tipo = st.selectbox("Selecione o tipo de análise", ["Razão Social", "Estado"])
###################################################################
if analise_tipo =='Razão Social':
    st.header('Análise por Razão Social')
    
    # Definir as opções de métricas que o usuário pode selecionar para análise
    metric_options = {
        'Número de Seguros': 'numero_seguros',
        'Contagem de Estados': 'contagem_estados',
        'Área Total': 'area_total'
    }
    
    top_estado_num_apolices= df_estado.loc[df_estado['numero_seguros'].idxmax()]
    top_estado_area_total = df_estado.loc[df_estado['area_total'].idxmax()]
    top_estado_valor_total = df_estado.loc[df_estado['valor_total'].idxmax()]
    
    with st.sidebar:
                st.markdown(
                    f"**Estado com maior número de apólices:** {top_estado_num_apolices['SG_UF_PROPRIEDADE']} "
                    f"com {top_estado_num_apolices['numero_seguros']} apólices.\n\n"
                    f"**Estado com maior área total assegurada:** {top_estado_area_total['SG_UF_PROPRIEDADE']} "
                    f"com {top_estado_area_total['area_total']:.2f} ha.\n\n"
                    f"**Estado com maior valor total assegurado:** {top_estado_valor_total['SG_UF_PROPRIEDADE']} "
                    f"com R$ {top_estado_valor_total['valor_total']:.2f}."
                )

        # Menu dropdown para o usuário selecionar a métrica desejada   
    selected_metric = st.selectbox("Selecione a Métrica", options=list(metric_options.keys()))
    metric_column = metric_options[selected_metric]
    
    
    # Ordenar os dados do DataFrame por ordem decrescente com base na métrica selecionada
    df_sorted = df_razao_social.sort_values(by=metric_column, ascending=False)
    
    ########################Gráficos############################################
    fig_bar = px.bar(
        df_sorted, x='NM_RAZAO_SOCIAL', y=metric_column,
        title=f'{selected_metric} por Razão Social',
        labels={'NM_RAZAO_SOCIAL':'Razão Social', metric_column:selected_metric}
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)
    st.divider()
    
    #######################Métricas#############################################
    max_num_seguros = df_razao_social['numero_seguros'].max()
    mean_num_seguros = df_razao_social['numero_seguros'].mean()
    var_num_seguros = ((max_num_seguros - mean_num_seguros) / mean_num_seguros) * 100
    top_razao_num_seguros = df_razao_social[df_razao_social['numero_seguros'] == max_num_seguros]['NM_RAZAO_SOCIAL'].values[0]

    max_count_estados = df_razao_social['contagem_estados'].max()
    mean_count_estados = df_razao_social['contagem_estados'].mean()
    var_count_estados = ((max_count_estados - mean_count_estados) / mean_count_estados) * 100
    top_razao_count_estados = df_razao_social[df_razao_social['contagem_estados'] == max_count_estados]['NM_RAZAO_SOCIAL'].values[0]

    max_area_total = df_razao_social['area_total'].max()
    mean_area_total = df_razao_social['area_total'].mean()
    var_area_total = ((max_area_total - mean_area_total) / mean_area_total) * 100
    top_razao_area_total = df_razao_social[df_razao_social['area_total'] == max_area_total]['NM_RAZAO_SOCIAL'].values[0]

    ##Exibir como cartões 
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric(
                label = f"Máximo Numero de Seguros - {top_razao_num_seguros}",
                value=f"{max_num_seguros:.0f}",
                delta=f"{var_num_seguros:.2f}% em relação à média" 
                
            )
    with col2:
        with st.container(border=True):
            st.metric(
            label=f"Máximo Contagem de Estados - {top_razao_count_estados}",
            value=f"{max_count_estados:.0f}",
            delta=f"{var_count_estados:.2f}% em relação à média"
            )
    with col3:
        with st.container(border=True):
            st.metric(
                label=f"Máximo Área Total (ha) - {top_razao_area_total}",
                value=f"{max_area_total:.2f}",
                delta=f"{var_area_total:.2f}% em relação à média"
            )
    st.divider()
    
    ########################Corr##################################
    st.subheader('Correlação entre Parâmetros')
    fig_heatmap = px.imshow(correlation_matrix, text_auto=True, 
                            color_continuous_scale="Blues", 
                            title="Correlação entre Parâmetros", 
                            width=400, height=800)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    ######################Criação do mapa e do gráfico de pizza
    ##Exibir os mapas e gráficos 
    col1, col2 = st.columns([1,1])
    with col1:
        with st.container(border=True):
            m_valor = folium.Map(location=[-15.78,-47.93], zoom_start=3)
            
            gdf.explore(
                m=m_valor,
                column='valor_total',
                cmap='BuPu',
                scheme='Quantiles',
                style_kwds=dict(color='black', weight=2, opacity=0.4),
                k=4,
                legend=True,
                legend_kwds=dict(colorbar=False, caption='Valor Total Assegurado')
            )
            
            st.subheader('Valor Total Assegurado')
            st_folium(m_valor,  width=800, height=600, use_container_width=True)
    
    with col2:
         with st.container(border=True):
            fig_pie_valor = px.pie(
                df_razao_social, 
                names='NM_RAZAO_SOCIAL', 
                values='valor_total', 
                title='Distribuição do Valor Total Assegurado por Razão Social'
            )
            
             # Configura a legenda para aparecer em duas colunas com fonte menor
            fig_pie_valor.update_layout(
                legend=dict(
                    orientation="h",  # Orientação horizontal
                    yanchor="top",    # Ancoragem no topo
                    y=-0.4,           # Posição abaixo do gráfico
                    xanchor="center", # Centraliza a legenda
                    x=0.5,
                    itemsizing='constant', # Mantém o tamanho dos itens constantes
                    traceorder='normal',   # Ordem normal de exibição
                    itemclick='toggle',    # Permite que a legenda seja clicável
                    font=dict(size=9),     # Ajusta o tamanho da fonte para 8
                    title=None,            # Remove o título da legenda
                    bgcolor='rgba(255, 255, 255, 0)',  # Fundo transparente
                ),
                width=700  # Ajuste a largura do gráfico, se necessário
            )

            st.plotly_chart(fig_pie_valor, use_container_width=True)
            
            
# Exibir os mapas de Área Total e Número de Apólices lado a lado
    col1, col2 = st.columns([1,1])
    with col1:
        with st.container(border=True):
            m_area = folium.Map(location=[-15.78, -47.93], zoom_start=3)
            gdf.explore(
                m=m_area,
                column='area_total',
                cmap='YlOrBr',
                scheme='Quantiles',
                style_kwds=dict(color="black", weight=2, opacity=0.4),
                k=4,
                legend=True,
                legend_kwds=dict(colorbar=False, caption='Área Total Assegurada')
            )
            st.subheader("Área Total Assegurada")
            st_folium(m_area, width=800, height=600, use_container_width=True)

    with col2:
        with st.container(border=True):
            m_apolice = folium.Map(location=[-15.78, -47.93], zoom_start=3)
            gdf.explore(
                m=m_apolice,
                column='numero_seguros',
                cmap='Greens',
                scheme='Quantiles',
                style_kwds=dict(color="black", weight=2, opacity=0.4),
                k=4,
                legend=True,
                legend_kwds=dict(colorbar=False ,caption='Número de Apólices')
            )
            st.subheader("Número de Apólices")
            st_folium(m_apolice, width=800, height=600, use_container_width=True)
    
    
####################################################################
else:
    st.header('Análise por Estado')
    
    # Seletor de Estado para o usuário escolher o estado desejado
    estado_escolhido = st.sidebar.selectbox("Selecione um Estado", df['SG_UF_PROPRIEDADE'].unique())
    
     
    # Filtrar os dados para o estado selecionado
    df_estado = df_razao_social_estado[df_razao_social_estado['SG_UF_PROPRIEDADE'] == estado_escolhido]
    # st.dataframe(df_estado)
    
        # Agrupar por município no estado selecionado para Top 10 por área e valor
    df_municipio = df[df['SG_UF_PROPRIEDADE'] == estado_escolhido].groupby('NM_MUNICIPIO_PROPRIEDADE').agg(
        area_total=('NR_AREA_TOTAL', 'sum'),
        valor_total=('VL_PREMIO_LIQUIDO', 'sum')
    ).reset_index()
    
      
   # Filtrar os Top 10 municípios por área e valor total
    df_top_area = df_municipio.nlargest(10, 'area_total')
    df_top_valor = df_municipio.nlargest(10, 'valor_total')

    # Combinar os Top 10 de área e valor para obter uma lista única de municípios
    df_top_combined = pd.concat([df_top_area, df_top_valor]).drop_duplicates()
    
    # Cálculo da correlação entre área total e valor total para os Top 10 municípios combinados
    correlation_top_municipios = df_top_combined[['area_total', 'valor_total']].corr().iloc[0, 1]

    # Exibir a correlação calculada
    st.sidebar.divider()
    st.sidebar.subheader('Análise exploratória dos dados')
    st.sidebar.markdown(f'Analisando os dados de Área Total e Valor do Prêmio Líquido nota-se uma correlação de {correlation_top_municipios:.2f}')
    st.sidebar.divider()
    
      # Gráfico de Barras - Top 10 Municípios com Maior Área
    col1, col2 = st.columns(2)
    with col1:
        fig_top_area = px.bar(df_top_area, x='NM_MUNICIPIO_PROPRIEDADE', y='area_total', 
                              title=f'Top 10 Municípios com Maior Área em {estado_escolhido}',
                              labels={'NM_MUNICIPIO_PROPRIEDADE': 'Município', 'area_total': 'Área Total'})
        st.plotly_chart(fig_top_area, use_container_width=True)

    # Gráfico de Barras - Top 10 Municípios com Maior Valor
    with col2:
        fig_top_valor = px.bar(df_top_valor, x='NM_MUNICIPIO_PROPRIEDADE', y='valor_total', 
                               title=f'Top 10 Municípios com Maior Valor Assegurado em {estado_escolhido}',
                               labels={'NM_MUNICIPIO_PROPRIEDADE': 'Município', 'valor_total': 'Valor Total'})
        st.plotly_chart(fig_top_valor, use_container_width=True)
    
    st.divider()     

     # Gráfico de Barras - Número de Seguros por Estado e Razão Social
    fig_bar_estado_seguros = px.bar(df_estado, x='NM_RAZAO_SOCIAL', y='numero_seguros', 
                                    title=f'Número de Seguros em {estado_escolhido} por Razão Social',
                                    labels={'NM_RAZAO_SOCIAL': 'Razão Social', 'numero_seguros': 'Número de Seguros'})
    st.plotly_chart(fig_bar_estado_seguros)
    
     # Gráfico de Pizza - Distribuição da Área Total Assegurada por Razão Social no Estado
    fig_pie_estado_area = px.pie(df_estado, names='NM_RAZAO_SOCIAL', values='area_total', 
                                 title=f'Distribuição da Área Total Assegurada em {estado_escolhido} por Razão Social')
    st.plotly_chart(fig_pie_estado_area)

    # Gráfico de Pizza - Distribuição do Valor Total Assegurado por Razão Social no Estado
    fig_pie_estado_valor = px.pie(df_estado, names='NM_RAZAO_SOCIAL', values='valor_total', 
                                  title=f'Distribuição do Valor Total Assegurado em {estado_escolhido} por Razão Social')
    st.plotly_chart(fig_pie_estado_valor)





