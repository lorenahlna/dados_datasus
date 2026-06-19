import streamlit as st
import requests
import pandas as pd
import io
import os
from pysus.api._impl.databases import sim, sih, sia, cnes

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
    .card-tutorial { background-color: #e6f0ff; padding: 15px; border-left: 5px solid #003399; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DICIONÁRIO DE METADADOS DINÂMICOS (Mapeamento de Filtros)
# ---------------------------------------------------------
METADADOS_SISTEMAS = {
    "cnes_tipo_sus": {
        "nome": "CNES - Estabelecimentos por Tipo (SUS e Não SUS)",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "metricas_coluna": ["Estabelecimentos", "Leitos"],
        "variaveis": "[Tipo_Estabelecimento] Classificação oficial da unidade",
        "subvars": ["Posto de Saúde", "Hospital", "UPA", "Clínica"],
        "pysus_func": cnes,
        "col_municipio": "CODUFMUN"
    },
    "sih_internacoes": {
        "nome": "SIH - Número de Internações e Morbidade Hospitalar",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "metricas_coluna": ["Internações (AIH)", "Valor Total (R$)"],
        "variaveis": "[Internações] Quantidade de AIH aprovadas",
        "subvars": ["Urgência", "Eletivo"],
        "pysus_func": sih,
        "col_municipio": "MUNIC_RES"
    },
    "sim_geral": {
        "nome": "SIM - Mortalidade Geral",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023],
        "metricas_coluna": ["Óbitos Absolutos"],
        "variaveis": "[Óbitos] Contagem absoluta de óbitos",
        "subvars": ["Geral"],
        "pysus_func": sim,
        "col_municipio": "CODMUNRES"
    }
}

CATALOGO_COMPLETO = [
    {"ID": "cnes_tipo_sus", "Grupo": "🏥 CNES", "Nome": "Estabelecimentos por Tipo", "Linha": "Tipo_Estabelecimento", "Incremento": "Estabelecimentos"},
    {"ID": "sih_internacoes", "Grupo": "🏥 PRODUÇÃO", "Nome": "Número de Internações (SIH)", "Linha": "Modalidade", "Incremento": "Internações"},
    {"ID": "sim_geral", "Grupo": "💀 MORTALIDADE", "Nome": "Mortalidade Geral (SIM)", "Linha": "Causa", "Incremento": "Óbitos"}
]

df_catalogo = pd.DataFrame(CATALOGO_COMPLETO)

# Inicialização das Variáveis de Estado
if "central_id_selecionado" not in st.session_state: st.session_state.central_id_selecionado = "sim_geral"
if "central_municipio_id" not in st.session_state: st.session_state.central_municipio_id = "310620" 
if "central_municipio_nome" not in st.session_state: st.session_state.central_municipio_nome = "Belo Horizonte - MG"

ESTADOS_MAPPING = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
    "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
}

# Funções de Busca Real
@st.cache_data
def buscar_dados_reais(sistema_id, uf, anos, municipio_id):
    meta = METADADOS_SISTEMAS[sistema_id]
    pysus_func = meta["pysus_func"]
    col_mun = meta["col_municipio"]
    
    dfs = []
    for ano in anos:
        try:
            # Para SIH/SIA/CNES pode precisar de mês, aqui pegamos o ano todo ou um mês padrão
            if sistema_id in ["sih_internacoes", "sia_ambulatorial", "cnes_tipo_sus"]:
                result = pysus_func(state=uf, year=ano, month=1) # Exemplo: Janeiro
            else:
                result = pysus_func(state=uf, year=ano)
            
            if isinstance(result, list):
                df_ano = pd.read_parquet(result[0])
            else:
                df_ano = result
                
            # Filtro por Município
            if col_mun in df_ano.columns:
                df_ano = df_ano[df_ano[col_mun].astype(str).str.startswith(municipio_id)]
            
            df_ano["Ano_Ref"] = ano
            dfs.append(df_ano)
        except Exception as e:
            st.warning(f"Não foi possível carregar dados de {ano}: {e}")
            
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

# Interface Streamlit (simplificada para o exemplo real)
st.sidebar.title("🧬 Central DataSUSX (REAL)")
aba_ativa = st.sidebar.radio("Navegar para:", ["📋 Guia Principal", "📍 Localidades"])

if aba_ativa == "📍 Localidades":
    st.title("📍 Localizador de Municípios")
    termo = st.text_input("Cidade:")
    if termo:
        res = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios")
        filtrados = [m for m in res.json() if termo.lower() in m['nome'].lower()]
        if filtrados:
            mun = st.selectbox("Selecione:", [f"{m['nome']} - {m['microrregiao']['mesorregiao']['UF']['sigla']}" for m in filtrados])
            cod = [m['id'] for m in filtrados if f"{m['nome']} - {m['microrregiao']['mesorregiao']['UF']['sigla']}" == mun][0]
            if st.button("Ativar"):
                st.session_state.central_municipio_id = str(cod)[:6]
                st.session_state.central_municipio_nome = mun
                st.success("Ativado!")

elif aba_ativa == "📋 Guia Principal":
    st.title("Extração de Dados Oficiais")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        sistema = st.selectbox("Sistema:", list(METADADOS_SISTEMAS.keys()))
        uf_nome = st.selectbox("UF:", list(ESTADOS_MAPPING.keys()), index=12)
        uf_sigla = ESTADOS_MAPPING[uf_nome]
        anos = st.multiselect("Anos:", METADADOS_SISTEMAS[sistema]["anos"], default=[2022])
        
        if st.button("🚀 BUSCAR DADOS REAIS"):
            with st.spinner("Conectando ao DATASUS..."):
                df_real = buscar_dados_reais(sistema, uf_sigla, anos, st.session_state.central_municipio_id)
                if not df_real.empty:
                    st.session_state.df_resultado = df_real
                    st.success("Dados carregados!")
                else:
                    st.error("Nenhum dado encontrado.")

    with col2:
        if "df_resultado" in st.session_state:
            st.write(f"### Dados de {st.session_state.central_municipio_nome}")
            st.dataframe(st.session_state.df_resultado.head(100))
            csv = st.session_state.df_resultado.to_csv(index=False).encode('utf-8')
            st.download_button("💾 Baixar CSV Real", csv, "dados_reais.csv", "text/csv")
        else:
            st.info("Selecione os parâmetros e clique em buscar.")
