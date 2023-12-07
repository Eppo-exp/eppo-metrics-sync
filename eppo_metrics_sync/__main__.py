import sys
import argparse
from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
        description="Scan specified directory for Eppo yaml files and sync with Eppo"
    )
    parser.add_argument("directory", help="The directory of yaml files to process")
    parser.add_argument("--dryrun", action="store_true", help="Run in dry run mode")

    args = parser.parse_args()

    eppo_metrics_sync = EppoMetricsSync(directory = args.directory)
    
    if args.dryrun:
        eppo_metrics_sync.read_yaml_files()
        eppo_metrics_sync.validate()
    else:
        eppo_metrics_sync.sync()
