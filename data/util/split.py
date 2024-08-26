import os
from icecream import ic
from pathlib import Path

train_path = Path("../yolo/v2/images/train/")
val_path = Path("../yolo/v2/images/val/")
label_train_path = Path("../yolo/v2/labels/train/")
label_val_path = Path("../yolo/v2/labels/val/")
base_label_path = Path("../yolo/v2/labels/")

for file in train_path.iterdir():
    if file.is_file():
        file_name = file.stem
        ic(file_name)
        # copy label to label_train_path, windows compatible
        ic(f"move {base_label_path / file_name}.txt {label_train_path / file_name}.txt")
        os.system(f"move {base_label_path / file_name}.txt {label_train_path / file_name}.txt")
        
for file in val_path.iterdir():
    if file.is_file():
        file_name = file.stem
        ic(file_name)
        # copy label to label_val_path, windows compatible
        ic(f"move {base_label_path / file_name}.txt {label_val_path / file_name}.txt")
        os.system(f"move {base_label_path / file_name}.txt {label_val_path / file_name}.txt")

for file in base_label_path.iterdir():
    if file.is_file():
       if file.suffix == ".txt":
           os.remove(f"{file}")