import streamlit as st
import requests
import pandas as pd
import io
import os

# ---------------------------------------------------------
# IMPORTAÇÃO ROBUSTA DO PYSUS (MOTOR DE DADOS REAIS)
# ---------------------------------------------------------
try:
    from pysus.api._impl.databases import sim, sih, sia, cnes
except ImportError:
    try:
        from pysus.api import sim, sih, sia, cnes
    except ImportError:
        st.error("Erro ao importar PySUS. Verifique se a biblioteca está instalada corretamente.")
        sim = sih = sia = cnes = None

# CONFIGURAÇÃO DE DESIGN DA PÁGINA
st.set_page_config(
    page_title="DataSUSX (Real)",
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
# METADADOS EMAPEAMENTO DO PYSUS
# ---------------------------------------------------------
METADADOS_SISTEMAS = {
    "sim_geral": {
        "nome": "SIM - Mortalidade Geral",
        "grupo": "Estatísticas Vitais",
        "desc": "Óbitos extraídos diretamente dos microdados das Declarações de Óbito (DO).",
        "anos": [2018, 2019, 2020, 2021, 2022],
        "pysus_func": sim,
        "col_municipio": "CODMUNRES",
        "variaveis": "[CODMUNRES] Cód. Município Residência\n[DTOBITO] Data do Óbito\n[CAUSABAS] Causa CID-10",
        "subvars": "Filtros baseados na extração bruta do PySUS (Microdados completos do ano)."
    },
    "sih_internacoes": {
        "nome": "SIH - Internações Hospitalares",
        "grupo": "Produção Hospitalar",
        "desc": "Microdados de Autorizações de Internação Hospitalar (AIH).",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "pysus_func": sih,
        "col_municipio": "MUNIC_RES",
        "variaveis": "[MUNIC_RES] Cód. Município Residência\n[DIAG_PRINC] Diagnóstico Principal\n[VAL_TOT] Valor Total Liquidado",
        "subvars": "Extração configurada para a competência de Janeiro (Lote 01)."
    },
    "cnes_estabelecimentos": {
        "nome": "CNES - Estabelecimentos Ativos",
        "grupo": "Infraestrutura de Saúde",
        "desc": "Mapeamento oficial de infraestrutura e unidades de saúde.",
        "anos": [2020, 2021, 2022, 2023, 2024],
        "pysus_func": cnes,
        "col_municipio": "CODUFMUN",
        "variaveis": "[CODUFMUN] Cód. Município IBGE\n[COMPETEN] Competência\n[FANTASIA] Nome Fantasia do Local",
        "subvars": "Extração configurada para a competência de Janeiro (Lote 01)."
    }
}

CATALOGO_COMPLETO = [{"ID": k, "Grupo": v["grupo"], "Nome": v["nome"], "Descrição": v["desc"]} for k, v in METADADOS_SISTEMAS.items()]
df_catalogo = pd.DataFrame(CATALOGO_COMPLETO)

ESTADOS_MAPPING = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
    "São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
}

# Inicialização do Session State
if "central_id_selecionado" not in st.session_state: st.session_state.central_id_selecionado = "sih_internacoes"
if "central_nome_selecionado" not in st.session_state: st.session_state.central_nome_selecionado = "SIH - Internações Hospitalares"
if "central_municipio_nome" not in st.session_state: st.session_state.central_municipio_nome = "Belo Horizonte - MG"
if "central_municipio_id" not in st.session_state: st.session_state.central_municipio_id = "310620" 

# Estado dos metadados
if "meta_nome_sus" not in st.session_state: st.session_state.meta_nome_sus = METADADOS_SISTEMAS["sih_internacoes"]["nome"]
if "meta_anos_sus" not in st.session_state: st.session_state.meta_anos_sus = METADADOS_SISTEMAS["sih_internacoes"]["anos"]
if "meta_vars_sus" not in st.session_state: st.session_state.meta_vars_sus = METADADOS_SISTEMAS["sih_internacoes"]["variaveis"]
if "meta_subvars_sus" not in st.session_state: st.session_state.meta_subvars_sus = METADADOS_SISTEMAS["sih_internacoes"]["subvars"]

