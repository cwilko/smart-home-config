import pendulum
from airflow.decorators import dag, task


@dag(
    schedule_interval="0 2 * * *",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    is_paused_upon_creation=False,
    tags=["storage"],
)
def influxdb_backup_clean():
    """
    ### Clean out old backups of influxDB
    This ETL pipeline extracts options data from barchart.com and loads to a price store
    """

    @task()
    def delete_backups():
        """
        #### Delete Backups
        """

        print("Date is " + "{{ ds }}")
        print("Airflow db: " + "{{ conn.airflow_db.host }}")
        print("Connection details: " + "{{ conn.nas.host }}")

    delete_backups()


dag = influxdb_backup_clean()
