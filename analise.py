import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- Configuração da Página ---
# Define o título da página, o ícone e o layout para ocupar a largura inteira.
st.set_page_config(
    page_title="Dashboard: Monitoramento das Usinas SolarZ",
    page_icon="📊",
    layout="wide",
)

# Carregar os dados
@st.cache_data
def load_data():
    df = pd.read_csv("DSZ.csv")

    # Convert 'Potência do Sistema' to numeric, handling errors
    df['Potência do Sistema'] = pd.to_numeric(df['Potência do Sistema'], errors='coerce')

    # Ensure date columns are datetime objects
    df['Data de Instalção'] = pd.to_datetime(df['Data de Instalção'], errors='coerce')
    df['Data Off-Line'] = pd.to_datetime(df['Data Off-Line'], errors='coerce')

    # Re-calculate 'Status da Garantia' and 'Status Operacional' to ensure consistency
    data_atual = pd.to_datetime(datetime.now().date())
    data_um_ano_atras = data_atual - timedelta(days=365)
    df['Status da Garantia'] = df['Data de Instalção'].apply(lambda x: 'Fora da Garantia' if pd.notna(x) and x < data_um_ano_atras else 'Na Garantia')
    df['Status Operacional'] = df['Data Off-Line'].apply(lambda x: 'Offline' if pd.notna(x) else 'Online')

    return df

df = load_data()

# --- Helper function for applying generation range filter ---
def apply_generation_range_filter(df_to_filter, generation_col, faixa_geracao):
    if faixa_geracao == 'Todos':
        return df_to_filter.copy() # Return a copy to ensure immutability

    if generation_col not in df_to_filter.columns:
        st.warning(f"Coluna '{generation_col}' não encontrada para o filtro de Faixa de Geração. Retornando DataFrame original.")
        return df_to_filter.copy() # Return a copy to avoid modifying original df unintentionally later

    df_filtered = df_to_filter.copy()

    # Make sure the column is clean before converting to numeric
    # Check if the column is of object type (string) and contains '%' or ','
    if pd.api.types.is_object_dtype(df_filtered[generation_col]):
        try:
            # Attempt to remove '%' and replace ',' with '.' for decimal conversion, then convert to numeric
            df_filtered[generation_col] = df_filtered[generation_col].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
        except AttributeError: # In case it's not string-like, e.g., already numeric but object type
            pass # Keep it as is if not string-like, pd.to_numeric will handle it

    # Convert to numeric, coercing errors to NaN
    df_filtered[generation_col] = pd.to_numeric(df_filtered[generation_col], errors='coerce')

    original_rows_before_dropna = df_filtered.shape[0]
    # Drop rows where conversion failed (i.e., NaN values in the generation column)
    df_filtered.dropna(subset=[generation_col], inplace=True)
    if df_filtered.shape[0] < original_rows_before_dropna:
        st.info(f"O filtro de Faixa de Geração para '{generation_col}' removeu {original_rows_before_dropna - df_filtered.shape[0]} linhas devido a valores não numéricos ou ausentes.")

    if df_filtered.empty:
        st.warning(f"Após o tratamento de dados, o DataFrame para '{generation_col}' está vazio. Não foi possível aplicar o filtro de Faixa de Geração.")
        return pd.DataFrame(columns=df_to_filter.columns) # Return empty DataFrame with original columns

    # Apply the actual percentage filter
    if faixa_geracao == '> 90%':
        return df_filtered[df_filtered[generation_col] > 90]
    elif faixa_geracao == '80% < x <= 90%':
        return df_filtered[(df_filtered[generation_col] > 80) & (df_filtered[generation_col] <= 90)]
    elif faixa_geracao == '70% < x <= 80%':
        return df_filtered[(df_filtered[generation_col] > 70) & (df_filtered[generation_col] <= 80)]
    elif faixa_geracao == '60% < x <= 70%':
        return df_filtered[(df_filtered[generation_col] > 60) & (df_filtered[generation_col] <= 70)]
    elif faixa_geracao == '50% < x <= 60%':
        return df_filtered[(df_filtered[generation_col] > 50) & (df_filtered[generation_col] <= 60)]
    elif faixa_geracao == '< 45%':
        return df_filtered[df_filtered[generation_col] < 45]
    return df_filtered # Fallback, though one of the above should be hit if faixa_geracao is valid

# --- Barra Lateral (Filtros) ---
st.sidebar.header("🔍 Filtros")

# NEW: Filtro por Período de Geração
periodo_geracao_options = ['Todos', 'Diário', 'Quinzenal', 'Mensal', 'Anual']
selected_periodo_geracao = st.sidebar.selectbox(
    "Selecionar Período de Geração",
    periodo_geracao_options,
    key='periodo_geracao_filter'
)

