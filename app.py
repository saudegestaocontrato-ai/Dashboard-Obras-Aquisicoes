import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import time

st.set_page_config(page_title="Dashboard Obras", layout="wide")

ARQUIVO = "Status de Obras e Compras de Mobiliário.xlsx"
COLUNA_VALOR_TOTAL = 'Valor Total (Estimado)'
COLUNA_QTDE = 'QTDE'
PARAMETRO_CER = 'CER III'

MAPA_STATUS = {
    1: '1. Atenção - Em cotação',
    2: '2. Em andamento - Em compra',
    3: '3. Finalizada - Entregue',
    4: '4. Não Necessita'
}

CORES_STATUS = {
    '1. Atenção - Em cotação': '#E74C3C',
    '2. Em andamento - Em compra': '#F4D03F',
    '3. Finalizada - Entregue': '#82C45A',
    '4. Não Necessita': '#D5D8DC',
    'Não informado': '#AEB6BF',
}

CORES_PRAZO = {
    'Finalizado': '#95A5A6',
    'Super Alerta': '#E74C3C',
    'Alerta': '#F4D03F',
    'No Prazo': '#82C45A'
}

VERSAO_DADOS = 11

def brl(valor):
    try:
        num = float(valor)
        if pd.isna(num) or num == 0:
            return "R$ 0,00"
        return f"R$ {num:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return "R$ 0,00"

def limpar_valor_br(x):
    if pd.isna(x):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    x = str(x).strip()
    if x == '' or x.lower() == 'nan':
        return 0.0
    x = x.replace('R$', '').replace(' ', '')
    if ',' in x:
        x = x.replace('.', '').replace(',', '.')
    try:
        return float(x)
    except:
        return 0.0

@st.cache_data
def carregar_dados(v=VERSAO_DADOS):
    import warnings
    warnings.filterwarnings('ignore')

    xls = pd.ExcelFile(ARQUIVO)
    todas_abas = []

    for aba in xls.sheet_names:
        if 'RESUMO' in aba.upper() or aba.strip() == 'Planilha1':
            continue

        df_raw = pd.read_excel(ARQUIVO, sheet_name=aba, header=None)

        linha_cabecalho = None
        for i, row in df_raw.iterrows():
            if 'QTDE' in row.values and 'ITENS' in row.values:
                linha_cabecalho = i
                break
        if linha_cabecalho is None:
            continue

        df = pd.read_excel(ARQUIVO, sheet_name=aba, header=linha_cabecalho)
        df.columns = df.columns.astype(str).str.replace('\n', ' ').str.strip()
        df.dropna(axis=1, how='all', inplace=True)

        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            idxs = cols[cols == dup].index.tolist()
            for k, idx in enumerate(idxs):
                if k!= 0:
                    cols[idx] = f"{dup}_{k}"
        df.columns = cols

        if COLUNA_QTDE in df.columns:
            df[COLUNA_QTDE] = pd.to_numeric(df[COLUNA_QTDE], errors='coerce').fillna(0)
            df = df[df[COLUNA_QTDE] > 0]
        else:
            continue

        if 'ITENS' in df.columns:
            df['ITENS'] = df['ITENS'].astype(str).str.strip()
            df = df[df['ITENS']!= '']
            df = df[df['ITENS'].str.upper()!= 'TOTAL']
            df = df[~df['ITENS'].str.upper().str.contains('SUBTOTAL')]

        if df.empty:
            continue

        df['UBS'] = aba
        todas_abas.append(df)

    if not todas_abas:
        return pd.DataFrame()

    df_final = pd.concat(todas_abas, ignore_index=True)

    for col in ['Valor Unitário (Estimado)', COLUNA_VALOR_TOTAL]:
        if col in df_final.columns:
            df_final[col] = df_final[col].apply(limpar_valor_br)

    if 'ENTREGA' in df_final.columns:
        df_final['ENTREGA_NUM'] = pd.to_numeric(df_final['ENTREGA'], errors='coerce')
        df_final['STATUS ENTREGA'] = df_final['ENTREGA_NUM'].map(MAPA_STATUS).fillna('Não informado')

    return df_final

