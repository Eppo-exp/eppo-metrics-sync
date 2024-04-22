import sys
import argparse
from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
        description="Scan specified directory for Eppo yaml files and sync with Eppo"
    )
    parser.add_argument("directory", help="The directory of yaml files to process")
    parser.add_argument("--dryrun", action="store_true", help="Run in dry run mode")
    parser.add_argument("--schema", help="One of: eppo[default], dbt", default='eppo')
    parser.add_argument("--dbt_table_prefix", help="One of: eppo[default], dbt", default=None)

    args = parser.parse_args()

    eppo_metrics_sync = EppoMetricsSync(
        directory = args.directory, 
        schema_type=args.schema,
        dbt_table_prefix=args.dbt_table_prefix
    )
    
    if args.dryrun:
        eppo_metrics_sync.read_yaml_files()
        eppo_metrics_sync.validate()
    else:
        eppo_metrics_sync.sync()
