import streamlit as st
import requests
import pandas as pd
import io
import os

# Importação robusta do PySUS
try:
    from pysus.api._impl.databases import sim, sih, sia, cnes
except ImportError:
    # Fallback para outras versões ou estruturas
    try:
        from pysus.api import sim, sih, sia, cnes
    except ImportError:
        st.error("Erro ao importar PySUS. Verifique se a biblioteca está instalada corretamente.")

# CONFIGURAÇÃO DE DESIGN DA PÁGINA
st.set_page_config(
    page_title="DataSUSX + Social (REAL)",
    page_icon="🏥",
    layout="wide"
)

# Customização visual premium
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    h1, h2, h3 { color: #003399 !important; font-family: 'Segoe UI', sans-serif; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #003399; color: white; }
    .stButton>button:hover { background-color: #002266; color: white; }
    div[data-testid="stExpander"] { background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# Mapeamento de Metadados
METADADOS_SISTEMAS = {
    "sim_geral": {
        "nome": "SIM - Mortalidade Geral",
        "anos": [2018, 2019, 2020, 2021, 2022],
        "pysus_func": sim,
        "col_municipio": "CODMUNRES"
    },
    "sih_internacoes": {
        "nome": "SIH - Internações Hospitalares",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "pysus_func": sih,
        "col_municipio": "MUNIC_RES"
    },
    "cnes_estabelecimentos": {
        "nome": "CNES - Estabelecimentos",
        "anos": [2020, 2021, 2022, 2023, 2024],
        "pysus_func": cnes,
        "col_municipio": "CODUFMUN"
    }
}

ESTADOS_MAPPING = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
    "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
}

@st.cache_data
def carregar_dados(sistema_id, uf, anos, municipio_id):
    meta = METADADOS_SISTEMAS[sistema_id]
    func = meta["pysus_func"]
    col_mun = meta["col_municipio"]
    
    dfs = []
    for ano in anos:
        try:
            # Chama a função do PySUS
            if sistema_id in ["sih_internacoes", "cnes_estabelecimentos"]:
                res = func(state=uf, year=ano, month=1) # Janeiro como padrão
            else:
                res = func(state=uf, year=ano)
            
            # Lê o arquivo retornado
            if isinstance(res, list):
                df_ano = pd.read_parquet(res[0])
            else:
                df_ano = res
            
            # Filtra por município (o código do IBGE de 6 dígitos)
            if col_mun in df_ano.columns:
                df_ano = df_ano[df_ano[col_mun].astype(str).str.startswith(municipio_id)]
            
            df_ano["Ano_Ref"] = ano
            dfs.append(df_ano)
        except Exception as e:
            st.warning(f"Erro no ano {ano}: {e}")
            
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# UI
st.title("🏥 DataSUSX - Conexão Real")

with st.sidebar:
    st.header("Configurações")
    sistema_sel = st.selectbox("Sistema:", list(METADADOS_SISTEMAS.keys()))
    uf_sel = st.selectbox("Estado:", list(ESTADOS_MAPPING.keys()), index=12)
    anos_sel = st.multiselect("Anos:", METADADOS_SISTEMAS[sistema_sel]["anos"], default=[2022])
    mun_id = st.text_input("Código IBGE (6 dígitos):", value="310620")

if st.button("🚀 Buscar Dados Oficiais"):
    with st.spinner("Baixando dados do DATASUS..."):
        df = carregar_dados(sistema_sel, ESTADOS_MAPPING[uf_sel], anos_sel, mun_id)
        if not df.empty:
            st.write(f"### Resultados: {len(df)} registros encontrados")
            st.dataframe(df)
            st.download_button("Baixar CSV", df.to_csv(index=False), "dados.csv")
        else:
            st.error("Nenhum dado encontrado para esses filtros.")
