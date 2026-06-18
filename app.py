import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale

# Formato brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')

def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(
    page_title="Status Obras - São José dos Campos",
    page_icon="🏗️",
    layout="wide"
)

# --- RESET DOS FILTROS ---
def limpar_filtros():
    for key in st.session_state.keys():
        if key.startswith('filtro_'):
            del st.session_state[key]

@st.cache_data(ttl=60)
def carregar_dados():
    ONEDRIVE_URL = "https://onedrive.live.com/:x:/g/personal/0fdc4fa293f9651b/IQCqtIBXI6OyTLcUhPFe4n_uASlSBP-lAutuIL6REUySCxQ?rtime=cW9dEA3H3kg&redeem=aHR0cHM6Ly8xZHJ2Lm1zL3gvYy8wZmRjNGZhMjkzZjk2NTFiL0lRQ3F0SUJYSTZPeVRMY1VoUEZlNG5fdUFTbFNCUC1sQXV0dUlMNlJFVXlTQ3hRP2U9NktuV04x&download=1"
    df = pd.read_excel(ONEDRIVE_URL, engine='openpyxl')
    return df

df = carregar_dados()

# --- TÍTULO ---
st.title("🏗️ Status de Obras e Compras de Mobiliário")
st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# --- FILTROS + BOTÃO LIMPAR ---
st.subheader("🔍 Filtros")
col_f1, col_f2, col_f3, col_f4 = st.columns([2,2,2,1])

with col_f1:
    ubs_selecionadas = st.multiselect(
        "UBS",
        options=sorted(df['UBS'].unique()) if 'UBS' in df.columns else [],
        key='filtro_ubs'
    )

with col_f2:
    status_selecionado = st.multiselect(
        "Status",
        options=sorted(df['STATUS'].unique()) if 'STATUS' in df.columns else [],
        key='filtro_status'
    )

with col_f3:
    item_selecionado = st.multiselect(
        "Item",
        options=sorted(df['ITEM'].unique()) if 'ITEM' in df.columns else [],
        key='filtro_item'
    )

with col_f4:
    st.write("")
    st.write("")
    if st.button("🗑️ Limpar Filtros", use_container_width=True):
        limpar_filtros()
        st.rerun()

# --- APLICA OS FILTROS ---
df_filtrado = df.copy()

if ubs_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['UBS'].isin(ubs_selecionadas)]

if status_selecionado:
    df_filtrado = df_filtrado[df_filtrado['STATUS'].isin(status_selecionado)]

if item_selecionado:
    df_filtrado = df_filtrado[df_filtrado['ITEM'].isin(item_selecionado)]

# --- CÁLCULOS COM DADOS FILTRADOS ---
total_itens = len(df_filtrado)
valor_total = df_filtrado['VALOR_TOTAL'].sum() if 'VALOR_TOTAL' in df_filtrado.columns else 0

# --- MÉTRICAS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total de Itens", f"{total_itens:,}")
col2.metric("Valor Total", formatar_real(valor_total))
col3.metric("UBSs Atendidas", df_filtrado['UBS'].nunique() if 'UBS' in df_filtrado.columns else 0)

st.divider()

# --- GRÁFICOS INVERTIDOS: BARRAS ESQ, PIZZA DIR ---
col_esq, col_dir = st.columns(2)

with col_esq:
    if 'UBS' in df_filtrado.columns and 'VALOR_TOTAL' in df_filtrado.columns:
        df_ubs = df_filtrado.groupby('UBS')['VALOR_TOTAL'].sum().reset_index()
        fig_bar = px.bar(
            df_ubs,
            x='UBS',
            y='VALOR_TOTAL',
            title="Valor Total por UBS",
            text_auto='.2s'
        )
        fig_bar.update_traces(texttemplate='R$ %{y:,.0f}', textposition='outside')
        fig_bar.update_layout(yaxis_tickprefix='R$ ', yaxis_tickformat=',.0f')
        st.plotly_chart(fig_bar, use_container_width=True)

with col_dir:
    if 'STATUS' in df_filtrado.columns:
        df_status = df_filtrado['STATUS'].value_counts().reset_index()
        df_status.columns = ['STATUS', 'QUANTIDADE']

        fig_pie = px.pie(
            df_status,
            values='QUANTIDADE',
            names='STATUS',
            title=f"Distribuição por Status - Total: {total_itens} itens",
            hole=0.4
        )
        fig_pie.update_traces(
            textposition='inside',
            textinfo='percent',
            textfont_size=14
        )
        st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# --- TABELA ---
st.subheader(f"📋 Detalhamento - {total_itens} itens")
if 'VALOR_TOTAL' in df_filtrado.columns:
    df_display = df_filtrado.copy()
    df_display['VALOR_TOTAL'] = df_display['VALOR_TOTAL'].apply(formatar_real)
    st.dataframe(df_display, use_container_width=True)
else:
    st.dataframe(df_filtrado, use_container_width=True)
