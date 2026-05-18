from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


# ======================
# Configuração da página
# ======================

st.set_page_config(
    page_title='CardFlow',
    layout='wide'
)


# ======================
# Caminhos
# ======================

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / 'data' / 'raw'
MODEL_DIR = BASE_DIR / 'data' / 'dashboard'


# ======================
# Funções auxiliares
# ======================

def formatar_brl(valor):
    return f"R$ {valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor):
    return f"{valor:,}".replace(",", ".")


def parse_datas_mistas(serie):
    serie = serie.astype(str)

    datas_iso = pd.to_datetime(
        serie,
        format='%Y-%m-%d',
        errors='coerce'
    )

    datas_iso_completa = pd.to_datetime(
        serie,
        format='%Y-%m-%d %H:%M:%S',
        errors='coerce'
    )

    datas_br = pd.to_datetime(
        serie,
        format='%d/%m/%Y',
        errors='coerce'
    )

    return datas_iso.fillna(datas_iso_completa).fillna(datas_br)


@st.cache_data
def carregar_dados():
    vendas = pd.read_csv(
        RAW_DIR / 'vendas_tcg.csv'
    )

    produtos = pd.read_csv(
        RAW_DIR / 'produtos_tcg.csv'
    )

    estoque = pd.read_csv(
        RAW_DIR / 'estoque_tcg.csv'
    )

    # Tratamento mínimo dos dados brutos
    vendas = vendas.drop_duplicates()

    produtos['raridade'] = produtos['raridade'].fillna(
        'Desconhecida'
    )

    produtos['fornecedor'] = produtos['fornecedor'].fillna(
        'Fornecedor não informado'
    )

    mapa_canais = {
        'site': 'Site',
        'SITE': 'Site',
        'marketplace': 'Marketplace',
        'Market Place': 'Marketplace',
        'loja fisica': 'Loja Física',
        'LOJA FÍSICA': 'Loja Física'
    }

    vendas['canal_venda'] = vendas['canal_venda'].replace(
        mapa_canais
    )

    vendas['data_venda'] = parse_datas_mistas(
        vendas['data_venda']
    )

    produtos['data_lancamento'] = pd.to_datetime(
        produtos['data_lancamento'],
        errors='coerce'
    )

    estoque['ultima_reposicao'] = pd.to_datetime(
        estoque['ultima_reposicao'],
        errors='coerce'
    )

    base = vendas.merge(
        produtos,
        on='produto_id',
        how='left'
    )

    base = base.merge(
        estoque,
        on='produto_id',
        how='left'
    )

    base['dia_semana'] = base['data_venda'].dt.day_name()

    base['mes'] = base['data_venda'].dt.month

    base['faturamento'] = (
        base['quantidade_vendida']
        *
        base['preco_venda_unitario']
    )

    base['lucro_estimado'] = (
        base['quantidade_vendida']
        *
        (
            base['preco_venda_unitario']
            -
            base['custo_unitario']
        )
    )

    return base, produtos, estoque


@st.cache_resource
def carregar_modelo(nome_arquivo):
    caminho = MODEL_DIR / nome_arquivo

    if caminho.exists():
        return joblib.load(caminho)

    return None


def classificar_prioridade(row, limite_alerta):
    if row['status_estoque'] == 'Crítico' and row['prob_explosao'] >= limite_alerta:
        return 'Alta'

    if row['prob_explosao'] >= limite_alerta:
        return 'Média'

    if row['status_estoque'] == 'Crítico':
        return 'Média'

    return 'Baixa'


def calcular_reposicao(row, limite_alerta):
    if row['status_estoque'] == 'Excesso':
        return 0

    estoque_alvo = max(
        row['estoque_minimo'] * 2,
        row['lote_reposicao']
    )

    sugestao = max(
        0,
        estoque_alvo - row['estoque_atual']
    )

    if row['prob_explosao'] >= 95:
        sugestao = max(
            sugestao,
            row['lote_reposicao'] * 2
        )

    elif row['prob_explosao'] >= limite_alerta:
        sugestao = max(
            sugestao,
            row['lote_reposicao']
        )

    return int(round(sugestao))


# ======================
# Carregamento
# ======================

base, produtos, estoque = carregar_dados()

