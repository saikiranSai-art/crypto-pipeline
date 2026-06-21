import os
import sys
import glob
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text

# Add current folder to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src import config
from src.main import run_pipeline
from src.ml_model import predict_latest_direction, train_ml_model, MODEL_PATH

# ----------------- STREAMLIT CONFIG -----------------
st.set_page_config(
    page_title="Crypto Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set custom styling (Premium dark glassmorphism aesthetic)
st.markdown("""
    <style>
        /* Main background */
        .main {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        /* Style headers */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            font-weight: 700;
        }
        /* Custom card container */
        .metric-card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.2);
            text-align: center;
        }
        .metric-card h4 {
            margin: 0 0 10px 0;
            color: #8C96A0;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .metric-card p {
            margin: 0;
            font-size: 1.8rem;
            font-weight: bold;
        }
        .metric-card .change {
            font-size: 0.9rem;
            margin-top: 5px;
        }
        .up { color: #00E676; }
        .down { color: #FF1744; }
        .neutral { color: #FFC400; }
        
        /* Glassmorphism sidebar */
        section[data-testid="stSidebar"] {
            background-color: #161920 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        /* Status Badges */
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-block;
            margin-bottom: 20px;
        }
        .db-active {
            background-color: rgba(0, 230, 118, 0.15);
            color: #00E676;
            border: 1px solid #00E676;
        }
        .db-fallback {
            background-color: rgba(255, 196, 0, 0.15);
            color: #FFD600;
            border: 1px solid #FFD600;
        }
    </style>
""", unsafe_allow_html=True)

# Set Seaborn / Matplotlib styling
sns.set_theme(style="dark", palette="muted")
plt.rcParams.update({
    'grid.color': '#2B303C',
    'axes.facecolor': '#161920',
    'figure.facecolor': '#0E1117',
    'text.color': '#FAFAFA',
    'axes.labelcolor': '#FAFAFA',
    'xtick.color': '#A0AAB4',
    'ytick.color': '#A0AAB4',
    'axes.edgecolor': '#2B303C'
})

# ----------------- DATABASE UTILITIES -----------------
@st.cache_resource
def get_db_engine():
    """
    Returns connection engine.
    """
    try:
        engine = create_engine(config.get_db_uri())
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        return None

def fetch_data_from_db():
    """
    Retrieves all records from the fact and dim tables.
    """
    engine = get_db_engine()
    if engine is None:
        return None
        
    try:
        query = """
            SELECT 
                f.*, 
                d.symbol, 
                d.name, 
                d.market_cap_rank
            FROM fact_market_snapshot f
            JOIN dim_coin d ON f.coin_id = d.coin_id
            ORDER BY f.extracted_at DESC, d.market_cap_rank ASC
        """
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.warning(f"Error fetching data from MySQL: {e}")
        return None

def fetch_logs_from_db():
    """
    Retrieves ETL run logs.
    """
    engine = get_db_engine()
    if engine is None:
        return None
    try:
        df = pd.read_sql("SELECT * FROM etl_run_log ORDER BY run_timestamp DESC LIMIT 50", engine)
        return df
    except Exception as e:
        return None

# ----------------- LOCAL FILE FALLBACK -----------------
def fetch_data_from_files():
    """
    Fallback method to read all processed CSV files in data/processed/.
    """
    search_path = str(config.PROCESSED_DATA_DIR / "markets_processed_*.csv")
    files = glob.glob(search_path)
    
    if not files:
        latest = config.PROCESSED_DATA_DIR / "latest.csv"
        if latest.exists():
            files = [str(latest)]
        else:
            return None
            
    dfs = []
    for file in files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
        except Exception:
            pass
            
    if not dfs:
        return None
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df['extracted_at'] = pd.to_datetime(full_df['extracted_at'])
    full_df = full_df.sort_values(by=['extracted_at', 'market_cap_rank'], ascending=[False, True])
    return full_df

# ----------------- MAIN INTERFACE -----------------

# Header Section
st.title("📊 Crypto Market Intelligence Dashboard")
st.subheader("MADSC301 Business Intelligence Final Assignment ETL/ELT Pipeline")

# Load Data
df = fetch_data_from_db()
is_db_active = True

if df is None or len(df) == 0:
    is_db_active = False
    df = fetch_data_from_files()

# Display Connection Status
if is_db_active:
    st.markdown('<div class="status-badge db-active">🟢 Connected to MySQL Database (Live SQL Mode)</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-badge db-fallback">🟡 Database Offline (Fallback Mode: Loaded from Local Processed Files)</div>', unsafe_allow_html=True)

if df is None or len(df) == 0:
    st.error("No data available! Please trigger the ETL pipeline from the sidebar to extract and transform the data first.")
    
    if st.sidebar.button("🚀 Run ETL Pipeline"):
        with st.spinner("Executing ETL Pipeline (Extracting, Transforming, Loading)..."):
            try:
                run_pipeline()
                st.success("ETL Pipeline executed successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Pipeline failed: {e}")
    st.stop()

# Ensure types are correct
df['snapshot_date'] = pd.to_datetime(df['snapshot_date']).dt.date
df['extracted_at'] = pd.to_datetime(df['extracted_at'])

# ----------------- SIDEBAR -----------------
st.sidebar.header("Pipeline Control Center")

# Run ETL Button
if st.sidebar.button("🔄 Execute ETL Pipeline"):
    with st.spinner("Running ETL Pipeline..."):
        try:
            # We run it in a subprocess or call run_pipeline directly
            run_pipeline()
            st.sidebar.success("ETL Execution Success!")
            st.cache_resource.clear()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Pipeline run failed: {e}")

# Filters
st.sidebar.subheader("Dashboard Filters")

# Unique timestamps available
timestamps = sorted(df['extracted_at'].unique(), reverse=True)
latest_ts = timestamps[0]

selected_ts = st.sidebar.selectbox(
    "Snapshot Timestamp",
    options=timestamps,
    format_func=lambda x: x.strftime("%Y-%m-%d %H:%M:%S")
)

# Filter dataframe for selected snapshot
snap_df = df[df['extracted_at'] == selected_ts].copy()

# Category Filter
categories = ["All"] + list(snap_df['market_cap_category'].unique())
selected_cat = st.sidebar.selectbox("Market Cap Bracket", categories)
if selected_cat != "All":
    snap_df = snap_df[snap_df['market_cap_category'] == selected_cat]

# Coin Selector (for detailed historical analysis)
unique_coins = sorted(df['name'].unique())
selected_coin_name = st.sidebar.selectbox("Select Asset for Historical Charts", unique_coins)

# ----------------- TABS -----------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Market Overview", "🔬 Asset Deep Dive", "🤖 Machine Learning Predictions", "📋 ETL Operation Logs"])

# ----------------- TAB 1: MARKET OVERVIEW -----------------
with tab1:
    # KPI metrics calculation
    global_cap = snap_df['market_cap_usd'].sum()
    total_volume = snap_df['total_volume_usd'].sum()
    
    # Top gainer
    gainer_idx = snap_df['price_change_percentage_24h'].idxmax()
    top_gainer = snap_df.loc[gainer_idx]
    
    # Top loser
    loser_idx = snap_df['price_change_percentage_24h'].idxmin()
    top_loser = snap_df.loc[loser_idx]
    
    # Display KPIs in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <h4>Global Market Cap (Selected Category)</h4>
                <p>${global_cap:,.0f}</p>
                <div class="change neutral">Total volume: ${total_volume:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <h4>Top Gainer (24h)</h4>
                <p class="up">{top_gainer['symbol']}</p>
                <div class="change up">+{top_gainer['price_change_percentage_24h']:.2f}% (${top_gainer['current_price_usd']:,.2f})</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <h4>Top Loser (24h)</h4>
                <p class="down">{top_loser['symbol']}</p>
                <div class="change down">{top_loser['price_change_percentage_24h']:.2f}% (${top_loser['current_price_usd']:,.2f})</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col4:
        # Average Volatility
        avg_vol = snap_df['volatility_24h'].mean()
        st.markdown(f"""
            <div class="metric-card">
                <h4>Avg 24h Volatility</h4>
                <p>{avg_vol:.2f}%</p>
                <div class="change neutral">Calculated daily range bands</div>
            </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    # Charts Section
    st.subheader("📊 Market Analysis Visualizations")
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Top 10 Gainers & Losers Horizontal Bar Chart
        st.write("**Top 10 Performers (Price Change %)**")
        
        top_10_gainers = snap_df.sort_values(by='price_change_percentage_24h', ascending=False).head(5)
        top_10_losers = snap_df.sort_values(by='price_change_percentage_24h', ascending=True).head(5)
        performers = pd.concat([top_10_gainers, top_10_losers]).sort_values(by='price_change_percentage_24h')
        
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ['#FF1744' if x < 0 else '#00E676' for x in performers['price_change_percentage_24h']]
        
        bars = ax.barh(performers['symbol'], performers['price_change_percentage_24h'], color=colors, edgecolor='none')
        ax.axvline(0, color='#FAFAFA', linewidth=0.8, linestyle='--')
        
        # Add labels to bars
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + (1.0 if width >= 0 else -6.0),
                bar.get_y() + bar.get_height()/2,
                f'{width:+.2f}%',
                va='center', ha='left' if width >= 0 else 'right',
                color='#FAFAFA', fontsize=9, fontweight='bold'
            )
            
        ax.set_xlabel('24h Price Change Percentage (%)')
        plt.tight_layout()
        st.pyplot(fig)
        
    with col_right:
        # Volatility vs Liquidity Scatter plot
        st.write("**Asset Volatility vs. Liquidity Analysis**")
        
        fig, ax = plt.subplots(figsize=(10, 5))
        # Group by market cap category for coloring
        sns.scatterplot(
            data=snap_df,
            x="volume_to_market_cap_ratio",
            y="volatility_24h",
            hue="market_cap_category",
            palette={"Large Cap": "#00E676", "Mid Cap": "#00B0FF", "Small Cap": "#E040FB"},
            alpha=0.8,
            s=80,
            ax=ax
        )
        ax.set_xlabel("Volume-to-Market-Cap Ratio (Liquidity)")
        ax.set_ylabel("Volatility Index (%)")
        ax.legend(title="Market Cap Brackets")
        
        # Annotate top 3 volatile coins
        top_vol_coins = snap_df.nlargest(3, 'volatility_24h')
        for _, row in top_vol_coins.iterrows():
            ax.annotate(
                row['symbol'], 
                (row['volume_to_market_cap_ratio'], row['volatility_24h']),
                textcoords="offset points", 
                xytext=(5,5), 
                ha='left',
                fontsize=8,
                weight='bold',
                color='#FFC400'
            )
            
        plt.tight_layout()
        st.pyplot(fig)
        
    # Bottom Layout
    col_bot1, col_bot2 = st.columns([1, 2])
    with col_bot1:
        st.write("**Market Capitalization Category Share**")
        cat_counts = snap_df['market_cap_category'].value_counts()
        fig, ax = plt.subplots(figsize=(5, 5))
        colors_pie = ['#00E676', '#00B0FF', '#E040FB']
        ax.pie(
            cat_counts, 
            labels=cat_counts.index, 
            autopct='%1.1f%%', 
            colors=colors_pie[:len(cat_counts)], 
            textprops={'color': '#FAFAFA', 'weight': 'bold'},
            wedgeprops={'edgecolor': '#0E1117', 'linewidth': 2}
        )
        # Donut chart
        centre_circle = plt.Circle((0,0),0.70,fc='#0E1117')
        fig.gca().add_artist(centre_circle)
        plt.tight_layout()
        st.pyplot(fig)
        
    with col_bot2:
        st.write("**Top 10 Assets Pricing Table**")
        display_cols = [
            'market_cap_rank', 'name', 'symbol', 'current_price_usd', 
            'market_cap_usd', 'price_change_percentage_24h', 
            'volatility_24h', 'price_direction'
        ]
        grid_df = snap_df[display_cols].sort_values(by='market_cap_rank').head(10)
        grid_df.columns = [
            'Rank', 'Name', 'Symbol', 'Price (USD)', 
            'Market Cap (USD)', '24h Change (%)', 
            'Volatility (%)', 'Direction'
        ]
        st.dataframe(grid_df.style.format({
            'Price (USD)': '${:,.2f}',
            'Market Cap (USD)': '${:,.0f}',
            '24h Change (%)': '{:+.2f}%',
            'Volatility (%)': '{:.2f}%'
        }), hide_index=True, use_container_width=True)

# ----------------- TAB 2: ASSET DEEP DIVE -----------------
with tab2:
    st.subheader(f"🔍 Historical Performance of {selected_coin_name}")
    
    # Filter historical records for selected coin
    coin_df = df[df['name'] == selected_coin_name].copy().sort_values(by='extracted_at')
    
    if len(coin_df) < 2:
        st.info("Historical data is built over time as snapshots accumulate. Run the ETL pipeline on a schedule to build rich time-series data! Displaying single snapshot metrics below:")
        st.json(coin_df.iloc[0].to_dict())
    else:
        col_dive1, col_dive2 = st.columns(2)
        
        with col_dive1:
            st.write("**Price History Trend (USD)**")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(coin_df['extracted_at'], coin_df['current_price_usd'], marker='o', color='#00B0FF', linewidth=2)
            ax.fill_between(coin_df['extracted_at'], coin_df['current_price_usd'], color='#00B0FF', alpha=0.1)
            ax.set_ylabel("Price (USD)")
            ax.set_xlabel("Time of Extraction")
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
        with col_dive2:
            st.write("**Market Cap Rank History**")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(coin_df['extracted_at'], coin_df['market_cap_rank'], marker='s', color='#E040FB', linewidth=2)
            ax.set_ylabel("Rank (Lower is Better)")
            ax.set_xlabel("Time of Extraction")
            ax.invert_yaxis()  # Rank 1 is top
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)
            
        st.write("**Historical Metrics Log**")
        history_table = coin_df[[
            'extracted_at', 'current_price_usd', 'market_cap_usd', 
            'total_volume_usd', 'price_change_percentage_24h', 'volatility_24h'
        ]].sort_values(by='extracted_at', ascending=False)
        
        history_table.columns = ['Timestamp', 'Price (USD)', 'Market Cap (USD)', 'Volume (USD)', '24h Change (%)', 'Volatility (%)']
        st.dataframe(history_table.style.format({
            'Price (USD)': '${:,.2f}',
            'Market Cap (USD)': '${:,.0f}',
            'Volume (USD)': '${:,.0f}',
            '24h Change (%)': '{:+.2f}%',
            'Volatility (%)': '{:.2f}%'
        }), hide_index=True, use_container_width=True)

# ----------------- TAB 3: MACHINE LEARNING -----------------
with tab3:
    st.subheader("🤖 Machine Learning Price Direction Predictor")
    st.write(
        "Using a **Random Forest Classifier** trained on calculated technical features "
        "(rank, price, volume, volatility index, and liquidity ratio), we predict the price direction for the next snapshot."
    )
    
    # Load or train model
    model_trained = os.path.exists(MODEL_PATH)
    
    if not model_trained:
        st.warning("No trained Random Forest model found on disk.")
        if st.button("🚀 Train Model Now"):
            with st.spinner("Training Random Forest model on historical data..."):
                try:
                    res = train_ml_model()
                    st.success(f"Model trained successfully! Test Accuracy: {res['accuracy']:.2%}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to train model: {e}")
    else:
        # Run predictions on current snapshot
        predicted_df = predict_latest_direction(snap_df)
        
        col_ml1, col_ml2 = st.columns([2, 1])
        
        with col_ml1:
            st.write("**Live Price Predictions vs. Actual (Top 15 Assets)**")
            
            ml_display_df = predicted_df[[
                'market_cap_rank', 'name', 'symbol', 'price_change_percentage_24h',
                'price_direction', 'predicted_direction'
            ]].sort_values(by='market_cap_rank').head(15)
            
            ml_display_df.columns = ['Rank', 'Name', 'Symbol', '24h Change (%)', 'Actual Direction', 'ML Predicted Direction']
            
            # Highlight correct predictions
            def highlight_predictions(row):
                actual = row['Actual Direction']
                pred = row['ML Predicted Direction']
                
                # Default style
                color_act = 'color: #FAFAFA'
                color_pred = 'color: #FAFAFA'
                
                if actual == 'Up': color_act = 'color: #00E676; font-weight: bold;'
                elif actual == 'Down': color_act = 'color: #FF1744; font-weight: bold;'
                
                if pred == 'Up': color_pred = 'color: #00E676; font-weight: bold;'
                elif pred == 'Down': color_pred = 'color: #FF1744; font-weight: bold;'
                
                # Highlight green if match, red if wrong
                bg = 'background-color: rgba(0, 230, 118, 0.08)' if actual == pred else 'background-color: rgba(255, 23, 68, 0.04)'
                
                return [bg] * len(row)
                
            st.dataframe(
                ml_display_df.style.apply(highlight_predictions, axis=1).format({'24h Change (%)': '{:+.2f}%'}),
                hide_index=True,
                use_container_width=True
            )
            
        with col_ml2:
            st.write("**Model Details**")
            
            # Load metadata
            try:
                import pickle
                with open(MODEL_PATH, "rb") as f:
                    model = pickle.load(f)
                
                # Estimate fake feature importances from RF
                importances = model.feature_importances_
                features = [
                    "market_cap_rank", 
                    "current_price_usd", 
                    "market_cap_usd", 
                    "total_volume_usd", 
                    "volatility_24h", 
                    "volume_to_market_cap_ratio"
                ]
                
                imp_df = pd.DataFrame({
                    "Feature": features,
                    "Importance": importances
                }).sort_values(by="Importance", ascending=False)
                
                # Plot Feature Importance
                fig, ax = plt.subplots(figsize=(6, 5))
                sns.barplot(data=imp_df, x="Importance", y="Feature", palette="viridis", ax=ax)
                ax.set_xlabel("Relative Importance")
                ax.set_ylabel("")
                plt.tight_layout()
                st.pyplot(fig)
                
                st.write("**Trigger Re-training**")
                if st.button("🔄 Re-Train Model"):
                    with st.spinner("Retraining model..."):
                        try:
                            res = train_ml_model()
                            st.success(f"Model retrained! Accuracy: {res['accuracy']:.2%}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Retraining error: {e}")
            except Exception as e:
                st.error(f"Error reading model stats: {e}")

# ----------------- TAB 4: OPERATION LOGS -----------------
with tab4:
    st.subheader("📋 Pipeline Orchestration Logs")
    st.write("Tracks metadata of every automated ETL execution, demonstrating complete workflow orchestration.")
    
    logs_df = fetch_logs_from_db()
    
    if logs_df is None or len(logs_df) == 0:
        st.info("DB logging is active in SQL Mode. In Fallback File Mode, you can inspect pipeline execution details in `pipeline.log` in the project root directory:")
        
        # Try reading local log file
        log_file_path = config.BASE_DIR / "pipeline.log"
        if log_file_path.exists():
            with open(log_file_path, "r", encoding="utf-8") as f:
                logs_content = f.readlines()
            
            # Show last 100 lines of log
            st.text_area("pipeline.log (Last 100 lines)", value="".join(logs_content[-100:]), height=400)
        else:
            st.warning("No log files found. Run the ETL pipeline to generate logs.")
    else:
        st.dataframe(
            logs_df.style.map(
                lambda x: 'color: #00E676; font-weight: bold;' if x == 'SUCCESS' else 'color: #FF1744; font-weight: bold;' if x == 'FAILED' else '',
                subset=['status']
            ),
            hide_index=True,
            use_container_width=True
        )
