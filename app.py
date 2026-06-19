import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Status Obras e Compras", page_icon="📊", layout="wide")

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

    # Coluna G = índice 6 = Valor Total (Estimado)
    col_valor_nome = 'Valor Total (Estimado)'
    if col_valor_nome in df.columns:
        df[col_valor_nome] = pd.to_numeric(df[col_valor_nome], errors='coerce').fillna(0)
    else:
        df.iloc[:, 6] = pd.to_numeric(df.iloc[:, 6], errors='coerce').fillna(0)
        df.rename(columns={df.columns[6]: col_valor_nome}, inplace=True)

    return df, col_valor_nome

df, col_valor = carregar_dados()
st.title("📊 Status de Obras e Compras de Mobiliário")

# --- 1. VALOR TOTAL ESTIMADO ---
st.subheader("Valor Total Estimado")
total_estimado = df[col_valor].sum()
st.metric(label="Total Geral", value=brl(total_estimado))
st.divider()

# --- 2. VALOR TOTAL POR FONTE DE COMPRA ---
col_fonte = 'FONTE DE COMPRA'
if col_fonte in df.columns:
    st.subheader("Valor Total por Fonte de Compra")
    valor_fonte = df.groupby(col_fonte)[col_valor].sum().reset_index().sort_values(col_valor, ascending=False)

    fig_fonte = px.bar(valor_fonte, x=col_fonte, y=col_valor, text=col_valor)
    fig_fonte.update_traces(
        texttemplate='R$ %{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
        textposition='outside'
    )
    fig_fonte.update_layout(yaxis_tickprefix="R$ ", yaxis_tickformat=",.2f", xaxis_title="", yaxis_title="Valor")
    st.plotly_chart(fig_fonte, use_container_width=True)
    st.divider()

# --- 3. ORÇAMENTO: ENTREGUE VS ABERTO ---
# Tenta achar sozinho. Se achar, mostra. Se não, ignora.
col_status = next((c for c in df.columns if any(p in c.lower() for p in ['status', 'situação', 'etapa', 'fase'])), None)

if col_status:
    st.subheader("Orçamento: Entregue vs Aberto")
    df['Status_Padronizado'] = df[col_status].astype(str).apply(
        lambda x: 'Entregue' if any(p in x.lower() for p in ['entreg', 'finaliz', 'conclu', 'pronto']) else 'Aberto'
    )

    valor_status = df.groupby('Status_Padronizado')[col_valor].sum().reset_index()
    fig_status = px.pie(
        valor_status, names='Status_Padronizado', values=col_valor, hole=0.4,
        color_discrete_map={'Entregue':'#2E8B57', 'Aberto':'#FF8C00'}
    )
    fig_status.update_traces(
        texttemplate='R$ %{value:,.2f}<br>%{percent}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    )
    st.plotly_chart(fig_status, use_container_width=True)
    st.divider()

# --- 4. DADOS DETALHADOS COM VALOR TOTAL ---
st.subheader("Dados Detalhados")
df_tabela = df.copy()
df_tabela[col_valor] = df_tabela[col_valor].apply(brl)
st.dataframe(df_tabela, use_container_width=True, hide_index=True)
st.caption(f"**Valor Total dos Dados Detalhados: {brl(df[col_valor].sum())}**")