modelo_explosao = carregar_modelo(
    'modelo_explosao.pkl'
)

modelo_demanda = carregar_modelo(
    'modelo_demanda.pkl'
)


# ======================
# Filtros
# ======================

st.sidebar.title('Filtros')

jogo_selecionado = st.sidebar.selectbox(
    'Escolha um TCG',
    ['Todos'] + sorted(base['jogo'].dropna().unique())
)

status_selecionado = st.sidebar.multiselect(
    'Status de estoque',
    sorted(base['status_estoque'].dropna().unique()),
    default=sorted(base['status_estoque'].dropna().unique())
)

canal_selecionado = st.sidebar.multiselect(
    'Canal de venda',
    sorted(base['canal_venda'].dropna().unique()),
    default=sorted(base['canal_venda'].dropna().unique())
)

limite_alerta = st.sidebar.slider(
    'Limiar de alto risco (%)',
    min_value=50,
    max_value=99,
    value=90,
    step=1
)


base_filtrada = base.copy()

if jogo_selecionado != 'Todos':
    base_filtrada = base_filtrada[
        base_filtrada['jogo'] == jogo_selecionado
    ]

base_filtrada = base_filtrada[
    base_filtrada['status_estoque'].isin(status_selecionado)
]

base_filtrada = base_filtrada[
    base_filtrada['canal_venda'].isin(canal_selecionado)
]


# ======================
# Título
# ======================

st.title('🎴 CardFlow — TCG Analytics')

st.write(
    'Dashboard para análise de vendas, estoque, risco operacional e alertas preditivos em e-commerces de TCG.'
)


# ======================
# KPIs principais
# ======================

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        'Faturamento',
        formatar_brl(base_filtrada['faturamento'].sum())
    )

with col2:
    st.metric(
        'Lucro estimado',
        formatar_brl(base_filtrada['lucro_estimado'].sum())
    )

with col3:
    st.metric(
        'Vendas',
        formatar_numero(base_filtrada.shape[0])
    )

with col4:
    st.metric(
        'Produtos críticos',
        base_filtrada[
            base_filtrada['status_estoque'] == 'Crítico'
        ]['produto_id'].nunique()
    )

with col5:
    st.metric(
        'Produtos analisados',
        base_filtrada['produto_id'].nunique()
    )

st.divider()


# ======================
# Alertas preditivos
# ======================

st.subheader('🚨 Alertas Preditivos de Explosão de Demanda')

features = [
    'preco_venda_unitario',
    'canal_venda',
    'foi_promocao',
    'evento_lancamento',
    'observacao_demanda',
    'dia_semana',
    'mes',
    'categoria',
    'jogo',
    'set_colecao',
    'raridade',
    'preco_unitario',
    'custo_unitario',
    'popularidade_base',
    'meta_relevancia',
    'fornecedor',
    'estoque_inicial',
    'estoque_atual',
    'estoque_minimo',
    'lead_time_dias',
    'lote_reposicao'
]

alertas = pd.DataFrame()

if modelo_explosao is None:
    st.warning(
        'Modelo de explosão não encontrado. Verifique se o arquivo modelo_explosao.pkl está em data/dashboard/.'
    )

