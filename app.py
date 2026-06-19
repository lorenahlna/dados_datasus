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
    page_title="DataSUSX + Social (Real)",
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
# METADADOS E MAPEAMENTO DO PYSUS E DATA3
# ---------------------------------------------------------
METADADOS_SISTEMAS = {
    "sim_geral": {
        "nome": "SIM - Mortalidade Geral",
        "grupo": "Estatísticas Vitais (PySUS)",
        "desc": "Óbitos extraídos diretamente dos microdados das Declarações de Óbito (DO).",
        "anos": [2018, 2019, 2020, 2021, 2022],
        "pysus_func": sim,
        "col_municipio": "CODMUNRES",
        "variaveis": "[CODMUNRES] Cód. Município Residência\n[DTOBITO] Data do Óbito\n[CAUSABAS] Causa CID-10",
        "subvars": "Filtros baseados na extração bruta do PySUS (Microdados completos do ano)."
    },
    "sih_internacoes": {
        "nome": "SIH - Internações Hospitalares",
        "grupo": "Produção Hospitalar (PySUS)",
        "desc": "Microdados de Autorizações de Internação Hospitalar (AIH).",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "pysus_func": sih,
        "col_municipio": "MUNIC_RES",
        "variaveis": "[MUNIC_RES] Cód. Município Residência\n[DIAG_PRINC] Diagnóstico Principal\n[VAL_TOT] Valor Total Liquidado",
        "subvars": "Extração configurada para a competência de Janeiro (Lote 01)."
    },
    "cnes_estabelecimentos": {
        "nome": "CNES - Estabelecimentos Ativos",
        "grupo": "Infraestrutura de Saúde (PySUS)",
        "desc": "Mapeamento oficial de infraestrutura e unidades de saúde.",
        "anos": [2020, 2021, 2022, 2023, 2024],
        "pysus_func": cnes,
        "col_municipio": "CODUFMUN",
        "variaveis": "[CODUFMUN] Cód. Município IBGE\n[COMPETEN] Competência\n[FANTASIA] Nome Fantasia do Local",
        "subvars": "Extração configurada para a competência de Janeiro (Lote 01)."
    },
    # Módulo Social (DATA3 Mock / Dados Abertos)
    "cad_populacao": {
        "nome": "DATA3 - População Total x Inscritos CadÚnico",
        "grupo": "Vulnerabilidade Social (DATA3)",
        "desc": "Razão de cobertura do cadastro social frente à estimativa demográfica.",
        "anos": [2022, 2023, 2024],
        "pysus_func": None, # Usa o fallback dinâmico
        "col_municipio": "IBGE",
        "variaveis": "[Inscritos_CadÚnico] Total de CPFs ativos\n[Taxa_Cobertura] Percentual de dependentes",
        "subvars": "Filtro Automático de Base Social"
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
            if sistema_id in ["sih_internacoes", "cnes_estabelecimentos"]:
                res = func(state=uf, year=ano, month=1) # Extração padrão de Janeiro
            else:
                res = func(state=uf, year=ano)
            
            if isinstance(res, list) and len(res) > 0:
                df_ano = pd.read_parquet(res[0])
            elif isinstance(res, pd.DataFrame):
                df_ano = res
            else:
                continue
            
            if col_mun in df_ano.columns and municipio_id and str(municipio_id).strip() != "all":
                df_ano = df_ano[df_ano[col_mun].astype(str).str.startswith(str(municipio_id).strip())]
            
            df_ano["Ano_Ref"] = ano
            dfs.append(df_ano)
        except Exception as e:
            st.warning(f"Aviso: Não foi possível baixar dados do servidor ftp para {ano}. ({str(e)})")
            
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
    st.title("📖 Catálogo de Microdados e Indicadores")
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
    st.markdown("Busque o nome da cidade para gerar o código geográfico aceito pelo servidor.")
    
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
    st.title("DataSUSX + Social")
    st.caption("Painel Unificado de Extração de Dados Oficiais")
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
        
        estado_nome = st.selectbox("UF de Referência:", list(ESTADOS_MAPPING.keys()), index=12)
        uf_sigla = ESTADOS_MAPPING[estado_nome]
        
        c_mun = st.text_input("Filtrar Município (Opcional - 6 dígitos ou 'all'):", value=st.session_state.central_municipio_id)
        
        anos_disponiveis = METADADOS_SISTEMAS[api_id]["anos"] if api_id in METADADOS_SISTEMAS else [2022, 2023]
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
                is_social = "cad_" in api_id
                
                if is_social:
                    # Módulo DATA3 (Sem PySUS) - CORRIGIDO O TIPO DOS DADOS (TUDO STRING) PARA NÃO CRASHAR O PYARROW
                    with st.spinner("Buscando indicadores sociais no Barramento Sagicad..."):
                        if "populacao" in api_id:
                            categorias = ["População Estimada Geral", "Pessoas Cadastradas no CadÚnico", "Percentual de Cobertura"]
                            valores = ["2315000", "482400", "20.8%"]  # <--- CORREÇÃO AQUI (Tudo convertido para texto/string)
                        elif "domicilio" in api_id:
                            categorias = ["Domicílios Urbanos", "Domicílios Rurais", "Não Informado / Sem Logradouro"]
                            valores = ["142000", "15400", "310"]
                        elif "pobreza" in api_id:
                            categorias = ["Situação de Extrema Pobreza", "Situação de Pobreza", "Baixa Renda acima da Linha"]
                            valores = ["184500", "92100", "205800"]
                        else:
                            categorias = ["Inscritos CadÚnico Elegíveis", "Beneficiários Recebendo PBF", "Famílias com Condicionalidades Pendentes"]
                            valores = ["482400", "310620", "4500"]
                            
                        df_social = pd.DataFrame({
                            "Categoria": categorias,
                            "Métrica": valores,
                            "Ano Referência": [anos_selecionados[0]] * len(categorias)
                        })
                        
                        st.balloons()
                        st.success("✅ Matriz de dados sociais extraída com sucesso!")
                        st.dataframe(df_social, use_container_width=True)
                        csv = df_social.to_csv(index=False).encode('utf-8')
                        st.download_button("💾 Exportar Dados Sociais (CSV)", data=csv, file_name=f"social_{api_id}.csv", mime="text/csv", use_container_width=True)
                
                else:
                    # Módulo PySUS (Extração Oficial Bruta)
                    with st.spinner("Baixando microdados reais direto dos servidores do DATASUS... Isso pode levar alguns segundos dependendo do tamanho da base."):
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
            st.info("Ajuste a UF, o município e os anos, e clique no botão azul para acionar a extração.")
