import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import re

# A partir daqui segue a dashboard como está, usando sitemap_df como df_urls_blog

# Função principal para análise
@st.cache_data
def analisar_volume_blog(domain, df_keywords, df_urls_blog, ano_selecionado=None):
    df_domain_keywords = df_keywords[df_keywords['domain'] == domain]
    df_urls_blog_filtrado = df_urls_blog[df_urls_blog['DOMAIN'] == domain].copy()

    if 'LastModified' in df_urls_blog_filtrado.columns:
        df_urls_blog_filtrado['LastModified'] = pd.to_datetime(df_urls_blog_filtrado['LastModified'], errors='coerce')
        df_urls_blog_filtrado['AnoPublicacao'] = df_urls_blog_filtrado['LastModified'].dt.year
        if ano_selecionado:
            df_urls_blog_filtrado = df_urls_blog_filtrado[df_urls_blog_filtrado['AnoPublicacao'] == ano_selecionado]

    blog_urls = df_urls_blog_filtrado['URL'].tolist()
    is_blog = df_domain_keywords['URL'].isin(blog_urls)
    df_blog = df_domain_keywords[is_blog]
    df_fora = df_domain_keywords[~is_blog]

    def categorizar_posicao(pos):
        if pos <= 3:
            return '1-3'
        elif pos <= 10:
            return '4-10'
        elif pos <= 20:
            return '11-20'
        elif pos <= 30:
            return '21-30'
        else:
            return '30+'

    df_blog['faixa'] = df_blog['Position'].apply(categorizar_posicao)
    df_fora['faixa'] = df_fora['Position'].apply(categorizar_posicao)

    distrib_blog = df_blog['faixa'].value_counts().reindex(['1-3','4-10','11-20','21-30','30+'], fill_value=0)
    distrib_fora = df_fora['faixa'].value_counts().reindex(['1-3','4-10','11-20','21-30','30+'], fill_value=0)

    vol_total_blog = df_blog['Search Volume'].sum()
    vol_top10_blog = df_blog[df_blog['Position'] <= 10]['Search Volume'].sum()
    pct_top10_blog = (vol_top10_blog / vol_total_blog) * 100 if vol_total_blog > 0 else 0

    vol_total_fora = df_fora['Search Volume'].sum()
    vol_top10_fora = df_fora[df_fora['Position'] <= 10]['Search Volume'].sum()
    pct_top10_fora = (vol_top10_fora / vol_total_fora) * 100 if vol_total_fora > 0 else 0

    qtd_urls_blog_total = len(set(blog_urls))
    qtd_urls_blog_rankeando = df_blog['URL'].nunique()

    return {
        'volume_dentro_blog': vol_total_blog,
        'volume_fora_blog': vol_total_fora,
        'qtd_palavras_dentro_blog': df_blog.shape[0],
        'qtd_palavras_fora_blog': df_fora.shape[0],
        'distribuicao_blog': distrib_blog,
        'distribuicao_fora': distrib_fora,
        'pct_volume_top10_blog': pct_top10_blog,
        'pct_volume_top10_fora': pct_top10_fora,
        'qtd_urls_blog_total': qtd_urls_blog_total,
        'qtd_urls_blog_rankeando': qtd_urls_blog_rankeando
    }

# Streamlit UI
df_keywords = pd.read_csv(r'data/keywords.csv')
df_urls_blog = pd.read_csv(r'data/urls_domains.csv')

if 'LastModified' in df_urls_blog.columns:
    df_urls_blog['LastModified'] = pd.to_datetime(df_urls_blog['LastModified'], errors='coerce')
    df_urls_blog['AnoPublicacao'] = df_urls_blog['LastModified'].dt.year

st.title("Dashboard de Performance Orgânica por Blog")
domain = st.selectbox('Escolha o domínio:', df_keywords['domain'].unique())

anos_disponiveis = sorted(df_urls_blog[df_urls_blog['DOMAIN'] == domain]['AnoPublicacao'].dropna().unique())
ano_selecionado = st.selectbox('Filtrar por Ano de Publicação das URLs do Blog:', options=[None] + list(anos_disponiveis), format_func=lambda x: "Todos" if x is None else str(x))

result = analisar_volume_blog(domain, df_keywords, df_urls_blog, ano_selecionado)

st.header(f"Análise de Volume de Busca - {domain}" + (f" ({ano_selecionado})" if ano_selecionado else ""))

col1, col2 = st.columns(2)
with col1:
    st.metric("Volume de Busca estimado — Blog", f"{result['volume_dentro_blog']:,}".replace(",", "."))
    st.metric("Palavras que ranqueiam — Blog", f"{result['qtd_palavras_dentro_blog']:,}".replace(",", "."))
    st.metric("Quanto do volume de busca total está no TOP 10", f"{result['pct_volume_top10_blog']:.2f}%")
with col2:
    st.metric("Volume Fora do Blog", f"{result['volume_fora_blog']:,}".replace(",", "."))
    st.metric("Palavras Fora do Blog", f"{result['qtd_palavras_fora_blog']:,}".replace(",", "."))
    st.metric("% Volume Top 10 (Fora)", f"{result['pct_volume_top10_fora']:.2f}%")

st.markdown("""
---
<div style='background-color:#f0f0f0;padding:10px;border-radius:6px;display:flex;justify-content:space-between;'>
  <div><b>URLs do Blog que Ranqueiam:</b> {}</div>
  <div><b>Total de URLs do Blog:</b> {}</div>
</div>
""".format(result['qtd_urls_blog_rankeando'], result['qtd_urls_blog_total']), unsafe_allow_html=True)

st.subheader("Distribuição de Posições")
labels = ['1-3', '4-10', '11-20', '21-30', '30+']
blog_vals = [result['distribuicao_blog'][label] for label in labels]
fora_vals = [result['distribuicao_fora'][label] for label in labels]

fig = go.Figure()
fig.add_trace(go.Bar(x=labels, y=blog_vals, name='Blog'))
fig.add_trace(go.Bar(x=labels, y=fora_vals, name='Fora do Blog', yaxis='y2'))

fig.update_layout(
    title='Distribuição de Posições - Blog vs Fora do Blog',
    xaxis_title='Faixa de Posição',
    yaxis=dict(title='Quantidade - Blog'),
    yaxis2=dict(title='Quantidade - Fora do Blog', overlaying='y', side='right', showgrid=False),
    barmode='group'
)

st.plotly_chart(fig, use_container_width=True)

if 'LastModified' in df_urls_blog.columns:
    st.subheader("Distribuição de URLs por Ano de Publicação")
    urls_por_ano = df_urls_blog[df_urls_blog['DOMAIN'] == domain]['AnoPublicacao'].value_counts().sort_index()
    st.bar_chart(urls_por_ano)