# NEW: Filtro por Faixa de Geração
faixa_geracao_options = ['Todos', '> 90%', '80% < x <= 90%', '70% < x <= 80%', '60% < x <= 70%', '50% < x <= 60%', '< 45%']
selected_faixa_geracao = st.sidebar.selectbox(
    "Filtrar por Faixa de Geração",
    faixa_geracao_options,
    key='faixa_geracao_filter'
)

# Filtro por Status da Garantia
warranty_options = ['Todos'] + list(df['Status da Garantia'].unique())
selected_warranty_status = st.sidebar.selectbox(
    "Filtrar por garantia",
    warranty_options,
    key='warranty_filter'
)

# Filtro por Status Operacional
operational_options = ['Todos'] + list(df['Status Operacional'].unique())
selected_operational_status = st.sidebar.selectbox(
    "Status da usina",
    operational_options,
    key='operational_filter'
)

# Aplicar os filtros base (Garantia e Operacional) ao DataFrame principal
filtered_df = df.copy()

if selected_warranty_status != 'Todos':
    filtered_df = filtered_df[filtered_df['Status da Garantia'] == selected_warranty_status]

if selected_operational_status != 'Todos':
    filtered_df = filtered_df[filtered_df['Status Operacional'] == selected_operational_status]

# Reset index to avoid potential indexing issues in subsequent operations
filtered_df = filtered_df.reset_index(drop=True)

# --- Conteúdo Principal ---
st.title("📊 Dashboard: Monitoramento das Usinas SolarZ")
st.markdown("Explore os dados de análise do desempenho e eficiência das usinas que estão dentro e fora da garantia. Utilize os filtros à esquerda para refinar sua análise.")

# Plotly Box Plot for 'Potência do Sistema'
# This plot uses the 'filtered_df' (filtered by warranty and operational status only)
fig_boxplot = px.box(
        filtered_df.dropna(subset=['Potência do Sistema']),
        x='Potência do Sistema',
        title='Distribuição da Potência do Sistema de Todas as Usinas',
        color_discrete_sequence=px.colors.sequential.Blugrn_r
    )
fig_boxplot.update_layout(
        xaxis_title='Potência do Sistema (kWp)'
    )
st.plotly_chart(fig_boxplot, key='power_boxplot')

# Display overall statistics
total_usinas_global = df.shape[0]
usinas_online_global = df[df['Status Operacional'] == 'Online'].shape[0]
usinas_offline_global = df[df['Status Operacional'] == 'Offline'].shape[0]

st.subheader("Visão Geral das Usinas")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Nº Usinas Total", value=total_usinas_global)
with col2:
    st.metric(label="Nº Usinas Online", value=usinas_online_global)
with col3:
    st.metric(label="Nº Usinas Off-line", value=usinas_offline_global)

col4, col5 = st.columns(2)

# Gerar e exibir gráfico de pizza para Status Operacional
# This plot uses the 'filtered_df' (filtered by warranty and operational status only)
if not filtered_df.empty:
    operational_counts = filtered_df['Status Operacional'].value_counts().reset_index()
    operational_counts.columns = ['Status', 'Quantidade']
    fig_operational = px.pie(
        operational_counts,
        values='Quantidade',
        names='Status',
        title='Proporção Entre Usinas Online e Offline',
        hole=0.5,
        color_discrete_sequence=px.colors.sequential.Blugrn_r
    )
    col4.plotly_chart(fig_operational)

# Gerar e exibir gráfico de pizza para Status da Garantia
# This plot uses the 'filtered_df' (filtered by warranty and operational status only)
warranty_counts = filtered_df['Status da Garantia'].value_counts().reset_index()
warranty_counts.columns = ['Status', 'Quantidade']
fig_warranty = px.pie(
    warranty_counts,
    values='Quantidade',
    names='Status',
    title='Proporção de Usinas em Relação a Garantia',
    hole=0.5,
    color_discrete_sequence=px.colors.sequential.Blugrn_r
    )
col5.plotly_chart(fig_warranty)

col6, col7 = st.columns(2)

# --- Daily Generation Chart ---
df_for_daily_chart = filtered_df.copy()
# Apply faixa_geracao filter if 'Diário' is selected or 'Todos' is selected for periodo_geracao
if selected_periodo_geracao == 'Diário' or selected_periodo_geracao == 'Todos':
    df_for_daily_chart = apply_generation_range_filter(df_for_daily_chart, 'Geração % diária', selected_faixa_geracao)

