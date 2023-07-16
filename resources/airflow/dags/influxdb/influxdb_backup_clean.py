import pendulum
from airflow.models import DAG
from airflow.operators.bash import BashOperator

dag = DAG(
    schedule_interval="0 2 * * *",
    catchup=False,
    is_paused_upon_creation=False,
    tags=["storage"],
)

cmd_command = "echo '{{ ds }}' '{{ conn.airflow_db.host }}' '{{ conn.nas.host }}'"

delete_backups = BashOperator(
    task_id="delete_backups", bash_command=cmd_command, dag=dag
)
