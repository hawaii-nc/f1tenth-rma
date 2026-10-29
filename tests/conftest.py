import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src' / 'f1tenth_research'))
sys.path.insert(0, str(REPO / 'src' / 'rma_deploy_pkg'))
sys.path.insert(0, str(REPO / 'experiments'))