df_original = carregar_dados()

if df_original.empty:
    st.error("Nenhum dado encontrado no arquivo.")
    st.stop()

df = df_original.copy()

st.sidebar.header("Filtros")

if st.sidebar.button("🗑️ Limpar Todos os Filtros", use_container_width=True):
    for key in ['ubs_filter', 'item_filter', 'status_filter', 'fonte_filter']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

ubs_selecionada = st.sidebar.multiselect(
    "Filtrar UBS",
    options=sorted(df['UBS'].unique()),
    key='ubs_filter'
)

if ubs_selecionada:
    df = df[df['UBS'].isin(ubs_selecionada)]

st.title("📊 Dashboard - Status Obras e Compras de Mobiliário")

if ubs_selecionada:
    ubs_texto = ", ".join([f"**{ubs}**" for ubs in ubs_selecionada])
    st.markdown(f"**UBS filtrada:** {ubs_texto}")
    if PARAMETRO_CER in ubs_selecionada:
        st.info(f"📍 Visualizando dados específicos do **{PARAMETRO_CER}**")
else:
    st.markdown("**Visão geral:** **Todas as UBS**")

if 'ITENS' in df.columns:
    lista_itens = sorted(df['ITENS'].dropna().unique())
    item_selecionado = st.sidebar.multiselect("Filtrar por Item", options=lista_itens, key='item_filter')
    if item_selecionado:
        df = df[df['ITENS'].isin(item_selecionado)]

if 'STATUS ENTREGA' in df.columns and df['STATUS ENTREGA'].notna().any():
    opcoes_status = sorted(df['STATUS ENTREGA'].dropna().unique())
    sel_status = st.sidebar.multiselect("Filtrar STATUS ENTREGA", options=opcoes_status, key='status_filter')
    if sel_status:
        df = df[df['STATUS ENTREGA'].isin(sel_status)]

if 'FONTE DE COMPRA' in df.columns and df['FONTE DE COMPRA'].notna().any():
    opcoes_fonte = sorted(df['FONTE DE COMPRA'].dropna().astype(str).unique())
    sel_fonte = st.sidebar.multiselect("Filtrar FONTE DE COMPRA", options=opcoes_fonte, key='fonte_filter')
    if sel_fonte:
        df = df[df['FONTE DE COMPRA'].isin(sel_fonte)]

qtde_total = df[COLUNA_QTDE].sum() if COLUNA_QTDE in df.columns else 0
valor_total = df[COLUNA_VALOR_TOTAL].sum() if COLUNA_VALOR_TOTAL in df.columns else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de UBS", df['UBS'].nunique())
col2.metric("Total de Itens", len(df))
col3.metric("Quantidade Total", f"{int(qtde_total):,}".replace(",", "."))
col4.metric("Valor Total Estimado", brl(valor_total))

st.divider()

col_g1, col_g2 = st.columns(2)

