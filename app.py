import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import streamlit_antd_components as sac

load_dotenv()

@st.cache_resource
def get_db_engine():
    return create_engine(os.getenv("DATABASE_URL"))

engine = get_db_engine()

@st.cache_data(ttl=300) 
def get_product_list():
    query = "SELECT product_id, name, brand, category_level_1, category_level_2, category_level_3 FROM products ORDER BY name;"
    return pd.read_sql(query, con=engine)

def get_product_details(product_id):
    query = "SELECT * FROM products WHERE product_id = %(product_id)s;"
    return pd.read_sql(query, con=engine, params={"product_id": product_id})

def get_price_history(product_id):
    query = """
        SELECT scraped_at, current_price, price_per_kg, on_sale, in_stock 
        FROM price_history 
        WHERE product_id = %(product_id)s 
        ORDER BY scraped_at DESC;
    """
    return pd.read_sql(query, con=engine, params={"product_id": product_id})

@st.cache_data
def build_hierarchical_items(df):
    items = []
    # We use TreeItem here to be explicit, though sac.CasItem often works interchangeably
    for l1, group1 in df.groupby('category_level_1'):
        l1_children = []
        for l2, group2 in group1.groupby('category_level_2'):
            l2_children = []
            for l3, group3 in group2.groupby('category_level_3'):
                l3_children = []
                for _, row in group3.iterrows():
                    l3_children.append(sac.TreeItem(row['display_name']))
                l2_children.append(sac.TreeItem(l3, children=l3_children))
            l1_children.append(sac.TreeItem(l2, children=l2_children))
        items.append(sac.TreeItem(l1, children=l1_children))
    return items

# --- CART FUNCTIONS ---
def add_to_cart(name, price):
    st.session_state.cart.append({"name": name, "price": price})
    st.toast(f"Added {name} to basket!", icon="🛒")

def clear_cart():
    st.session_state.cart = []

# --- PAGE CONFIG ---
st.set_page_config(page_title="Sklavenitis Prices Tracker", page_icon="🛒", layout="wide")

# Initialize Cart
if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- SIDEBAR CART DISPLAY ---
with st.sidebar:
    st.image("data/sklavenitis_logo.png", width=150)
    st.header("🛒 My Shopping List")
    
    if not st.session_state.cart:
        st.info("Your basket is empty.")
    else:
        cart_df = pd.DataFrame(st.session_state.cart)
        for _, item in cart_df.iterrows():
            st.write(f"**{item['name']}**")
            st.caption(f"{item['price']}€")
        
        st.divider()
        total_price = cart_df['price'].sum()
        st.subheader(f"Total: {total_price:.2f}€")
        
        if st.button("Clear Basket", use_container_width=True):
            clear_cart()
            st.rerun()

# --- MAIN UI ---
st.title("Sklavenitis Prices Tracker")

df_products = get_product_list()

if df_products.empty:
    st.warning("No products found in the database.")
else:
    df_products['category_level_1'] = df_products['category_level_1'].fillna("Unknown")
    df_products['category_level_2'] = df_products['category_level_2'].fillna("Unknown")
    df_products['category_level_3'] = df_products['category_level_3'].fillna("Unknown")
    df_products['display_name'] = df_products['name'] + " (" + df_products['brand'].fillna('N/A') + ")"
    
    # --- Tree Selection Section ---
    st.subheader("Explore Categories")
    tree_items = build_hierarchical_items(df_products)
    
    # 1. Add a simple search box above the tree
    search_q = st.text_input("🔍 Quick search products...", placeholder="e.g. Φέτα")
    
    # 2. Logic to handle search vs tree selection
    quick_select = None
    if search_q:
        matches = df_products[df_products['display_name'].str.contains(search_q, case=False, na=False)]
        if not matches.empty:
            quick_select = st.selectbox("Search Results", matches['display_name'], index=None)

    # 3. The Tree (Simplified to basics)
    with st.container(height=400):
        tree_selection = sac.tree(
            items=tree_items,
            label='',
            open_all=False,
            show_line=True,
            key='main_product_tree'
        )

    # Final decision: Priority to Search, then Tree
    leaf_selection = quick_select if quick_select else tree_selection

    # Check if the selection is a product (and not a category name)
    if leaf_selection and leaf_selection in df_products['display_name'].values:
        selected_product_id = df_products.loc[df_products['display_name'] == leaf_selection, 'product_id'].iloc[0]
        
        st.divider()
        
        # Fetch Details and History
        df_details = get_product_details(selected_product_id)
        df_history = get_price_history(selected_product_id)
        
        # --- Product Details Section ---
        st.subheader("Product Details")
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col1:
            image_url = df_details['image_url'].iloc[0] if not df_details.empty and pd.notna(df_details['image_url'].iloc[0]) else ""
            if image_url:
                st.image(image_url, width=150)
            else:
                st.info("No image available.")
                
        with col2:
            st.markdown(f"### {leaf_selection}")
            display_details = df_details.drop(columns=['image_url', 'url'], errors='ignore')
            st.dataframe(display_details, use_container_width=True, hide_index=True)

        with col3:
            current_price = 0.0
            if not df_history.empty:
                current_price = float(df_history['current_price'].iloc[0])
                st.metric("Current Price", f"{current_price}€")
            
            if st.button("➕ Add to Basket", use_container_width=True, type="primary"):
                add_to_cart(df_details['name'].iloc[0], current_price)
            
            product_url = df_details['url'].iloc[0] if not df_details.empty and pd.notna(df_details['url'].iloc[0]) else ""
            if product_url:
                st.link_button("🌐 Open in Store", product_url, use_container_width=True)

        st.divider()
        
        # --- Price History Section ---
        st.subheader("Price Analysis")
        if not df_history.empty:
            tab1, tab2 = st.tabs(["Trend Chart", "Raw History"])
            with tab1:
                chart_data = df_history.copy().set_index('scraped_at')
                st.line_chart(chart_data['current_price'])
            with tab2:
                st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.info("No price history available.")
    else:
        st.info("👆 Expand the categories above and click on a product name.")