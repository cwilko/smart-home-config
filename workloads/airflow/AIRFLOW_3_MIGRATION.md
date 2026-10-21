# Airflow 2.9.3 → 3.x Migration Assessment

Assessment date: 2026-10-15. Current state: Airflow 2.9.3, image `wilkobets/airflow:latest` built from a fork of apache/airflow (see `my-image-build.yml` in the `airflow` repo). 9 DAGs, ~1,910 LOC, under `dags/`.

This is a planning document, not a changelog — nothing below has been applied yet. Re-verify findings against whatever Airflow 3.x point release you actually target, since behavior can shift between 3.0 and later 3.x releases.

## Blocking infra changes (outside the DAG files themselves)

### 1. `CeleryKubernetesExecutor` is removed in Airflow 3

`deployment.yaml` sets `AIRFLOW__CORE__EXECUTOR=CeleryKubernetesExecutor` (lines ~45, ~87). This executor (and `LocalKubernetesExecutor`) no longer exists in Airflow 3 — replaced by multi-executor support: `AIRFLOW__CORE__EXECUTOR=CeleryExecutor,KubernetesExecutor`, with tasks that need Kubernetes declaring it explicitly via `executor="KubernetesExecutor"` instead of being routed by `queue='kubernetes'` to `AIRFLOW__CELERY_KUBERNETES_EXECUTOR__KUBERNETES_QUEUE`.

Tasks currently relying on the queue-routing trick, that will need an explicit `executor=` kwarg instead:

- `dags/influxdb-backup/influxdb_backup.py` — `KubernetesPodOperator(..., queue='kubernetes')`
- `dags/etf-pipeline/etf_pipeline_dag.py` — `@task.virtualenv(..., executor_config={"pod_override": ...})` (Selenium/Chrome)
- `dags/gilt-market-data/uk_bond_market_dag.py` — same pattern
- `dags/housemarket-etl/housemarket-etl.py` — same pattern

This is the single largest piece of work — a config + per-task change, not a Python syntax fix.

### 2. Webserver auth manager

`af-config.yaml` ships a `webserver_config.py` using FAB: `from airflow.www.fab_security.manager import AUTH_DB`, with `AUTH_ROLE_PUBLIC = 'Admin'` (UI fully open, no login required). Airflow 3's default auth manager is the new `SimpleAuthManager`, not FAB.

Decision needed before migrating:
- **Keep FAB**: install `apache-airflow-providers-fab`, set `[core] auth_manager = airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager`.
- **Move to SimpleAuthManager**: different config/UX (e.g. static user file) — worth it as a chance to reconsider the fully-open `AUTH_ROLE_PUBLIC='Admin'` setting.

Also: `airflow webserver` becomes `airflow api-server`, and the DAG processor becomes its own standalone process (`airflow dag-processor`) rather than being embedded in the scheduler. Update container commands/args in `deployment.yaml` accordingly.

### 3. Rebuild the custom Airflow image

In the separate `airflow` fork repo, `.github/workflows/my-image-build.yml` currently builds with `AIRFLOW_VERSION=2.9.3` and extras `cncf-kubernetes,virtualenv,postgres,redis,celery`. For Airflow 3:

- Bump `AIRFLOW_VERSION` to the target 3.x release.
- Re-validate the extras list: `BashOperator`, `PythonOperator`, and `PythonVirtualenvOperator` (and therefore the `@task.virtualenv` decorator used by 8 of the 9 DAGs) move out of `airflow-core` into `apache-airflow-providers-standard` in Airflow 3. Confirm whether the extras mechanism needs an explicit `standard` entry added.
- Confirm `apache-airflow-providers-cncf-kubernetes` resolves to an Airflow-3-compatible release (used directly by `influxdb_backup.py`, and indirectly by the pod-override tasks).

`README-custom.md` in that repo is already stale relative to the current workflow (says Airflow 2.6.2 and an older extras list) — update it together with the version bump.

## DAG code change — mechanical, affects all 9 files

### 4. `schedule_interval=` → `schedule=`

