import os
from icecream import ic
from pathlib import Path

raw_data_path = Path("../raw/")
image_data_path = Path("../yolo/v1/images/")
labels_path = Path("../yolo/v1/labels/")

for file in labels_path.iterdir():
    if file.is_file():
        file_name = file.stem
        ic(file_name)
        # extract image name via substring
        image_name = file_name.split("-")[1]
        original_image_name = image_name + ".jpg"
        ic(original_image_name)
        copy_image_name = file_name + ".jpg"
        ic(copy_image_name)
        # copy image to image_data_path, windows compatible
        ic(f"copy {raw_data_path / original_image_name} {image_data_path / copy_image_name}")
        os.system(f"copy {raw_data_path / original_image_name} {image_data_path / copy_image_name}")