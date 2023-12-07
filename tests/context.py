# supposed this helps with build context for other developers? i'm sure if i need this

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import eppo_metrics_sync.eppo_metrics_sync as eppo_metrics_sync
import eppo_metrics_sync.validation as validation