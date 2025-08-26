import pendulum
from airflow.decorators import dag, task
import json


@dag(
    schedule_interval="0 */6 * * *",  # Every 6 hours
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    is_paused_upon_creation=False,
    tags=["economics", "finance", "data"],
    max_active_runs=1,
)
def econometrics_data_pipeline():
    """
    ### Econometrics Data Pipeline
    
    Collects economic and financial data from various government and financial sources:
    - Economic indicators: CPI, Fed Funds Rate, Unemployment, GDP
    - Market data: S&P 500, VIX, Treasury yields, P/E ratios
    
    Data is stored in PostgreSQL for dashboard visualization and analysis.
    """

    @task.virtualenv(
        task_id="create_database_tables",
        requirements=[
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
    )
    def create_tables():
        """Create database tables if they don't exist."""
        import psycopg2
        import os
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Get database connection from Airflow connection
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_name = os.getenv('POSTGRES_DB', 'econometrics') 
        db_user = os.getenv('POSTGRES_USER')
        db_password = os.getenv('POSTGRES_PASSWORD')
        db_port = os.getenv('POSTGRES_PORT', '5432')

        try:
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            
            with conn.cursor() as cur:
                # Read SQL file from git-synced location
                sql_path = "/opt/airflow/sync/smart-home-config/workloads/airflow/dags/econometrics-pipeline/config/create_tables.sql"
                with open(sql_path, 'r') as f:
                    sql = f.read()
                
                cur.execute(sql)
                conn.commit()
                logger.info("Database tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @task.virtualenv(
        task_id="collect_fed_funds_rate",
        requirements=[
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
    )
    def collect_fed_funds_rate():
        """Collect Federal Funds Rate data from FRED API."""
        import requests
        import psycopg2
        import os
        import logging
        from datetime import datetime

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Get API key and database connection
        fred_api_key = os.getenv('FRED_API_KEY')
        if not fred_api_key:
            raise ValueError("FRED_API_KEY not found in environment variables")

        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_name = os.getenv('POSTGRES_DB', 'econometrics')
        db_user = os.getenv('POSTGRES_USER')
        db_password = os.getenv('POSTGRES_PASSWORD')
        db_port = os.getenv('POSTGRES_PORT', '5432')

        try:
            # Fetch data from FRED
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": "FEDFUNDS",
                "api_key": fred_api_key,
                "file_type": "json",
                "limit": 100,
                "sort_order": "desc"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "observations" not in data:
                logger.error("No observations found in FRED response")
                return 0
            
            # Connect to database
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            
            success_count = 0
            with conn.cursor() as cur:
                for item in data["observations"]:
                    if item["value"] == ".":
                        continue
                        
                    try:
                        date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                        rate = float(item["value"])
                        
                        # Upsert data
                        sql = """
                        INSERT INTO federal_funds_rate (date, effective_rate, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (date) DO UPDATE SET
                        effective_rate = EXCLUDED.effective_rate, 
                        updated_at = CURRENT_TIMESTAMP
                        """
                        cur.execute(sql, (date, rate))
                        success_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Error processing item: {str(e)}")
                        continue
                        
                conn.commit()
                logger.info(f"Successfully processed {success_count} Fed Funds Rate records")
                return success_count
                
        except Exception as e:
            logger.error(f"Error collecting Fed Funds Rate data: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    @task.virtualenv(
        task_id="collect_cpi_data",
        requirements=[
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
    )
    def collect_cpi_data():
        """Collect Consumer Price Index data from BLS API."""
        import requests
        import psycopg2
        import json
        import os
        import logging
        from datetime import datetime

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Get API key (optional for BLS)
        bls_api_key = os.getenv('BLS_API_KEY')
        
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_name = os.getenv('POSTGRES_DB', 'econometrics')
        db_user = os.getenv('POSTGRES_USER')
        db_password = os.getenv('POSTGRES_PASSWORD')
        db_port = os.getenv('POSTGRES_PORT', '5432')

        try:
            # Prepare BLS request
            current_year = datetime.now().year
            payload = {
                "seriesid": ["CUUR0000SA0"],  # All items CPI-U
                "startyear": str(current_year - 1),
                "endyear": str(current_year),
            }
            
            if bls_api_key:
                payload["registrationkey"] = bls_api_key
                
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(
                "https://api.bls.gov/publicAPI/v2/timeseries/data",
                data=json.dumps(payload),
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "REQUEST_SUCCEEDED":
                logger.error(f"BLS API error: {data.get('message', 'Unknown error')}")
                return 0
            
            series_data = data["Results"]["series"][0]["data"]
            
            # Connect to database
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            
            success_count = 0
            with conn.cursor() as cur:
                for item in series_data:
                    try:
                        year = int(item["year"])
                        period = item["period"]
                        if not period.startswith("M"):
                            continue
                            
                        month = int(period[1:])
                        date = datetime(year, month, 1).date()
                        value = float(item["value"])
                        
                        # Calculate year-over-year change if possible
                        yoy_change = None
                        prev_year_data = [d for d in series_data 
                                        if d["year"] == str(year-1) and d["period"] == period]
                        if prev_year_data:
                            prev_value = float(prev_year_data[0]["value"])
                            yoy_change = ((value - prev_value) / prev_value) * 100
                        
                        # Upsert data
                        sql = """
                        INSERT INTO consumer_price_index (date, value, year_over_year_change, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (date) DO UPDATE SET
                        value = EXCLUDED.value,
                        year_over_year_change = EXCLUDED.year_over_year_change,
                        updated_at = CURRENT_TIMESTAMP
                        """
                        cur.execute(sql, (date, value, yoy_change))
                        success_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Error processing CPI item: {str(e)}")
                        continue
                        
                conn.commit()
                logger.info(f"Successfully processed {success_count} CPI records")
                return success_count
                
        except Exception as e:
            logger.error(f"Error collecting CPI data: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    @task.virtualenv(
        task_id="collect_sp500_data",
        requirements=[
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
    )
    def collect_sp500_data():
        """Collect S&P 500 index data from FRED API."""
        import requests
        import psycopg2
        import os
        import logging
        from datetime import datetime

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        fred_api_key = os.getenv('FRED_API_KEY')
        if not fred_api_key:
            raise ValueError("FRED_API_KEY not found in environment variables")

        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_name = os.getenv('POSTGRES_DB', 'econometrics')
        db_user = os.getenv('POSTGRES_USER')
        db_password = os.getenv('POSTGRES_PASSWORD')
        db_port = os.getenv('POSTGRES_PORT', '5432')

        try:
            # Fetch S&P 500 data from FRED
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": "SP500",
                "api_key": fred_api_key,
                "file_type": "json",
                "limit": 100,
                "sort_order": "desc"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "observations" not in data:
                logger.error("No observations found in FRED response")
                return 0
            
            # Connect to database
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            
            success_count = 0
            with conn.cursor() as cur:
                for item in data["observations"]:
                    if item["value"] == ".":
                        continue
                        
                    try:
                        date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                        price = float(item["value"])
                        
                        # FRED only provides closing prices, so we use the same value for OHLC
                        sql = """
                        INSERT INTO sp500_index (date, open_price, high_price, low_price, close_price, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        updated_at = CURRENT_TIMESTAMP
                        """
                        cur.execute(sql, (date, price, price, price, price))
                        success_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Error processing S&P 500 item: {str(e)}")
                        continue
                        
                conn.commit()
                logger.info(f"Successfully processed {success_count} S&P 500 records")
                return success_count
                
        except Exception as e:
            logger.error(f"Error collecting S&P 500 data: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    @task.virtualenv(
        task_id="collect_treasury_yields",
        requirements=[
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
    )
    def collect_treasury_yields():
        """Collect Treasury yield curve data from Treasury API."""
        import requests
        import psycopg2
        import os
        import logging
        from datetime import datetime

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_name = os.getenv('POSTGRES_DB', 'econometrics')
        db_user = os.getenv('POSTGRES_USER')
        db_password = os.getenv('POSTGRES_PASSWORD')
        db_port = os.getenv('POSTGRES_PORT', '5432')

        try:
            # Fetch Treasury yield data
            url = "https://api.fiscaldata.treasury.gov/services/api/v1/accounting/od/daily_treasury_yield_curve"
            params = {
                "format": "json",
                "sort": "-record_date",
                "page[size]": 100
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data:
                logger.error("No data found in Treasury response")
                return 0
            
            # Maturity mapping
            maturity_mapping = {
                "1_mo": "1M", "2_mo": "2M", "3_mo": "3M", "4_mo": "4M", "6_mo": "6M",
                "1_yr": "1Y", "2_yr": "2Y", "3_yr": "3Y", "5_yr": "5Y", 
                "7_yr": "7Y", "10_yr": "10Y", "20_yr": "20Y", "30_yr": "30Y"
            }
            
            # Connect to database
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            
            success_count = 0
            with conn.cursor() as cur:
                for record in data["data"]:
                    try:
                        record_date = datetime.strptime(record["record_date"], "%Y-%m-%d").date()
                        
                        for api_field, maturity in maturity_mapping.items():
                            if record.get(api_field) and record[api_field] != "":
                                yield_rate = float(record[api_field])
                                
                                sql = """
                                INSERT INTO treasury_yields (date, maturity, yield_rate, updated_at)
                                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                                ON CONFLICT (date, maturity) DO UPDATE SET
                                yield_rate = EXCLUDED.yield_rate,
                                updated_at = CURRENT_TIMESTAMP
                                """
                                cur.execute(sql, (record_date, maturity, yield_rate))
                                success_count += 1
                                
                    except Exception as e:
                        logger.warning(f"Error processing Treasury yield record: {str(e)}")
                        continue
                        
                conn.commit()
                logger.info(f"Successfully processed {success_count} Treasury yield records")
                return success_count
                
        except Exception as e:
            logger.error(f"Error collecting Treasury yield data: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    # Define task dependencies
    tables_task = create_tables()
    
    # Economic indicators
    fed_funds_task = collect_fed_funds_rate()
    cpi_task = collect_cpi_data()
    
    # Market data
    sp500_task = collect_sp500_data()
    treasury_task = collect_treasury_yields()
    
    # Set dependencies
    tables_task >> [fed_funds_task, cpi_task, sp500_task, treasury_task]


# Create the DAG instance
econometrics_dag = econometrics_data_pipeline()