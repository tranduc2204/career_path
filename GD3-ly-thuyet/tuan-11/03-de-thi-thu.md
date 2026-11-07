# 11.3 Đề thi thử: 65 câu / 120 phút

> Đề viết bằng **tiếng Anh** như đề thật. Bấm giờ 120 phút, không mở docs. Chấm bằng [04-dap-an-de-thi-thu.md](04-dap-an-de-thi-thu.md), ≥ 43/65 (65%) là đạt.
> Đây là đề **tự soạn** theo outline kỳ thi để luyện, không phải câu hỏi thật của dbt Labs. Câu chọn nhiều có ghi "(choose N)".

---

## Part 1: Developing models (Q1–Q15)

**Q1.** A model has no `materialized` config anywhere in the project. What does dbt build?
A) table  B) view  C) ephemeral  D) incremental

**Q2.** In an incremental model, `is_incremental()` returns `true` when (choose 2):
A) the target relation already exists as a table
B) the run uses `--full-refresh`
C) the model is configured as `materialized='incremental'`
D) the target relation exists as a view

**Q3.** An incremental model uses `on_schema_change` with its default value. A new column is added to the model's SELECT. On the next (non full-refresh) run:
A) dbt fails the run
B) dbt adds the column to the target table
C) the new column is ignored and not added to the target table
D) dbt drops and recreates the table

**Q4.** Which incremental strategy replaces whole partitions of the target table and is commonly used on BigQuery?
A) append  B) merge  C) delete+insert  D) insert_overwrite

**Q5.** A microbatch model is configured with `event_time='order_ts'`, `batch_size='day'`, `lookback=2`. What does `lookback=2` do on a scheduled run?
A) Keeps the last 2 days in a staging table
B) Reprocesses the 2 batches before the current batch in addition to the current batch
C) Retries failed batches twice
D) Delays processing by 2 days

**Q6.** In a microbatch model, an upstream model also has `event_time` configured. By default:
A) dbt raises an error
B) dbt reads the full upstream model for every batch
C) dbt automatically filters the upstream model to the current batch's time window
D) dbt materializes the upstream model as microbatch too

**Q7.** Which command backfills a microbatch model for the first week of November 2026?
A) `dbt run -s m --vars '{"start": "2026-11-01"}'`
B) `dbt run -s m --event-time-start "2026-11-01" --event-time-end "2026-11-08"`
C) `dbt run -s m --full-refresh --sample "7 days"`
D) `dbt retry -s m --start 2026-11-01`

**Q8.** What does `dbt build --empty` do?
A) Drops all models in the target schema
B) Builds models with refs and sources limited to zero rows, validating SQL and schemas
C) Builds only models that have no tests
D) Runs only unit tests

**Q9.** In dbt 1.9+, snapshots can be defined in YAML. Which key points a YAML snapshot at the data to snapshot?
A) `model:`  B) `source:`  C) `relation:`  D) `select:`

**Q10.** A snapshot uses `strategy: check`. Which config is required with it?
A) `updated_at`  B) `check_cols`  C) `unique_key` only  D) `invalidate_hard_deletes`

**Q11.** Config for the same model is set in `dbt_project.yml` (`+materialized: view`), in a properties YAML file (`materialized: table`), and in the model's `{{ config(materialized='incremental') }}`. What is the result?
A) view  B) table  C) incremental  D) dbt raises a conflict error

**Q12.** Which statement about Python models is correct?
A) They can run on any adapter
B) They must define `def model(dbt, session)` and return a DataFrame
C) They can use Jinja `{{ ref() }}`
D) They cannot be referenced by SQL models

**Q13.** You want column descriptions from YAML to appear as column comments in Snowflake. Which config?
A) `docs: {show: true}`  B) `persist_docs: {columns: true}`  C) `meta: {comment: true}`  D) `grants: {comment: [...]}`

**Q14.** Which file defines reusable long descriptions that can be referenced with `{{ doc('order_status') }}`?
A) A `.md` file containing `{% docs order_status %}...{% enddocs %}`
B) `dbt_project.yml` under `docs:`
C) `packages.yml`
D) A `.sql` file in `analyses/`