# ---------------------------------------------------------
# FUNÇÃO DE EXTRAÇÃO REAL VIA PYSUS
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def carregar_dados_reais(sistema_id, uf, anos, municipio_id):
    meta = METADADOS_SISTEMAS.get(sistema_id)
    if not meta or not meta.get("pysus_func"):
        return pd.DataFrame()

    func = meta["pysus_func"]
    col_mun = meta["col_municipio"]
    
    dfs = []
    for ano in anos:
        try:
            # Regra adaptada do seu script: SIH e CNES precisam do mês
            if sistema_id in ["sih_internacoes", "cnes_estabelecimentos"]:
                res = func(state=uf, year=ano, month=1) # Usando Janeiro como amostra padrão
            else:
                res = func(state=uf, year=ano)
            
            # Tratamento da resposta do PySUS
            if isinstance(res, list) and len(res) > 0:
                df_ano = pd.read_parquet(res[0])
            elif isinstance(res, pd.DataFrame):
                df_ano = res
            else:
                continue
            
            # Filtro Geográfico de Município
            if col_mun in df_ano.columns and municipio_id and municipio_id != "all":
                df_ano = df_ano[df_ano[col_mun].astype(str).str.startswith(str(municipio_id))]
            
            df_ano["Ano_Ref"] = ano
            dfs.append(df_ano)
        except Exception as e:
            st.warning(f"Aviso: Não foi possível baixar dados para o ano {ano}. Erro interno: {str(e)}")
            
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# =========================================================
# MENU LATERAL UNIFICADO
# =========================================================
st.sidebar.title("🧬 DataSUSX v3.0 (Real)")
st.sidebar.markdown("---")
st.sidebar.subheader("Menu de Opções")

