import pendulum
from airflow.decorators import dag, task

@dag(
    dag_id="celery_test_fed_funds",
    schedule=None,  # Manual trigger only for testing
    start_date=pendulum.datetime(2024, 1, 1, tz="US/Eastern"),
    catchup=False,
    tags=["test", "celery", "economics"],
    max_active_runs=1,
    description="Test DAG for Celery execution of Fed Funds Rate collection"
)
def celery_test_pipeline():
    """
    ### Celery Test Pipeline
    
    Test DAG for Fed Funds Rate collection via Celery:
    - Uses persistent Celery workers with shared secrets
    - Manual trigger only for safe testing
    - Same data collection logic as main econometrics pipeline
    - Tests performance and functionality of Celery execution
    """

    @task.virtualenv(
        task_id="collect_fed_funds_celery",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
        ],
        queue="celery",  # Route to Celery workers instead of Kubernetes
        # No executor_config needed - secrets come from worker environment
    )
    def collect_fed_funds_celery():
        """Collect daily Federal Funds Rate data via Celery worker."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_daily_fed_funds_rate

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')  # From worker environment
            if not database_url:
                raise ValueError("DATABASE_URL not found in worker environment")
            
            fred_api_key = os.getenv('FRED_API_KEY')  # From worker environment
            if not fred_api_key:
                raise ValueError("FRED_API_KEY not found in worker environment")
            
            logger.info("Starting Fed Funds Rate collection via Celery worker")
            logger.info(f"DATABASE_URL available: {'Yes' if database_url else 'No'}")
            logger.info(f"FRED_API_KEY available: {'Yes' if fred_api_key else 'No'}")
            
            result = collect_daily_fed_funds_rate(database_url=database_url)
            logger.info(f"Successfully collected {result} Fed Funds Rate records via Celery")
            return result
        except Exception as e:
            logger.error(f"Error collecting Fed Funds Rate data via Celery: {str(e)}")
            raise

    # Single Celery task
    collect_fed_funds_celery()

# Create the DAG instance
celery_test_dag = celery_test_pipeline()