import pendulum

# from kubernetes.client import models as k8s

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

dag = DAG(
    "influxdb_backup",
    schedule_interval="0 1 * * 0",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    is_paused_upon_creation=False,
    tags=["storage"],
)

influxdb_backup = KubernetesPodOperator(
    dag=dag,
    pod_template_file="/opt/airflow/sync/smart-home-config/workloads/airflow/pod_templates/influxdb_pod_template.yaml",
    task_id="influxdb_backup",
    namespace="storage",
    name="influxdb-backup",
    is_delete_operator_pod=True,
    hostnetwork=False,
    get_logs=True,
)
