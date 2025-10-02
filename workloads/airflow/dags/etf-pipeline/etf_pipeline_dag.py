import pendulum
from airflow.decorators import dag, task
import json
from kubernetes import client as k8s

# Executor configuration for Chrome web scraping tasks (Vanguard ETF collection)
executor_env_overrides = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            node_selector={"arm64": "true"},
            containers=[
                k8s.V1Container(
                    name="base",
                    image="wilkobets/airflow-chrome:latest",
                    env_from=[
                        k8s.V1EnvFromSource(
                            secret_ref=k8s.V1SecretEnvSource(
                                name="airflow-econometrics-secret"
                            )
                        )
                    ]
                )
            ]
        )
    )
}


@dag(
    schedule_interval="0 23 * * 1-5",  # 6 PM ET (11 PM UTC) weekdays - after UK market close
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["etf", "nav", "arbitrage", "uk", "finance"],
    max_active_runs=1,
)
def etf_data_pipeline():
    """
    ### ETF Data Collection Pipeline
    
    Collects ETF and NAV data for UK market analysis and arbitrage strategies:
    
    **ETF Data Sources (4 metrics):**
    - iShares Core UK Gilts ETF (IGLT) - Historical NAV data
    - iShares UK Index-Linked Gilts ETF (INXG) - Inflation-protected bonds ETF NAV data
    - Vanguard UK Gilt UCITS ETF (VGOV) - Historical NAV and market prices
    - SSGA SPDR Bloomberg UK Gilt ETF (GLTY) - Historical NAV data
    
    **Data Types Collected:**
    - Historical NAV values for premium/discount analysis
    - Historical price data from investing.com for arbitrage analysis
    - Current holdings for duration and credit analysis
    - Performance metrics for ETF evaluation
    
    **Supporting Strategies:**
    - ETF arbitrage (premium/discount to NAV)
    - Cross-ETF analysis (nominal vs index-linked)
    - Creation/redemption flow monitoring
    - Breakeven inflation strategies via IGLT vs INXG
    
    **Total: 5 ETF datasets collected daily on weekdays (4 NAV + 1 price dataset)**
    
    Data supports the Gilt Market Analysis Guide arbitrage strategies and integrates
    with comprehensive UK yield curves for professional-grade fixed income analysis.
    """

    @task.virtualenv(
        task_id="create_etf_database_tables",
        requirements=[
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=True,
        queue="celery",
        retries=1,  # Retry once if task fails
    )
    def create_etf_tables():
        """Create ETF database tables if they don't exist."""
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
                sql_path = "/opt/airflow/sync/smart-home-config/workloads/airflow/dags/etf-pipeline/config/etf_tables.sql"
                with open(sql_path, 'r') as f:
                    sql = f.read()
                
                # Execute SQL statements separately to avoid transaction issues
                statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
                for i, statement in enumerate(statements):
                    try:
                        cur.execute(statement)
                        conn.commit()
                        logger.info(f"Executed ETF table statement {i+1}/{len(statements)}")
                    except Exception as e:
                        logger.error(f"Failed to execute statement {i+1}: {statement[:100]}...")
                        logger.error(f"Error: {str(e)}")
                        raise
                        
                logger.info("ETF database tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating ETF tables: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @task.virtualenv(
        task_id="collect_iglt_etf_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
            "openpyxl>=3.1.0",  # For modern Excel files
            "xlrd>=2.0.1",      # For legacy Excel files
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",
        retries=1,  # Retry once if task fails
    )
    def collect_iglt_etf_data():
        """Collect iShares Core UK Gilts ETF (IGLT) NAV and holdings data."""
        import logging
        import os
        from data_collectors.etf_data import collect_ishares_etf_nav

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_ishares_etf_nav(database_url=database_url, etf_tickers=['IGLT'])
            logger.info(f"Successfully collected {result} IGLT ETF NAV records")
            return result
        except Exception as e:
            logger.error(f"Error collecting IGLT ETF data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_inxg_etf_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0", 
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
            "openpyxl>=3.1.0",
            "xlrd>=2.0.1",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",
        retries=1,  # Retry once if task fails
    )
    def collect_inxg_etf_data():
        """Collect iShares UK Index-Linked Gilts ETF (INXG) NAV and holdings data."""
        import logging
        import os
        from data_collectors.etf_data import collect_ishares_etf_nav

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_ishares_etf_nav(database_url=database_url, etf_tickers=['INXG'])
            logger.info(f"Successfully collected {result} INXG ETF NAV records")
            return result
        except Exception as e:
            logger.error(f"Error collecting INXG ETF data: {str(e)}")
            raise


    @task.virtualenv(
        task_id="collect_vgov_etf_data",
        requirements=[
            "marketinsights-collector[selenium]@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
            "openpyxl>=3.1.0",
            "undetected-chromedriver>=3.5.0",
        ],
        system_site_packages=True,
        pip_install_options=["--no-user"],
        queue="kubernetes",
        executor_config=executor_env_overrides,
        retries=1,  # Retry once if task fails
    )
    def collect_vgov_etf_data():
        """Collect Vanguard UK Gilt UCITS ETF (VGOV) historical price data using Selenium."""
        import logging
        import os
        from data_collectors.etf_data import collect_vanguard_etf_data

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info("Starting Vanguard ETF data collection (using Chrome pod override)")

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_vanguard_etf_data(database_url=database_url, etf_tickers=['VGOV'])
            logger.info(f"Successfully collected {result} VGOV ETF price records")
            return result
        except Exception as e:
            logger.error(f"Error collecting VGOV ETF data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_glty_etf_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
            "openpyxl>=3.1.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",
        retries=1,  # Retry once if task fails
    )
    def collect_glty_etf_data():
        """Collect SSGA SPDR Bloomberg UK Gilt ETF (GLTY) historical NAV data."""
        import logging
        import os
        from data_collectors.etf_data import collect_ssga_etf_data

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_ssga_etf_data(database_url=database_url, etf_tickers=['GLTY'])
            logger.info(f"Successfully collected {result} GLTY ETF NAV records")
            return result
        except Exception as e:
            logger.error(f"Error collecting GLTY ETF data: {str(e)}")
            raise

    @task.virtualenv(
        task_id="collect_etf_prices_data",
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
        queue="celery",  # Use Celery workers with pre-loaded secrets
        retries=1,  # Retry once if task fails
    )
    def collect_etf_prices_data():
        """Collect ETF price data from investing.com for all 4 ETF tickers."""
        import logging
        import os
        from data_collectors.etf_prices import collect_etf_prices

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_etf_prices(database_url=database_url, etf_tickers=['IGLT', 'INXG', 'VGOV', 'GLTY'])
            logger.info(f"Successfully collected {result} ETF price records")
            return result
        except Exception as e:
            logger.error(f"Error collecting ETF price data: {str(e)}")
            raise

    # Define task dependencies
    tables_task = create_etf_tables()
    
    # ETF data collection tasks
    iglt_task = collect_iglt_etf_data()
    inxg_task = collect_inxg_etf_data()
    vgov_task = collect_vgov_etf_data()
    glty_task = collect_glty_etf_data()
    etf_prices_task = collect_etf_prices_data()
    
    # Set dependencies - all collectors run in parallel after tables are created
    tables_task >> [iglt_task, inxg_task, vgov_task, glty_task, etf_prices_task]


# Create the DAG instance
etf_pipeline_dag = etf_data_pipeline()