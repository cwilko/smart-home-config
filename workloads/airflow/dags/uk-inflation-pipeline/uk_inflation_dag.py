import pendulum
from airflow.decorators import dag, task


@dag(
    schedule_interval="0 11 * * *",  # 11 AM UTC daily (6 AM EST / 11 AM BST) 
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["uk", "inflation", "economics", "ons"],
    max_active_runs=1,
)
def uk_inflation_data_pipeline():
    """
    ### UK Inflation Data Pipeline
    
    Collects comprehensive UK inflation data from ONS MM23.csv with complete COICOP hierarchy:
    
    **Data collected:**
    - **CPI (Consumer Price Index)**: 316 categories across 4 COICOP levels
    - **CPIH (CPI including owner occupiers' housing costs)**: 318 categories (adds housing costs)
    - **RPI (Retail Price Index)**: Headline index for historical comparison
    
    **COICOP hierarchy (318 total categories):**
    - Level 1: 13 major groups (Food, Housing, Transport, etc.)
    - Level 2: 42 groups (includes CPIH housing categories 04.2, 04.9)
    - Level 3: 71 classes  
    - Level 4: 192 sub-classes
    
    **Key features:**
    - Downloads latest MM23.csv directly from ONS website (~23MB)
    - Processes all 318 COICOP categories with alphabetic suffixes (07.1.1A, 07.1.1B)
    - Collects ~130,000+ inflation data points with weights
    - Validates strict data integrity (318 categories expected)
    - Stores in optimized schema for YoY rate calculations and contribution analysis
    
    **Database tables:**
    - `uk_inflation_coicop_hierarchy`: 4-level COICOP classification with parent-child relationships
    - `uk_inflation_price_data`: Monthly index values and weights for all categories
    - Views: `uk_inflation_yoy_ready`, `uk_inflation_hierarchy_tree`
    
    Data is updated daily to capture latest ONS releases.
    """

    @task.virtualenv(
        task_id="create_uk_inflation_tables",
        requirements=[
            "psycopg2-binary>=2.9.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",
    )
    def create_tables():
        """Create UK inflation database tables with COICOP hierarchy and price data storage."""
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
                sql_path = "/opt/airflow/sync/smart-home-config/workloads/airflow/dags/uk-inflation-pipeline/config/uk_inflation_tables.sql"
                with open(sql_path, 'r') as f:
                    sql = f.read()
                
                cur.execute(sql)
                conn.commit()
                logger.info("UK inflation database tables created successfully")
                logger.info("Tables: uk_inflation_coicop_hierarchy, uk_inflation_price_data")
                logger.info("Views: uk_inflation_yoy_ready, uk_inflation_hierarchy_tree")
                
        except Exception as e:
            logger.error(f"Error creating UK inflation tables: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @task.virtualenv(
        task_id="collect_uk_inflation_data",
        requirements=[
            "marketinsights-collector@git+https://github.com/cwilko/marketinsights-collector.git",
            "requests>=2.28.0",
            "pandas>=1.5.0",
        ],
        system_site_packages=False,
        pip_install_options=["--no-user"],
        queue="celery",
    )
    def collect_uk_inflation_data():
        """
        Collect UK inflation data by downloading latest MM23.csv from ONS and processing all COICOP categories.
        
        Downloads ~23MB MM23.csv file and processes:
        - 318 COICOP categories (CPI: 316, CPIH: 318 with housing costs)
        - Complete 4-level hierarchy with parent-child relationships  
        - ~130,000+ monthly inflation data points with weights
        - Strict validation ensuring all expected categories are found
        """
        import logging
        import os
        from data_collectors.uk_inflation_data import collect_uk_inflation_data

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        try:
            database_url = os.getenv('DATABASE_URL')
            
            # Download latest MM23.csv from ONS and collect data
            logger.info("Starting UK inflation data collection from ONS MM23.csv...")
            result = collect_uk_inflation_data(database_url=database_url)
            
            logger.info(f"Successfully collected {result} UK inflation records")
            logger.info("Data includes CPI (316 categories), CPIH (318 categories), and RPI")
            logger.info("Complete COICOP hierarchy with 4 levels processed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error collecting UK inflation data: {str(e)}")
            raise

    # Define task dependencies
    tables_task = create_tables()
    inflation_task = collect_uk_inflation_data()
    
    # Set dependency - data collection depends on tables being created
    tables_task >> inflation_task


# Create the DAG instance
uk_inflation_dag = uk_inflation_data_pipeline()