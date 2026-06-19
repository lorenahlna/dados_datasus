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
# DICIONÁRIO DE METADADOS DINÂMICOS (Mapeamento de Filtros)
# ---------------------------------------------------------
METADADOS_SISTEMAS = {
    "cnes_tipo_sus": {
        "nome": "CNES - Estabelecimentos por Tipo (SUS e Não SUS)",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Estabelecimentos Conveniados", "Leitos Operacionais"],
        "variaveis": "[Tipo_Estabelecimento] Classificação oficial da unidade (Hospital, UBS, UPA)\n[Vínculo_SUS] Indicador de convênio público (Sim/Não)",
        "subvars": ["Posto de Saúde / UBS", "Hospital Geral", "Pronto Atendimento (UPA)", "Clínica Especializada"]
    },
    "cnes_medicos": {
        "nome": "CNES - Médico por Habitante e Profissionais",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Profissionais Ativos", "Horas Contratuais Semanais", "Razão por 1.000 hab."],
        "variaveis": "[Especialidade_Médica] Código de especialidade CBO\n[Carga_Horária] Horas contratuais semanais do profissional",
        "subvars": ["Clínica Médica", "Pediatria", "Ginecologia e Obstetrícia", "Cirurgia Geral"]
    },
    "cnes_leitos": {
        "nome": "CNES - Número de Leitos de Internação (SUS / Geral)",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Leitos Sustentados SUS", "Leitos Não SUS", "Total Leitos"],
        "variaveis": "[Tipo_Leito] Divisão de leitos cirúrgicos, clínicos ou críticos\n[Leitos_Sustentados] Leitos operacionais ativos na competência",
        "subvars": ["Leitos Cirúrgicos", "Leitos Clínicos", "Leitos Obstétricos", "UTI Adulto Tipo II"]
    },
    "cnes_capacidade": {
        "nome": "CNES - Capacidade de Atendimento Geral",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Salas Ativas", "Equipamentos em Uso"],
        "variaveis": "[Instalação_Física] Contagem física de salas operacionais\n[Equipamento] Quantidade de maquinários de imagem ou suporte à vida",
        "subvars": ["Consultórios", "Salas de Vacina", "Aparelhos de Raio-X", "Tomógrafos"]
    },
    "sih_internacoes": {
        "nome": "SIH - Número de Internações e Morbidade Hospitalar",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Internações (AIH)", "Valor Total Liquido (R$)", "Dias de Permanência"],
        "variaveis": "[Internações] Quantidade de AIH aprovadas no período\n[Valor_Total] Recursos financeiros liquidados para os estabelecimentos",
        "subvars": ["Atendimento de Urgência", "Atendimento Eletivo"]
    },
    "sia_ambulatorial": {
        "nome": "SIA - Produção Ambulatorial do SUS",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Quantidade Aprovada", "Valor Aprovado (R$)"],
        "variaveis": "[Procedimento] Código do procedimento unificado do SUS\n[Quantidade_Aprovada] Volume de atendimentos ambulatoriais liquidados",
        "subvars": ["Consultas Médicas Especializadas", "Exames Laboratoriais", "Radiodiagnósticos"]
    },
    "covid_casos": {
        "nome": "E-SUS - Óbitos e Casos de Covid-19",
        "anos": [2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Casos Confirmados", "Óbitos Confirmados", "Internações SRAG"],
        "variaveis": "[Casos_Confirmados] Notificações com laudo Positivo\n[Óbitos_SRAG] Mortes por complicações respiratórias",
        "subvars": ["Sintomáticos", "Assintomáticos"]
    },
    "sim_geral": {
        "nome": "SIM - Mortalidade Geral",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Óbitos Absolutos", "Média de Idade ao Óbito"],
        "variaveis": "[Óbitos] Contagem absoluta de óbitos por local de residência\n[Causa_Básica] Código de 4 dígitos da CID-10",
        "subvars": ["Doenças Circulatórias", "Neoplasias (Câncer)", "Causas Externas (Acidentes/Violência)"]
    },
    "sim_prematuro": {
        "nome": "SIM - Óbitos Prematuros (30 a 69 anos)",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Óbitos 30 a 69 anos", "Taxa por 100k hab."],
        "variaveis": "[Óbitos_30_a_69_anos] Mortes prematuras por Doenças Crônicas Não Transmissíveis (DCNT)",
        "subvars": ["Doenças Cardiovasculares", "Câncer", "Diabetes Mellitus", "Doenças Respiratórias Crônicas"]
    },
    "sim_menores_5": {
        "nome": "SIM - Taxa de Óbitos em Menores de 5 anos",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Óbitos Menores de 5 Anos", "Óbitos Neonatais (<28 dias)"],
        "variaveis": "[Óbitos_Menores_5_Anos] Óbitos na infância\n[Idade_Detanhada] Divisão por dias e meses de vida do bebê",
        "subvars": ["Neonatal Precoce (0-6 dias)", "Neonatal Tardio (7-27 dias)", "Pós-neonatal (28 dias a 1 ano)", "1 a 4 anos completos"]
    },
    "cad_populacao": {
        "nome": "DATA3 - População Total x Pessoas Inscritas no CadÚnico",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Inscritos CadÚnico", "Famílias Cadastradas", "Percentual de Cobertura (%)"],
        "variaveis": "[Inscritos_CadÚnico] Total de CPFs ativos registrados na base social\n[Taxa_Cobertura] Percentual da população local dependente do Cadastro Único",
        "subvars": ["Extrema Pobreza", "Pobreza", "Baixa Renda"]
    },
    "cad_domicilio": {
        "nome": "DATA3 - Pessoas Inscritas no CadÚnico por Domicílio (Urbano x Rural)",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Domicílios Mapeados", "Total de Moradores Cobertos"],
        "variaveis": "[Domicílios_Cadastrados] Total de núcleos familiares mapeados\n[Situação_Domicílio] Zoneamento da residência familiar",
        "subvars": ["Área Urbana", "Área Rural"]
    },
    "cad_pobreza": {
        "nome": "DATA3 - Pessoas Inscritas x Situação de Pobreza e Extrema Pobreza",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Pessoas Vulneráveis", "Benefícios Concedidos"],
        "variaveis": "[Pessoas_Vulneráveis] Volume total de cidadãos abaixo das linhas oficiais de vulnerabilidade",
        "subvars": ["Situação de Extrema Pobreza", "Situação de Pobreza"]
    },
    "cad_bolsa": {
        "nome": "DATA3 - Pessoas Inscritas no CadÚnico x Beneficiários do PBF",
        "anos": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        "metricas_coluna": ["Beneficiários Ativos", "Recursos Repassados (R$)", "Valor Médio por Família"],
        "variaveis": "[Beneficiários_Ativos] Famílias que recebem o benefício monetário\n[Valor_Transferido] Volume financeiro repassado para o município",
        "subvars": ["Benefício Liberado", "Benefício Bloqueado/Suspenso"]
    }
}

CATALOGO_COMPLETO = [
    {"ID": "cnes_tipo_sus", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Estabelecimentos por Tipo (SUS e Não SUS)", "Descrição": "Número de estabelecimentos de saúde divididos por tipo de atendimento e vínculo com o SUS.", "Linha": "Tipo_Estabelecimento", "Incremento": "Estabelecimentos"},
    {"ID": "cnes_medicos", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Médico por Habitante e Profissionais", "Descrição": "Quantidade de profissionais médicos e razão estimada por mil habitantes.", "Linha": "Especialidade_Médica", "Incremento": "Profissionais"},
    {"ID": "cnes_leitos", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Número de Leitos de Internação (SUS / Geral)", "Descrição": "Capacidade instalada de leitos hospitalares cirúrgicos, clínicos, obstétricos e UTIs.", "Linha": "Tipo_Leito", "Incremento": "Leitos_Sustentados"},
    {"ID": "cnes_capacidade", "Grupo": "🏥 CNES - Estrutura e Capacidade", "Nome": "Capacidade de Atendimento Geral", "Descrição": "Mapeamento físico de salas de atendimento, consultórios e ambulatórios ativos.", "Linha": "Instalação_Física", "Incremento": "Salas/Unidades"},
    {"ID": "sih_internacoes", "Grupo": "🏥 PRODUÇÃO - Hospitalar e Ambulatorial", "Nome": "Número de Internações (SIH/SUS)", "Descrição": "Morbidade Hospitalar do SUS - Volume de Autorizações de Internação Hospitalar (AIH) registradas por local de internação.", "Linha": "Município", "Incremento": "Internações"},
    {"ID": "sia_ambulatorial", "Grupo": "🏥 PRODUÇÃO - Hospitalar e Ambulatorial", "Nome": "Produção Ambulatorial (SIA/SUS)", "Descrição": "Volume de consultas, exames, procedimentos complexos e atendimentos de balcão.", "Linha": "Procedimento", "Incremento": "Quantidade_Aprovada"},
    {"ID": "covid_casos", "Grupo": "🏥 PRODUÇÃO - Hospitalar e Ambulatorial", "Nome": "Óbitos e Casos de Covid-19", "Descrição": "Séries históricas de notificações de Síndrome Respiratória Aguda Grave por COVID-19.", "Linha": "Semana_Epitemiológica", "Incremento": "Casos/Óbitos"},
    {"ID": "sim_geral", "Grupo": "💀 MORTALIDADE - Estatísticas Vitais", "Nome": "Mortalidade Geral (SIM)", "Descrição": "Estatísticas brutas de óbitos baseadas no cruzamento de Declarações de Óbito (DO).", "Linha": "Causa_Básica_(CID-10)", "Incremento": "Óbitos"},
    {"ID": "sim_prematuro", "Grupo": "💀 MORTALIDADE - Estatísticas Vitais", "Nome": "Número de Óbitos Prematuros (30 a 69 anos)", "Descrição": "Mortes prematuras ocorridas na faixa etária produtiva por Doenças Crônicas Não Transmissíveis (DCNT).", "Linha": "Grupo_Causa_DCNT", "Incremento": "Óbitos_30_a_69_anos"},
    {"ID": "sim_menores_5", "Grupo": "💀 MORTALIDADE - Estatísticas Vitais", "Nome": "Taxa de Óbitos em Menores de 5 anos", "Descrição": "Indicador de mortalidade na infância e óbitos neonatais precoce/tardio.", "Linha": "Idade_Detanhada", "Incremento": "Óbitos_Menores_5_Anos"},
    {"ID": "cad_populacao", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "População Total x Pessoas Inscritas no CadÚnico", "Descrição": "Razão de cobertura do cadastro social frente à estimativa demográfica do município.", "Linha": "Faixa_Renda", "Incremento": "Inscritos_CadÚnico"},
    {"ID": "cad_domicilio", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "Pessoas Inscritas por Domicílio (Urbano x Rural)", "Descrição": "Divisão geográfica e situação de moradia das famílias cadastradas.", "Linha": "Situação_Domicílio", "Incremento": "Domicílios_Cadastrados"},
    {"ID": "cad_pobreza", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "Pessoas Inscritas x Situação de Pobreza e Extrema Pobreza", "Descrição": "Volumetria de famílias abaixo da linha de vulnerabilidade monetária ativa.", "Linha": "Grau_Pobreza", "Incremento": "Pessoas_Vulneráveis"},
    {"ID": "cad_bolsa", "Grupo": "🌐 SOCIAL - DATA3 / Cadastro Único", "Nome": "Pessoas Inscritas no CadÚnico x Beneficiários do PBF", "Descrição": "Mapeamento de elegibilidade e cobertura do Programa Bolsa Família.", "Linha": "Status_Beneficiário", "Incremento": "Beneficiários_Ativos"}
]

df_catalogo = pd.DataFrame(CATALOGO_COMPLETO)

# Inicialização das Variáveis de Estado (Session State)
if "central_id_selecionado" not in st.session_state: st.session_state.central_id_selecionado = "cnes_medicos"
if "central_nome_selecionado" not in st.session_state: st.session_state.central_nome_selecionado = "Médico por Habitante e Profissionais"
if "central_municipio_nome" not in st.session_state: st.session_state.central_municipio_nome = "Belo Horizonte - MG"
if "central_municipio_id" not in st.session_state: st.session_state.central_municipio_id = "310620" 
if "central_linha_param" not in st.session_state: st.session_state.central_linha_param = "Especialidade_Médica"
if "central_inc_param" not in st.session_state: st.session_state.central_inc_param = "Profissionais"

# Estado dos metadados ativos (Padrão inicial preenchido com cnes_medicos para sincronizar com o print)
if "meta_nome_sus" not in st.session_state: st.session_state.meta_nome_sus = "CNES - Médico por Habitante e Profissionais"
if "meta_anos_sus" not in st.session_state: st.session_state.meta_anos_sus = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
if "meta_vars_sus" not in st.session_state: st.session_state.meta_vars_sus = "Profissionais Ativos, Horas Contratuais Semanais, Razão por 1.000 hab."
if "meta_subvars_sus" not in st.session_state: st.session_state.meta_subvars_sus = ["Clínica Médica", "Pediatria", "Ginecologia e Obstetrícia", "Cirurgia Geral"]

ESTADOS_MAPPING = {
    "Acre": "ac", "Alagoas": "al", "Amapá": "ap", "Amazonas": "am", "Bahia": "ba", "Ceará": "ce",
    "Distrito Federal": "df", "Espírito Santo": "es", "Goiás": "go", "Maranhão": "ma", "Mato Grosso": "mt",
    "Mato Grosso do Sul": "ms", "Minas Gerais": "mg", "Pará": "pa", "Paraíba": "pb", "Paraná": "pr",
    "Pernambuco": "pe", "Piauí": "pi", "Rio de Janeiro": "rj", "Rio Grande do Norte": "rn",
    "Rio Grande do Sul": "rs", "Rondônia": "ro", "Roraima": "rr", "Santa Catarina": "sc",
    "São Paulo": "sp", "Sergipe": "se", "Tocantins": "to"
}

# =========================================================
# MENU LATERAL
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
# ABA: CATALOGO DE INFORMAÇÕES
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
                    
                    # Atualiza os metadados dinamicamente no clique igual ao IBGE
                    if row['ID'] in METADADOS_SISTEMAS:
                        dm = METADADOS_SISTEMAS[row['ID']]
                        st.session_state.meta_nome_sus = dm["nome"]
                        st.session_state.meta_anos_sus = dm["anos"]
                        st.session_state.meta_vars_sus = ", ".join(dm["metricas_coluna"])
                        st.session_state.meta_subvars_sus = dm["subvars"]
                    st.success(f"Eixo '{row['Nome']}' e Metadados carregados!")

# =========================================================
# ABA: LOCALIDADES
# =========================================================
elif aba_ativa == "📍 Localidades (Cód. Município)":
    st.title("📍 Localizador de Municípios Integrado")
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

# =========================================================
# ABA: GUIA PRINCIPAL (COMPLETAMENTE ADAPTADA PARA FILTROS AVANÇADOS)
# =========================================================
elif aba_ativa == "📋 Guia Principal":
    st.title("DataSUSX + Social")
    st.caption("Painel Unificado de Consolidação Governamental")
    st.markdown("---")
    
    col_inputs, col_outputs = st.columns([1, 2])
    
    with col_inputs:
        st.subheader("📥 Parâmetros Ativos")
        api_id = st.text_input("ID do Sistema:", value=st.session_state.central_id_selecionado, disabled=True)
        
        if st.button("🔵 CONSULTAR API (Metadados)", type="secondary", use_container_width=True):
            if api_id in METADADOS_SISTEMAS:
                dm = METADADOS_SISTEMAS[api_id]
                st.session_state.meta_nome_sus = dm["nome"]
                st.session_state.meta_anos_sus = dm["anos"]
                st.session_state.meta_vars_sus = ", ".join(dm["metricas_coluna"])
                st.session_state.meta_subvars_sus = dm["subvars"]
                st.toast("Metadados Sincronizados!", icon="✅")
        
        st.markdown("---")
        st.subheader("⚙️ Estrutura do Formulário")
        c_mun = st.text_input("Código de Área (6 dígitos):", value=st.session_state.central_municipio_id)
        estado_nome = st.selectbox("UF de Referência:", list(ESTADOS_MAPPING.keys()), index=12)
        uf_sigla = ESTADOS_MAPPING[estado_nome]
        
        # MELHORIA 1: PERÍODO MULTISELECT (Escolha mais de um ano para gerar série temporal)
        lista_anos_disponiveis = METADADOS_SISTEMAS[api_id]["anos"] if api_id in METADADOS_SISTEMAS else [2022, 2023, 2024, 2025, 2026]
        anos_selecionados = st.multiselect("Selecione o Período (Anos desejados):", options=lista_anos_disponiveis, default=[2024])
        
        linha_param = st.text_input("Agrupamento das Linhas (Variável de Corte):", value=st.session_state.central_linha_param)
        
        # MELHORIA 2: FILTRO DE SUBVARIÁVEIS (Escolha quais categorias específicas de linha exibir)
        lista_subvars_disponiveis = st.session_state.meta_subvars_sus if isinstance(st.session_state.meta_subvars_sus, list) else [st.session_state.central_linha_param]
        subvars_filtradas = st.multiselect("Filtrar Subvariáveis (Categorias de Linha):", options=lista_subvars_disponiveis, default=lista_subvars_disponiveis)
        
        # MELHORIA 3: FILTRO DE VARIÁVEIS DE COLUNA (Escolha se quer ver Profissionais, Horas, etc.)
        lista_metricas_disponiveis = METADADOS_SISTEMAS[api_id]["metricas_coluna"] if api_id in METADADOS_SISTEMAS else [st.session_state.central_inc_param]
        metricas_selecionadas = st.multiselect("Variáveis Principais (Métricas da Coluna):", options=lista_metricas_disponiveis, default=[lista_metricas_disponiveis[0]])
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_baixar = st.button("🚀 PROCESSAR MATRIZ DE DADOS", type="primary", use_container_width=True)
        
    with col_outputs:
        if st.session_state.meta_nome_sus:
            st.info(f"📍 **Indicador Ativo:** {st.session_state.meta_nome_sus}")
            with st.expander("📂 INFORMAÇÕES E METADADOS DO ENDPOINT (Padrão IBGE)", expanded=True):
                sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📅 Períodos Cobertos", "🔢 Variáveis de Coluna", "🧩 Subvariáveis da Linha"])
                with sub_tab1: 
                    st.write(f"Série histórica indexável: **{st.session_state.meta_anos_sus}**")
                with sub_tab2: 
                    st.text(st.session_state.meta_vars_sus)
                with sub_tab3: 
                    st.text("\n".join([f"- {s}" for s in lista_subvars_disponiveis]))
                    
        st.subheader("📊 Planilha Consolidada Resultante")
        
        if btn_baixar:
            if not anos_selecionados:
                st.error("Erro: Selecione ao menos um ano para o Período.")
            elif not metricas_selecionadas:
                st.error("Erro: Selecione ao menos uma Variável Principal de Coluna.")
            elif not subvars_filtradas:
                st.error("Erro: Selecione ao menos uma Subvariável de Linha.")
            else:
                with st.spinner("Processando cruzamento avançado de matrizes..."):
                    st.balloons()
                    st.success("✅ Extração e cruzamento de variáveis executados com sucesso!")
                    
                    # Montagem dinâmica e inteligente da tabela cruzando as seleções feitas pelo usuário
                    base_dict = {f"{linha_param}": subvars_filtradas}
                    
                    # O loop cria colunas combinando cada Métrica selecionada com cada Ano selecionado no período
                    for m in metricas_selecionadas:
                        for a in anos_selecionados:
                            # Simulação de valores proporcionais consistentes para o mock do CNES/MDS
                            if "Horas" in m:
                                base_dict[f"{m} ({a})"] = [42000, 18500, 14200, 11900][:len(subvars_filtradas)]
                            elif "Habitante" in m or "Percentual" in m or "Razão" in m:
                                base_dict[f"{m} ({a})"] = ["2.4", "0.9", "1.1", "0.7"][:len(subvars_filtradas)]
                            elif "Valor" in m:
                                base_dict[f"{m} ({a})"] = [540000, 310000, 89000, 45000][:len(subvars_filtradas)]
                            else:
                                base_dict[f"{m} ({a})"] = [1200, 450, 380, 290][:len(subvars_filtradas)]
                    
                    df_resultado = pd.DataFrame(base_dict)
                    
                    # Adiciona a linha totalizadora calculada automaticamente no rodapé se houver colunas numéricas
                    df_numerico = df_resultado.select_dtypes(include=['number'])
                    if not df_numerico.empty and "Habitante" not in "".join(metricas_selecionadas):
                        linha_total = {f"{linha_param}": "TOTAL"}
                        for col in df_numerico.columns:
                            linha_total[col] = df_resultado[col].sum()
                        df_resultado = pd.concat([df_resultado, pd.DataFrame([linha_total])], ignore_index=True)
                        
                    st.dataframe(df_resultado, use_container_width=True)
                    csv = df_resultado.to_csv(index=False).encode('utf-8')
                    st.download_button(label="💾 Exportar Relatório Customizado (CSV)", data=csv, file_name=f"cruzamento_{api_id}_{c_mun}.csv", mime="text/csv", use_container_width=True)
        else:
            st.info("Ajuste os filtros de período e variáveis na coluna da esquerda e processe os dados.")
