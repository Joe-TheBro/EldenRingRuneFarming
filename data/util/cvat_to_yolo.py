import os
import argparse
import random
from icecream import ic
from pathlib import Path

cvat_path = Path("../yolo/v4-cvat/")
output_path = Path("../yolo/v4/")
raw_path = Path("../raw/")

# create yaml file
output_path.mkdir(parents=True, exist_ok=True)
with open(output_path / "eldenring.yaml", 'w') as f:
    f.write("path: ''\n")
    f.write("train: images/train\n")
    f.write("val: images/val\n")
    f.write("names:\n")
    with open(cvat_path / "obj.names", 'r') as names:
        num_classes = 0
        for name in names:
            f.write(f"  {num_classes}: {name.strip()}\n")
            num_classes += 1
    f.write("download: null")

# create train, val, test directories
[(output_path / x).mkdir(parents=True, exist_ok=True) for x in ["images/train", "images/val", "labels/train", "labels/val"]]


def copy_data(name: str, img_list: list):
    for img in img_list:
        img = img.strip().split('/')[-1]
        img.replace("\n", "")
        ic("Copying", img)
        image_dir = output_path / f"images/{name}"
        label_dir = output_path / f"labels/{name}"
        label_name = img.replace('jpg', 'txt')
        os.system(f"copy {raw_path / img} {image_dir / img}")
        os.system(f"copy {cvat_path / "obj_train_data" / label_name} {label_dir / label_name}")

# split train, val, test
# get nums of lines in cvat dataset
with open(cvat_path / "train.txt", 'r') as f:
    orig_data = f.readlines()
    random.shuffle(orig_data)
    orig_length = len(orig_data)
    train_length = int(orig_length * 0.85)
    val_length = orig_length - train_length
    train_data = orig_data[:train_length]
    val_data = orig_data[train_length:]
    copy_data("train", train_data)
    copy_data("val", val_data)
