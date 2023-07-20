import pendulum
from airflow.decorators import dag, task

connectionData = {
    "login": "{{ conn.postgres.login }}",
    "password": "{{ conn.postgres.password }}",
    "host": "{{ conn.postgres.host }}",
    "port": "{{ conn.postgres.port }}",
}


@dag(
    schedule_interval="0 21 * * *",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    is_paused_upon_creation=False,
    tags=["housemarket"],
)
def housemarket_etl():
    """
    ### Extract HouseMarket Data
    """

    @task.virtualenv(
        task_id="extract_and_load",
        requirements=[
            "housemarket-scraper@git+https://github.com/cwilko/housemarket-scraper.git",
        ],
        system_site_packages=False,
    )
    def extract_and_load(conn):
        """
        #### Extract task
        """
        from housemarket.extract import HouseScraper
        from housemarket.load import HouseDatabase
        from housemarket.transform import PropertyIndex

        regionCode = "5E91999"  # NewForest
        regionName = "NewForest"

        data = HouseScraper().requestData(
            regionCode, maxPrice=200000, maxDaysSinceAdded=None
        )

        db = HouseDatabase(
            host=conn["host"],
            dbName="squirrel",
            port=conn["port"],
            user=conn["login"],
            pw=conn["password"],
        )

        for x in PropertyIndex(data, regionName).index:
            db.addEntry(x)

        print("Updates complete")

    extract_and_load(connectionData)


dag = housemarket_etl()
