import os
import cv2
import numpy as np
import pickle
from skimage.feature import hog
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split

# Path to dataset folder (relative to this file)
DATASET_DIR = "dataset"

X = []
y = []

print("🔍 Scanning dataset from:", os.path.abspath(DATASET_DIR))

for label in os.listdir(DATASET_DIR):
    class_dir = os.path.join(DATASET_DIR, label)
    if not os.path.isdir(class_dir):
        continue

    print(f"\n📂 Class: {label}")
    count = 0

    for img_name in os.listdir(class_dir):
        img_path = os.path.join(class_dir, img_name)

        try:
            img = cv2.imread(img_path)
            if img is None:
                print("  ⚠ Skipping unreadable image:", img_path)
                continue

            img = cv2.resize(img, (128, 128))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            hog_features = hog(
                gray,
                pixels_per_cell=(16, 16),
                cells_per_block=(2, 2)
            )

            X.append(hog_features)
            y.append(label)
            count += 1
        except Exception as e:
            print("  ⚠ Error on image, skipping:", img_path, "| reason:", e)

    print(f"  ✅ Loaded {count} images for class '{label}'")

X = np.array(X)
y = np.array(y)

print("\n📊 Total samples collected:", len(X))

if len(X) == 0:
    raise ValueError("No images found! Check your dataset path and structure.")

# Simple train-test split (even with few images)
test_size = 0.25 if len(X) > 4 else 0.5  # small data -> smaller split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=test_size, random_state=42
)

print("\n🧠 Training SVM model...")
model = SVC(kernel="linear", probability=True)
model.fit(X_train, y_train)

train_acc = model.score(X_train, y_train)
test_acc = model.score(X_test, y_test) if len(X_test) > 0 else None

print(f"✅ Train accuracy: {train_acc:.2f}")
if test_acc is not None:
    print(f"✅ Test accuracy : {test_acc:.2f}")
else:
    print("ℹ Not enough samples for a separate test set.")

# Save model
MODEL_PATH = "street_issue_model.pkl"
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

print(f"\n💾 Model saved as {MODEL_PATH}")
