import numpy as np
import pandas as pd
from pathlib import Path

# =========================
# Configuração dos caminhos
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / 'data' / 'raw'

if not RAW_DIR.exists():
    RAW_DIR.mkdir(parents=True)

# =========================
# Configurações iniciais
# =========================

np.random.seed(42)

num_produtos = 250
num_dias = 180

data_final = pd.Timestamp.today().normalize()
datas = pd.date_range(end=data_final, periods=num_dias)

jogos = ['Pokémon', 'Magic', 'Yu-Gi-Oh']
categorias = ['Carta Avulsa', 'Booster', 'Box', 'Deck']

raridades = [
    'Comum',
    'Incomum',
    'Rara',
    'Ultra Rara',
    'Secret Rare'
]

sets_por_jogo = {
    'Pokémon': [
        'Scarlet & Violet',
        'Paldea Evolved',
        'Obsidian Flames',
        'Paradox Rift',
        'Temporal Forces'
    ],
    'Magic': [
        'Bloomburrow',
        'Duskmourn',
        'Murders at Karlov Manor',
        'Outlaws of Thunder Junction',
        'The Lost Caverns of Ixalan'
    ],
    'Yu-Gi-Oh': [
        'Age of Overlord',
        'Phantom Nightmare',
        'Legacy of Destruction',
        'The Infinite Forbidden',
        'Rage of the Abyss'
    ]
}

fornecedores = [
    'Distribuidor A',
    'Distribuidor B',
    'Distribuidor C',
    'Distribuidor D'
]

# =========================
# 1. PRODUTOS
# =========================

produtos = []

for i in range(1, num_produtos + 1):

    jogo = np.random.choice(
        jogos,
        p=[0.45, 0.35, 0.20]
    )

    set_colecao = np.random.choice(
        sets_por_jogo[jogo]
    )

    categoria = np.random.choice(
        categorias,
        p=[0.45, 0.25, 0.15, 0.15]
    )

    raridade = np.random.choice(
        raridades,
        p=[0.30, 0.25, 0.20, 0.15, 0.10]
    )

    if categoria == 'Carta Avulsa':
        nome = f'Carta {i:03d} - {set_colecao}'
    elif categoria == 'Booster':
        nome = f'Booster {set_colecao} #{i:03d}'
    elif categoria == 'Box':
        nome = f'Box {set_colecao} #{i:03d}'
    else:
        nome = f'Deck {set_colecao} #{i:03d}'

    preco_base = {
        'Carta Avulsa': np.random.uniform(5, 150),
        'Booster': np.random.uniform(20, 45),
        'Box': np.random.uniform(180, 420),
        'Deck': np.random.uniform(60, 150)
    }[categoria]

    custo = preco_base * np.random.uniform(0.45, 0.70)
    popularidade = np.random.randint(20, 100)

    meta = np.random.choice(
        [0, 1],
        p=[0.70, 0.30]
    )

    data_lancamento = (
        data_final -
        pd.Timedelta(days=np.random.randint(0, 365))
    )

    fornecedor = np.random.choice(fornecedores)

    produtos.append([
        i,
        nome,
        categoria,
        jogo,
        set_colecao,
        raridade,
        round(preco_base, 2),
        round(custo, 2),
        data_lancamento,
        popularidade,
        meta,
        fornecedor
    ])

produtos_df = pd.DataFrame(
    produtos,
    columns=[
        'produto_id',
        'nome_produto',
        'categoria',
        'jogo',
        'set_colecao',
        'raridade',
        'preco_unitario',
        'custo_unitario',
        'data_lancamento',
        'popularidade_base',
        'meta_relevancia',
        'fornecedor'
    ]
)

# =========================
# 2. ESTOQUE
# =========================

estoque = []

