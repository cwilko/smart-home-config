import pendulum
from airflow.decorators import dag, task


@dag(
    schedule_interval="0 2 * * *",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    is_paused_upon_creation=False,
    tags=["marketinsights"],
)
def influxdb_backup_clean():
    """
    ### Clean out old backups of influxDB
    This ETL pipeline extracts options data from barchart.com and loads to a price store
    """

    @task.virtualenv(
        task_id="delete_backups",
        system_site_packages=False,
    )
    def delete_backups():
        """
        #### Delete Backups
        """

        print("Connection details " + {{conn.NAS.host}})

    delete_backups()


dag = influxdb_backup_clean()
