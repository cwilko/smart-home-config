import pendulum
from airflow.decorators import dag, task
import json
from kubernetes import client as k8s

# Executor configuration for Chrome web scraping tasks
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
    schedule_interval="0 23 * * 1-5",  # 6 PM ET (11 PM UTC) weekdays only - after UK markets close
    start_date=pendulum.datetime(2024, 1, 1, tz="US/Eastern"),
    catchup=False,
    tags=["uk", "finance", "gilt", "web-scraping"],
    max_active_runs=1,
)
def gilt_market_data_pipeline():
    """
    ### UK Gilt Market Data Pipeline
    
    Collects real-time gilt market prices from Hargreaves Lansdown broker using Selenium web scraping.
    
    **Data collected:**
    - **Nominal Gilts**: Bond names, clean/dirty prices, YTM, after-tax YTM
    - **Index-Linked Gilts**: Real yields, after-tax real yields, inflation assumptions
    - Coupon rates and maturity dates
    - Accrued interest calculations
    
    **Technology:**
    - Chrome-based web scraping using Selenium WebDriver
    - ARM64 optimized ChromeDriver via custom Docker image
    - Kubernetes executor with dedicated pod template
    
    Data is stored in PostgreSQL for UK economic dashboard visualization and breakeven inflation analysis.
    """

    @task.virtualenv(
        task_id="collect_gilt_market_prices_data",
        requirements=[
            "marketinsights-collector[gilt_market]@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=True,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_gilt_market_prices",
        queue="kubernetes",
        executor_config=executor_env_overrides,
    )
    def collect_gilt_market_prices_data():
        """Collect real-time gilt market prices from Hargreaves Lansdown broker."""
        import logging
        import os
        from data_collectors.gilt_market_data import collect_gilt_market_prices

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info("Starting gilt market data collection (using Chrome pod override)")

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_gilt_market_prices(database_url=database_url)
            logger.info(f"Successfully collected {result} gilt market price records")
            return result
        except Exception as e:
            logger.error(f"CRITICAL: Error collecting gilt market prices: {str(e)}")
            raise RuntimeError(f"Gilt market data collection failed: {e}") from e

    @task.virtualenv(
        task_id="collect_index_linked_gilt_prices_data",
        requirements=[
            "marketinsights-collector[gilt_market]@git+https://github.com/cwilko/marketinsights-collector.git",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=True,
        pip_install_options=["--no-user"],
        venv_cache_path="/tmp/venv_index_linked_gilt_prices",
        queue="kubernetes",
        executor_config=executor_env_overrides,
    )
    def collect_index_linked_gilt_prices_data():
        """Collect real-time index-linked gilt prices from Hargreaves Lansdown broker."""
        import logging
        import os
        from data_collectors.gilt_market_data import collect_index_linked_gilt_prices

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info("Starting index-linked gilt market data collection (using Chrome pod override)")

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_index_linked_gilt_prices(database_url=database_url)
            logger.info(f"Successfully collected {result} index-linked gilt price records")
            return result
        except Exception as e:
            logger.error(f"CRITICAL: Error collecting index-linked gilt prices: {str(e)}")
            raise RuntimeError(f"Index-linked gilt data collection failed: {e}") from e

    # Execute the tasks (can run in parallel since they scrape different pages)
    gilt_market_task = collect_gilt_market_prices_data()
    index_linked_gilt_task = collect_index_linked_gilt_prices_data()


# Create the DAG instance
gilt_market_dag = gilt_market_data_pipeline()