import json
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from google.auth import default

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "t-lexicon-231513"
DATASET_ID = "onepiece"
TABLE_ID = "chapters"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
SPEAKERS_REF = f"{PROJECT_ID}.{DATASET_ID}.speakers"
CHAPTER_STATS_REF = f"{PROJECT_ID}.{DATASET_ID}.chapter_stats"
LUFFY_STATS_REF = f"{PROJECT_ID}.{DATASET_ID}.luffy_stats"

# Détecter l'environnement
IS_CLOUD_RUN = os.getenv("K_SERVICE") is not None

# Palette
OR        = "#E9A84C"
OR_PALE   = "#F4C87A"
TEAL      = "#0A774D"
TEAL2     = "#1A9E6A"
ROUGE     = "#C0392B"
OCEAN     = "#0B1D3A"
OCEAN2    = "#0D2545"
CIEL      = "#1B4F7A"
FOND      = "#070E1C"
TEXTE     = "#D4B896"

# Arcs narratifs One Piece
ARCS = [
    {"nom": "East Blue",         "debut": 1,    "fin": 100,  "saga": "East Blue"},
    {"nom": "Arabasta",          "debut": 101,  "fin": 216,  "saga": "Grand Line"},
    {"nom": "Skypiea",           "debut": 217,  "fin": 302,  "saga": "Grand Line"},
    {"nom": "Water Seven",       "debut": 303,  "fin": 441,  "saga": "Grand Line"},
    {"nom": "Thriller Bark",     "debut": 442,  "fin": 489,  "saga": "Grand Line"},
    {"nom": "Summit War",        "debut": 490,  "fin": 597,  "saga": "Grand Line"},
    {"nom": "Fish-Man Island",   "debut": 598,  "fin": 653,  "saga": "New World"},
    {"nom": "Dressrosa",         "debut": 654,  "fin": 801,  "saga": "New World"},
    {"nom": "Whole Cake Island", "debut": 802,  "fin": 902,  "saga": "New World"},
    {"nom": "Wano",              "debut": 903,  "fin": 1057, "saga": "New World"},
    {"nom": "Egghead",           "debut": 1058, "fin": 1172, "saga": "New World"},
]

