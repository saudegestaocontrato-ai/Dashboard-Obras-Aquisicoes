import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Status Obras e Compras", page_icon="📊", layout="wide")

# --- FUNÇÃO PRA FORMATAR REAL ---
def brl(valor):
    try:
        num = float(valor)
        if pd.isna(num) or num == 0:
            return "R$ 0,00"
        return f"R$ {num:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return "R$ 0,00"

@st.cache_data
def carregar_dados():
    df = pd.read_excel("Status de Obras e Compras de Mobiliário.xlsx")
    df.columns = df.columns.str.strip()
    return df

df = carregar_dados()

st.title("📊 Status de Obras e Compras de Mobiliário")

# Colunas que você informou
col_valor = 'Valor Total (Estimado)'  # Coluna G
col_fonte = 'FONTE DE COMPRA'

# Converte valor pra número pra conseguir somar
df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)

# --- 1. VALOR TOTAL ESTIMADO ---
st.subheader("Valor Total Estimado")
total_estimado = df[col_valor].sum()
st.metric(label="Total Geral", value=brl(total_estimado))  # AQUI APLICA R$
st.divider()

# --- 2. VALOR TOTAL POR FONTE DE COMPRA ---
if col_fonte in df.columns:
    st.subheader("Valor Total por Fonte de Compra")
    valor_fonte = df.groupby(col_fonte)[col_valor].sum().reset_index()
    
    fig_fonte = px.bar(valor_fonte, x=col_fonte, y=col_valor, text=col_valor)
    fig_fonte.update_traces(
        texttemplate='R$ %{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),  # AQUI APLICA R$
        textposition='outside'
    )
    fig_fonte.update_layout(
        yaxis_tickprefix="R$ ",  # AQUI APLICA R$ no eixo Y
        yaxis_tickformat=",.2f"
    )
    st.plotly_chart(fig_fonte, use_container_width=True)
    st.divider()

# --- 3. ORÇAMENTO: ENTREGUE VS ABERTO ---
# Se você tiver coluna de status, me fala o nome que eu coloco aqui
# Por enquanto deixo sem pra não quebrar nada que já existia

# --- 4. DADOS DETALHADOS ---
st.subheader("Dados Detalhados")
df_tabela = df.copy()
df_tabela[col_valor] = df_tabela[col_valor].apply(brl)  # AQUI APLICA R$ na tabela
st.dataframe(df_tabela, use_container_width=True, hide_index=True)
st.caption(f"**Valor Total dos Dados Detalhados: {brl(df[col_valor].sum())}**")  # AQUI APLICA R$
