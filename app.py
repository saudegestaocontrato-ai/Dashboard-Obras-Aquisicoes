import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Status Obras e Compras", page_icon="📊", layout="wide")

def brl(valor):
    if pd.isna(valor) or valor == 0:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

@st.cache_data
def carregar_dados():
    try:
        df = pd.read_excel("Status de Obras e Compras de Mobiliário.xlsx")
    except FileNotFoundError:
        st.error("Arquivo Excel não encontrado. Verifica se o nome está igual ao do GitHub.")
        st.stop()
    
    df.columns = df.columns.str.strip() # Remove espaços extras nos nomes das colunas
    return df

df = carregar_dados()

st.title("📊 Status de Obras e Compras de Mobiliário")

# --- CHECAGEM AUTOMÁTICA DAS COLUNAS ---
# Tenta achar as colunas mais prováveis. Se não achar, mostra erro.
colunas = df.columns.tolist()
col_valor = next((c for c in colunas if 'valor' in c.lower() or 'total' in c.lower() or 'preço' in c.lower()), None)
col_ubs = next((c for c in colunas if 'ubs' in c.lower() or 'unidade' in c.lower() or 'local' in c.lower()), None)
col_status = next((c for c in colunas if 'status' in c.lower() or 'situação' in c.lower() or 'etapa' in c.lower()), None)

if not col_valor:
    st.error("Não achei a coluna de Valor no Excel.")
    st.write("Colunas disponíveis:", colunas)
    st.info("Me fala qual é a coluna de valor que eu arrumo o código.")
    st.stop()

df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)

# --- KPIs ---
col1, col2, col3 = st.columns(3)
total_valor = df[col_valor].sum()
total_itens = len(df)
total_ubs = df[col_ubs].nunique() if col_ubs else 0

col1.metric("Valor Total", brl(total_valor))
col2.metric("Total de Itens", f"{total_itens:,}".replace(",", "."))
col3.metric("Total de UBS" if col_ubs else "Total de Linhas", f"{total_ubs}" if col_ubs else "-")
st.divider()

# --- FILTROS ---
df_filtrado = df.copy()
if col_ubs and col_status:
    col_f1, col_f2 = st.columns(2)
    ubs_sel = col_f1.multiselect(f"Filtrar por {col_ubs}", sorted(df[col_ubs].dropna().unique()))
    status_sel = col_f2.multiselect(f"Filtrar por {col_status}", sorted(df[col_status].dropna().unique()))
    if ubs_sel:
        df_filtrado = df_filtrado[df_filtrado[col_ubs].isin(ubs_sel)]
    if status_sel:
        df_filtrado = df_filtrado[df_filtrado[col_status].isin(status_sel)]

# --- GRÁFICOS ---
if col_ubs:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader(f"Valor por {col_ubs}")
        valor_ubs = df_filtrado.groupby(col_ubs)[col_valor].sum().reset_index()
        fig = px.bar(valor_ubs, x=col_ubs, y=col_valor, text=col_valor)
        fig.update_traces(texttemplate='R$ %{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'))
        fig.update_layout(yaxis_tickprefix="R$ ", yaxis_tickformat=",.2f", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    if col_status:
        with col_g2:
            st.subheader(f"Valor por {col_status}")
            valor_st = df_filtrado.groupby(col_status)[col_valor].sum().reset_index()
            fig = px.pie(valor_st, names=col_status, values=col_valor, hole=0.4)
            fig.update_traces(texttemplate='R$ %{value:,.2f}<br>%{percent}'.replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Detalhamento")
df_tabela = df_filtrado.copy()
df_tabela[col_valor] = df_tabela[col_valor].apply(brl)
st.dataframe(df_tabela, use_container_width=True, hide_index=True)
st.caption(f"Total filtrado: {len(df_filtrado)} itens | {brl(df_filtrado[col_valor].sum())}")
