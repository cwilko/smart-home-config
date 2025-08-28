import pendulum
from airflow.models import DAG
from airflow.operators.bash import BashOperator
from kubernetes.client import models as k8s

dag = DAG(
    "influxdb_backup_clean",
    schedule_interval="0 3 * * 0",
    start_date=pendulum.datetime(2023, 1, 1, tz="Europe/London"),
    catchup=False,
    tags=["storage"],
)

executor_env_overrides = {
    "pod_override": k8s.V1Pod(
        spec=k8s.V1PodSpec(
            containers=[
                k8s.V1Container(
                    name="base",
                    env_from=[
                        # Keep existing secrets from pod template
                        k8s.V1EnvFromSource(
                            secret_ref=k8s.V1SecretEnvSource(
                                name="airflow-secret"
                            )
                        ),
                        k8s.V1EnvFromSource(
                            secret_ref=k8s.V1SecretEnvSource(
                                name="airflow-connections"
                            )
                        ),
                        # Add new secret
                        k8s.V1EnvFromSource(
                            secret_ref=k8s.V1SecretEnvSource(
                                name="airflow-nas-secret"
                            )
                        )
                    ]
                )
            ]
        )
    )
}

command = "/opt/airflow/sync/smart-home-config/workloads/airflow/dags/influxdb-backup-clean/backup-clean.sh "

delete_backups = BashOperator(
    task_id="delete_backups",
    bash_command=command,
    executor_config=executor_env_overrides,
    dag=dag,
)
