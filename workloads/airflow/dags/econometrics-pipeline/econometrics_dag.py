import pendulum
from airflow.decorators import dag, task
import json


@dag(
    schedule_interval="0 23 * * 1-5",  # 6PM Eastern / 11 PM UTC weekdays only
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["economics", "finance", "data"],
    max_active_runs=1,
)
def econometrics_data_pipeline():
    """
    ### Econometrics Data Pipeline
    
    Collects economic and financial data from various government and financial sources:
    
    **Economic indicators (5 metrics):**
    - Daily Federal Funds Rate (FRED DFF series)
    - Monthly Federal Funds Rate (FRED FEDFUNDS series) 
    - Consumer Price Index (BLS API)
    - Unemployment Rate (BLS API)
    - Gross Domestic Product (BEA API)
    
    **Market data (6 metrics):**
    - S&P 500 Index (FRED SP500 series)
    - VIX Volatility Index (FRED VIXCLS series)
    - Treasury Yield Curve - 10 maturities (FRED DGS* series)
    - TIPS Yields - 5 maturities (FRED DFII* series)
    - Forward Inflation Expectations - T5YIFR (5yr-5yr forward)
    - P/E Ratios (FRED MULTPL series)
    
    **Total: 11 metrics collected daily on weekdays**
    
    Data is stored in PostgreSQL for dashboard visualization and analysis.
    """

    @task.virtualenv(
        task_id="create_database_tables",
        requirements=[
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  
    )
    def create_tables():
        """Create database tables if they don't exist."""
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
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_fed_funds_rate():
        """Collect daily Federal Funds Rate data from FRED API (DFF series)."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_daily_fed_funds_rate

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_daily_fed_funds_rate(database_url=database_url)
            logger.info(f"Successfully collected {result} Fed Funds Rate records")
            return result
        except Exception as e:
            logger.error(f"Error collecting Fed Funds Rate data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_cpi_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_cpi_data():
        """Collect Consumer Price Index data from BLS API."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_cpi

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_cpi(database_url=database_url)
            logger.info(f"Successfully collected {result} CPI records")
            return result
        except Exception as e:
            logger.error(f"Error collecting CPI data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_sp500_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_sp500_data():
        """Collect S&P 500 index data from FRED API."""
        import logging
        import os
        from data_collectors.market_data import collect_sp500

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_sp500(database_url=database_url)
            logger.info(f"Successfully collected {result} S&P 500 records")
            return result
        except Exception as e:
            logger.error(f"Error collecting S&P 500 data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_monthly_fed_funds_rate",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_monthly_fed_funds_rate():
        """Collect monthly Federal Funds Rate data from FRED API (FEDFUNDS series)."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_monthly_fed_funds_rate

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_monthly_fed_funds_rate(database_url=database_url)
            logger.info(f"Successfully collected {result} monthly Fed Funds Rate records")
            return result
        except Exception as e:
            logger.error(f"Error collecting monthly Fed Funds Rate data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_unemployment_rate",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_unemployment_rate():
        """Collect unemployment rate data from BLS API."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_unemployment_rate

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_unemployment_rate(database_url=database_url)
            logger.info(f"Successfully collected {result} unemployment rate records")
            return result
        except Exception as e:
            logger.error(f"Error collecting unemployment rate data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_gdp_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_gdp_data():
        """Collect GDP data from BEA API."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_gdp

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_gdp(database_url=database_url)
            logger.info(f"Successfully collected {result} GDP records")
            return result
        except Exception as e:
            logger.error(f"Error collecting GDP data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_vix_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_vix_data():
        """Collect VIX volatility index data from FRED API."""
        import logging
        import os
        from data_collectors.market_data import collect_vix

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_vix(database_url=database_url)
            logger.info(f"Successfully collected {result} VIX records")
            return result
        except Exception as e:
            logger.error(f"Error collecting VIX data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_pe_ratios",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_pe_ratios():
        """Collect P/E ratio data from FRED API."""
        import logging
        import os
        from data_collectors.market_data import collect_pe_ratios

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_pe_ratios(database_url=database_url)
            logger.info(f"Successfully collected {result} P/E ratio records")
            return result
        except Exception as e:
            logger.error(f"Error collecting P/E ratio data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_treasury_yields",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_treasury_yields():
        """Collect Treasury yield curve data from FRED API."""
        import logging
        import os
        from data_collectors.market_data import collect_fred_treasury_yields

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_fred_treasury_yields(database_url=database_url)
            logger.info(f"Successfully collected {result} Treasury yield records")
            return result
        except Exception as e:
            logger.error(f"Error collecting Treasury yield data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_us_tips_yields",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_us_tips_yields():
        """Collect US TIPS yield data and forward inflation expectations from FRED API."""
        import logging
        import os
        from data_collectors.us_tips_data import collect_us_tips

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_us_tips(database_url=database_url)
            logger.info(f"Successfully collected {result} US TIPS yield and forward inflation records")
            return result
        except Exception as e:
            logger.error(f"Error collecting US TIPS yield data: {str(e)}")
            raise

    # Define task dependencies
    tables_task = create_tables()
    
    # Economic indicators
    daily_fed_funds_task = collect_fed_funds_rate()
    monthly_fed_funds_task = collect_monthly_fed_funds_rate()
    cpi_task = collect_cpi_data()
    unemployment_task = collect_unemployment_rate()
    gdp_task = collect_gdp_data()
    
    # Market data
    sp500_task = collect_sp500_data()
    vix_task = collect_vix_data()
    treasury_task = collect_treasury_yields()
    tips_task = collect_us_tips_yields()
    pe_ratios_task = collect_pe_ratios()
    
    # Set dependencies - all collectors depend on tables being created
    tables_task >> [
        daily_fed_funds_task, monthly_fed_funds_task, cpi_task, 
        unemployment_task, gdp_task, sp500_task, vix_task, 
        treasury_task, tips_task, pe_ratios_task
    ]


# Create the DAG instance
econometrics_dag = econometrics_data_pipeline()