import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "onepiece-pipeline"
DATASET_ID = "onepiece"
TABLE_ID = "chapters"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# Palette — coucher de soleil sur l'océan
OR        = "#E9A84C"   # Or chaud sunset
OR_PALE   = "#F4C87A"   # Or pâle
TEAL      = "#0A774D"   # Teal océan profond
TEAL2     = "#1A9E6A"   # Teal clair
ROUGE     = "#C0392B"   # Rouge sang de pirate
OCEAN     = "#0B1D3A"   # Bleu océan profond
OCEAN2    = "#0D2545"   # Bleu nuit
CIEL      = "#1B4F7A"   # Bleu ciel horizon
FOND      = "#070E1C"   # Fond ultra sombre
TEXTE     = "#D4B896"   # Beige parchemin


# ============================================================
# STYLE
# ============================================================

def apply_style():
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Lato:wght@300;400;700&display=swap');

        .stApp {{
            background: radial-gradient(ellipse at top, {OCEAN2} 0%, {FOND} 60%);
            background-attachment: fixed;
        }}

        /* Titre */
        h1 {{
            font-family: 'Cinzel', serif !important;
            color: {OR} !important;
            font-size: 3rem !important;
            text-align: center !important;
            letter-spacing: 8px !important;
            font-weight: 900 !important;
            text-shadow:
                0 0 30px rgba(233,168,76,0.4),
                0 2px 4px rgba(0,0,0,0.8);
            padding: 16px 0 8px 0 !important;
            border: none !important;
        }}

        /* Sous-titres */
        h2, h3 {{
            font-family: 'Cinzel', serif !important;
            color: {OR_PALE} !important;
            font-weight: 700 !important;
            letter-spacing: 3px !important;
            font-size: 1rem !important;
            text-transform: uppercase !important;
            opacity: 0.9;
        }}

        /* Texte général */
        p, div, span, label {{
            font-family: 'Lato', sans-serif !important;
            color: {TEXTE} !important;
        }}

        /* Séparateur */
        hr {{
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg,
                transparent 0%,
                {TEAL} 20%,
                {OR} 50%,
                {TEAL} 80%,
                transparent 100%) !important;
            opacity: 0.5;
            margin: 28px 0 !important;
        }}

        /* Métriques */
        [data-testid="stMetric"] {{
            background: linear-gradient(145deg,
                rgba(11,29,58,0.9),
                rgba(13,37,69,0.6));
            border: 1px solid rgba(233,168,76,0.15);
            border-bottom: 2px solid {OR};
            border-radius: 4px;
            padding: 24px 16px !important;
            text-align: center !important;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }}

        [data-testid="stMetric"]:hover {{
            border-bottom-color: {TEAL2};
            background: linear-gradient(145deg,
                rgba(10,119,77,0.15),
                rgba(13,37,69,0.8));
            transform: translateY(-3px);
        }}

        [data-testid="stMetricLabel"] p {{
            color: {OR} !important;
            font-size: 0.7rem !important;
            letter-spacing: 3px !important;
            text-transform: uppercase !important;
            font-weight: 700 !important;
        }}

        [data-testid="stMetricValue"] {{
            color: #ffffff !important;
            font-family: 'Cinzel', serif !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
        }}

        /* Tableau */
        [data-testid="stDataFrame"] {{
            border: 1px solid rgba(233,168,76,0.2) !important;
            border-radius: 4px !important;
        }}

        /* Inputs */
        [data-baseweb="input"] {{
            background: rgba(11,29,58,0.8) !important;
            border: 1px solid rgba(233,168,76,0.3) !important;
        }}
        [data-baseweb="input"] input {{
            color: {TEXTE} !important;
            font-family: 'Lato', sans-serif !important;
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 4px; }}
        ::-webkit-scrollbar-track {{ background: {FOND}; }}
        ::-webkit-scrollbar-thumb {{ background: {OR}; border-radius: 2px; }}

        /* Spinner */
        .stSpinner > div {{ border-top-color: {OR} !important; }}
        </style>
    """, unsafe_allow_html=True)


# ============================================================
# DONNÉES
# ============================================================

@st.cache_data
def get_chapters():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT
            CAST(chapter_number AS INT64) AS chapter_number,
            url, image_count, source, language, scraped_at
        FROM `{TABLE_REF}`
        ORDER BY CAST(chapter_number AS INT64)
    """
    return client.query(query).to_dataframe()


# ============================================================
# GRAPHIQUES
# ============================================================

LAYOUT = dict(
    plot_bgcolor="rgba(7,14,28,0.0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Lato, sans-serif", color=TEXTE, size=12),
    title_font=dict(family="Cinzel, serif", color=OR_PALE, size=14),
    xaxis=dict(
        showgrid=False,
        color=TEXTE,
        linecolor="rgba(233,168,76,0.2)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        gridcolor="rgba(233,168,76,0.06)",
        color=TEXTE,
        linecolor="rgba(233,168,76,0.2)",
        tickfont=dict(size=11),
    ),
    margin=dict(t=50, b=30, l=10, r=10),
    legend=dict(
        bgcolor="rgba(7,14,28,0.7)",
        bordercolor="rgba(233,168,76,0.2)",
        borderwidth=1,
        font=dict(color=TEXTE),
    ),
)


