import pendulum
from airflow.decorators import dag, task


@dag(
    schedule_interval="0 22 * * *",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["marketinsights"],
)
def options_data_etl():
    """
    ### TaskFlow API Tutorial Documentation
    This ETL pipeline extracts options data from barchart.com and loads to a price store
    """

    @task.virtualenv(
        task_id="extract_and_load",
        requirements=[
            "marketinsights-price-aggregator@git+https://github.com/cwilko/marketinsights-price-aggregator.git",
            #           "marketinsights-remote@git+https://github.com/cwilko/marketinsights-remote.git",
        ],
        system_site_packages=False,
    )
    def extract_and_load():
        """
        #### Extract task
        A simple Extract task to get data ready for the rest of the data
        pipeline. In this case, getting data is simulated by reading from a
        hardcoded JSON string.
        """
        import json
        from datetime import datetime, date, timedelta
        from marketinsights.remote.datastore import MIDataStoreRemote
        import marketinsights.utils.store as priceStore

        ds_location = "/opt/airflow/sync/smart-home-config/resources/airflow/dags/datasources/datasources.json"
        with open(ds_location) as json_file:
            ds_config = json.load(json_file)

        # Local Options
        mds = MIDataStoreRemote(location="http://pricestore.192.168.1.203.nip.io")
        priceStore.saveHistoricalOptionData(
            mds,
            ds_config,
            start=str(date.today()),
            end=str(date.today() + timedelta(days=1)),
            records=1,
            refreshUnderyling=True,
            debug=False,
        )

        print("Updates complete at " + str(datetime.utcnow()))

    extract_and_load()


options_dag = options_data_etl()