**Q15.** Which statements about `ephemeral` models are true? (choose 2)
A) They are compiled as CTEs into the models that reference them
B) They create a view in the warehouse
C) Model contracts cannot be enforced on them
D) They are the default materialization

## Part 2: Governance (Q16–Q22)

**Q16.** A model has `contract: {enforced: true}`. A column in the SELECT is missing from the YAML. What happens?
A) dbt warns and builds the model
B) dbt fails the model before replacing the existing relation
C) dbt adds the column to the YAML automatically
D) dbt builds the model but skips its tests

**Q17.** On Snowflake, a model contract declares `constraints: [{type: primary_key}]` on `order_id`. Which is true?
A) Snowflake rejects duplicate `order_id` values on insert
B) The constraint is created as metadata but not enforced; you still need a `unique` test
C) dbt runs a uniqueness check automatically before the build
D) primary_key constraints are not allowed in contracts

**Q18.** `dim_customers` has `latest_version: 2` and versions 1 and 2. A downstream model uses `{{ ref('dim_customers') }}`. Which version does it get?
A) 1  B) 2  C) dbt raises an error because the ref is ambiguous  D) whichever was built most recently

**Q19.** What is the default relation name for version 1 of `dim_customers`?
A) `dim_customers`  B) `dim_customers_1`  C) `dim_customers_v1`  D) `v1_dim_customers`

**Q20.** Version 1 has `deprecation_date: 2027-01-31`. After that date, what does dbt do when another model references v1?
A) Fails the run
B) Drops the v1 relation
C) Emits a deprecation warning
D) Silently redirects the ref to v2

**Q21.** Which change to a public, contracted model is a **breaking change** that should come with a new version?
A) Adding a new nullable column
B) Renaming an existing column
C) Updating a column description
D) Adding a not_null test

**Q22.** For a model with an enforced contract that is materialized as incremental, which `on_schema_change` values are supported? (choose 2)
A) `ignore`  B) `append_new_columns`  C) `fail`  D) `sync_all_columns`

## Part 3: Debugging (Q23–Q30)

**Q23.** A model references `{{ ref('stg_order') }}` but the model is named `stg_orders`. What type of error occurs, and when?
A) Database error at run time
B) Compilation error when dbt parses/compiles the project
C) Runtime warning only
D) Dependency error during `dbt deps`

**Q24.** dbt reports `Database Error: invalid identifier 'CUSTOMER_NAM'`. Where do you find the exact SQL sent to the warehouse, including the DDL wrapper?
A) `target/compiled/`  B) `target/run/`  C) `logs/query_log.sql`  D) `dbt_packages/`

**Q25.** Inside a macro, `{% set results = run_query("select max(id) from t") %}` followed by `{{ results.columns[0].values()[0] }}` fails during parsing with `'None' has no attribute 'columns'`. The fix is to:
A) Wrap the usage in `{% if execute %}`
B) Use `{{ this }}` instead
C) Add `materialized='table'`
D) Run `dbt deps`

**Q26.** Which command checks the profile, connection to the warehouse, and that `dbt_project.yml` is valid?
A) `dbt parse`  B) `dbt debug`  C) `dbt compile`  D) `dbt ls`

**Q27.** You want to print a variable's value to the console during a run. Which Jinja is correct?
A) `{{ print(x) }}`  B) `{{ log("x=" ~ x, info=True) }}`  C) `{% echo x %}`  D) `{{ debug(x) }}`

**Q28.** What are behavior change flags in `dbt_project.yml`?
A) Flags that change model materializations per environment
B) Settings under `flags:` that opt in to (or out of) new dbt behaviors during a deprecation/transition period
C) Command-line flags saved in the project
D) Feature toggles for dbt packages only

**Q29.** A model contains `{% if target.name == 'prod' %} where is_deleted = false` but the matching `{% endif %}` is missing. What happens?
A) Database error from the warehouse
B) Compilation error raised by Jinja before any SQL is sent
C) The `where` clause is silently ignored
D) dbt adds the missing `endif` automatically