else:
    base_pred = base_filtrada.dropna(
        subset=features
    ).copy()

    if base_pred.empty:
        st.info(
            'Não há dados suficientes para gerar alertas com os filtros atuais.'
        )

    else:
        base_pred['prob_explosao'] = (
            modelo_explosao
            .predict_proba(
                base_pred[features]
            )[:, 1]
        )

        if modelo_demanda is not None:
            base_pred['demanda_prevista'] = (
                modelo_demanda
                .predict(
                    base_pred[features]
                )
            )

            base_pred['demanda_prevista'] = (
                base_pred['demanda_prevista']
                .clip(lower=0)
            )

        else:
            base_pred['demanda_prevista'] = np.nan

        alertas = (
            base_pred
            .groupby(
                [
                    'produto_id',
                    'nome_produto',
                    'jogo',
                    'categoria',
                    'estoque_atual',
                    'estoque_minimo',
                    'lote_reposicao',
                    'lead_time_dias',
                    'status_estoque'
                ]
            )
            .agg(
                prob_explosao=('prob_explosao', 'max'),
                demanda_prevista=('demanda_prevista', 'mean'),
                unidades_vendidas=('quantidade_vendida', 'sum'),
                faturamento=('faturamento', 'sum')
            )
            .reset_index()
        )

        alertas['prob_explosao'] = (
            alertas['prob_explosao'] * 100
        ).round(2)

        alertas['demanda_prevista'] = (
            alertas['demanda_prevista']
            .round(2)
        )

        alertas['prioridade'] = alertas.apply(
            lambda row: classificar_prioridade(
                row,
                limite_alerta
            ),
            axis=1
        )

        alertas['reposicao_sugerida'] = alertas.apply(
            lambda row: calcular_reposicao(
                row,
                limite_alerta
            ),
            axis=1
        )

        mapa_prioridade = {
            'Alta': 1,
            'Média': 2,
            'Baixa': 3
        }

        alertas['prioridade_ordem'] = (
            alertas['prioridade']
            .map(mapa_prioridade)
        )

        alertas = alertas.sort_values(
            [
                'prioridade_ordem',
                'prob_explosao',
                'reposicao_sugerida'
            ],
            ascending=[
                True,
                False,
                False
            ]
        )

        produtos_alto_risco = (
            alertas['prob_explosao'] >= limite_alerta
        ).sum()

        produtos_criticos_previstos = (
            (
                alertas['status_estoque'] == 'Crítico'
            )
            &
            (
                alertas['prob_explosao'] >= limite_alerta
            )
        ).sum()

        maior_probabilidade = alertas['prob_explosao'].max()

        a1, a2, a3 = st.columns(3)

        with a1:
            st.metric(
                'Produtos em alto risco',
                produtos_alto_risco
            )

        with a2:
            st.metric(
                'Maior probabilidade',
                f'{maior_probabilidade:.2f}%'
            )

        with a3:
            st.metric(
                'Produtos críticos previstos',
                produtos_criticos_previstos
            )

        st.caption(
            f'Produtos em alto risco são aqueles com probabilidade prevista de explosão de demanda igual ou superior a {limite_alerta}%.'
        )

        with st.expander('Ver Top 10 Alertas'):
            st.dataframe(
                alertas
                .drop(columns='prioridade_ordem')
                .head(10),
                use_container_width=True
            )

        st.caption(
            'Produtos com alta probabilidade prevista podem exigir reposição antecipada.'
        )

st.divider()


# ======================
# Recomendações de reposição
# ======================

st.subheader('📦 Recomendações de Reposição')

if alertas.empty:
    st.info(
        'Nenhuma recomendação disponível para os filtros atuais.'
    )

else:
    recomendacoes = (
        alertas[
            (
                alertas['prioridade'].isin(['Alta', 'Média'])
            )
            &
            (
                alertas['reposicao_sugerida'] > 0
            )
        ]
        .sort_values(
            [
                'prioridade_ordem',
                'prob_explosao',
                'reposicao_sugerida'
            ],
            ascending=[
                True,
                False,
                False
            ]
        )
        .head(15)
    )

    if recomendacoes.empty:
        st.success(
            'Nenhuma reposição urgente identificada com os filtros atuais.'
        )

    else:
        st.dataframe(
            recomendacoes[
                [
                    'produto_id',
                    'nome_produto',
                    'jogo',
                    'categoria',
                    'estoque_atual',
                    'estoque_minimo',
                    'status_estoque',
                    'prob_explosao',
                    'demanda_prevista',
                    'prioridade',
                    'reposicao_sugerida'
                ]
            ],
            use_container_width=True
        )

        st.caption(
            'A reposição sugerida considera estoque atual, estoque mínimo, lote de compra e risco previsto de explosão de demanda. A decisão final ainda deve considerar orçamento, fornecedor e estratégia comercial.'
        )

st.divider()


# ======================
# Linha 1 de gráficos
# ======================

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader('Distribuição de Produtos por TCG')

    produtos_tcg = (
        base_filtrada
        .drop_duplicates('produto_id')
        .groupby('jogo')
        .size()
        .sort_values()
    )

    if produtos_tcg.empty:
        st.info('Sem dados para exibir.')

    else:
        fig, ax = plt.subplots(
            figsize=[7, 4]
        )

        produtos_tcg.plot(
            kind='barh',
            ax=ax
        )

        ax.set_title('Produtos por TCG')
        ax.set_xlabel('Quantidade de Produtos')
        ax.set_ylabel('TCG')

        st.pyplot(fig)

