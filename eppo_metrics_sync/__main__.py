import os
import sys
import argparse
from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Scan specified directory for Eppo yaml files and sync with Eppo"
    )
    parser.add_argument("directory", help="The directory of yaml files to process")
    parser.add_argument("--allow-upgrades", action="store_true", help="Allow existing non-certified metrics/fact sources to become certified")
    parser.add_argument("--dryrun", action="store_true", help="Run in dry run mode")
    parser.add_argument("--schema", help="One of: eppo[default], dbt-model", default='eppo')
    parser.add_argument("--sync-prefix", help="Used for testing in a shared Q/A workspace. "
                                              "Will use this as a sync tag and append all fact and metric definitions with this prefix.",
                        required=False
                        )
    parser.add_argument(
        "--dbt-model-prefix",
        help="The warehouse and schema where the dbt models live",
        default=None
    )
    parser.add_argument(
        "--creator-email",
        help="Email for metric creator/author (sync-level). Overrides YAML. Can also set EPPO_CREATOR_EMAIL.",
        default=None
    )
    parser.add_argument(
        "--updater-email",
        help="Email for last updater (sync-level). Overrides YAML. Can also set EPPO_UPDATER_EMAIL.",
        default=None
    )
    parser.add_argument(
        "--team-name",
        help="Team name to associate with metrics (sync-level). Overrides YAML. Can also set EPPO_TEAM_NAME.",
        default=None
    )

    args = parser.parse_args()

    creator_email = args.creator_email or os.environ.get('EPPO_CREATOR_EMAIL')
    updater_email = args.updater_email or os.environ.get('EPPO_UPDATER_EMAIL')
    team_name = args.team_name or os.environ.get('EPPO_TEAM_NAME')

    eppo_metrics_sync = EppoMetricsSync(
        directory=args.directory,
        schema_type=args.schema,
        dbt_model_prefix=args.dbt_model_prefix,
        sync_prefix=args.sync_prefix,
        allow_upgrades=args.allow_upgrades,
        creator_email=creator_email,
        updater_email=updater_email,
        team_name=team_name
    )

    if args.dryrun:
        eppo_metrics_sync.read_yaml_files()
        eppo_metrics_sync.validate()
    else:
        eppo_metrics_sync.sync()
