import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import bigquery

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "onepiece-pipeline"
DATASET_ID = "onepiece"
TABLE_ID = "chapters"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# Couleurs du thème One Piece
ROUGE = "#CC0000"
BLEU = "#003087"
BLEU_CLAIR = "#0055b3"
OR = "#FFD700"
FOND = "#0d0d0d"
FOND_CARTE = "#0a0a1a"


# ============================================================
# STYLE
# ============================================================

def apply_style():
    """Injecte du CSS personnalisé pour le thème One Piece."""
    st.markdown("""
        <style>
        .stApp {
            background-color: #0d0d0d;
        }
        h1 {
            color: #003087 !important;
            font-size: 2.5rem !important;
            text-align: center;
            text-shadow: 2px 2px 8px #CC0000;
            border-bottom: 3px solid #CC0000;
            padding-bottom: 16px;
        }
        h2, h3 {
            color: #003087 !important;
        }
        p, div {
            color: #f0f0f0;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #0a0a1a, #0d0d2a);
            border: 1px solid #003087;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        [data-testid="stMetricLabel"] {
            color: #0055b3 !important;
            font-size: 0.85rem !important;
        }
        [data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-size: 2rem !important;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #003087;
            border-radius: 8px;
        }
        hr {
            border-color: #CC0000;
        }
        </style>
    """, unsafe_allow_html=True)


# ============================================================
# DONNÉES
# ============================================================

@st.cache_data
def get_chapters():
    """Récupère les chapitres depuis BigQuery."""
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            CAST(chapter_number AS INT64) AS chapter_number,
            title,
            CAST(volume AS INT64) AS volume,
            published_at,
            scraped_at
        FROM `{TABLE_REF}`
        ORDER BY CAST(chapter_number AS INT64)
    """

    return client.query(query).to_dataframe()


# ============================================================
# GRAPHIQUES
# ============================================================

def chart_chapters_by_volume(df):
    """Graphique : nombre de chapitres par tome."""
    df_v = df[df["volume"].notna()]

    if df_v.empty:
        st.info("Pas assez de données pour ce graphique.")
        return

    counts = (
        df_v.groupby("volume")
        .size()
        .reset_index(name="chapitres")
        .sort_values("volume")
    )

    fig = px.bar(
        counts,
        x="volume",
        y="chapitres",
        title="Chapitres par tome",
        labels={"volume": "Tome", "chapitres": "Nb chapitres"},
        color_discrete_sequence=[BLEU_CLAIR],
    )
    fig.update_layout(
        plot_bgcolor=FOND_CARTE,
        paper_bgcolor=FOND,
        font_color="#f0f0f0",
        title_font_color=BLEU,
        bargap=0.1,
        xaxis=dict(
            showgrid=False,
            tickmode="linear",
            dtick=5,
        ),
        yaxis=dict(
            gridcolor="#1a1a2e",
        ),
    )
    fig.update_traces(
        marker_line_color=ROUGE,
        marker_line_width=0.5,
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_chapters_by_year(df):
    """Graphique : nombre de chapitres publiés par année."""
    df = df.copy()
    df["year"] = pd.to_datetime(df["published_at"]).dt.year

    counts = (
        df.groupby("year")
        .size()
        .reset_index(name="chapitres")
    )

    fig = px.line(
        counts,
        x="year",
        y="chapitres",
        title="Chapitres publiés par année",
        markers=True,
        labels={"year": "Année", "chapitres": "Nb chapitres"},
    )
    fig.update_traces(
        line_color=ROUGE,
        marker_color=BLEU_CLAIR,
        marker_size=10,
        fill="tozeroy",
        fillcolor="rgba(0, 48, 135, 0.15)",
    )
    fig.update_layout(
        plot_bgcolor=FOND_CARTE,
        paper_bgcolor=FOND,
        font_color="#f0f0f0",
        title_font_color=BLEU,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#1a1a2e"),
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_recent_chapters(df):
    """Tableau des 10 derniers chapitres publiés."""
    recent = (
        df.sort_values("chapter_number", ascending=False)
        .head(10)[["chapter_number", "title", "published_at"]]
        .rename(columns={
            "chapter_number": "Chapitre",
            "title": "Titre",
            "published_at": "Publié le",
        })
    )
    st.dataframe(recent, use_container_width=True, hide_index=True)


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    st.set_page_config(
        page_title="One Piece Dashboard",
        page_icon="🏴‍☠️",
        layout="wide",
    )

    apply_style()

    # Titre
    st.title("🏴‍☠️ One Piece — Dashboard")
    st.markdown(
        "<p style='text-align:center; color:#888;'>"
        "Statistiques des chapitres • Source : MangaDex API"
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Chargement
    with st.spinner("Chargement depuis BigQuery..."):
        df = get_chapters()

    if df.empty:
        st.error("Aucune donnée trouvée dans BigQuery.")
        return

    # Métriques
    st.subheader("📊 Vue générale")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Chapitres récupérés", len(df))
    with col2:
        st.metric("Premier chapitre", f"#{df['chapter_number'].min()}")
    with col3:
        st.metric("Dernier chapitre", f"#{df['chapter_number'].max()}")
    with col4:
        nb_volumes = int(df["volume"].notna().sum())
        st.metric("Chapitres avec tome", nb_volumes)

    st.markdown("---")

    # Graphiques côte à côte
    st.subheader("📈 Statistiques")
    col_left, col_right = st.columns(2)

    with col_left:
        chart_chapters_by_volume(df)

    with col_right:
        chart_chapters_by_year(df)

    st.markdown("---")

    # Derniers chapitres
    st.subheader("🆕 Derniers chapitres publiés")
    chart_recent_chapters(df)

    st.markdown("---")

    # Tableau complet
    st.subheader("📖 Tous les chapitres")
    st.dataframe(
        df[["chapter_number", "title", "volume", "published_at"]]
        .rename(columns={
            "chapter_number": "Chapitre",
            "title": "Titre",
            "volume": "Tome",
            "published_at": "Publié le",
        }),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
