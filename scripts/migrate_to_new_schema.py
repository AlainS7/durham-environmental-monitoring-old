import os
import pandas as pd
import logging
from sqlalchemy import create_engine, text
from datetime import datetime

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Do export DATABASE_URL=$(gcloud secrets versions access latest --secret=DATABASE_URL) && python3 migrate_to_new_schema.py")
# --- End Configuration ---

def get_db_engine():
    """Creates a new SQLAlchemy engine."""
    try:
        engine = create_engine(DATABASE_URL) # pyright: ignore[reportArgumentType]
        log.info("Database engine created successfully.")
        return engine
    except Exception as e:
        log.error(f"Failed to create database engine: {e}", exc_info=True)
        raise

def backfill_master_and_deployments(engine):
    """
    Backfills sensors_master and creates an initial deployment for each sensor.
    """
    log.info("Starting to backfill sensors_master and deployments tables.")
    
    # SQL to get unique sensors from old tables
    queries = {
        'WU': "SELECT DISTINCT stationid AS native_sensor_id, 'WU' as sensor_type, stationid as friendly_name, MIN(obstimeutc) as first_seen FROM wu_data GROUP BY 1,2,3;",
        'TSI': "SELECT DISTINCT device_id AS native_sensor_id, 'TSI' as sensor_type, device_name as friendly_name, MIN(reading_time) as first_seen FROM tsi_data GROUP BY 1,2,3;"
    }
    
    all_sensors = []
    with engine.connect() as connection:
        for sensor_type, query in queries.items():
            try:
                df = pd.read_sql(query, connection)
                log.info(f"Found {len(df)} unique sensors of type {sensor_type}.")
                all_sensors.append(df)
            except Exception as e:
                log.warning(f"Could not fetch {sensor_type} sensors. Maybe table does not exist? Error: {e}")

    if not all_sensors:
        log.warning("No sensors found in old tables. Skipping backfill.")
        return

    sensors_df = pd.concat(all_sensors, ignore_index=True)
    sensors_df['first_seen'] = pd.to_datetime(sensors_df['first_seen']).dt.date

    with engine.connect() as connection:
        with connection.begin(): # Start transaction
            for _, row in sensors_df.iterrows():
                row = row.where(pd.notnull(row), None)
                
                # 1. Insert into sensors_master and get the new sensor_pk
                insert_master_sql = text("""
                    INSERT INTO sensors_master (native_sensor_id, sensor_type, friendly_name)
                    VALUES (:native_sensor_id, :sensor_type, :friendly_name)
                    ON CONFLICT (native_sensor_id, sensor_type) DO UPDATE
                    SET friendly_name = EXCLUDED.friendly_name
                    RETURNING sensor_pk;
                """)
                master_params = {
                    'native_sensor_id': row['native_sensor_id'],
                    'sensor_type': row['sensor_type'],
                    'friendly_name': row.get('friendly_name')
                }
                result = connection.execute(insert_master_sql, master_params)
                sensor_pk = result.scalar_one()

                # 2. Create a default first deployment for this sensor
                insert_deployment_sql = text("""
                    INSERT INTO deployments (sensor_fk, location, status, start_date, end_date)
                    VALUES (:sensor_fk, :location, :status, :start_date, NULL)
                    ON CONFLICT (sensor_fk, end_date) DO NOTHING;
                """)
                deployment_params = {
                    'sensor_fk': sensor_pk,
                    'location': 'Default Migrated Location', # You should update this later
                    'status': 'active', # Assume all migrated sensors are active
                    'start_date': row.get('first_seen', datetime.now().date())
                }
                connection.execute(insert_deployment_sql, deployment_params)

    log.info(f"Successfully backfilled {len(sensors_df)} sensors and created initial deployments.")

def migrate_readings_to_new_schema(engine):
    """
    Migrates time-series data from old tables to the new sensor_readings table.
    """
    log.info("Starting data migration to sensor_readings.")
    
    with engine.connect() as connection:
        # Get a map of native_id -> current_deployment_pk
        # This assumes one active deployment per sensor after the initial backfill
        deployment_map_sql = """
            SELECT d.deployment_pk, sm.native_sensor_id, sm.sensor_type
            FROM deployments d
            JOIN sensors_master sm ON d.sensor_fk = sm.sensor_pk
            WHERE d.end_date IS NULL;
        """
        deployment_map_df = pd.read_sql(deployment_map_sql, connection)
        
        # --- Migrate WU Data ---
        try:
            wu_df = pd.read_sql("SELECT * FROM wu_data", connection)
            if not wu_df.empty:
                wu_map = deployment_map_df[deployment_map_df['sensor_type'] == 'WU']
                wu_df = wu_df.merge(wu_map, left_on='stationid', right_on='native_sensor_id')
                wu_df.rename(columns={'obstimeutc': 'timestamp', 'deployment_pk': 'deployment_fk'}, inplace=True)
                
                value_vars = ['tempavg', 'humidityavg', 'solarradiationhigh', 'preciprate'] # Add all metrics
                wu_long = pd.melt(wu_df, id_vars=['timestamp', 'deployment_fk'], value_vars=value_vars, var_name='metric_name', value_name='value')
                
                wu_long.dropna(subset=['value'], inplace=True)
                log.info(f"Migrating {len(wu_long)} WU records.")
                wu_long.to_sql('sensor_readings', connection, if_exists='append', index=False, method='multi', chunksize=5000)
        except Exception as e:
            log.warning(f"Could not migrate WU data. Error: {e}")

        # --- Migrate TSI Data ---
        try:
            tsi_df = pd.read_sql("SELECT * FROM tsi_data", connection)
            if not tsi_df.empty:
                tsi_map = deployment_map_df[deployment_map_df['sensor_type'] == 'TSI']
                tsi_df = tsi_df.merge(tsi_map, left_on='device_id', right_on='native_sensor_id')
                tsi_df.rename(columns={'reading_time': 'timestamp', 'deployment_pk': 'deployment_fk'}, inplace=True)

                value_vars = ['temperature', 'rh', 'p_bar', 'co2', 'pm_2_5'] # Add all metrics
                tsi_long = pd.melt(tsi_df, id_vars=['timestamp', 'deployment_fk'], value_vars=value_vars, var_name='metric_name', value_name='value')
                
                tsi_long.dropna(subset=['value'], inplace=True)
                log.info(f"Migrating {len(tsi_long)} TSI records.")
                tsi_long.to_sql('sensor_readings', connection, if_exists='append', index=False, method='multi', chunksize=5000)
        except Exception as e:
            log.warning(f"Could not migrate TSI data. Error: {e}")

    log.info("Data migration to sensor_readings complete.")


if __name__ == "__main__":
    log.info("Starting database migration process.")
    if input("Have you backed up your database and run schema.sql? (yes/no): ").lower() != 'yes':
        log.info("Migration cancelled.")
    else:
        engine = get_db_engine()
        backfill_master_and_deployments(engine)
        migrate_readings_to_new_schema(engine)
        log.info("Migration script finished successfully.")
        log.warning("Please verify data, then consider dropping old tables: wu_data, tsi_data, collection_log, collection_metadata")