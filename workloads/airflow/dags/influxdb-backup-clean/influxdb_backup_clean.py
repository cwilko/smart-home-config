import pendulum
from airflow.models import DAG
from airflow.operators.bash import BashOperator

dag = DAG(
    "influxdb_backup_clean",
    schedule_interval="0 3 * * 0",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    is_paused_upon_creation=False,
    tags=["storage"],
)

command = "/opt/airflow/sync/smart-home-config/workloads/airflow/dags/influxdb-backup-clean/backup-clean.sh "

delete_backups = BashOperator(
    task_id="delete_backups",
    bash_command=command,
    env={
        "NAS_USER": "{{ conn.nas.login }}",
        "NAS_PASSWORD": "{{ conn.nas.password }}",
        "NAS_HOST": "{{ conn.nas.host }}",
    },
    dag=dag,
)
