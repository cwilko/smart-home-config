import pendulum
from airflow import DAG
from airflow.decorators import task
from kubernetes.client import models as k8s

# Pod override configuration
executor_env_overrides = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    env_from=[
                        # Add new secret
                        k8s.V1EnvFromSource(
                            secret_ref=k8s.V1SecretEnvSource(
                                name="airflow-postgres-secret"
                            )
                        )
                    ]
                )
            ]
        )
    )
}

with DAG(
    dag_id="housemarket_etl",
    schedule_interval="0 21 * * *",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    tags=["housemarket"],
    doc_md="### Extract HouseMarket Data",
) as dag:

    @task.virtualenv(
        task_id="extract_and_load",
        requirements=[
            "housemarket-scraper@git+https://github.com/cwilko/housemarket-scraper.git",
            "marketinsights-dbschema@git+https://github.com/cwilko/marketinsights-dbschema.git",
        ],
        system_site_packages=False,
        executor_config=executor_env_overrides,
    )
    def extract_and_load():
        """
        #### Extract task
        """
        import os
        from housemarket.extract import HouseScraper
        from marketinsights.database import MIDatabase
        from marketinsights.dbschema import House
        from housemarket.transform import PropertyIndex
        
        regionCode = "5E91999"  # NewForest
        regionName = "NewForest"

        data = HouseScraper().requestData(
            regionCode, maxPrice=200000, maxDaysSinceAdded=None
        )

        db = MIDatabase(
            dbClass=House,
            host=os.getenv('POSTGRES_HOST'),
            dbName=os.getenv('POSTGRES_DB'),
            port=os.getenv('POSTGRES_PORT'),
            user=os.getenv('POSTGRES_USER'),
            pw=os.getenv('POSTGRES_PASSWORD'),
        )

        result = db.upsert(PropertyIndex(data, regionName).getDict(), update=True)

        print(f"Complete: Inserted - {result['inserted']}, Updated {result['updated']}")

    extract_and_load()