with col_g2:
    st.subheader('Faturamento Diário')

    faturamento_tempo = (
        base_filtrada
        .groupby('data_venda')['faturamento']
        .sum()
        .sort_index()
    )

    if faturamento_tempo.empty:
        st.info('Sem dados para exibir.')

    else:
        fig, ax = plt.subplots(
            figsize=[7, 4]
        )

        faturamento_tempo.plot(
            ax=ax
        )

        ax.set_title('Faturamento Diário ao Longo do Tempo')
        ax.set_xlabel('Data')
        ax.set_ylabel('Faturamento (R$)')

        st.pyplot(fig)

st.divider()


# ======================
# Linha 2 de gráficos
# ======================

col_g3, col_g4 = st.columns(2)

with col_g3:
    st.subheader('Top Produtos Críticos')

    criticos = base_filtrada[
        base_filtrada['status_estoque'] == 'Crítico'
    ]

    top_criticos = (
        criticos['nome_produto']
        .value_counts()
        .head(10)
    )

    if top_criticos.empty:
        st.info('Sem produtos críticos para os filtros atuais.')

    else:
        fig, ax = plt.subplots(
            figsize=[7, 5]
        )

        top_criticos.plot(
            kind='barh',
            ax=ax
        )

        ax.set_title('Produtos com Maior Frequência em Status Crítico')
        ax.set_xlabel('Quantidade de Registros')
        ax.set_ylabel('Produto')
        ax.invert_yaxis()

        st.pyplot(fig)

with col_g4:
    st.subheader('Distribuição por Canal de Venda')

    canal_counts = (
        base_filtrada['canal_venda']
        .value_counts()
    )

    if canal_counts.empty:
        st.info('Sem dados para exibir.')

    else:
        fig, ax = plt.subplots(
            figsize=[7, 4]
        )

        canal_counts.plot(
            kind='bar',
            ax=ax
        )

        ax.set_title('Vendas por Canal')
        ax.set_xlabel('Canal')
        ax.set_ylabel('Quantidade de Vendas')
        ax.tick_params(
            axis='x',
            rotation=0
        )

        st.pyplot(fig)

st.divider()


# ======================
# Linha 3 de gráficos
# ======================

col_g5, col_g6 = st.columns(2)

with col_g5:
    st.subheader('Status de Estoque')

    status_counts = (
        base_filtrada
        .drop_duplicates('produto_id')
        ['status_estoque']
        .value_counts()
    )

    if status_counts.empty:
        st.info('Sem dados para exibir.')

    else:
        fig, ax = plt.subplots(
            figsize=[7, 4]
        )

        status_counts.plot(
            kind='bar',
            ax=ax
        )

        ax.set_title('Produtos por Status de Estoque')
        ax.set_xlabel('Status')
        ax.set_ylabel('Quantidade de Produtos')
        ax.tick_params(
            axis='x',
            rotation=0
        )

        st.pyplot(fig)

with col_g6:
    st.subheader('Top Produtos Mais Lucrativos')

    top_lucro = (
        base_filtrada
        .groupby('nome_produto')['lucro_estimado']
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    if top_lucro.empty:
        st.info('Sem dados para exibir.')

    else:
        fig, ax = plt.subplots(
            figsize=[7, 5]
        )

        top_lucro.plot(
            kind='barh',
            ax=ax
        )

        ax.set_title('Produtos com Maior Lucro Estimado')
        ax.set_xlabel('Lucro Estimado (R$)')
        ax.set_ylabel('Produto')
        ax.invert_yaxis()

        st.pyplot(fig)

st.divider()


# ======================
# Dados
# ======================

st.subheader('Amostra dos Dados')

colunas_tabela = [
    'data_venda',
    'produto_id',
    'nome_produto',
    'jogo',
    'categoria',
    'quantidade_vendida',
    'preco_venda_unitario',
    'canal_venda',
    'estoque_atual',
    'status_estoque',
    'faturamento',
    'lucro_estimado'
]

st.dataframe(
    base_filtrada[colunas_tabela].head(100),
    use_container_width=True
)