for _, row in produtos_df.iterrows():

    categoria = row['categoria']

    if categoria == 'Carta Avulsa':
        estoque_inicial = np.random.randint(15, 120)
    elif categoria == 'Booster':
        estoque_inicial = np.random.randint(30, 180)
    elif categoria == 'Box':
        estoque_inicial = np.random.randint(8, 70)
    else:
        estoque_inicial = np.random.randint(10, 90)

    estoque_minimo = max(
        3,
        int(estoque_inicial * 0.25)
    )

    lead = np.random.randint(7, 31)

    lote = np.random.choice(
        [5, 10, 20, 30, 50]
    )

    estoque.append([
        row['produto_id'],
        estoque_inicial,
        estoque_inicial,
        estoque_minimo,
        lead,
        lote,
        data_final - pd.Timedelta(days=np.random.randint(5, 60)),
        'Normal'
    ])

estoque_df = pd.DataFrame(
    estoque,
    columns=[
        'produto_id',
        'estoque_inicial',
        'estoque_atual',
        'estoque_minimo',
        'lead_time_dias',
        'lote_reposicao',
        'ultima_reposicao',
        'status_estoque'
    ]
)

# =========================
# 3. VENDAS
# =========================

vendas = []
venda_id = 1

for data in datas:

    for _, produto in produtos_df.iterrows():

        categoria = produto['categoria']
        popularidade = produto['popularidade_base']
        meta = produto['meta_relevancia']

        dias = (data - produto['data_lancamento']).days

        fator_lancamento = 1
        evento = 0

        if 0 <= dias <= 21:
            fator_lancamento = 3
            evento = 1

        fator_meta = 2.5 if meta else 1
        fator_fim_semana = 1.25 if data.dayofweek in [5, 6] else 1

        base_demanda = {
            'Carta Avulsa': 0.20,
            'Booster': 0.28,
            'Box': 0.10,
            'Deck': 0.13
        }[categoria]

        demanda = (
            base_demanda *
            (popularidade / 30) *
            fator_lancamento *
            fator_meta *
            fator_fim_semana
        )

        qtd = np.random.poisson(demanda)

        if qtd > 0:

            promo = np.random.choice(
                [0, 1],
                p=[0.88, 0.12]
            )

            if promo:
                qtd += np.random.randint(1, 5)

            observacao = (
                'Pico'
                if fator_lancamento > 1 or meta or promo
                else 'Normal'
            )

            canal = np.random.choice(
                ['Site', 'Marketplace', 'Loja Física'],
                p=[0.60, 0.30, 0.10]
            )

            vendas.append([
                venda_id,
                data,
                produto['produto_id'],
                qtd,
                produto['preco_unitario'],
                canal,
                promo,
                evento,
                observacao
            ])

            venda_id += 1

vendas_df = pd.DataFrame(
    vendas,
    columns=[
        'venda_id',
        'data_venda',
        'produto_id',
        'quantidade_vendida',
        'preco_venda_unitario',
        'canal_venda',
        'foi_promocao',
        'evento_lancamento',
        'observacao_demanda'
    ]
)

# =========================
# 4. INSERIR IMPERFEIÇÕES REALISTAS
# =========================

produtos_df.loc[
    produtos_df.sample(frac=0.03, random_state=1).index,
    'fornecedor'
] = np.nan

produtos_df.loc[
    produtos_df.sample(frac=0.02, random_state=2).index,
    'raridade'
] = np.nan

idx_canal = vendas_df.sample(frac=0.03, random_state=3).index

valores_inconsistentes = [
    'site',
    'SITE',
    'marketplace',
    'Market Place',
    'loja fisica',
    'LOJA FÍSICA'
]

vendas_df.loc[
    idx_canal,
    'canal_venda'
] = np.random.choice(
    valores_inconsistentes,
    size=len(idx_canal)
)

duplicatas = vendas_df.sample(
    frac=0.015,
    random_state=4
)

vendas_df = pd.concat(
    [vendas_df, duplicatas],
    ignore_index=True
)

idx_outliers = vendas_df.sample(
    frac=0.005,
    random_state=5
).index