aba_ativa = st.sidebar.radio(
    "Navegar para:",
    ["📋 Guia Principal", "📖 Catálogo (Consultas)", "📍 Localidades (Cód. Município)"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Parâmetros Atuais:")
st.sidebar.info(f"**Indicador:** {st.session_state.central_id_selecionado}\n\n**Município:** {st.session_state.central_municipio_nome}\n\n**Código (6d):** {st.session_state.central_municipio_id}")

# =========================================================
# ABA: CATALOGO DE INFORMAÇÕES
# =========================================================
if aba_ativa == "📖 Catálogo (Consultas)":
    st.title("📖 Catálogo de Microdados (PySUS)")
    st.markdown("Clique no sistema desejado para configurar o motor de extração na Guia Principal.")
    
    st.dataframe(df_catalogo, use_container_width=True, hide_index=True)
    
    st.subheader("🎯 Ativação Rápida:")
    grupos = df_catalogo["Grupo"].unique()
    for g in grupos:
        with st.expander(f"📁 {g}"):
            sub_df = df_catalogo[df_catalogo["Grupo"] == g]
            for _, row in sub_df.iterrows():
                if st.button(f"Carregar: {row['Nome']}", key=f"btn_{row['ID']}"):
                    st.session_state.central_id_selecionado = row['ID']
                    st.session_state.central_nome_selecionado = row['Nome']
                    
                    dm = METADADOS_SISTEMAS[row['ID']]
                    st.session_state.meta_nome_sus = dm["nome"]
                    st.session_state.meta_anos_sus = dm["anos"]
                    st.session_state.meta_vars_sus = dm["variaveis"]
                    st.session_state.meta_subvars_sus = dm["subvars"]
                    st.success(f"Motor '{row['Nome']}' ativado com sucesso!")

# =========================================================
# ABA: LOCALIDADES (GERADOR DE CÓDIGO)
# =========================================================
elif aba_ativa == "📍 Localidades (Cód. Município)":
    st.title("📍 Localizador de Municípios Integrado")
    st.markdown("Busque o nome da cidade para gerar o código geográfico aceito pelo servidor do Ministério da Saúde.")
    
    termo_busca = st.text_input("Digite o nome da cidade:", value="").strip()
    if termo_busca:
        with st.spinner("Buscando malhas geográficas na API do IBGE..."):
            res = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios?ordenar=nome")
            if res.status_code == 200:
                filtrados = [m for m in res.json() if termo_busca.lower() in m['nome'].lower()]
                if filtrados:
                    opcoes_mun = {f"{m['nome']} - {m['microrregiao']['mesorregiao']['UF']['sigla']}": str(m['id']) for m in filtrados}
                    municipio_escolhido = st.selectbox("Selecione a localidade correta:", list(opcoes_mun.keys()))
                    id_datasus = opcoes_mun[municipio_escolhido][:-1]
                    
                    st.markdown(f"📍 Município Ativo: **{municipio_escolhido}**")
                    st.markdown(f"🔢 Código Técnico (6 dígitos): `{id_datasus}`")
                    
                    if st.button("🚀 Ativar Localidade no Painel", type="primary"):
                        st.session_state.central_municipio_nome = municipio_escolhido
                        st.session_state.central_municipio_id = id_datasus
                        st.success("Código geográfico gravado na memória!")
                else:
                    st.error("Nenhuma cidade localizada com esse nome.")

# =========================================================
# ABA: GUIA PRINCIPAL (O PAINEL EXTRATOR)
# =========================================================
elif aba_ativa == "📋 Guia Principal":
    st.title("DataSUSX (Microdados Reais)")
    st.caption("Painel Unificado de Extração Oficial usando infraestrutura PySUS")
    st.markdown("---")
    
    col_inputs, col_outputs = st.columns([1, 2])
    
    with col_inputs:
        st.subheader("📥 Motor de Extração")
        api_id = st.text_input("ID do Sistema:", value=st.session_state.central_id_selecionado, disabled=True)
        
        if st.button("🔵 CONSULTAR API (Metadados)", type="secondary", use_container_width=True):
            if api_id in METADADOS_SISTEMAS:
                dm = METADADOS_SISTEMAS[api_id]
                st.session_state.meta_nome_sus = dm["nome"]
                st.session_state.meta_anos_sus = dm["anos"]
                st.session_state.meta_vars_sus = dm["variaveis"]
                st.session_state.meta_subvars_sus = dm["subvars"]
                st.toast("Dicionário técnico mapeado!", icon="✅")
        
        st.markdown("---")
        st.subheader("⚙️ Filtros de Requisição")
        
        estado_nome = st.selectbox("UF de Referência (Obrigatório para PySUS):", list(ESTADOS_MAPPING.keys()), index=12)
        uf_sigla = ESTADOS_MAPPING[estado_nome]
        
        c_mun = st.text_input("Filtrar Município (Opcional - 6 dígitos ou 'all'):", value=st.session_state.central_municipio_id)
        
        # O Multiselect garante a extração do seu script (lista de anos)
        anos_disponiveis = METADADOS_SISTEMAS[api_id]["anos"] if api_id in METADADOS_SISTEMAS else [2022]
        anos_selecionados = st.multiselect("Anos Base (Período):", options=anos_disponiveis, default=[anos_disponiveis[-1]])
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_baixar = st.button("🚀 BAIXAR DADOS OFICIAIS", type="primary", use_container_width=True)
        
    with col_outputs:
        if st.session_state.meta_nome_sus:
            st.info(f"📍 **Base de Dados Ativa:** {st.session_state.meta_nome_sus}")
            with st.expander("📂 INFORMAÇÕES E METADADOS DO ENDPOINT", expanded=True):
                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📅 Períodos Cobertos", "🔢 Principais Colunas Brutas", "🧩 Escopo da Base"])
                with sub_tab1: 
                    st.write(f"Anos indexados no backend: **{st.session_state.meta_anos_sus}**")
                with sub_tab2: 
                    st.text(st.session_state.meta_vars_sus)
                with sub_tab3: 
                    st.text(st.session_state.meta_subvars_sus)
                    
        st.subheader("📊 Microdados Consolidados")
        
        if btn_baixar:
            if not anos_selecionados:
                st.error("Por favor, selecione ao menos um ano para extração.")
            else:
                with st.spinner("Baixando microdados reais direto dos servidores do DATASUS... Isso pode levar alguns segundos dependendo do tamanho da base."):
                    # >>> CHAMA A SUA FUNÇÃO REAL DO PYSUS <<<
                    df_resultado = carregar_dados_reais(api_id, uf_sigla, anos_selecionados, c_mun)
                    
                    if not df_resultado.empty:
                        st.balloons()
                        st.success(f"✅ Extração oficial concluída! {len(df_resultado)} registros brutos encontrados.")
                        
                        st.dataframe(df_resultado, use_container_width=True)
                        
                        csv = df_resultado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="💾 Exportar Microdados Brutos (CSV)", 
                            data=csv, 
                            file_name=f"pysus_{api_id}_{uf_sigla}_{c_mun}.csv", 
                            mime="text/csv", 
                            use_container_width=True
                        )
                    else:
                        st.error("Nenhum dado encontrado no servidor para os parâmetros e filtros selecionados.")
        else:
            st.info("Ajuste a UF, o município e os anos, e clique em **BAIXAR DADOS OFICIAIS** para acionar o motor PySUS.")
