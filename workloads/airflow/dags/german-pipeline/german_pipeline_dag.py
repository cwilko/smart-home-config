import pendulum
from airflow.decorators import dag, task


@dag(
    schedule_interval="0 22 * * 1-5",  # 5 PM ET (10 PM UTC) weekdays - after European market close
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["german", "bund", "yields", "bundesbank", "finance"],
    max_active_runs=1,
)
def german_data_pipeline():
    """
    ### German Economic Data Collection Pipeline
    
    Collects German government bond and economic data for European market analysis:
    
    **German Data Sources (1 metric - expandable):**
    - German Bund Yield Curves (1-30Y) - Bundesbank StatisticDownload API
    
    **Data Types Collected:**
    - Daily German government bond yields across full maturity spectrum (1-30 years)
    - Historical data from 1997 to present (~28 years of data)
    - ~200,000+ daily yield observations covering all maturities
    
    **Future Expansion Planned:**
    - German inflation data (Destatis)
    - German unemployment rate (Destatis)
    - German GDP data (Destatis)
    - ECB policy rates
    - German corporate bond spreads
    
    **Supporting Analysis:**
    - Cross-market yield curve analysis (US, UK, German)
    - European sovereign bond spread analysis
    - German yield curve shape and steepening/flattening trends
    - ECB monetary policy transmission analysis
    
    **Total: 1 comprehensive dataset (206,710+ records) collected daily on weekdays**
    
    Data integrates with existing US (Treasury) and UK (BoE) yield curves for 
    comprehensive three-region fixed income analysis covering the world's largest
    bond markets.
    """

    @task.virtualenv(
        task_id="create_german_database_tables",
        requirements=[
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=True,
        queue="celery",  
    )
    def create_german_tables():
        """Create German economic data database tables if they don't exist."""
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
                sql_path = "/opt/airflow/sync/smart-home-config/workloads/airflow/dags/german-pipeline/config/german_tables.sql"
                with open(sql_path, 'r') as f:
                    sql = f.read()
                
                # Execute SQL statements separately to avoid transaction issues
                statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
                for i, statement in enumerate(statements):
                    try:
                        cur.execute(statement)
                        conn.commit()
                        logger.info(f"Executed German table statement {i+1}/{len(statements)}")
                    except Exception as e:
                        logger.error(f"Failed to execute statement {i+1}: {statement[:100]}...")
                        logger.error(f"Error: {str(e)}")
                        raise
                        
                logger.info("German database tables created successfully")
                
        except Exception as e:
            logger.error(f"Error creating German tables: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @task.virtualenv(
        task_id="collect_german_bund_yields",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "pandas>=2.0.0",
            "requests>=2.31.0",
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",
    )
    def collect_german_bund_yields():
        """Collect German Bund yield curve data (1-30 years) from Bundesbank."""
        import logging
        import os
        from data_collectors.economic_indicators import collect_german_bund_yields

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            result = collect_german_bund_yields(database_url=database_url)
            logger.info(f"Successfully collected {result} German Bund yield records")
            return result
        except Exception as e:
            logger.error(f"Error collecting German Bund yield data: {str(e)}")
            raise

    # Define task dependencies
    tables_task = create_german_tables()
    
    # German data collection tasks
    bund_yields_task = collect_german_bund_yields()
    
    # Set dependencies - collectors run after tables are created
    tables_task >> bund_yields_task


# Create the DAG instance
german_pipeline_dag = german_data_pipeline()