vendas_df.loc[
    idx_outliers,
    'quantidade_vendida'
] = vendas_df.loc[
    idx_outliers,
    'quantidade_vendida'
] * np.random.randint(
    8,
    20,
    size=len(idx_outliers)
)

idx_datas = vendas_df.sample(
    frac=0.005,
    random_state=6
).index

vendas_df.loc[
    idx_datas,
    'data_venda'
] = pd.to_datetime(
    vendas_df.loc[idx_datas, 'data_venda']
).dt.strftime('%d/%m/%Y')

# =========================
# 5. ATUALIZAR ESTOQUE
# =========================

vendas_para_estoque = vendas_df.copy()

vendas_para_estoque['quantidade_vendida'] = pd.to_numeric(
    vendas_para_estoque['quantidade_vendida'],
    errors='coerce'
)

vendas_produto = (
    vendas_para_estoque
    .groupby('produto_id')['quantidade_vendida']
    .sum()
    .reset_index()
)

vendas_produto.columns = [
    'produto_id',
    'total_vendido'
]

estoque_df = estoque_df.merge(
    vendas_produto,
    on='produto_id',
    how='left'
)

estoque_df['total_vendido'] = (
    estoque_df['total_vendido']
    .fillna(0)
)

# Simula comportamentos operacionais diferentes:
# alguns itens venderam sem reposição, outros foram parcialmente reabastecidos.
fator_consumo = np.random.uniform(
    0.45,
    0.85,
    len(estoque_df)
)

estoque_df['estoque_atual'] = (
    estoque_df['estoque_inicial'] -
    (estoque_df['total_vendido'] * fator_consumo)
)

estoque_df['estoque_atual'] = (
    estoque_df['estoque_atual']
    .clip(lower=0)
    .round()
    .astype(int)
)

# =========================
# 6. CLASSIFICAR STATUS DO ESTOQUE
# =========================

media_vendas = (
    vendas_para_estoque
    .groupby('produto_id')['quantidade_vendida']
    .mean()
    .reset_index()
)

estoque_df = estoque_df.merge(
    media_vendas,
    on='produto_id',
    how='left'
)

estoque_df['quantidade_vendida'] = (
    estoque_df['quantidade_vendida']
    .fillna(0)
)

condicoes = [
    estoque_df['estoque_atual'] <= estoque_df['estoque_minimo'],
    estoque_df['estoque_atual'] > estoque_df['quantidade_vendida'] * 12
]

valores = [
    'Crítico',
    'Excesso'
]

estoque_df['status_estoque'] = np.select(
    condicoes,
    valores,
    default='Normal'
)

estoque_df.drop(
    columns=[
        'total_vendido',
        'quantidade_vendida'
    ],
    inplace=True
)

# =========================
# 7. EXPORTAÇÃO
# =========================

produtos_df.to_csv(
    RAW_DIR / 'produtos_tcg.csv',
    index=False
)

estoque_df.to_csv(
    RAW_DIR / 'estoque_tcg.csv',
    index=False
)

vendas_df.to_csv(
    RAW_DIR / 'vendas_tcg.csv',
    index=False
)

# =========================
# 8. RESUMO NO TERMINAL
# =========================

print('\nArquivos gerados com sucesso:\n')
print(RAW_DIR / 'produtos_tcg.csv')
print(RAW_DIR / 'estoque_tcg.csv')
print(RAW_DIR / 'vendas_tcg.csv')

print('\nResumo dos produtos por jogo:\n')
print(produtos_df['jogo'].value_counts())

print('\nResumo do status de estoque:\n')
print(estoque_df['status_estoque'].value_counts())

print('\nResumo das vendas:\n')
print(vendas_df['quantidade_vendida'].describe())

print('\nValores ausentes em produtos:\n')
print(produtos_df.isna().sum())

print('\nDuplicatas em vendas:\n')
print(vendas_df.duplicated().sum())

print('\nCanais de venda:\n')
print(vendas_df['canal_venda'].value_counts())