# 🛒 Supermarket Price Tracker

A full-stack Python application designed to monitor and visualize grocery price trends in Greece. This project handles the end-to-end process of scraping live data from major retailers and providing an interactive dashboard for consumers to track inflation and manage their shopping baskets.

## 🚀 Features

* **Multi-Source Scraping**: Automated scrapers for **Sklavenitis**, **AB Vassilopoulos**, and **e-Katanalotis**.
* **Price History**: Tracks price fluctuations over time to identify the best time to buy.
* **Interactive Dashboard**: Built with **Streamlit** for real-time data exploration and visualization.
* **Smart Basket**: Add products to a virtual cart to calculate total costs across different categories.
* **Relational Database**: Managed via **SQLAlchemy** for robust data persistence and price history logging.

## 🛠️ Tech Stack

* **Language**: Python 3.12+
* **Frontend**: Streamlit, Streamlit Antd Components
* **Scraping**: Playwright, BeautifulSoup4, Requests
* **Database**: PostgreSQL / SQLite (via SQLAlchemy)
* **Environment**: `uv` for lightning-fast dependency management

## 📦 Setup & Installation

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/AlexMilionis/supermarket-tracker.git](https://github.com/AlexMilionis/supermarket-tracker.git)
    cd supermarket-tracker
    ```

2.  **Environment Setup**:
    Create a `.env` file based on the required variables:
    ```text
    BASE_URL=[https://www.sklavenitis.gr](https://www.sklavenitis.gr)
    DATABASE_URL=postgresql://user:password@localhost:5432/dbname
    ```

3.  **Install Dependencies**:
    ```bash
    # Using uv (recommended)
    uv sync
    source .venv/Scripts/activate  # On Windows: .venv\Scripts\activate
    ```

4.  **Run the Scraper**:
    ```bash
    python scraper.py
    ```

5.  **Launch the Dashboard**:
    ```bash
    streamlit run app.py
    ```

## 📂 Project Structure

* `app.py`: The main Streamlit dashboard.
* `scraper.py`: Core logic for fetching product and price data.
* `db_manager.py`: Database schema and upsert logic.
* `data/`: Assets, logos, and local storage.
* `.env.example`: Template for required environment variables.

---

**Disclaimer**: This project is for educational purposes. Please ensure compliance with the terms of service of the respective retailers when running automated scrapers.