SAGA_COLORS = {
    "East Blue": ROUGE,
    "Grand Line": CIEL,
    "New World": OR,
}


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

        h2, h3 {{
            font-family: 'Cinzel', serif !important;
            color: {OR_PALE} !important;
            font-weight: 700 !important;
            letter-spacing: 3px !important;
            font-size: 1rem !important;
            text-transform: uppercase !important;
            opacity: 0.9;
        }}

        p, div, span, label {{
            font-family: 'Lato', sans-serif !important;
            color: {TEXTE} !important;
        }}

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

        [data-testid="stDataFrame"] {{
            border: 1px solid rgba(233,168,76,0.2) !important;
            border-radius: 4px !important;
        }}

        [data-baseweb="input"] {{
            background: rgba(11,29,58,0.8) !important;
            border: 1px solid rgba(233,168,76,0.3) !important;
        }}
        [data-baseweb="input"] input {{
            color: {TEXTE} !important;
            font-family: 'Lato', sans-serif !important;
        }}

        ::-webkit-scrollbar {{ width: 4px; }}
        ::-webkit-scrollbar-track {{ background: {FOND}; }}
        ::-webkit-scrollbar-thumb {{ background: {OR}; border-radius: 2px; }}

        .stSpinner > div {{ border-top-color: {OR} !important; }}
        </style>
    """, unsafe_allow_html=True)


# ============================================================
# DONNÉES
# ============================================================

def query_with_cost_estimation(client, query_text, description="Query"):
    """
    Exécute une requête BigQuery avec estimation du volume scanné (dry run).

    IMPORTANT COÛT :
    - Le dry run (dry_run=True) est 100% GRATUIT selon Google Cloud
      (https://cloud.google.com/bigquery/docs/samples/bigquery-query-dry-run)
    - Seule la vraie requête (deuxième appel) est facturée normalement
    - Aucun risque de double facturation

    Retourne le job de requête BigQuery standard.
    Stocke l'estimation dans st.session_state pour affichage sidebar.
    """
    # Dry run pour estimer le coût sans exécuter ni facturer (GRATUIT)
    dry_run_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False
    )
    dry_run_job = client.query(query_text, job_config=dry_run_config)

    # Récupérer les bytes estimés
    bytes_processed = dry_run_job.total_bytes_processed
    mb_processed = bytes_processed / (1024 * 1024)

    # Logger pour debug
    print(f"[DRY RUN] {description}: {mb_processed:.2f} MB estimés")

    # Stocker dans session state pour affichage sidebar
    # (limite à 20 dernières entrées pour éviter fuite mémoire théorique)
    if "query_costs" not in st.session_state:
        st.session_state.query_costs = []
    st.session_state.query_costs.append({
        "query": description,
        "mb": mb_processed
    })
    st.session_state.query_costs = st.session_state.query_costs[-20:]

    # Exécuter la vraie requête (avec cache BigQuery normal si applicable)
    # C'est CE CALL qui est facturé, pas le dry run ci-dessus
    return client.query(query_text)


@st.cache_data
def get_chapters():
    """Lit la table brute chapters (pour scraped_at dans l'explorateur).

    ATTENTION BUG CONNU : Cette table contient des doublons (ex: chapitres 1, 2, 3
    apparaissent 3 fois suite à plusieurs runs de scraping non-idempotents).
    L'explorateur affichera donc des lignes en double. Ce bug sera corrigé côté
    scraper, pas ici. En attendant, chapter_stats déduplique ces données.
    """
    if IS_CLOUD_RUN:
        credentials, _ = default()
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
    else:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["gcp_service_account"]) if isinstance(st.secrets["gcp_service_account"], str) else dict(st.secrets["gcp_service_account"])
        )
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

    query = f"""
        SELECT
            CAST(chapter_number AS INT64) AS chapter_number,
            url, image_count, source, language, scraped_at
        FROM `{TABLE_REF}`
        ORDER BY CAST(chapter_number AS INT64)
    """
    return query_with_cost_estimation(
        client, query, "get_chapters()"
    ).to_dataframe()


@st.cache_data
def get_chapter_stats():
    """Lit la table agrégée chapter_stats (pré-calculée par Dataform)."""
    if IS_CLOUD_RUN:
        credentials, _ = default()
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
    else:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["gcp_service_account"]) if isinstance(st.secrets["gcp_service_account"], str) else dict(st.secrets["gcp_service_account"])
        )
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

    query = f"""
        SELECT
            chapter_number,
            image_count,
            tranche,
            tranche_moy,
            arc_name,
            arc_saga,
            rolling_mean_50,
            is_top10
        FROM `{CHAPTER_STATS_REF}`
        ORDER BY chapter_number
    """
    return query_with_cost_estimation(
        client, query, "get_chapter_stats()"
    ).to_dataframe()


@st.cache_data
def get_speakers():
    if IS_CLOUD_RUN:
        credentials, _ = default()
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
    else:
        # En local ou sur Streamlit Cloud, utiliser st.secrets
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["gcp_service_account"]) if isinstance(st.secrets["gcp_service_account"], str) else dict(st.secrets["gcp_service_account"])
        )
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

    query = f"""
        SELECT
            chapter_number,
            speaker,
            phrase,
            luffy_says_it,
            about_luffy
        FROM `{SPEAKERS_REF}`
        ORDER BY chapter_number
    """
    try:
        return query_with_cost_estimation(
            client, query, "get_speakers()"
        ).to_dataframe()
    except Exception:
        return pd.DataFrame()


@st.cache_data
def get_luffy_stats():
    """Lit la table agrégée luffy_stats (pré-calculée par Dataform)."""
    if IS_CLOUD_RUN:
        credentials, _ = default()
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
    else:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["gcp_service_account"]) if isinstance(st.secrets["gcp_service_account"], str) else dict(st.secrets["gcp_service_account"])
        )
        client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

    query = f"""
        SELECT
            chapter_number,
            total_mentions,
            luffy_mentions,
            about_luffy_mentions,
            other_mentions
        FROM `{LUFFY_STATS_REF}`
        ORDER BY chapter_number
    """
    try:
        return query_with_cost_estimation(
            client, query, "get_luffy_stats()"
        ).to_dataframe()
    except Exception:
        return pd.DataFrame()


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

    fig.add_trace(go.Scatter(
        x=df["chapter_number"],
        y=df["image_count"],
        mode="lines",
        name="Pages / chapitre",
        line=dict(color=CIEL, width=1, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(27,79,122,0.2)",
    ))

    fig.add_trace(go.Scatter(
        x=df["chapter_number"],
        y=df["rolling_mean_50"],
        mode="lines",
        name="Tendance (50 chap.)",
        line=dict(color=OR, width=2.5, shape="spline"),
    ))

    fig.update_layout(
        title="ÉVOLUTION DU NOMBRE DE PAGES PAR CHAPITRE",
        **LAYOUT,
        height=320,
        xaxis_title="Numéro de chapitre",
        yaxis_title="Nombre de pages",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_arcs(df):
    """Utilise arc_name et arc_saga pré-calculés dans chapter_stats."""
    # Compter par arc_name (déjà calculé dans chapter_stats)
    arc_counts = df.groupby('arc_name').size().reset_index(name='chapitres')

    # Enrichir avec saga et label depuis ARCS (pour le hover et les couleurs)
    arc_lookup = {arc["nom"]: {"saga": arc["saga"], "label": f"{arc['debut']}–{arc['fin']}"} for arc in ARCS}
    arc_counts["saga"] = arc_counts["arc_name"].map(lambda x: arc_lookup.get(x, {}).get("saga"))
    arc_counts["label"] = arc_counts["arc_name"].map(lambda x: arc_lookup.get(x, {}).get("label"))

    # Préserver l'ordre chronologique de ARCS (pas alphabétique)
    arc_order_df = pd.DataFrame({"arc_name": [arc["nom"] for arc in ARCS]})
    arc_counts = arc_order_df.merge(arc_counts, on="arc_name", how="inner")

    df_arcs = arc_counts.rename(columns={"arc_name": "nom"})

    fig = go.Figure()

    # Une trace par saga pour avoir une légende propre
    for saga, color in SAGA_COLORS.items():
        mask = df_arcs["saga"] == saga
        fig.add_trace(go.Bar(
            x=df_arcs[mask]["nom"],
            y=df_arcs[mask]["chapitres"],
            name=saga,
            marker=dict(color=color, opacity=0.85),
            text=df_arcs[mask]["chapitres"].apply(lambda x: f"{x} chap."),
            textposition="outside",
            textfont=dict(color=OR_PALE, size=10),
            customdata=df_arcs[mask]["label"],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Chapitres : %{customdata}<br>"
                "Total : %{y}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title="NOMBRE DE CHAPITRES PAR ARC NARRATIF",
        plot_bgcolor="rgba(7,14,28,0.0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Lato, sans-serif", color=TEXTE, size=12),
        title_font=dict(family="Cinzel, serif", color=OR_PALE, size=14),
        xaxis=dict(showgrid=False, color=TEXTE, linecolor="rgba(233,168,76,0.2)", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(233,168,76,0.06)", color=TEXTE, linecolor="rgba(233,168,76,0.2)", tickfont=dict(size=11)),
        legend=dict(bgcolor="rgba(7,14,28,0.7)", bordercolor="rgba(233,168,76,0.2)", borderwidth=1, font=dict(color=TEXTE)),
        height=400,
        margin=dict(t=80, b=30, l=10, r=10),
        xaxis_title="Arc narratif",
        yaxis_title="Nombre de chapitres",
        barmode="overlay",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_tranches(df):
    """Utilise les données pré-agrégées de chapter_stats."""
    # Prendre les valeurs uniques tranche + tranche_moy
    moy = df[["tranche", "tranche_moy"]].drop_duplicates().sort_values("tranche")
    moy["label"] = moy["tranche"].apply(lambda x: f"{x}–{x+99}")
    moy = moy.rename(columns={"tranche_moy": "moy"})

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
        title="MOYENNE DE PAGES PAR TRANCHE DE 100 CHAPITRES",
        plot_bgcolor="rgba(7,14,28,0.0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Lato, sans-serif", color=TEXTE, size=12),
        title_font=dict(family="Cinzel, serif", color=OR_PALE, size=14),
        xaxis=dict(showgrid=False, color=TEXTE, linecolor="rgba(233,168,76,0.2)", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(233,168,76,0.06)", color=TEXTE, linecolor="rgba(233,168,76,0.2)", tickfont=dict(size=11)),
        legend=dict(bgcolor="rgba(7,14,28,0.7)", bordercolor="rgba(233,168,76,0.2)", borderwidth=1, font=dict(color=TEXTE)),
        height=400,
        margin=dict(t=80, b=30, l=10, r=10),
        xaxis_title="Tranche de chapitres",
        yaxis_title="Moyenne de pages",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_top10(df):
    """Utilise le flag is_top10 de chapter_stats."""
    top = df[df["is_top10"]].copy()
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
        xaxis_title="Nombre de pages",
    )
    fig.update_xaxes(showgrid=False, showticklabels=False)
    st.plotly_chart(fig, use_container_width=True)


def chart_roi_par_chapitre(df_stats):
    """Utilise luffy_stats pré-agrégé."""
    par_chapitre = df_stats[["chapter_number", "total_mentions"]].rename(
        columns={"total_mentions": "occurrences"}
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=par_chapitre["chapter_number"],
        y=par_chapitre["occurrences"],
        marker=dict(color=OR, opacity=0.85),
        name="Occurrences",
    ))
    fig.update_layout(
        title='OCCURRENCES DE "ROI DES PIRATES" PAR CHAPITRE',
        **LAYOUT,
        height=300,
        xaxis_title="Numéro de chapitre",
        yaxis_title="Nombre de mentions",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_luffy_vs_autres(df_stats):
    """Utilise luffy_stats pré-agrégé."""
    luffy = df_stats["luffy_mentions"].sum()
    autres = df_stats["about_luffy_mentions"].sum()
    reste = df_stats["other_mentions"].sum()

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=["Luffy le dit", "Quelqu'un parle de Luffy", "Autre contexte"],
        values=[luffy, autres, reste],
        marker=dict(colors=[OR, TEAL2, CIEL]),
        textfont=dict(color=FOND, family="Cinzel"),
        hole=0.4,
    ))
    fig.update_layout(
        title='QUI MENTIONNE "ROI DES PIRATES" ?',
        **LAYOUT,
        height=300,
    )
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

    with st.spinner("Navigation vers les données..."):
        df = get_chapter_stats()
        df_chapters_raw = get_chapters()  # pour scraped_at dans l'explorateur
        df_luffy_stats = get_luffy_stats()
        df_speakers = get_speakers()

    if df.empty:
        st.error("Aucune donnée trouvée dans BigQuery.")
        return

    total_chapitres = len(df)
    st.title("ONE PIECE")
    st.markdown(
        f"<p style='text-align:center; color:{TEAL2}; "
        f"letter-spacing:5px; font-size:0.75rem; "
        f"font-family:Cinzel,serif; margin-top:-8px;'>"
        f"DATA PIPELINE &nbsp;•&nbsp; {total_chapitres} CHAPITRES "
        f"&nbsp;•&nbsp; VF &nbsp;•&nbsp; v2"
        f"</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Métriques — 3 colonnes ─────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Chapitres", f"{len(df):,}")
    with c2:
        st.metric("Moy. pages / chapitre", f"{df['image_count'].mean():.1f}")
    with c3:
        st.metric("Total pages scrapées", f"{df['image_count'].sum():,}")

    st.markdown("---")

    # ── Évolution ──────────────────────────────────────────
    chart_evolution(df)

    st.markdown("---")

    # ── Arcs narratifs + Moyenne par tranche ───────────────
    col1, col2 = st.columns(2)
    with col1:
        chart_arcs(df)
    with col2:
        chart_tranches(df)

    st.markdown("---")

    # ── Top 10 ─────────────────────────────────────────────
    chart_top10(df)

    st.markdown("---")

    # ── Roi des Pirates ────────────────────────────────────
    st.subheader("🏴‍☠️ Roi des Pirates")

    if df_luffy_stats.empty:
        st.info(
            "L'analyse NLP est en cours de traitement. "
            "Les statistiques apparaîtront ici automatiquement."
        )
    else:
        luffy_count = df_luffy_stats["luffy_mentions"].sum()
        about_count = df_luffy_stats["about_luffy_mentions"].sum()
        total = df_luffy_stats["total_mentions"].sum()

        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric("Total mentions", f"{total:,}")
        with r2:
            st.metric("Luffy le dit", f"{luffy_count:,}")
        with r3:
            st.metric("Parlent de Luffy", f"{about_count:,}")

        col1, col2 = st.columns(2)
        with col1:
            chart_roi_par_chapitre(df_luffy_stats)
        with col2:
            chart_luffy_vs_autres(df_luffy_stats)

        st.markdown("---")
        st.subheader("Exemples de phrases de Luffy")
        exemples = (
            df_speakers[df_speakers["luffy_says_it"]][
                ["chapter_number", "phrase"]
            ]
            .drop_duplicates()
            .head(10)
            .rename(columns={
                "chapter_number": "Chapitre",
                "phrase": "Phrase",
            })
        )
        st.dataframe(exemples, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Explorateur ────────────────────────────────────────
    st.subheader("Explorer les chapitres")
    c_min, c_max = st.columns(2)
    with c_min:
        mn = st.number_input("De", 1, int(df["chapter_number"].max()), 1)
    with c_max:
        mx = st.number_input("À", 1, int(df["chapter_number"].max()), 100)

    # ATTENTION : df_chapters_raw contient des doublons (bug scraper non-idempotent)
    # donc l'explorateur affichera des lignes en double pour certains chapitres
    filtered = df_chapters_raw[
        (df_chapters_raw["chapter_number"] >= mn) &
        (df_chapters_raw["chapter_number"] <= mx)
    ][["chapter_number", "image_count", "scraped_at"]].rename(columns={
        "chapter_number": "Chapitre",
        "image_count": "Pages",
        "scraped_at": "Récupéré le",
    })

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    # ── Coûts BigQuery ────────────────────────────────────────
    if "query_costs" in st.session_state and st.session_state.query_costs:
        with st.sidebar:
            with st.expander("📊 Coûts BigQuery estimés", expanded=False):
                total_mb = sum(q["mb"] for q in st.session_state.query_costs)
                st.caption(f"**Volume total scanné :** {total_mb:.2f} MB")
                for q in st.session_state.query_costs:
                    st.caption(f"• {q['query']}: {q['mb']:.2f} MB")


if __name__ == "__main__":
    main()