with col_g1: # Barras na esquerda - GRÁFICO CORRIGIDO
    if 'FONTE DE COMPRA' in df.columns and COLUNA_VALOR_TOTAL in df.columns:
        df_fonte = df[df['FONTE DE COMPRA'].notna() & (df['FONTE DE COMPRA'].astype(str).str.strip()!= '')]
        if not df_fonte.empty:
            soma_valor = (
                df_fonte.groupby('FONTE DE COMPRA')[COLUNA_VALOR_TOTAL]
   .sum()
   .reset_index()
   .sort_values(COLUNA_VALOR_TOTAL, ascending=False)
            )
            
            # Força formatação BR nos textos das barras
            soma_valor['texto_br'] = soma_valor[COLUNA_VALOR_TOTAL].apply(brl)
            
            fig2 = px.bar(
                soma_valor,
                x='FONTE DE COMPRA',
                y=COLUNA_VALOR_TOTAL,
                title="Valor Total por Fonte de Compra",
                text='texto_br',
                color='FONTE DE COMPRA',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig2.update_traces(
                textposition='outside'
            )
            fig2.update_layout(
                showlegend=False,
                yaxis_title="Valor (R$)",
                yaxis_tickprefix="R$ ",
                yaxis_tickformat=",.2f".replace(",", "v").replace(".", ",").replace("v", ".")
            )
            st.plotly_chart(fig2, use_container_width=True)

with col_g2: # Pizza na direita - TÍTULO ALTERADO
    if 'STATUS ENTREGA' in df.columns:
        contagem = df['STATUS ENTREGA'].value_counts().reset_index()
        contagem.columns = ['Status', 'Qtd Itens']

        fig = px.pie(
            contagem, names='Status', values='Qtd Itens',
            title=f"Distribuição por Status Total de Itens - {PARAMETRO_CER if PARAMETRO_CER in df['UBS'].unique() else 'Geral'}",
            hole=0.4,
            color='Status',
            color_discrete_map=CORES_STATUS
        )
        fig.update_traces(textposition='inside', textinfo='percent')
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("📈 Indicadores de Gestão de Aquisições")

col_ind1, col_ind2, col_ind3 = st.columns(3)

with col_ind1:
    st.markdown("**% Conclusão por UBS**")
    if 'STATUS ENTREGA' in df.columns and 'UBS' in df.columns:
        conclusao_ubs = df.groupby('UBS')['STATUS ENTREGA'].apply(
            lambda x: (x == '3. Finalizada - Entregue').sum() / len(x) * 100 if len(x) > 0 else 0
        ).reset_index(name='% Concluído')

        for _, row in conclusao_ubs.iterrows():
            destaque = "🎯 " if row['UBS'] == PARAMETRO_CER else ""
            st.text(f"{destaque}{row['UBS']}")
            st.progress(int(row['% Concluído']) / 100, text=f"{row['% Concluído']:.1f}%")
    else:
        st.info("Coluna STATUS ENTREGA não encontrada")

with col_ind2:
    st.markdown("**Orçamento: Entregue vs Em Aberto**")
    if 'STATUS ENTREGA' in df.columns and COLUNA_VALOR_TOTAL in df.columns:
        valor_entregue = df[df['STATUS ENTREGA'] == '3. Finalizada - Entregue'][COLUNA_VALOR_TOTAL].sum()
        valor_aberto = df[df['STATUS ENTREGA']!= '3. Finalizada - Entregue'][COLUNA_VALOR_TOTAL].sum()
        total = valor_entregue + valor_aberto

        if total > 0:
            st.metric("Entregue", brl(valor_entregue), f"{valor_entregue/total*100:.1f}%")
            st.metric("Em Aberto", brl(valor_aberto), f"{valor_aberto/total*100:.1f}%")
            st.progress(valor_entregue / total, text="Concretizado")
    else:
        st.info("Dados insuficientes")

with col_ind3:
    st.markdown("**🚨 Alertas: Itens em Atenção**")
    if 'STATUS ENTREGA' in df.columns and 'UBS' in df.columns:
        atencao_ubs = df[df['STATUS ENTREGA'] == '1. Atenção - Em cotação'].groupby('UBS').size().reset_index(name='Qtd Atenção')
        atencao_ubs = atencao_ubs.sort_values('Qtd Atenção', ascending=False).head(3)

        if not atencao_ubs.empty:
            for _, row in atencao_ubs.iterrows():
                destaque = "🎯 " if row['UBS'] == PARAMETRO_CER else ""
                st.error(f"{destaque}**{row['UBS']}**: {row['Qtd Atenção']} itens em Atenção")
        else:
            st.success("Nenhum item em Atenção")
    else:
        st.info("Coluna STATUS ENTREGA não encontrada")

st.divider()

st.subheader("💰 Top 5 Itens Mais Caros Ainda Pendentes")
if 'STATUS ENTREGA' in df.columns and COLUNA_VALOR_TOTAL in df.columns and 'ITENS' in df.columns:
    pendentes = df[df['STATUS ENTREGA']!= '3. Finalizada - Entregue'].copy()
    if not pendentes.empty:
        cols_ranking = ['UBS', 'ITENS', COLUNA_QTDE, COLUNA_VALOR_TOTAL, 'STATUS ENTREGA']
        if 'Valor Unitário (Estimado)' in pendentes.columns:
            cols_ranking.insert(3, 'Valor Unitário (Estimado)')
        
        ranking = pendentes.nlargest(5, COLUNA_VALOR_TOTAL)[cols_ranking]
        
        config_ranking = {
            COLUNA_VALOR_TOTAL: st.column_config.NumberColumn("Valor Total", format="R$ %.2f"),
            COLUNA_QTDE: st.column_config.NumberColumn("Qtde", format="%d"),
            'ITENS': st.column_config.TextColumn("Item", width="large")
        }
        if 'Valor Unitário (Estimado)' in ranking.columns:
            config_ranking['Valor Unitário (Estimado)'] = st.column_config.NumberColumn("Valor Unit.", format="R$ %.2f")
            
        st.dataframe(ranking, use_container_width=True, hide_index=True, column_config=config_ranking)
    else:
        st.success("Todos os itens foram finalizados!")
else:
    st.info("Dados insuficientes para ranking")

st.divider()

st.subheader("📊 Comparativo de Status por UBS")

if 'UBS' in df.columns and 'STATUS ENTREGA' in df.columns:
    status_ubs = df.groupby(['UBS', 'STATUS ENTREGA']).size().reset_index(name='Quantidade')

    fig_status = px.bar(
        status_ubs,
        x='UBS',
        y='Quantidade',
        color='STATUS ENTREGA',
        title="Quantidade de Itens por UBS e Status",
        color_discrete_map=CORES_STATUS,
        barmode='group',
        text='Quantidade'
    )
    fig_status.update_traces(textposition='outside')
    fig_status.update_layout(xaxis_tickangle=-45, height=450)
    st.plotly_chart(fig_status, use_container_width=True)

    pivot_status = status_ubs.pivot(index='UBS', columns='STATUS ENTREGA', values='Quantidade').fillna(0)

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_status.values,
        x=pivot_status.columns,
        y=pivot_status.index,
        colorscale='RdYlGn',
        text=pivot_status.values,
        texttemplate="%{text}",
        textfont={"size":12},
        hovertemplate='UBS: %{y}<br>Status: %{x}<br>Qtd: %{z}<extra></extra>'
    ))
    fig_heatmap.update_layout(
        title="Heatmap: Concentração de Status por UBS",
        xaxis_title="Status de Entrega",
        yaxis_title="UBS",
        height=300
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
else:
    st.info("Dados insuficientes para comparativo")

st.divider()

st.subheader("🚦 Controle de Prazos - Semáforo por UBS")

@st.cache_data
def buscar_dias_vencimento_por_ubs():
    try:
        xls = pd.ExcelFile(ARQUIVO)
        dados_prazos = []

        for aba in xls.sheet_names:
            if 'RESUMO' in aba.upper() or aba.strip() == 'Planilha1':
                continue

            df_raw = pd.read_excel(ARQUIVO, sheet_name=aba, header=None)

            try:
                dias_ubs = df_raw.iloc[2, 14]
                dias_ubs = pd.to_numeric(dias_ubs, errors='coerce')
            except:
                dias_ubs = None

            if pd.notna(dias_ubs):
                df_dados = df_original[df_original['UBS'] == aba]
                qtd_itens = len(df_dados)

                dados_prazos.append({
                    'UBS': aba,
                    'DIAS_VENCIMENTO': int(dias_ubs),
                    'QTD_ITENS': qtd_itens
                })

        df_venc = pd.DataFrame(dados_prazos)

        if not df_venc.empty:
            df_venc['STATUS_PRAZO'] = df_venc['DIAS_VENCIMENTO'].apply(
                lambda x: 'Finalizado' if x == 0 else (
                    'Super Alerta' if x <= 30 else (
                        'Alerta' if x <= 60 else 'No Prazo'
                    )
                )
            )
        return df_venc
    except Exception as e:
        st.error(f"Erro ao buscar prazos: {e}")
        return pd.DataFrame()

df_prazos_ubs = buscar_dias_vencimento_por_ubs()

if not df_prazos_ubs.empty:
    if ubs_selecionada:
        df_prazos_ubs = df_prazos_ubs[df_prazos_ubs['UBS'].isin(ubs_selecionada)]

    finalizado = df_prazos_ubs[df_prazos_ubs['STATUS_PRAZO'] == 'Finalizado']
    super_alerta = df_prazos_ubs[df_prazos_ubs['STATUS_PRAZO'] == 'Super Alerta']
    alerta = df_prazos_ubs[df_prazos_ubs['STATUS_PRAZO'] == 'Alerta']
    no_prazo = df_prazos_ubs[df_prazos_ubs['STATUS_PRAZO'] == 'No Prazo']

    col_p1, col_p2, col_p3, col_p4 = st.columns(4)

    with col_p1:
        st.markdown(f"<div style='padding:10px; background-color:{CORES_PRAZO['Finalizado']}; border-radius:5px; text-align:center;'>"
                    f"<h3 style='color:white; margin:0;'>⚫ {len(finalizado)}</h3>"
                    f"<p style='color:white; margin:0;'>Finalizado<br>0 dias</p></div>",
                    unsafe_allow_html=True)

    with col_p2:
        st.markdown(f"<div style='padding:10px; background-color:{CORES_PRAZO['Super Alerta']}; border-radius:5px; text-align:center;'>"
                    f"<h3 style='color:white; margin:0;'>🔴 {len(super_alerta)}</h3>"
                    f"<p style='color:white; margin:0;'>Super Alerta<br>1 a 30 dias</p></div>",
                    unsafe_allow_html=True)

    with col_p3:
        st.markdown(f"<div style='padding:10px; background-color:{CORES_PRAZO['Alerta']}; border-radius:5px; text-align:center;'>"
                    f"<h3 style='color:black; margin:0;'>🟡 {len(alerta)}</h3>"
                    f"<p style='color:black; margin:0;'>Alerta<br>31 a 60 dias</p></div>",
                    unsafe_allow_html=True)

    with col_p4:
        st.markdown(f"<div style='padding:10px; background-color:{CORES_PRAZO['No Prazo']}; border-radius:5px; text-align:center;'>"
                    f"<h3 style='color:white; margin:0;'>🟢 {len(no_prazo)}</h3>"
                    f"<p style='color:white; margin:0;'>No Prazo<br>> 60 dias</p></div>",
                    unsafe_allow_html=True)

    st.markdown("### Detalhes por UBS")

    if not super_alerta.empty:
        st.error("**🔴 SUPER ALERTA - UBS com prazo ≤ 30 dias:**")
        st.dataframe(super_alerta[['UBS', 'DIAS_VENCIMENTO', 'QTD_ITENS']], hide_index=True,
                     column_config={
                         'DIAS_VENCIMENTO': st.column_config.NumberColumn("Dias Restantes", format="%d dias"),
                         'QTD_ITENS': st.column_config.NumberColumn("Qtd Itens", format="%d")
                     })

    if not alerta.empty:
        st.warning("**🟡 ALERTA - UBS com prazo 31 a 60 dias:**")
        st.dataframe(alerta[['UBS', 'DIAS_VENCIMENTO', 'QTD_ITENS']], hide_index=True,
                     column_config={
                         'DIAS_VENCIMENTO': st.column_config.NumberColumn("Dias Restantes", format="%d dias"),
                         'QTD_ITENS': st.column_config.NumberColumn("Qtd Itens", format="%d")
                     })

    if not no_prazo.empty:
        st.success("**🟢 NO PRAZO - UBS com prazo > 60 dias:**")
        st.dataframe(no_prazo[['UBS', 'DIAS_VENCIMENTO', 'QTD_ITENS']], hide_index=True,
                     column_config={
                         'DIAS_VENCIMENTO': st.column_config.NumberColumn("Dias Restantes", format="%d dias"),
                         'QTD_ITENS': st.column_config.NumberColumn("Qtd Itens", format="%d")
                     })

    if not finalizado.empty:
        with st.expander(f"⚫ Ver {len(finalizado)} UBS finalizadas"):
            st.dataframe(finalizado[['UBS', 'DIAS_VENCIMENTO', 'QTD_ITENS']], hide_index=True,
                         column_config={
                             'DIAS_VENCIMENTO': st.column_config.NumberColumn("Dias Restantes", format="%d dias"),
                             'QTD_ITENS': st.column_config.NumberColumn("Qtd Itens", format="%d")
                         })
else:
    st.info("Célula O3 com dias de vencimento não encontrada nas abas do Excel.")

st.divider()
st.subheader(
    f"Dados Detalhados — {len(df)} itens | "
    f"{int(qtde_total):,} unidades | "
    f"Valor: {brl(valor_total)}"
)

busca = st.text_input("🔍 Buscar item", placeholder="Digite para filtrar a tabela...")
df_exibir = df.copy()
if busca:
    mask = df_exibir.astype(str).apply(
        lambda col: col.str.contains(busca, case=False, na=False)
    ).any(axis=1)
    df_exibir = df_exibir

colunas_prioridade = ['UBS', 'ITENS', COLUNA_QTDE, 'Valor Unitário (Estimado)',
                      COLUNA_VALOR_TOTAL, 'FONTE DE COMPRA', 'STATUS ENTREGA', 'COMPLEMENTO']
colunas_exibir = [c for c in colunas_prioridade if c in df_exibir.columns]
outras = [c for c in df_exibir.columns if c not in colunas_exibir and c not in ('ENTREGA', 'ENTREGA_NUM')]
colunas_exibir += outras

# Formata as colunas monetárias pra R$ 18.214,00
if COLUNA_VALOR_TOTAL in df_exibir.columns:
    df_exibir[COLUNA_VALOR_TOTAL] = df_exibir[COLUNA_VALOR_TOTAL].apply(brl)
if 'Valor Unitário (Estimado)' in df_exibir.columns:
    df_exibir['Valor Unitário (Estimado)'] = df_exibir['Valor Unitário (Estimado)'].apply(brl)

config_colunas = {
    'Valor Unitário (Estimado)': st.column_config.TextColumn("Valor Unit."),
    COLUNA_VALOR_TOTAL: st.column_config.TextColumn("Valor Total"),
    COLUNA_QTDE: st.column_config.NumberColumn("Qtde", format="%d"),
    'ITENS': st.column_config.TextColumn("Descrição do Item", width="large"),
    'UBS': st.column_config.TextColumn("UBS", width="medium"),
    'STATUS ENTREGA': st.column_config.TextColumn("Status Entrega", width="medium"),
    'FONTE DE COMPRA': st.column_config.TextColumn("Fonte de Compra", width="medium"),
    'COMPLEMENTO': st.column_config.TextColumn("Complemento", width="large"),
}

st.dataframe(
    df_exibir[colunas_exibir],
    use_container_width=True,
    height=600,
    column_config=config_colunas,
    hide_index=True
)

def to_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

st.download_button(
    "📥 Baixar Excel Filtrado",
    data=to_excel(df_exibir[colunas_exibir]),
    file_name="dados_obras_filtrado.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()
st.caption(f"🔄 Dashboard atualiza automaticamente a cada 3 minutos | v3.0 - Título Gráfico Pizza Atualizado")

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 180:
    st.session_state.last_refresh = time.time()
    st.rerun()
