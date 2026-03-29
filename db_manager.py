import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY, 
            sku TEXT, 
            name TEXT, 
            brand TEXT, 
            category_level_1 TEXT,
            category_level_2 TEXT,
            category_level_3 TEXT,
            unit TEXT, 
            image_url TEXT, 
            url TEXT,
            step_increment INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
            product_id TEXT REFERENCES products(product_id),
            current_price FLOAT, 
            price_per_kg FLOAT,
            on_sale BOOLEAN, 
            in_stock BOOLEAN,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def upsert_data(data_list):
    if not data_list: return

    conn = get_connection()
    cur = conn.cursor()

    try:
        product_records = [
            (i['product_id'], i['sku'], i['name'], i['brand'], i['category_level_1'], 
             i['category_level_2'], i['category_level_3'], i['unit'], i['image_url'], 
             i['url'], i['step']) 
            for i in data_list
        ]
        
        product_query = """
            INSERT INTO products (product_id, sku, name, brand, category_level_1, category_level_2, category_level_3, unit, image_url, url, step_increment)
            VALUES %s
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                category_level_1 = EXCLUDED.category_level_1,
                category_level_2 = EXCLUDED.category_level_2,
                category_level_3 = EXCLUDED.category_level_3,
                image_url = EXCLUDED.image_url,
                url = EXCLUDED.url;
        """
        execute_values(cur, product_query, product_records)

        price_records = [
            (i['product_id'], i['current_price'], i['price_per_kg'], i['on_sale'], i['in_stock']) 
            for i in data_list
        ]
        
        price_query = """
            INSERT INTO price_history (product_id, current_price, price_per_kg, on_sale, in_stock)
            VALUES %s;
        """
        execute_values(cur, price_query, price_records)

        conn.commit()
        print(f"   [DB] Sync complete for {len(data_list)} items.")
    except Exception as e:
        conn.rollback()
        print(f"   [DB Error] Transaction rolled back: {e}")
    finally:
        cur.close()
        conn.close()