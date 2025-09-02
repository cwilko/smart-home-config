import pendulum
from airflow.decorators import dag, task
import json


@dag(
    schedule_interval="0 22 * * 1-5",  # 5 PM ET (10 PM UTC) weekdays only - 1 hour before US data
    start_date=pendulum.datetime(2024, 1, 1, tz="US/Eastern"),
    catchup=False,
    tags=["uk", "economics", "finance", "data"],
    max_active_runs=1,
)
def uk_metrics_data_pipeline():
    """
    ### UK Metrics Data Pipeline
    
    Collects UK economic and financial data from official government and financial sources:
    
    **UK Economic indicators (4 metrics):**
    - UK Consumer Price Index - CPIH (ONS Beta API)
    - UK Unemployment Rate (ONS Beta API) 
    - UK GDP Monthly (ONS Beta API)
    - UK Bank Rate (Bank of England IADB)
    
    **UK Market data (2 metrics):**
    - UK Gilt Yields - 5Y/10Y/20Y (Bank of England IADB)
    - FTSE 100 Index (MarketWatch CSV API)
    
    **Total: 6 UK metrics collected daily on weekdays**
    
    Data is stored in PostgreSQL for UK economic dashboard visualization and analysis.
    Complements the main US econometrics pipeline with comprehensive UK data.
    """

    @task.virtualenv(
        task_id="create_uk_database_tables",
        requirements=[
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=True,
        queue="celery",  
    )
    def create_uk_tables():
        """Create UK database tables if they don't exist."""
        import psycopg2
        import os
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            conn = None
            try:
                conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            except Exception as e:
                logger.error(f"Failed to connect via DATABASE_URL: {str(e)}")
                raise

            with conn.cursor() as cur:
                # UK-specific table creation SQL
                uk_tables_sql = """
                -- UK Consumer Price Index (CPIH)
                CREATE TABLE IF NOT EXISTS uk_consumer_price_index (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    cpi_value DECIMAL(10, 3) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- UK Unemployment Rate
                CREATE TABLE IF NOT EXISTS uk_unemployment_rate (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    unemployment_rate DECIMAL(5, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- UK GDP (Monthly)
                CREATE TABLE IF NOT EXISTS uk_gdp_monthly (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    gdp_value DECIMAL(10, 4) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- UK Bank Rate
                CREATE TABLE IF NOT EXISTS uk_bank_rate (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    bank_rate DECIMAL(5, 3) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- UK Gilt Yields
                CREATE TABLE IF NOT EXISTS uk_gilt_yields (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    maturity TEXT NOT NULL,
                    yield_rate DECIMAL(6, 3) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, maturity)
                );

                -- FTSE 100 Index
                CREATE TABLE IF NOT EXISTS ftse_100_index (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    open_price DECIMAL(10, 2) NOT NULL,
                    high_price DECIMAL(10, 2) NOT NULL,
                    low_price DECIMAL(10, 2) NOT NULL,
                    close_price DECIMAL(10, 2) NOT NULL,
                    volume BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create indexes for better query performance
                CREATE INDEX IF NOT EXISTS idx_uk_cpi_date ON uk_consumer_price_index(date);
                CREATE INDEX IF NOT EXISTS idx_uk_unemployment_date ON uk_unemployment_rate(date);
                CREATE INDEX IF NOT EXISTS idx_uk_gdp_date ON uk_gdp_monthly(date);
                CREATE INDEX IF NOT EXISTS idx_uk_bank_rate_date ON uk_bank_rate(date);
                CREATE INDEX IF NOT EXISTS idx_uk_gilt_yields_date ON uk_gilt_yields(date);
                CREATE INDEX IF NOT EXISTS idx_uk_gilt_yields_maturity ON uk_gilt_yields(maturity);
                CREATE INDEX IF NOT EXISTS idx_ftse_100_date ON ftse_100_index(date);
                """
                
                cur.execute(uk_tables_sql)
                conn.commit()
                logger.info("UK database tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating UK tables: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @task.virtualenv(
        task_id="collect_uk_cpi_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=True,
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_cpi_data():
        """Collect UK Consumer Price Index (CPIH) data from ONS Beta API."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_uk_cpi

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_cpi(database_url=database_url)
            logger.info(f"Successfully collected {result} UK CPI records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK CPI data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_uk_unemployment_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=True,
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_unemployment_data():
        """Collect UK unemployment rate data from ONS Beta API."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_uk_unemployment

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_unemployment(database_url=database_url)
            logger.info(f"Successfully collected {result} UK unemployment records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK unemployment data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_uk_gdp_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=True,
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_gdp_data():
        """Collect UK GDP monthly data from ONS Beta API."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_uk_gdp

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_gdp(database_url=database_url)
            logger.info(f"Successfully collected {result} UK GDP records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK GDP data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_uk_bank_rate_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=True,
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_bank_rate_data():
        """Collect UK Bank Rate data from Bank of England IADB."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_uk_bank_rate

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_bank_rate(database_url=database_url)
            logger.info(f"Successfully collected {result} UK Bank Rate records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK Bank Rate data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_uk_gilt_yields_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=True,
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_gilt_yields_data():
        """Collect UK gilt yields (5Y, 10Y, 20Y) data from Bank of England IADB."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_uk_gilt_yields

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_gilt_yields(database_url=database_url)
            logger.info(f"Successfully collected {result} UK gilt yields records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK gilt yields data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_ftse_100_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=True,
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_ftse_100_data():
        """Collect FTSE 100 index data from MarketWatch CSV API."""
        import logging
        import os
        from data_collectors.uk_market_data import collect_ftse_100

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_ftse_100(database_url=database_url)
            logger.info(f"Successfully collected {result} FTSE 100 records")
            return result
        except Exception as e:
            logger.error(f"Error collecting FTSE 100 data: {str(e)}")
            raise

    # Define task dependencies
    tables_task = create_uk_tables()
    
    # UK Economic indicators
    uk_cpi_task = collect_uk_cpi_data()
    uk_unemployment_task = collect_uk_unemployment_data()
    uk_gdp_task = collect_uk_gdp_data()
    uk_bank_rate_task = collect_uk_bank_rate_data()
    
    # UK Market data
    uk_gilt_yields_task = collect_uk_gilt_yields_data()
    ftse_100_task = collect_ftse_100_data()
    
    # Set dependencies - all collectors depend on tables being created
    tables_task >> [
        uk_cpi_task, uk_unemployment_task, uk_gdp_task, 
        uk_bank_rate_task, uk_gilt_yields_task, ftse_100_task
    ]


# Create the DAG instance
uk_metrics_dag = uk_metrics_data_pipeline()