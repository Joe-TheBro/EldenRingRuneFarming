from ultralytics.hub import check_dataset
from pathlib import Path

dataset = Path("../yolo/v2.zip")
check_dataset(dataset)