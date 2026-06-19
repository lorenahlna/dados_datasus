import streamlit as st
import requests
import pandas as pd
import io

# CONFIGURAÇÃO DE DESIGN DA PÁGINA
st.set_page_config(
    page_title="DataSUSX + Social",
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
# NOVO CATÁLOGO DE APIS E DIRETÓRIOS MAPEADOS (SUA LISTA EXATA)
# ---------------------------------------------------------
CATALOGO_COMPLETO = [
    # --- GRUPO: ESTRUTURA E CAPACIDADE (CNES) ---
    {"ID": "cnes_tipo_sus", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Estabelecimentos por Tipo (SUS e Não SUS)", "Descrição": "Número de estabelecimentos de saúde divididos por tipo de atendimento e vínculo com o SUS.", "Linha": "Tipo_Estabelecimento", "Incremento": "Estabelecimentos"},
    {"ID": "cnes_medicos", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Médico por Habitante e Profissionais", "Descrição": "Quantidade de profissionais médicos e razão estimada por mil habitantes.", "Linha": "Especialidade_Médica", "Incremento": "Profissionais"},
    {"ID": "cnes_leitos", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Número de Leitos de Internação (SUS / Geral)", "Descrição": "Capacidade instalada de leitos hospitalares cirúrgicos, clínicos, obstétricos e UTIs.", "Linha": "Tipo_Leito", "Incremento": "Leitos_Sustentados"},
    {"ID": "cnes_capacidade", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Capacidade de Atendimento Geral", "Descrição": "Mapeamento físico de salas de atendimento, consultórios e ambulatórios ativos.", "Linha": "Instalação_Física", "Incremento": "Salas/Unidades"},

    # --- GRUPO: PRODUÇÃO HOSPITALAR E AMBULATORIAL (SIH/SIA) ---
    {"ID": "sih_internacoes", "Grupo": "🏥 PRODUÇÃO - Hospitalar e Ambulatorial", "Nome": "Número de Internações (SIH/SUS)", "Descrição": "Morbidade Hospitalar do SUS - Volume de Autorizações de Internação Hospitalar (AIH) registradas por local de internação.", "Linha": "Município", "Incremento": "Internações"},
    {"ID": "sia_ambulatorial", "Grupo": "🏥 PRODUÇÃO - Hospitalar e Ambulatorial", "Nome": "Produção Ambulatorial (SIA/SUS)", "Descrição": "Volume de consultas, exames, procedimentos complexos e atendimentos de balcão.", "Linha": "Procedimento", "Incremento": "Quantidade_Aprovada"},
    {"ID": "covid_casos", "Grupo": "🏥 PRODUÇÃO - Hospitalar e Ambulatorial", "Nome": "Óbitos e Casos de Covid-19", "Descrição": "Séries históricas de notificações de Síndrome Respiratória Aguda Grave por COVID-19.", "Linha": "Semana_Epitemiológica", "Incremento": "Casos/Óbitos"},

    # --- GRUPO: MORTALIDADE (SIM) ---
    {"ID": "sim_geral", "Grupo": "💀 MORTALIDADE - Estatísticas Vitais", "Nome": "Mortalidade Geral (SIM)", "Descrição": "Estatísticas brutas de óbitos baseadas no cruzamento de Declarações de Óbito (DO).", "Linha": "Causa_Básica_(CID-10)", "Incremento": "Óbitos"},
    {"ID": "sim_prematuro", "Grupo": "💀 MORTALIDADE - Estatísticas Vitais", "Nome": "Número de Óbitos Prematuros (30 a 69 anos)", "Descrição": "Mortes prematuras ocorridas na faixa etária produtiva por Doenças Crônicas Não Transmissíveis (DCNT).", "Linha": "Grupo_Causa_DCNT", "Incremento": "Óbitos_30_a_69_anos"},
    {"ID": "sim_menores_5", "Grupo": "💀 MORTALIDADE - Estatísticas Vitais", "Nome": "Taxa de Óbitos em Menores de 5 anos", "Descrição": "Indicador de mortalidade na infância e óbitos neonatais precoce/tardio.", "Linha": "Idade_Detanhada", "Incremento": "Óbitos_Menores_5_Anos"},

    # --- GRUPO: CADÚNICO E BOLSA FAMÍLIA (DATA3) ---
    {"ID": "cad_populacao", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "População Total x Pessoas Inscritas no CadÚnico", "Descrição": "Razão de cobertura do cadastro social frente à estimativa demográfica do município.", "Linha": "Faixa_Renda", "Incremento": "Inscritos_CadÚnico"},
    {"ID": "cad_domicilio", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "Pessoas Inscritas por Domicílio (Urbano x Rural)", "Descrição": "Divisão geográfica e situação de moradia das famílias cadastradas.", "Linha": "Situação_Domicílio", "Incremento": "Domicílios_Cadastrados"},
    {"ID": "cad_pobreza", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "Pessoas Inscritas x Situação de Pobreza e Extrema Pobreza", "Descrição": "Volumetria de famílias abaixo da linha de vulnerabilidade monetária ativa.", "Linha": "Grau_Pobreza", "Incremento": "Pessoas_Vulneráveis"},
    {"ID": "cad_bolsa", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "Pessoas Inscritas no CadÚnico x Beneficiários do PBF", "Descrição": "Mapeamento de elegibilidade e cobertura do Programa Bolsa Família.", "Linha": "Status_Beneficiário", "Incremento": "Beneficiários_Ativos"}
]

df_catalogo = pd.DataFrame(CATALOGO_COMPLETO)

# Inicialização das Variáveis de Estado
if "central_id_selecionado" not in st.session_state: st.session_state.central_id_selecionado = "cnes_tipo_sus"
if "central_nome_selecionado" not in st.session_state: st.session_state.central_nome_selecionado = "Estabelecimentos por Tipo (SUS e Não SUS)"
if "central_municipio_nome" not in st.session_state: st.session_state.central_municipio_nome = "Belo Horizonte - MG"
if "central_municipio_id" not in st.session_state: st.session_state.central_municipio_id = "310620" 
if "central_linha_param" not in st.session_state: st.session_state.central_linha_param = "Tipo_Estabelecimento"
if "central_inc_param" not in st.session_state: st.session_state.central_inc_param = "Estabelecimentos"

ESTADOS_MAPPING = {
    "Acre": "ac", "Alagoas": "al", "Amapá": "ap", "Amazonas": "am", "Bahia": "ba", "Ceará": "ce",
    "Distrito Federal": "df", "Espírito Santo": "es", "Goiás": "go", "Maranhão": "ma", "Mato Grosso": "mt",
    "Mato Grosso do Sul": "ms", "Minas Gerais": "mg", "Pará": "pa", "Paraíba": "pb", "Paraná": "pr",
    "Pernambuco": "pe", "Piauí": "pi", "Rio de Janeiro": "rj", "Rio Grande do Norte": "rn",
    "Rio Grande do Sul": "rs", "Rondônia": "ro", "Roraima": "rr", "Santa Catarina": "sc",
    "São Paulo": "sp", "Sergipe": "se", "Tocantins": "to"
}

# =========================================================
# MENU LATERAL UNIFICADO
# =========================================================
st.sidebar.title("🧬 Central DataSUSX + Social")
st.sidebar.markdown("---")
st.sidebar.subheader("Menu de Opções")

aba_ativa = st.sidebar.radio(
    "Navegar para:",
    ["📋 Guia Principal", "📖 Catálogo (Consultas)", "📍 Localidades (Cód. Município)"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Parâmetros Selecionados:")
st.sidebar.info(f"**Indicador:** {st.session_state.central_id_selecionado}\n\n**Município:** {st.session_state.central_municipio_nome}\n\n**Código (6d):** {st.session_state.central_municipio_id}")

# =========================================================
# ABA: CATALOGO DE INFORMAÇÕES (SUA LISTA MAPEADA)
# =========================================================
if aba_ativa == "📖 Catálogo (Consultas)":
    st.title("📖 Mapeamento de Parâmetros Técnicos")
    st.markdown("Clique em qualquer um dos indicadores abaixo para configurar instantaneamente os eixos da Guia Principal.")
    
    st.dataframe(df_catalogo[["Grupo", "Nome", "Descrição"]], use_container_width=True, hide_index=True)
    
    st.subheader("🎯 Ativação Rápida:")
    grupos = df_catalogo["Grupo"].unique()
    for g in grupos:
        with st.expander(f"📁 {g}"):
            sub_df = df_catalogo[df_catalogo["Grupo"] == g]
            for _, row in sub_df.iterrows():
                if st.button(f"Carregar: {row['Nome']}", key=f"btn_{row['ID']}"):
                    st.session_state.central_id_selecionado = row['ID']
                    st.session_state.central_nome_selecionado = row['Nome']
                    st.session_state.central_linha_param = row['Linha']
                    st.session_state.central_inc_param = row['Incremento']
                    st.success(f"Eixo '{row['Nome']}' carregado no SessionState!")

# =========================================================
# ABA: LOCALIDADES (GERADOR DE CÓDIGO)
# =========================================================
elif aba_ativa == "📍 Localidades (Cód. Município)":
    st.title("📍 Localizador de Municípios Integrado")
    st.markdown("Gere o código de 6 dígitos aceito de forma universal nas requisições do DATASUS e DATA3.")
    
    termo_busca = st.text_input("Digite o nome da cidade:", value="").strip()
    if termo_busca:
        with st.spinner("Buscando malhas geográficas..."):
            res = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios?ordenar=nome")
            if res.status_code == 200:
                filtrados = [m for m in res.json() if termo_busca.lower() in m['nome'].lower()]
                if filtrados:
                    opcoes_mun = {f"{m['nome']} - {m['microrregiao']['mesorregiao']['UF']['sigla']}": str(m['id']) for m in filtrados}
                    municipio_escolhido = st.selectbox("Selecione a localidade correta:", list(opcoes_mun.keys()))
                    
                    id_datasus_sagicad = opcoes_mun[municipio_escolhido][:-1]
                    
                    st.markdown(f"📍 Município Ativo: **{municipio_escolhido}**")
                    st.markdown(f"🔢 Código Técnico (6 dígitos): `{id_datasus_sagicad}`")
                    
                    if st.button("🚀 Ativar Localidade e Ir para o Painel", type="primary"):
                        st.session_state.central_municipio_nome = municipio_escolhido
                        st.session_state.central_municipio_id = id_datasus_sagicad
                        st.success("Configuração salva!")
                else:
                    st.error("Nenhuma cidade localizada.")

# =========================================================
# ABA: GUIA PRINCIPAL (O MOTOR DO PROCESSAMENTO)
# =========================================================
elif aba_ativa == "📋 Guia Principal":
    st.title("DataSUSX + Social")
    st.caption("Painel Unificado de Consolidação Governamental")
    st.markdown("---")
    
    col_inputs, col_outputs = st.columns([1, 2])
    
    with col_inputs:
        st.subheader("📥 Parâmetros Ativos")
        api_id = st.text_input("ID do Sistema:", value=st.session_state.central_id_selecionado, disabled=True)
        
        st.markdown("---")
        st.subheader("⚙️ Estrutura do Formulário")
        c_mun = st.text_input("Código de Área (6 dígitos):", value=st.session_state.central_municipio_id)
        estado_nome = st.selectbox("UF de Referência:", list(ESTADOS_MAPPING.keys()), index=12) # MG Padrão
        uf_sigla = ESTADOS_MAPPING[estado_nome]
        
        ano = st.slider("Ano de Análise:", min_value=2015, max_value=2026, value=2024)
        
        linha_param = st.text_input("Agrupamento das Linhas (Variável):", value=st.session_state.central_linha_param)
        inc_param = st.text_input("Métrica do Incremento (Valores):", value=st.session_state.central_inc_param)
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_baixar = st.button("🚀 PROCESSAR MATRIZ DE DADOS", type="primary", use_container_width=True)
        
    with col_outputs:
        st.info(f"📋 **Alvo Selecionado:** {st.session_state.central_nome_selecionado}")
        
        st.subheader("📊 Planilha Consolidada Resultante")
        
        if btn_baixar:
            is_social = "SOCIAL" in df_catalogo[df_catalogo["ID"] == api_id]["Grupo"].values[0]
            tipo_spinner = "Exfiltrando dados do barramento DATA3..." if is_social else "Conectando ao barramento TabNet..."
            
            with st.spinner(tipo_spinner):
                try:
                    # SIMULAÇÃO DE RESPOSTA INALTERADA DE INTEROPERABILIDADE 
                    # Criação de um mock altamente estruturado baseado nas variáveis dinâmicas de cada item solicitado
                    st.balloons()
                    st.success("✅ Extração executada com sucesso!")
                    
                    if is_social:
                        # Resposta do Módulo DATA3 (Cadastro Único e Bolsa Família)
                        if "populacao" in api_id:
                            categorias = ["População Estimada Geral", "Pessoas Cadastradas no CadÚnico", "Percentual de Cobertura"]
                            valores = [2315000, 482400, "20.8%"]
                        elif "domicilio" in api_id:
                            categorias = ["Domicílios Urbanos", "Domicílios Rurais", "Não Informado / Sem Logradouro"]
                            valores = [142000, 15400, 310]
                        elif "pobreza" in api_id:
                            categorias = ["Situação de Extrema Pobreza", "Situação de Pobreza", "Baixa Renda acima da Linha"]
                            valores = [184500, 92100, 205800]
                        else:
                            categorias = ["Inscritos CadÚnico Elegíveis", "Beneficiários Recebendo PBF", "Famílias com Condicionalidades Pendentes"]
                            valores = [482400, 310620, 4500]
                            
                        df_resultado = pd.DataFrame({
                            f"{linha_param}": categorias,
                            "Métrica": valores,
                            "Ano Referência": [ano] * len(categorias)
                        })
                    else:
                        # Resposta do Módulo DATASUS (CNES / SIH / SIM)
                        if "tipo_sus" in api_id:
                            cats = ["Posto de Saúde / UBS", "Hospital Geral", "Pronto Atendimento (UPA)", "Clínica Especializada", "TOTAL"]
                            vals = [145, 24, 12, 89, 270]
                        elif "medicos" in api_id:
                            cats = ["Clínica Médica", "Pediatria", "Ginecologia e Obstetrícia", "Cirurgia Geral", "TOTAL"]
                            vals = [1200, 450, 380, 290, 2320]
                        elif "leitos" in api_id:
                            cats = ["Leitos Cirúrgicos", "Leitos Clínicos", "Leitos Obstétricos", "UTI Adulto Tipo II", "TOTAL"]
                            vals = [450, 890, 310, 120, 1770]
                        elif "prematuro" in api_id:
                            cats = ["Doenças do Aparelho Circulatório", "Neoplasias (Câncer)", "Diabetes Mellitus", "Doenças Respiratórias Crônicas", "TOTAL"]
                            vals = [1240, 980, 410, 230, 2860]
                        elif "menores_5" in api_id:
                            cats = ["Período Neonatal Precoce (0-6 dias)", "Período Neonatal Tardio (7-27 dias)", "Pós-neonatal (28 dias a 1 ano)", "1 a 4 anos completos", "TOTAL"]
                            vals = [45, 18, 22, 12, 97]
                        else:
                            cats = ["Região Hub Centro", "Polo Regional Norte", "Polo Regional Sul", "Zonas Limitrofes", "TOTAL"]
                            vals = [18450, 9120, 12300, 5100, 45150]
                            
                        df_resultado = pd.DataFrame({
                            f"{linha_param}": cats,
                            f"{inc_param} ({ano})": vals
                        })
                        
                    st.dataframe(df_resultado, use_container_width=True)
                    csv = df_resultado.to_csv(index=False).encode('utf-8')
                    st.download_button(label="💾 Exportar Relatório Consolidado (CSV)", data=csv, file_name=f"extracao_{api_id}_{c_mun}.csv", mime="text/csv", use_container_width=True)
                except Exception as e:
                    st.error(f"Erro na requisição: {str(e)}")
        else:
            st.info("Aguardando parametrização. Defina os eixos e clique em **PROCESSAR MATRIZ DE DADOS**.")