mais_que_90 = df_for_daily_chart[df_for_daily_chart['Geração % diária'] > 90].shape[0]
mais_que_80_menos_que_90 = df_for_daily_chart[(df_for_daily_chart['Geração % diária'] > 80) & (df_for_daily_chart['Geração % diária'] <= 90)].shape[0]
mais_que_70_menos_que_80 = df_for_daily_chart[(df_for_daily_chart['Geração % diária'] > 70) & (df_for_daily_chart['Geração % diária'] <= 80)].shape[0]
mais_que_60_menos_que_70 = df_for_daily_chart[(df_for_daily_chart['Geração % diária'] > 60) & (df_for_daily_chart['Geração % diária'] <= 70)].shape[0]
mais_que_50_menos_que_60 = df_for_daily_chart[(df_for_daily_chart['Geração % diária'] > 50) & (df_for_daily_chart['Geração % diária'] <= 60)].shape[0]
menos_que_45 = df_for_daily_chart[df_for_daily_chart['Geração % diária'] < 45].shape[0]

data_daily = {
        'Faixa de Geração Diária': [
            'Maior que 90%',
            'Maior que 80%',
            'Maior que 70%',
            'Maior que 60%',
            'Maior que 50%',
            'Menos que 45%'
        ],
        'Quantidade de Usinas': [
            mais_que_90,
            mais_que_80_menos_que_90,
            mais_que_70_menos_que_80,
            mais_que_60_menos_que_70,
            mais_que_50_menos_que_60,
            menos_que_45
        ]
    }
summary_df = pd.DataFrame(data_daily)

fig_daily = px.bar(
        summary_df,
        x='Faixa de Geração Diária',
        y='Quantidade de Usinas',
        title='Quantidade de Usinas por Faixa de Geração (Diária)',
        color_discrete_sequence=px.colors.sequential.Blugrn_r
    )
col6.plotly_chart(fig_daily)

# --- Fortnightly Generation Chart ---
df_for_fortnightly_chart = filtered_df.copy()
# Apply faixa_geracao filter if 'Quinzenal' is selected or 'Todos' is selected for periodo_geracao
if selected_periodo_geracao == 'Quinzenal' or selected_periodo_geracao == 'Todos':
    df_for_fortnightly_chart = apply_generation_range_filter(df_for_fortnightly_chart, 'Geração % quinzenal', selected_faixa_geracao)

semana_mais_que_90 = df_for_fortnightly_chart[df_for_fortnightly_chart['Geração % quinzenal'] > 90].shape[0]
semana_mais_que_80_menos_que_90 = df_for_fortnightly_chart[(df_for_fortnightly_chart['Geração % quinzenal'] > 80) & (df_for_fortnightly_chart['Geração % quinzenal'] <= 90)].shape[0]
semana_mais_que_70_menos_que_80 = df_for_fortnightly_chart[(df_for_fortnightly_chart['Geração % quinzenal'] > 70) & (df_for_fortnightly_chart['Geração % quinzenal'] <= 80)].shape[0]
semana_mais_que_60_menos_que_70 = df_for_fortnightly_chart[(df_for_fortnightly_chart['Geração % quinzenal'] > 60) & (df_for_fortnightly_chart['Geração % quinzenal'] <= 70)].shape[0]
semana_mais_que_50_menos_que_60 = df_for_fortnightly_chart[(df_for_fortnightly_chart['Geração % quinzenal'] > 50) & (df_for_fortnightly_chart['Geração % quinzenal'] <= 60)].shape[0]
semana_menos_que_45 = df_for_fortnightly_chart[df_for_fortnightly_chart['Geração % quinzenal'] < 45].shape[0]

data_fortnightly = {
        'Faixa de Geração Quinzenal': [
            'Maior que 90%',
            'Maior que 80%',
            'Maior que 70%',
            'Maior que 60%',
            'Maior que 50%',
            'Menos que 45%'
        ],
        'Quantidade de Usinas Solar': [
            semana_mais_que_90,
            semana_mais_que_80_menos_que_90,
            semana_mais_que_70_menos_que_80,
            semana_mais_que_60_menos_que_70,
            semana_mais_que_50_menos_que_60,
            semana_menos_que_45
        ]
    }
semana_power_df = pd.DataFrame(data_fortnightly)

fig_fortnightly = px.bar(
            semana_power_df,
            x='Faixa de Geração Quinzenal',
            y='Quantidade de Usinas Solar',
            title='Quantidade de Usinas por Faixa de Geração (Quinzenal)',
            color_discrete_sequence=px.colors.sequential.Blugrn_r
        )
col7.plotly_chart(fig_fortnightly)

# --- Monthly Generation Chart ---
df_for_monthly_chart = filtered_df.copy()
# Apply faixa_geracao filter if 'Mensal' is selected or 'Todos' is selected for periodo_geracao
if selected_periodo_geracao == 'Mensal' or selected_periodo_geracao == 'Todos':
    df_for_monthly_chart = apply_generation_range_filter(df_for_monthly_chart, 'Geração % mensal', selected_faixa_geracao)

