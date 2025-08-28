import pendulum
from airflow.decorators import dag, task
from kubernetes.client import models as k8s
import json

# Pod override configuration for database environment variables
executor_env_overrides = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    env_from=[
                        # Add database connection secrets
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
    schedule_interval="0 23 * * 1-5",  # 6 PM ET (11 PM UTC) weekdays only
    start_date=pendulum.datetime(2024, 1, 1, tz="US/Eastern"),
    catchup=False,
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
        executor_config=executor_env_overrides,
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
        executor_config=executor_env_overrides,
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
        executor_config=executor_env_overrides,
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
        executor_config=executor_env_overrides,
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
        task_id="collect_treasury_yields",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        system_site_packages=False,
        executor_config=executor_env_overrides,
    )
    def collect_treasury_yields():
        """Collect Treasury yield curve data from FRED API."""
        import logging
        from data_collectors.economic_indicators import FREDCollector
        from datetime import datetime

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Treasury yield series from FRED with maturity mapping
        yield_series = {
            "DGS1MO": "1M",   # 1-Month
            "DGS3MO": "3M",   # 3-Month  
            "DGS6MO": "6M",   # 6-Month
            "DGS1": "1Y",     # 1-Year
            "DGS2": "2Y",     # 2-Year
            "DGS5": "5Y",     # 5-Year
            "DGS10": "10Y",   # 10-Year
            "DGS30": "30Y"    # 30-Year
        }

        try:
            database_url = os.getenv('DATABASE_URL')
            collector = FREDCollector(database_url)
            success_count = 0
            
            # Fetch each yield series from FRED
            for series_id, maturity in yield_series.items():
                try:
                    logger.info(f"Fetching {maturity} Treasury yields ({series_id})")
                    series_data = collector.get_series_data(series_id)
                    
                    for item in series_data:
                        try:
                            if item["value"] == ".":  # FRED uses "." for missing values
                                continue
                                
                            data = {
                                "date": datetime.strptime(item["date"], "%Y-%m-%d").date(),
                                "maturity": maturity,
                                "yield_rate": float(item["value"])
                            }
                            
                            if collector.upsert_data("treasury_yields", data, conflict_columns=["date", "maturity"]):
                                success_count += 1
                                
                        except Exception as e:
                            logger.warning(f"Error processing {series_id} item: {str(e)}")
                            continue
                            
                    logger.info(f"Successfully processed {maturity} yields from {series_id}")
                        
                except Exception as e:
                    logger.warning(f"Error fetching {series_id}: {str(e)}")
                    continue
                
            logger.info(f"Successfully processed {success_count} total Treasury yield records")
            return success_count
                
        except Exception as e:
            logger.error(f"Error collecting Treasury yield data: {str(e)}")
            raise

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