import pendulum
from airflow.decorators import dag, task
import json


@dag(
    schedule_interval="0 22 * * 1-5",  # 5 PM ET (10 PM UTC) weekdays only - 1 hour before US data
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
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
    - UK Bank Rate Monthly (Bank of England IADB)
    
    **UK Market data (4 metrics):**
    - FTSE 100 Index (MarketWatch CSV API)
    - UK Gilt Yields - 5Y, 10Y, 20Y (Bank of England IADB)
    - BoE Comprehensive Yield Curves - 80+ maturities, 4 yield types (Bank of England ZIP files)
    - UK Swap Rates - 2Y, 5Y, 10Y, 30Y GBP Interest Rate Swaps (investiny)
    
    **Total: 8 UK metrics collected daily on weekdays**
    
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
                
                # Execute SQL statements separately to avoid transaction issues
                statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
                for i, statement in enumerate(statements):
                    try:
                        cur.execute(statement)
                        conn.commit()
                        logger.info(f"Executed statement {i+1}/{len(statements)}")
                    except Exception as e:
                        logger.error(f"Failed to execute statement {i+1}: {statement[:100]}...")
                        logger.error(f"Error: {str(e)}")
                        raise
                        
                logger.info("Database tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @task.virtualenv(
        task_id="collect_uk_cpi_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_uk_cpi",
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
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_uk_unemployment",
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
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_uk_gdp",
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
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_uk_bank_rate",
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_bank_rate_data():
        """Collect UK Bank Rate monthly data from Bank of England IADB."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_uk_monthly_bank_rate

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_monthly_bank_rate(database_url=database_url)
            logger.info(f"Successfully collected {result} UK Bank Rate records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK Bank Rate data: {str(e)}")
            raise


    @task.virtualenv(
        task_id="collect_ftse_100_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_ftse_100",
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


    @task.virtualenv(
        task_id="collect_uk_gilt_yields_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_uk_gilt_yields",
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_gilt_yields_data():
        """Collect UK gilt yields (5Y, 10Y, 20Y) from Bank of England IADB."""
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
        task_id="collect_boe_yield_curves_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
            "openpyxl>=3.1.0",  # Required for Excel file parsing
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_boe_yield_curves",
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_boe_yield_curves_data():
        """Collect comprehensive BoE yield curves (80+ maturities, 4 yield types) from Bank of England ZIP files."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_boe_yield_curves

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_boe_yield_curves(database_url=database_url)
            logger.info(f"Successfully collected {result} BoE comprehensive yield curves records")
            return result
        except Exception as e:
            logger.error(f"Error collecting BoE yield curves data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_uk_swap_rates_data",
        requirements=[
            "marketinsights-collector[investiny]@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_uk_swap_rates",
        queue="celery",  # Use Celery workers with pre-loaded secrets
    )
    def collect_uk_swap_rates_data():
        """Collect UK GBP Interest Rate Swap curves (2Y, 5Y, 10Y, 30Y) from investiny."""
        import logging
        import os
        from data_collectors.uk_swap_rates import collect_uk_swap_rates

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_uk_swap_rates(database_url=database_url)
            logger.info(f"Successfully collected {result} UK swap rates records")
            return result
        except Exception as e:
            logger.error(f"Error collecting UK swap rates data: {str(e)}")
            raise


    # Define task dependencies
    tables_task = create_uk_tables()
    
    # UK Economic indicators
    uk_cpi_task = collect_uk_cpi_data()
    uk_unemployment_task = collect_uk_unemployment_data()
    uk_gdp_task = collect_uk_gdp_data()
    uk_bank_rate_task = collect_uk_bank_rate_data()
    
    # UK Market data  
    ftse_100_task = collect_ftse_100_data()
    
    # UK gilt yields data
    uk_gilt_yields_task = collect_uk_gilt_yields_data()
    
    # BoE comprehensive yield curves data  
    boe_yield_curves_task = collect_boe_yield_curves_data()
    
    # UK swap rates data
    uk_swap_rates_task = collect_uk_swap_rates_data()
    
    # Set dependencies - all collectors depend on tables being created
    tables_task >> [
        uk_cpi_task, uk_unemployment_task, uk_gdp_task, 
        uk_bank_rate_task, ftse_100_task, uk_gilt_yields_task, 
        boe_yield_curves_task, uk_swap_rates_task
    ]


# Create the DAG instance
uk_metrics_dag = uk_metrics_data_pipeline()