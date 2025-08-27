import pendulum
from airflow.decorators import dag, task

connectionData = {
    "login": "{{ conn.postgres.login }}",
    "password": "{{ conn.postgres.password }}",
    "host": "{{ conn.postgres.host }}",
    "port": "{{ conn.postgres.port }}",
}

default_args = {"email": "wilkobets@googlemail.com", "email_on_failure": True}


@dag(
    schedule_interval="0 21 * * *",
    default_args=default_args,
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
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
            "marketinsights-dbschema@git+https://github.com/cwilko/marketinsights-dbschema.git",
        ],
        system_site_packages=False,
    )
    def extract_and_load(conn):
        """
        #### Extract task
        """
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
            host=conn["host"],
            dbName="squirrel",
            port=conn["port"],
            user=conn["login"],
            pw=conn["password"],
        )

        result = db.upsert(PropertyIndex(data, regionName).getDict(), update=True)

        print(f"Complete: Inserted - {result['inserted']}, Updated {result['updated']}")

    extract_and_load(connectionData)


dag = housemarket_etl()
