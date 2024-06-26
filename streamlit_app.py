import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
import os
from utils import css_to_markdown, load_credentials

sql_query = """
            SELECT *
            FROM public.products_catalog
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            """

# Load a sample dataset
def load_data(query):
    engine = create_engine(f"postgresql://{os.environ['user']}:{os.environ['password']}@{os.environ['host']}:{os.environ['port']}/{os.environ['database']}?sslmode=require")
    df = pd.read_sql(query, engine)
    return (df)

# Main function
def main():
    st.cache_data.clear()
    try:
        del st.session_state['products_catalog']
    except:
        pass
    st.set_page_config(layout="wide")

    load_credentials()

    # Load data
    global products_catalog
    if 'products_catalog' not in st.session_state:
        st.session_state.products_catalog = load_data(sql_query)
        # remove outliers for viz purposes
        q_high = st.session_state.products_catalog["price"].quantile(0.95)
        q_low = st.session_state.products_catalog["price"].quantile(0.05)
        st.session_state.products_catalog = st.session_state.products_catalog[(st.session_state.products_catalog["price"] < q_high) & 
                                                                              (st.session_state.products_catalog["price"] > q_low)]

    # loading fonts
    st.markdown("""
        <link href="https://fonts.googleapis.com/css?family=Nunito:200,300,700" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css?family=Bungee" rel="stylesheet">
        """,
        unsafe_allow_html= True)

    st.write("<h2 style='font-family: Bungee; color: orange''>Vinted Dashboard</h2>", 
             unsafe_allow_html=True)
    latest_date = st.session_state.products_catalog["date"].max()
    st.write(f"Latest updated on {latest_date}", 
             unsafe_allow_html=True)

    # wrapping up with containers
    with st.container():
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric(label="**Brands**", 
                    value=st.session_state.products_catalog['brand_title'].nunique(),
                    help="Number of unique brands in the sample")
        with col2:
            st.metric(label="**Products**", 
                    value=st.session_state.products_catalog['product_id'].nunique(),
                    help="Number of unique products in the sample")
        with col3:
            st.metric(label="**Users**", 
                    value=st.session_state.products_catalog['user_id'].nunique(),
                    help="Number of unique users in the sample")
        with col4:
            st.metric(label="**Catalogs**", 
                    value=st.session_state.products_catalog['catalog_id'].nunique(),
                    help="Number of unique catalogs in the sample")
        with col5:
            st.metric(label="**Price Median (€)**", 
                    value="{:,.2f} €".format(st.session_state.products_catalog['price'].median()),
                    help="Median price of the articles in the sample in Euro")
        with col6:
            st.metric(label="**Total Volume (€)**", 
                    value="{:,.0f} €".format(st.session_state.products_catalog['price'].sum()),
                    help="Total volume of the articles in the sample in Euro")

    # selecting only the top 15 brands (count items) for visualization purposes
    # avoiding cluttering
    brands = st.session_state.products_catalog.groupby(["brand_title"])["product_id"].count().sort_values(ascending = False).head(15).reset_index()["brand_title"]

    aggregated_data = st.session_state.products_catalog[st.session_state.products_catalog["brand_title"].isin(brands)].groupby(['catalog_id', 'brand_title', 'status']).agg(
        total_volume=('price', 'sum'),
        median_price=('price', 'median'),
        count=('price', 'count')
    ).reset_index()

    css_to_markdown("assets/st_app.css")

    fig = px.treemap(aggregated_data, 
                    path=['catalog_id', "brand_title"], 
                    values='total_volume',
                    labels={'total_volume': 'Total Volume', 'median_price': 'Median Price', 'count': 'Count'}
                    )

    st.plotly_chart(fig, 
                    use_container_width=True) 

    price = st.session_state.products_catalog.groupby(["catalog_id"])["price"].sum()
    price = price/price.sum()

    products = st.session_state.products_catalog.groupby(["catalog_id"])["product_id"].count()
    products = products/products.sum()
    fig = px.box(st.session_state.products_catalog, 
                       y="price", 
                       color="catalog_id",
                       orientation="v",
                       title= "Catalog boxplot")

    # Catalogs Container
    with st.container():
        st.write("<h5 style='font-family: Bungee; color: orange'>Catalogs</h5>", 
                 unsafe_allow_html=True)
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            st.plotly_chart(fig, use_container_width=True) 

        fig = px.pie(price, 
                    values=price.sort_values(ascending = False).head(10).reset_index()["price"], 
                    names=price.sort_values(ascending = False).head(10).reset_index()["catalog_id"], 
                    title='Market share')
        fig.update_traces(textposition='inside', textinfo='percent+label',\
                        hovertemplate = "Catalog:%{label}: <br>Volume: %{value} </br>"
        )
        with col2:
            st.plotly_chart(fig, 
                            use_container_width=True)

    #
    price = st.session_state.products_catalog.groupby(["brand_title"])["price"].sum()
    price = price/price.sum()

    products = st.session_state.products_catalog.groupby(["brand_title"])["product_id"].count()
    products = products/products.sum()
    fig = go.Figure(data=[
        go.Bar(name='Price', 
               x=price.sort_values(ascending = False).head(15).reset_index()["brand_title"], 
               y=price.sort_values(ascending = False).head(15).reset_index()["price"]
               ),
        go.Bar(name='Count', 
               x=products.sort_values(ascending = False).head(15).reset_index()["brand_title"], 
               y=products.sort_values(ascending = False).head(15).reset_index()["product_id"])
    ])
    fig.update_layout(title = "Price and count (%)")

    fig = px.box(st.session_state.products_catalog[st.session_state.products_catalog["brand_title"].isin(brands)], 
                       y="price", 
                       color="brand_title",
                       orientation="v",
                       title= "Brand boxplot")
    with st.container():
        st.write("<h5 style='font-family: Bungee; color: orange'>Brands</h5>", unsafe_allow_html=True)
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            st.plotly_chart(fig, use_container_width=True) 

        fig = px.pie(price, 
                    values=price.sort_values(ascending = False).head(15).reset_index()["price"], 
                    names=price.sort_values(ascending = False).head(15).reset_index()["brand_title"], 
                    title='Market share')
        with col2:
            st.plotly_chart(fig, use_container_width=True) 

    price = st.session_state.products_catalog.groupby(["status"])["price"].sum()
    price = price/price.sum()

    products = st.session_state.products_catalog.groupby(["status"])["product_id"].count()
    products = products/products.sum()

    status = st.session_state.products_catalog.groupby(["status"])["product_id"].count().sort_values(ascending = False).head(30).reset_index()["status"]

    fig = px.box(st.session_state.products_catalog[st.session_state.products_catalog["status"].isin(status)], 
                       y="price", 
                       color="status",
                       orientation="v",
                       title= "Status-Price boxplot",
                       category_orders= {"status": ["Satisfatório", "Bom", "Muito bom", "Novo sem etiquetas", "Novo com etiquetas"]})

    with st.container():
        st.write("<h5 style='font-family: Bungee; color: orange'>Status</h5>", unsafe_allow_html=True)
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            st.plotly_chart(fig, use_container_width=True) 

        fig = px.pie(price, 
                    values=price.sort_values(ascending = False).head(20).reset_index()["price"], 
                    names=price.sort_values(ascending = False).head(20).reset_index()["status"], 
                    title='Market share')
        with col2:
            st.plotly_chart(fig, use_container_width=True) 

    with st.container():
        st.write("<h5 style='font-family: Bungee; color: orange'>Datatable</h5>", unsafe_allow_html=True)
        st.dataframe(
            st.session_state.products_catalog[["product_id", "title", "price", "brand_title", "url", "promoted", "size_title", "status", "catalog_id", "view_count"]],
            column_config={
                "product_id": "Article ID",
                "title": "Article title",
                "price": st.column_config.NumberColumn(
                    "Price",
                    help="Price in EUR",
                    format="%.2f €"
                ),
                "brand_title": "Brand",
                "url": st.column_config.LinkColumn(
                    "Link",
                    help="Link to the item"
                ),
                "promoted": "Promoted",
                "size_title": "Size",
                "status": "Condition",
                "catalog_id": "Catalog",
                "view_count": st.column_config.NumberColumn(
                    "Views",
                    help="Number of views",
                    format="%.0f"
                )
            },
            hide_index=True,
            use_container_width=True
        )
if __name__ == "__main__":
    main()