**Q30.** `dbt run` fails with `Compilation Error: dbt found two models with the name "orders"`. Which is the most likely cause?
A) Two `.sql` files named `orders.sql` exist in different folders of the same project
B) The model has two tests
C) `orders` is a reserved word
D) The warehouse already has a table named `orders`

## Part 4: Pipelines and troubleshooting (Q31–Q37)

**Q31.** During `dbt build`, a `not_null` test (severity error) on `stg_orders` fails. What happens to `fct_orders`, which depends on `stg_orders`?
A) It is built normally
B) It is skipped
C) It is built, then its tests are skipped
D) The whole run stops immediately even without `--fail-fast`

**Q32.** What does `dbt retry` do?
A) Re-runs the entire previous command from scratch
B) Re-runs nodes that errored or were skipped in the previous invocation, using `run_results.json`
C) Retries failed connections 3 times
D) Re-runs only failed tests

**Q33.** What does `dbt clone --state prod-artifacts/` do?
A) Copies the dbt project to a new folder
B) Creates clones (zero-copy clones where supported, otherwise views) of selected nodes from the state's environment into the current target schema
C) Clones the git repository of a package
D) Duplicates every model as a new version

**Q34.** By default, if a relation already exists in the current target, `dbt clone`:
A) Overwrites it
B) Does not recreate it unless `--full-refresh` is passed
C) Fails
D) Renames the existing relation

**Q35.** `dbt build --fail-fast` (`-x`):
A) Skips all tests
B) Stops the run as soon as any node fails
C) Runs models with maximum threads
D) Retries failures quickly

**Q36.** An Airflow task running `dbt build` fails because a test fails due to bad source data. What is the best first response?
A) Configure Airflow to retry the task 5 times
B) Investigate the failing test's data (e.g., `store_failures`) and fix or quarantine the source issue
C) Change the test severity to warn permanently
D) Delete the test

**Q37.** Which artifact does `dbt retry` read?
A) `manifest.json` only  B) `run_results.json`  C) `sources.json`  D) `catalog.json`

## Part 5: Tests (Q38–Q48)

**Q38.** A generic test macro should return:
A) The number of passing rows
B) The rows that fail the assertion (zero rows = pass)
C) `true` or `false`
D) A single row with column `result`

**Q39.** Which is the correct way to declare a custom generic test?
A) `{% macro test_positive(model, column_name) %}` in `macros/`, or `{% test positive(model, column_name) %}` in `tests/generic/`
B) A `.yml` file with `test:` keyword
C) A Python file in `tests/`
D) Only `{% test %}` blocks inside `analyses/`

**Q40.** What is a singular test?
A) A test that runs on one column
B) A `.sql` file in the `tests/` directory that returns failing rows
C) A unit test with one input row
D) A test with severity warn

**Q41.** A test has `config: {severity: error, warn_if: ">0", error_if: ">100"}`. The test returns 25 failing rows. Status?
A) pass  B) warn  C) error  D) skipped

**Q42.** What does `store_failures: true` do?
A) Saves failing rows into a table in the warehouse for investigation
B) Stores the test SQL in `target/`
C) Sends failures to Slack
D) Prevents downstream models from building

**Q43.** Unit tests in dbt (choose 2):
A) Test the logic of a model's SQL using mocked input rows
B) Test data quality of production data
C) Are defined under `unit_tests:` in YAML with `given` and `expect`
D) Can be written for Python models

**Q44.** Which command runs only unit tests?
A) `dbt test --select test_type:unit`  B) `dbt unit`  C) `dbt test --unit-only`  D) `dbt build --select tag:unit`

**Q45.** In `dbt build`, when do unit tests for a model run?
A) After the model and its data tests
B) Before the model is built
C) Only at the end of the run
D) Only in CI

**Q46.** In a unit test, which `format` values are valid for `given` rows? (choose 3)
A) `dict`  B) `csv`  C) `sql`  D) `json`

**Q47.** In dbt ≥ 1.10, how should arguments to a generic test be specified to avoid deprecation warnings?
A) Directly under the test name
B) Under an `arguments:` key
C) Under `meta:`
D) Under `config: {args: ...}`

