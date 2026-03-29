import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import time
import os
import re
from db_manager import init_db, upsert_data

# Access the variables
BASE_URL = os.getenv("BASE_URL", "https://www.sklavenitis.gr")

def clean_price(val):
    if not val: return 0.0
    try:
        val_str = str(val).replace(',', '.')
        match = re.search(r"(\d+\.\d+|\d+)", val_str)
        return float(match.group(1)) if match else 0.0
    except: return 0.0

def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'lxml')
    except Exception as e:
        print(f"!!! Failed to fetch {url}: {e}")
        return None

def get_all_categories(soup):
    """Extracts sub-category URLs and their parent categories from the sidebar."""
    categories = []
    
    # Find all sub-menus (Level 2 containers)
    sub_menus = soup.find_all('ul', class_='mainNav_sub')
    
    for sub_menu in sub_menus:
        # Find the parent list item to get the Level 1 Category name
        parent_li = sub_menu.find_parent('li')
        level1_tag = parent_li.find('a') if parent_li else None
        level1_name = level1_tag.get_text(strip=True) if level1_tag else "Άγνωστη Κατηγορία (L1)"
        
        # Now loop through the Level 2 links inside this sub-menu
        for link in sub_menu.find_all('a'):
            href = link.get('href')
            level2_name = link.get_text(strip=True)
            if href:
                full_url = BASE_URL + href if href.startswith('/') else href
                categories.append({
                    'level1': level1_name,
                    'level2': level2_name,
                    'url': full_url
                })
                
    return categories

def scrape_category(cat_info):
    """Scrapes all products from all pages of a specific category."""
    level1_name = cat_info.get('level1', '')
    level2_name = cat_info.get('level2', '')
    base_cat_url = cat_info['url']
    products_list = []
    page = 1
    
    while True:
        url = f"{base_cat_url}?pg={page}"
        print(f"  > Scraping {level2_name} | Page {page}")
        soup = get_soup(url)
        
        if not soup: break
        
        items = soup.find_all('div', class_='product')
        if not items: break # No more products on this page
        
        for p in items:
            try:
                # 1. Parse JSON Blobs
                plugin_data = json.loads(p.get('data-plugin-product', '{}'))
                item_data = json.loads(p.get('data-item', '{}'))
                analytics = json.loads(p.get('data-plugin-analyticsimpressions', '{}'))
                details = analytics.get('Call', {}).get('ecommerce', {}).get('items', [{}])[0]

                # 2. Extract Text Data
                price_tag = p.find('div', class_='price')
                current_price = clean_price(price_tag.get('data-price')) if price_tag else 0.0
                
                price_kg_tag = p.find('div', class_='priceKil')
                price_per_kg = clean_price(price_kg_tag.text) if price_kg_tag else 0.0
                
                name_tag = p.find('h4', class_='product__title')

                # 3. Extract Product URL
                a_tag = p.find('a', class_='absLink')
                product_url = ""
                if a_tag and a_tag.get('href'):
                    href = a_tag.get('href')
                    product_url = BASE_URL + href if href.startswith('/') else href

                # 4. Extract Image URL
                img_tag = p.find('img')
                image_url = ""
                if img_tag:
                    raw_img = img_tag.get('data-src') or img_tag.get('src') or ""
                    image_url = BASE_URL + raw_img if raw_img.startswith('/') else raw_img

                # --- NEW: 5. Build the Full Category Path ---
                level3_name = details.get('item_category', '').strip()
                
                is_on_sale = bool(p.find('div', class_='main-price--previous'))

                # 6. Append to List
                products_list.append({
                    'product_id': item_data.get('ProductID'),
                    'sku': plugin_data.get('sku'),
                    'name': name_tag.text.strip() if name_tag else details.get('item_name'),
                    'brand': details.get('item_brand'),
                    'category_level_1': level1_name,
                    'category_level_2': level2_name,
                    'category_level_3': level3_name,
                    'current_price': current_price,
                    'price_per_kg': price_per_kg,
                    'unit': plugin_data.get('unitDisplay'),
                    'step': plugin_data.get('step'),
                    'in_stock': not plugin_data.get('notBuyable', False),
                    'on_sale': is_on_sale,
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'image_url': image_url,
                    'url': product_url
                })
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
        
        page += 1
        # time.sleep(0.8)
        
    return products_list

def main():
    print("--- Starting Live Cloud-Sync Scrape ---")
    
    # 1. Prepare Database
    init_db()
    
    # 2. Get Categories
    initial_soup = get_soup(f"{BASE_URL}/freska-froyta-lachanika/froyta/")
    if not initial_soup: return
    
    all_categories = get_all_categories(initial_soup)
    print(f"Found {len(all_categories)} categories.")

    # 3. Scrape and Sync immediately
    total_items = 0
    for i, cat in enumerate(all_categories):
        print(f"[{i+1}/{len(all_categories)}] Processing: {cat['level1']} > {cat['level2']}")
        
        # Get data for THIS category only
        cat_data = scrape_category(cat) 
        
        if cat_data:
            # OPTIMAL MOVE: Push this category to DB immediately
            upsert_data(cat_data)
            total_items += len(cat_data)
        
        # Optional: Small sleep to avoid hammering the site
        time.sleep(1)

    print(f"--- Finished! Total items synced to Cloud: {total_items} ---")

if __name__ == "__main__":
    main()