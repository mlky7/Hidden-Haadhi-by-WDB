import os
import shutil
import random
import tensorflow as tf
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import layers, models
from icrawler.builtin import GoogleImageCrawler
import json

classes = [
    "abbey_falls", "baba_budangiri", "bangalore_palace", "brindavan_gardens",
    "chamundi_hills", "cubbon_park", "hebbe_falls", "lalbagh", "mullayanagiri",
    "rajas_seat", "st_philomenas_church", "vidhana_soudha", "mysore_palace"
]

# base_raw_dir = "raw"
# os.makedirs(base_raw_dir, exist_ok=True)

# for label in classes:
#     query = label.replace("_", " ") + " Karnataka"
#     save_dir = os.path.join(base_raw_dir, label)
#     os.makedirs(save_dir, exist_ok=True)

#     print(f"Downloading: {query}")
#     crawler = GoogleImageCrawler(storage={"root_dir": save_dir})
#     crawler.crawl(keyword=query, max_num=50)


def split_dataset(source_dir, dest_dir, train_ratio=0.7, val_ratio=0.15):
    os.makedirs(dest_dir, exist_ok=True)
    for class_name in os.listdir(source_dir):
        src_folder = os.path.join(source_dir, class_name)
        if not os.path.isdir(src_folder): continue
        
        images = os.listdir(src_folder)
        random.shuffle(images)

        train_cut = int(len(images) * train_ratio)
        val_cut = int(len(images) * (train_ratio + val_ratio))

        splits = {
            'train': images[:train_cut],
            'val': images[train_cut:val_cut],
            'test': images[val_cut:]
        }

        for split, files in splits.items():
            split_folder = os.path.join(dest_dir, split, class_name)
            os.makedirs(split_folder, exist_ok=True)
            for img in files:
                shutil.copy(os.path.join(src_folder, img), os.path.join(split_folder, img))

split_dataset("dataset/raw", "dataset")

DATASET_DIR = "dataset"
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 20

train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=30,
    zoom_range=0.2,
    horizontal_flip=True
)

val_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "train"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical"
)

val_generator = val_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "val"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical"
)

with open("class_indices.json", "w") as f:
    json.dump(train_generator.class_indices, f)

base_model = MobileNetV2(input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet")
base_model.trainable = False  # Freeze for now

model = Sequential([
    base_model,
    GlobalAveragePooling2D(),
    Dense(128, activation="relu"),
    Dropout(0.3),
    Dense(train_generator.num_classes, activation="softmax")
])

model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
model.fit(train_generator, validation_data=val_generator, epochs=EPOCHS)

model.save("karnataka_places_model.h5")
print("Model saved.")