**Q48.** Which built-in generic tests come with dbt Core? (choose 4)
A) `unique`  B) `not_null`  C) `accepted_values`  D) `relationships`  E) `accepted_range`

## Part 6: External dependencies (Q49–Q55)

**Q49.** A source has `freshness: {warn_after: {count: 12, period: hour}, error_after: {count: 24, period: hour}}` and `loaded_at_field: _loaded_at`. The newest `_loaded_at` is 18 hours old. Status?
A) pass  B) warn  C) error  D) runtime error

**Q50.** Where does `dbt source freshness` write its results?
A) `target/run_results.json` only  B) `target/sources.json`  C) `target/freshness.yml`  D) the `dbt_freshness` table

**Q51.** Which exposure `type` values are valid? (choose 3)
A) dashboard  B) notebook  C) spreadsheet  D) ml

**Q52.** Which field is required on an exposure?
A) `url`  B) `owner` (with name or email)  C) `maturity`  D) `description`

**Q53.** You want to build everything a specific dashboard depends on. Which selector?
A) `dbt build -s exposure:daily_dashboard+`
B) `dbt build -s +exposure:daily_dashboard`
C) `dbt build -s daily_dashboard`
D) `dbt build --exposure daily_dashboard`

**Q54.** After `dbt deps`, which file records the exact resolved versions of installed packages?
A) `packages.yml`  B) `dependencies.yml`  C) `package-lock.yml`  D) `manifest.json`

**Q55.** A package macro must be overridden by your project's implementation on your adapter. Which mechanism?
A) `dispatch` config with `search_order` in `dbt_project.yml`
B) Renaming the package
C) `packages.yml` `override: true`
D) `vars`

## Part 7: dbt state (Q56–Q65)

**Q56.** In CI, you want to build only changed models and their children, resolving refs to unchanged models against production. Which command?
A) `dbt build -s state:modified+ --defer --state prod-artifacts`
B) `dbt build -s modified+ --prod`
C) `dbt build -s +state:modified --full-refresh`
D) `dbt build --state prod-artifacts`

**Q57.** With `--defer`, a ref to a model that is **not selected** and **does not exist** in the CI schema resolves to:
A) An error
B) The relation in the environment described by the `--state` manifest
C) An empty table
D) The latest version of the model in the dev schema

**Q58.** What does `--favor-state` add to `--defer`?
A) Prefer the state (prod) relation even if the node exists in the current environment
B) Saves state after the run
C) Ignores state for tests
D) Uses the newest manifest automatically

**Q59.** Which artifact contains the full representation of the project (nodes, configs, dependencies) used for state comparison?
A) `run_results.json`  B) `manifest.json`  C) `catalog.json`  D) `graph.gpickle`

**Q60.** Which selector re-runs only nodes that errored in the previous run and their children?
A) `result:error+` with `--state target/`
B) `status:failed`
C) `state:failed+`
D) `error:true+`

**Q61.** You change only a macro used by model `m`. Does `state:modified` select `m`?
A) No, macros are never tracked
B) Yes, via the `state:modified.macros` sub-selector included in `state:modified`
C) Only if `m` is a snapshot
D) Only with `--full-refresh`

**Q62.** Which `state:modified` sub-selectors exist? (choose 3)
A) `state:modified.body`  B) `state:modified.configs`  C) `state:modified.owner`  D) `state:modified.contract`

**Q63.** `dbt build -s source_status:fresher+ --state prod-artifacts/` builds:
A) Models whose sources have newer data than in the previous freshness results, plus their children
B) Only sources
C) Models with freshness errors
D) All models older than 24 hours

**Q64.** Which selector selects a model, all its descendants, and all ancestors of those descendants?
A) `+m+`  B) `@m`  C) `m+`  D) `*m`

**Q65.** `dbt build -s "tag:finance,config.materialized:incremental"` selects:
A) Nodes with tag finance OR incremental
B) Nodes with tag finance AND materialized incremental
C) Only tests
D) A syntax error
