
# Optional Advice for Change to BigQuery

## **Key Considerations for BigQuery Schema**

1. **Time-Series Table (`sensor_readings`)**:
   - **Current Design**:  
     The `sensor_readings` table uses a "wide-to-long" format, where each metric (e.g., temperature, humidity) is stored as a row with `metric_name` and `value`.
   - **BigQuery Suitability**:  
     This design is flexible and works in BigQuery for querying individual metrics, but it may increase query costs due to row scanning. BigQuery performs better with "wide-flat" tables, where each metric is a separate column.
   - **Recommendation**:  
     Consider pivoting `sensor_readings` into a wide format with separate columns for each metric (e.g., `temperature`, `humidity`, etc.). This reduces row-based scanning costs in BigQuery.

   **Example**:

   ```sql
   CREATE TABLE sensor_readings (
       timestamp TIMESTAMP,
       deployment_fk INT,
       temperature FLOAT,
       humidity FLOAT,
       pm_2_5 FLOAT,
       co2 FLOAT,
       PRIMARY KEY (timestamp, deployment_fk)
   );
   ```

2. **Foreign Keys**:
   - **Current Design**:  
     Tables like `deployments` and `sensors_master` use foreign keys (`sensor_fk`, `deployment_fk`) to enforce relationships.
   - **BigQuery Suitability**:  
     BigQuery doesn’t enforce foreign keys. While the schema is fine, ensure the application logic (or ETL process) enforces relationships.

   **Recommendation**:  
   Denormalize related data where possible. For example:
   - Add sensor details (e.g., `native_sensor_id`, `sensor_type`) directly into `sensor_readings` to reduce the need for joins.

3. **Views**:
   - **Current Design**:  
     Views like `readings` and `collection_metadata_view` are used for logical abstractions.
   - **BigQuery Suitability**:  
     BigQuery supports views but doesn’t directly import them. Instead, materialize these views into tables during batch loading.

   **Recommendation**:  
   Replace complex views with materialized tables during ETL, as batch loading from Google Cloud Storage doesn’t support views.

4. **Indexes**:
   - **Current Design**:  
     PostgreSQL indexes (e.g., on `timestamp` and foreign keys) aren’t applicable in BigQuery.
   - **BigQuery Suitability**:  
     Use **partitioning** on `timestamp` columns and **clustering** on frequently queried fields (e.g., `deployment_fk`).

   **Recommendation**:
   - Partition `sensor_readings` by `timestamp` for efficient time-based queries.
   - Cluster by `deployment_fk` to reduce scan costs.

5. **Scalability**:
   - BigQuery is designed for analytical workloads at scale. If you frequently query metrics by sensor, deployment, or time, ensure the schema supports these patterns with proper partitioning and clustering.

---

### **Schema-Level Adjustments for BigQuery**

1. **Denormalization**:
   - Add sensor-related fields (e.g., `native_sensor_id`, `sensor_type`) directly into `sensor_readings`.
   - Add deployment-related fields (e.g., `location`, `status`) into `sensor_readings`.

2. **Wide Format for Metrics**:
   - Pivot `metric_name` and `value` into separate columns for each metric.

3. **Partitioning and Clustering**:
   - Partition `sensor_readings` by `timestamp`.
   - Cluster by `deployment_fk` or other frequently queried fields.

---

### **Adjusted Schema Example for BigQuery**

**`sensor_readings` (Wide Format, Partitioned, and Clustered):**

```sql
CREATE TABLE sensor_readings (
    timestamp TIMESTAMP,
    deployment_fk INT,
    temperature FLOAT,
    humidity FLOAT,
    pm_2_5 FLOAT,
    co2 FLOAT,
    latitude FLOAT,
    longitude FLOAT
)
PARTITION BY DATE(timestamp)
CLUSTER BY deployment_fk;

**`deployments` (Flattened for Denormalization):**

```sql
CREATE TABLE deployments (
    deployment_pk INT,
    sensor_fk INT,
    location STRING,
    latitude FLOAT,
    longitude FLOAT,
    status STRING,
    start_date DATE,
    end_date DATE
);
```

**`sensors_master`:**

```sql
CREATE TABLE sensors_master (
    sensor_pk INT,
    native_sensor_id STRING,
    sensor_type STRING,
    friendly_name STRING
);
```

---

### **Batch Loading to BigQuery via Google Cloud Storage**

1. **Export Data**:
   - Write the data to CSV, JSON, or Parquet files in Google Cloud Storage.
   - Adjust the ETL process to pivot `metric_name` into separate columns if adopting a wide format.

2. **Load into BigQuery**:
   - Use the `bq` command-line tool or BigQuery Console to load data from GCS into partitioned and clustered tables.

---

Let me know if you'd like help rewriting queries or adjusting the ETL process for these changes!

Current Schema:

### Key Tables and Their Structures

1. **`sensors_master`**
   - Tracks sensor details (`sensor_pk`, `native_sensor_id`, `sensor_type`, `friendly_name`).
   - Unique constraint on `native_sensor_id` and `sensor_type`.

2. **`deployments`**
   - Tracks sensor deployments (`deployment_pk`, `sensor_fk`, `location`, `latitude`, `longitude`, `status`, `start_date`, `end_date`).
   - Foreign key links `sensor_fk` to `sensors_master`.

3. **`sensor_readings`**
   - Stores time-series data (`timestamp`, `deployment_fk`, `metric_name`, `value`).
   - Foreign key links `deployment_fk` to `deployments`.
   - Primary key ensures uniqueness on `timestamp`, `deployment_fk`, and `metric_name`.