`schedule_interval` is removed in Airflow 3 (flagged by `ruff --select AIR301`). Every DAG uses the old kwarg:

| File | Line |
|---|---|
| `dags/econometrics-pipeline/econometrics_dag.py` | 7 |
| `dags/etf-pipeline/etf_pipeline_dag.py` | 29 |
| `dags/german-pipeline/german_pipeline_dag.py` | 6 |
| `dags/gilt-market-data/uk_bond_market_dag.py` | 29 |
| `dags/housemarket-etl/housemarket-etl.py` | 29 |
| `dags/influxdb-backup/influxdb_backup.py` | 10 |
| `dags/options/options_dag.py` | 5 |
| `dags/uk-inflation-pipeline/uk_inflation_dag.py` | 6 |
| `dags/uk-metrics-pipeline/uk_metrics_dag.py` | 7 |

Straight rename, no behavioral risk: none of these DAGs reference `ds`/`execution_date`/data-interval macros, so the underlying timetable change (cron strings now default to `CronTriggerTimetable` instead of `CronDataIntervalTimetable`) has no visible effect here.

## Checked and confirmed — no change needed

- No `SubDagOperator` anywhere.
- No `execution_date`, `prev_ds`, `next_ds`, `tomorrow_ds`, or other removed template macros/context keys.
- No `Dataset`/`Asset`, no `outlets`/`inlets` — no data-aware scheduling to migrate.
- No `Variable.get`/`set`. No explicit `xcom_pull`/`xcom_push` — task return values are produced but never consumed downstream by other tasks, so the Airflow 3 change to `xcom_pull()`'s default `task_ids` behavior doesn't apply.
- No custom operators/hooks/sensors, no `plugins/` directory.
- No `default_args`, `trigger_rule`, `depends_on_past`, `provide_context`, `op_kwargs`/`op_args`, or SLA usage anywhere.
- `catchup=False` already set both globally (`AIRFLOW__SCHEDULER__CATCHUP_BY_DEFAULT`) and per-DAG — matches the Airflow 3 default.

## Can't verify from this repo

- **Python version**: only signal found is a stray `econometrics_dag.cpython-312.pyc` → Python 3.12, which is within Airflow 3.0's supported range (3.9–3.12). Confirm the actual image base.
- **Provider/core version pins**: none exist in `smart-home-config` — governed entirely by the image build in the `airflow` fork repo (see item 3).
- The 4 external git-installed packages used inside `@task.virtualenv` tasks (`marketinsights-collector`, `housemarket-scraper`, `marketinsights-dbschema`, `marketinsights-price-aggregator`) live outside this repo and weren't assessed — they run inside per-task virtualenvs so are largely insulated from the Airflow core version, but worth a quick smoke test.

## Recommended order of work

1. In the `airflow` fork repo: bump `AIRFLOW_VERSION` to the target 3.x release, fix the extras list, rebuild and smoke-test the image boots (`airflow version`, `airflow db migrate`).
2. Decide FAB vs `SimpleAuthManager`; update `af-config.yaml`/`webserver_config.py`; switch the webserver container to `airflow api-server` and split out a `dag-processor` container/pod.
3. Migrate `deployment.yaml` off `CeleryKubernetesExecutor` to the multi-executor config; add explicit `executor="KubernetesExecutor"` to the 4 affected tasks, replacing the `queue='kubernetes'` routing.
4. Mechanical find/replace `schedule_interval=` → `schedule=` across all 9 DAG files.
5. Confirm `apache-airflow-providers-cncf-kubernetes` version compatibility.
6. Stand up a staging Airflow 3 instance against these DAGs, unpause and manually trigger each one, and verify: virtualenv tasks still install their external git packages correctly, Selenium/Chrome pod-override tasks land on the Kubernetes executor, and Postgres loads complete end-to-end.

## Verification

There are no automated tests for these DAGs. Verification is manual (step 6 above) — the executor and auth-manager changes especially need to be proven against a real staging cluster before cutover; nothing here is safely unit-testable in isolation.