mensal_mais_que_90 = df_for_monthly_chart[df_for_monthly_chart['Geração % mensal'] > 90].shape[0]
mensal_mais_que_80_menos_que_90 = df_for_monthly_chart[(df_for_monthly_chart['Geração % mensal'] > 80) & (df_for_monthly_chart['Geração % mensal'] <= 90)].shape[0]
mensal_mais_que_70_menos_que_80 = df_for_monthly_chart[(df_for_monthly_chart['Geração % mensal'] > 70) & (df_for_monthly_chart['Geração % mensal'] <= 80)].shape[0]
mensal_mais_que_60_menos_que_70 = df_for_monthly_chart[(df_for_monthly_chart['Geração % mensal'] > 60) & (df_for_monthly_chart['Geração % mensal'] <= 70)].shape[0]
mensal_mais_que_50_menos_que_60 = df_for_monthly_chart[(df_for_monthly_chart['Geração % mensal'] > 50) & (df_for_monthly_chart['Geração % mensal'] <= 60)].shape[0]
mensal_menos_que_45 = df_for_monthly_chart[df_for_monthly_chart['Geração % mensal'] < 45].shape[0]

data_monthly = {
        'Faixa de Geração Mensal': [
            'Maior que 90%',
            'Maior que 80%',
            'Maior que 70%',
            'Maior que 60%',
            'Maior que 50%',
            'Menos que 45%'
        ],
        'Quantidade de Usina Fotovoltaica': [
            mensal_mais_que_90,
            mensal_mais_que_80_menos_que_90,
            mensal_mais_que_70_menos_que_80,
            mensal_mais_que_60_menos_que_70,
            mensal_mais_que_50_menos_que_60,
            mensal_menos_que_45
        ]
    }
mes_power_df = pd.DataFrame(data_monthly)

col8, col9 = st.columns(2)

fig_monthly = px.bar(
        mes_power_df,
        x='Faixa de Geração Mensal',
        y='Quantidade de Usina Fotovoltaica',
        title='Quantidade de Usinas por Faixa de Geração (Mensal)',
        color_discrete_sequence=px.colors.sequential.Blugrn_r
        )
col8.plotly_chart(fig_monthly)

# --- Annual Generation Chart ---
df_for_annual_chart = filtered_df.copy()
# Apply faixa_geracao filter if 'Anual' is selected or 'Todos' is selected for periodo_geracao
if selected_periodo_geracao == 'Anual' or selected_periodo_geracao == 'Todos':
    df_for_annual_chart = apply_generation_range_filter(df_for_annual_chart, 'Geração % anual', selected_faixa_geracao)

anual_mais_que_90 = df_for_annual_chart[df_for_annual_chart['Geração % anual'] > 90].shape[0]
anual_mais_que_80_menos_que_90 = df_for_annual_chart[(df_for_annual_chart['Geração % anual'] > 80) & (df_for_annual_chart['Geração % anual'] <= 90)].shape[0]
anual_mais_que_70_menos_que_80 = df_for_annual_chart[(df_for_annual_chart['Geração % anual'] > 70) & (df_for_annual_chart['Geração % anual'] <= 80)].shape[0]
anual_mais_que_60_menos_que_70 = df_for_annual_chart[(df_for_annual_chart['Geração % anual'] > 60) & (df_for_annual_chart['Geração % anual'] <= 70)].shape[0]
anual_mais_que_50_menos_que_60 = df_for_annual_chart[(df_for_annual_chart['Geração % anual'] > 50) & (df_for_annual_chart['Geração % anual'] <= 60)].shape[0]
anual_menos_que_45 = df_for_annual_chart[df_for_annual_chart['Geração % anual'] < 45].shape[0]

data_annual = {
        'Faixa de Geração Anual': [
            'Maior que 90%',
            'Maior que 80%',
            'Maior que 70%',
            'Maior que 60%',
            'Maior que 50%',
            'Menos que 45%'
        ],
        'Quantidade de Usina Solar Fotovoltaica': [
            anual_mais_que_90,
            anual_mais_que_80_menos_que_90,
            anual_mais_que_70_menos_que_80,
            anual_mais_que_60_menos_que_70,
            anual_mais_que_50_menos_que_60,
            anual_menos_que_45
        ]
    }
ano_power_df = pd.DataFrame(data_annual)

fig_annual = px.bar(
            ano_power_df,
            x='Faixa de Geração Anual',
            y='Quantidade de Usina Solar Fotovoltaica',
            title='Quantidade de Usinas por Faixa de Geração (Anual)',
            color_discrete_sequence=px.colors.sequential.Blugrn_r
        )
col9.plotly_chart(fig_annual)

# Exibir os dados filtrados (This table reflects only warranty and operational filters)
st.subheader("Dados Filtrados")
st.write(f"Total de Usinas: {filtered_df.shape[0]}")
st.dataframe(filtered_df)






