def chart_evolution(df):
    fig = go.Figure()

    # Zone remplie
    fig.add_trace(go.Scatter(
        x=df["chapter_number"],
        y=df["image_count"],
        mode="lines",
        name="Pages / chapitre",
        line=dict(color=CIEL, width=1, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(27,79,122,0.2)",
    ))

    # Moyenne mobile 50
    rolling = df["image_count"].rolling(50, center=True).mean()
    fig.add_trace(go.Scatter(
        x=df["chapter_number"],
        y=rolling,
        mode="lines",
        name="Tendance (50 chap.)",
        line=dict(color=OR, width=2.5, shape="spline"),
    ))

    fig.update_layout(
        title="ÉVOLUTION DU NOMBRE DE PAGES",
        **LAYOUT,
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_distribution(df):
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["image_count"],
        nbinsx=28,
        name="Chapitres",
        marker=dict(
            color=TEAL,
            opacity=0.85,
            line=dict(color=TEAL2, width=0.5),
        ),
    ))
    fig.update_layout(
        title="DISTRIBUTION DES PAGES",
        **LAYOUT,
        height=280,
        bargap=0.05,
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_tranches(df):
    df = df.copy()
    df["tranche"] = (df["chapter_number"] // 100) * 100
    moy = (
        df.groupby("tranche")["image_count"]
        .mean().round(1).reset_index()
        .rename(columns={"image_count": "moy"})
    )
    moy["label"] = moy["tranche"].apply(lambda x: f"{x}–{x+99}")

    colors = [OR if v == moy["moy"].max() else CIEL for v in moy["moy"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=moy["label"],
        y=moy["moy"],
        marker=dict(color=colors, opacity=0.9),
        text=moy["moy"],
        textposition="outside",
        textfont=dict(color=OR_PALE, size=10),
    ))
    fig.update_layout(
        title="MOYENNE PAR TRANCHE DE 100 CHAPITRES",
        **LAYOUT,
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_top10(df):
    top = df.nlargest(10, "image_count").copy()
    top = top.sort_values("image_count")
    top["label"] = top["chapter_number"].apply(lambda x: f"Chapitre {x}")

    colors = [
        f"rgba(233,168,76,{0.5 + i*0.05})"
        for i in range(len(top))
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top["image_count"],
        y=top["label"],
        orientation="h",
        marker=dict(color=colors),
        text=top["image_count"].apply(lambda x: f"{x} pages"),
        textposition="inside",
        textfont=dict(color=FOND, size=11, family="Cinzel"),
    ))
    fig.update_layout(
        title="TOP 10 — CHAPITRES LES PLUS LONGS",
        **LAYOUT,
        height=340,
    )
    fig.update_xaxes(showgrid=False, showticklabels=False)
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    st.set_page_config(
        page_title="One Piece — Data Pipeline",
        page_icon="🏴‍☠️",
        layout="wide",
    )

    apply_style()

    # Header
    st.title("ONE PIECE")
    st.markdown(
        f"<p style='text-align:center; color:{TEAL2}; "
        f"letter-spacing:5px; font-size:0.75rem; "
        f"font-family:Cinzel,serif; margin-top:-8px;'>"
        f"DATA PIPELINE &nbsp;•&nbsp; 1172 CHAPITRES &nbsp;•&nbsp; VF"
        f"</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    with st.spinner("Navigation vers les données..."):
        df = get_chapters()

    if df.empty:
        st.error("Aucune donnée trouvée dans BigQuery.")
        return

    # ── Métriques ──────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Chapitres", f"{len(df):,}")
    with c2:
        st.metric("Premier", f"# {df['chapter_number'].min()}")
    with c3:
        st.metric("Dernier", f"# {df['chapter_number'].max()}")
    with c4:
        st.metric("Moy. pages", f"{df['image_count'].mean():.1f}")
    with c5:
        st.metric("Total pages", f"{df['image_count'].sum():,}")

    st.markdown("---")

    # ── Graphique principal ─────────────────────────────────
    chart_evolution(df)

    st.markdown("---")

    # ── Graphiques secondaires ──────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        chart_distribution(df)
    with col2:
        chart_tranches(df)

    st.markdown("---")

    # ── Top 10 ─────────────────────────────────────────────
    chart_top10(df)

    st.markdown("---")

    # ── Explorateur ────────────────────────────────────────
    st.subheader("Explorer")
    c_min, c_max = st.columns(2)
    with c_min:
        mn = st.number_input("De", 1, int(df["chapter_number"].max()), 1)
    with c_max:
        mx = st.number_input("À", 1, int(df["chapter_number"].max()), 100)

    filtered = df[
        (df["chapter_number"] >= mn) &
        (df["chapter_number"] <= mx)
    ][["chapter_number", "image_count", "scraped_at"]].rename(columns={
        "chapter_number": "Chapitre",
        "image_count": "Pages",
        "scraped_at": "Récupéré le",
    })

    st.dataframe(filtered, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
