import os
import glob
import pandas as pd
from datetime import datetime

RAW_WU_DIR = 'raw_pulls/wu/2025/'
RAW_TSI_DIR = 'raw_pulls/tsi/2025/'
MASTER_WU = 'data/master_data/wu_master_historical_data.csv'
MASTER_TSI = 'data/master_data/tsi_master_historical_data.csv'

def merge_csvs(raw_dir, master_file, key_cols=None):
    files = sorted(glob.glob(os.path.join(raw_dir, '*.csv')))
    if not files:
        print(f'No CSV files found in {raw_dir}')
        return
    print(f'Merging {len(files)} files from {raw_dir} into {master_file}')
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f'Error reading {f}: {e}')
    if not dfs:
        print('No data to merge.')
        return
    all_data = pd.concat(dfs, ignore_index=True)
    if key_cols:
        all_data = all_data.drop_duplicates(subset=key_cols)
    else:
        all_data = all_data.drop_duplicates()
    all_data = all_data.sort_values(by=all_data.columns[1])  # sort by timestamp/obsTimeUtc
    all_data.to_csv(master_file, index=False)
    print(f'Wrote merged data to {master_file} ({len(all_data)} rows)')

def main():
    merge_csvs(RAW_WU_DIR, MASTER_WU, key_cols=["stationID", "obsTimeUtc"])  # adjust columns as needed
    merge_csvs(RAW_TSI_DIR, MASTER_TSI, key_cols=["device_id", "timestamp"])  # adjust columns as needed
    print('Master data update complete.')

if __name__ == '__main__':
    main()
