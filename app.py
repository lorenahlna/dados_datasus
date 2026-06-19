import streamlit as st
import pandas as pd
import requests

# Tenta importar o PySUS de várias formas possíveis
try:
    # Forma 1: Estrutura da versão 2.3.0+
    from pysus.api._impl.databases import sim, sih, sia, cnes
except ImportError:
    try:
        # Forma 2: Estrutura simplificada
        from pysus.api import sim, sih, sia, cnes
    except ImportError:
        try:
            # Forma 3: Importação direta dos módulos
            import pysus.api.sim as sim
            import pysus.api.sih as sih
            import pysus.api.sia as sia
            import pysus.api.cnes as cnes
        except ImportError:
            st.error("ERRO CRÍTICO: A biblioteca PySUS não foi encontrada. Verifique se o arquivo 'requirements.txt' foi enviado corretamente para o GitHub.")
            st.stop()

st.set_page_config(page_title="DataSUS Real", layout="wide")

# Mapeamento de funções para facilitar o uso
SISTEMAS = {
    "SIM (Mortalidade)": {"func": sim, "mun_col": "CODMUNRES", "anos": [2020, 2021, 2022]},
    "SIH (Internações)": {"func": sih, "mun_col": "MUNIC_RES", "anos": [2021, 2022, 2023]},
    "CNES (Estabelecimentos)": {"func": cnes, "mun_col": "CODUFMUN", "anos": [2022, 2023, 2024]}
}

ESTADOS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

st.title("🏥 Extração de Dados Reais - DATASUS")

with st.sidebar:
    st.header("Filtros")
    sistema_nome = st.selectbox("Selecione o Sistema:", list(SISTEMAS.keys()))
    uf = st.selectbox("Estado (UF):", ESTADOS, index=12) # MG padrão
    ano = st.selectbox("Ano:", SISTEMAS[sistema_nome]["anos"])
    municipio_id = st.text_input("Código IBGE (6 dígitos):", value="310620")

@st.cache_data
def load_data(sistema, uf, ano, mun_id):
    config = SISTEMAS[sistema]
    try:
        # Executa a função de download
        if sistema == "SIM (Mortalidade)":
            res = config["func"](state=uf, year=ano)
        else:
            res = config["func"](state=uf, year=ano, month=1)
        
        # Trata o retorno (pode ser lista de caminhos ou DataFrame)
        if isinstance(res, list):
            df = pd.read_parquet(res[0])
        else:
            df = res
            
        # Filtra por município
        col = config["mun_col"]
        if col in df.columns:
            df = df[df[col].astype(str).str.startswith(mun_id)]
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()

if st.button("🚀 Carregar Dados Oficiais"):
    with st.spinner("Buscando no FTP do Ministério da Saúde..."):
        df_result = load_data(sistema_nome, uf, ano, municipio_id)
        if not df_result.empty:
            st.success(f"Sucesso! {len(df_result)} registros encontrados.")
            st.dataframe(df_result)
            st.download_button("Baixar CSV", df_result.to_csv(index=False), "dados_datasus.csv")
        else:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
