# -*- coding: utf-8 -*-
"""SemanticSegmentationUnetInference.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GY-XaUKOos3EXf4Kd9BozT1x1MQJ2qoN

# Morphing inference test

## Configuration
"""

########################################## CONFIGURATION ####################################
!pip install segmentation_models -q
!pip install -U wandb -q
import os
os.environ['SM_FRAMEWORK'] = 'tf.keras'
import glob
import cv2
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
import segmentation_models as sm
import numpy as np
from google.colab import drive
import wandb
import glob

# Connecting to W&B
wandb.login()
# Connecting to google drive
drive.mount('/content/drive')
# Unzipping dataset
if not os.path.isdir("/content/MorphedDB_v3.0_subset"):
  !unzip -q "/content/drive/MyDrive/MasterThesis/MorphedDB_v3.0_subset.zip" -d "/content/MorphedDB_v3.0_subset"

# Configuration
morph_folder_base = "MorphedDB_v3.0_subset"
delete_run = True
project_name = 'FaceParsingUNet'
artifact_model_iou = 0.86
artifact_model_architecture = 'UNet'
artifact_model_backbone = 'efficientnetb3'
image_size = 256
classes_to_segment = {'skin': True, 'nose': True, 'eye': True, 'brow': True, 'ear': True, 'mouth': True, 
                      'hair': True, 'neck': True, 'cloth': False}

"""## Color configuration"""

from itertools import compress
all_colors = {'blue': [0, 0, 204], 'green': [0, 153, 76], 'water': [0, 204, 204], 'orange': [255, 51, 51], 'purple': [204, 0, 204], 
              'yellow': [255, 255, 0], 'lilla': [204, 204, 255], 'dark_blue': [0, 51, 102], 'blue2': [0, 0, 255], 
              'light_green': [0, 204, 102], 'light_blue': [0, 255, 255], 'red': [204, 0, 0], 'violet': [153, 51, 255], 
              'dark_green': [0, 60, 0], 'brown': [150,75,0]}

class_labels_mapping = {'skin': ['skin'], 'nose': ['nose'], 'eye': ['l_eye', 'r_eye'], 'brow': ['l_brow', 'r_brow'], 
                      'ear': ['l_ear', 'r_ear'], 'mouth': ['mouth', 'u_lip', 'l_lip'], 'hair': ['hair'], 
                      'neck': ['neck', 'neck_l'], 'cloth': ['cloth']}

class_color_mapping = {'skin': 'blue', 'nose': 'green', 'eye': 'violet', 'brow': 'brown', 'ear': 'yellow', 'mouth': 'red',
                        'hair': 'orange', 'neck': 'light_blue', 'cloth': 'purple'}

classes_to_segment_boolean_Indexing = list(classes_to_segment.values())

classes_list = list(compress(classes_to_segment, classes_to_segment_boolean_Indexing))
print("Classes list:", classes_list)

colors_list = [class_color_mapping.get(key) for key in classes_list]
print("Colors list:", colors_list)

colors_values_list = [all_colors.get(key) for key in colors_list]
print("Colors rgb values:", colors_values_list)

n_classes = len(classes_list)
print(n_classes, "classes")

figure_colors = plt.figure(figsize=(20, 4))
plt.suptitle("Class to color", fontsize = 30)

for idx, elem in enumerate(zip(classes_list, colors_values_list)):
        plt.subplot(1, len(classes_list), idx + 1)
        plt.title('{}'.format(elem[0]), fontsize = 20)
        plt.imshow(np.full((50, 50, 3), elem[1], dtype='uint8'))
        plt.axis('off')

"""## Load the model"""

from datetime import datetime, timezone
import pytz
tz = pytz.timezone('Europe/Rome')
italy_now = datetime.now(tz)
# initialize W&B with your project name and optionally with configutations.
model_name = "{}-{}-iou_{:.2f}".format(artifact_model_architecture, artifact_model_backbone, artifact_model_iou)
run_name = "{}-{}-inference-{}".format(artifact_model_architecture, artifact_model_backbone, italy_now.strftime("%d/%m/%y-%H:%M"))

run = wandb.init(project=project_name, job_type="training", name=run_name)
# use the newest/most recent version of this model
model_at = run.use_artifact(model_name + ":latest")
# download this model locally
save_model_dir = model_at.download() 
# load model using Keras
dice_loss = sm.losses.DiceLoss()
jackard_loss = sm.losses.JaccardLoss()
total_loss = dice_loss + jackard_loss
inference_model = keras.models.load_model(save_model_dir, custom_objects={'dice_loss_plus_jaccard_loss': total_loss,
                                                      'iou_score': sm.metrics.IOUScore(threshold=0.7),
                                                      'f1-score': sm.metrics.FScore(threshold=0.7)})

"""## Denormalized and RGB"""

"""
Denrmalize 'float32' image in [0,1] to 'uint8' image in [0,255]
"""
def denormalize(image):
    if image.dtype == 'uint8':
        raise ValueError('Cannot denormalize already uint8 image')
    return (image * 255.).astype('uint8')

"""
Convert denormalized image 'uint8' [0,255] to RGB image [0,255]
"""
def mask_channels_to_rgb(image):
    channels = np.dsplit(image, n_classes + 1)
    rgb_out_image = np.zeros((image_size, image_size, 3))
    # Iterate over binary masks and applying color to rgb image only in corresponding foreground pixels in masks 
    for idx, color in enumerate(colors_values_list):
        indexing = np.reshape(channels[idx], (image_size, image_size))
        indexing = indexing > 128 # Foreground
        rgb_out_image[indexing] = color
    # applying color to rgb image only in corresponding foreground pixels of background mask
    indexing = np.reshape(channels[-1], (image_size, image_size))
    indexing = indexing > 128
    rgb_out_image[indexing] = [0,0,0]
    return rgb_out_image.astype('uint8')

"""## Loading morphing dataset"""

def load_images_printscan_batches(folder_base, image_size, batches_to_load, images_per_batch = 3):
    group_images_to_load = batches_to_load * images_per_batch
    total_images_to_load = group_images_to_load * 2
    images_per_group = int(total_images_to_load / 2) # normal images and print and scanned
    normal_images = np.empty((images_per_group, image_size, image_size, 3), dtype='uint8')
    print_and_scan_images = np.empty((images_per_group, image_size, image_size, 3), dtype='uint8')
    
    loaded_images = 0
    morph_folders = os.listdir(folder_base)
    morph_folders.sort()
    for folder in morph_folders:
        folder_images = glob.glob("{}/{}/*Cropped*.png".format(folder_base, folder))
        folder_images.sort()
        for idx, img in enumerate(folder_images):
            if loaded_images >= total_images_to_load - 1:
                return normal_images, print_and_scan_images
            image = cv2.imread(img, cv2.IMREAD_COLOR)
            image = cv2.resize(image, (image_size, image_size))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            image_group_index = int(loaded_images/2)
            if idx % 2 == 0:
              normal_images[image_group_index] = image
            else:
              print_and_scan_images[image_group_index] = image
            loaded_images += 1
    return normal_images, print_and_scan_images

"""## Show image mosaic"""

# Show morphed images
def show_images_mosaic(title, images, images_predicted):
    test_mosaic = plt.figure(1, figsize=(30, 20))
    test_mosaic.suptitle(title, fontsize = 30)
    subplot_per_image = 2
    for idx in range(0, len(images_predicted) * subplot_per_image, subplot_per_image):
        row = 3
        col = 6 #2
        if idx > (col * row) - 1: break
        image_index = int(idx / subplot_per_image)
        # Subplot RGB
        image_to_predict = images[image_index]
        ax_image = test_mosaic.add_subplot(row, col, idx + 1)
        ax_image.axis('off')
        ax_image.set_title('{}'.format("Image: " + str(image_index)), fontsize = 20)
        img = denormalize(image_to_predict)
        image_plot = plt.imshow(img)
        # Subplot Mask
        mask = denormalize(images_predicted[image_index])
        ax_mask = test_mosaic.add_subplot(row, col, idx + 2)
        ax_mask.axis('off')
        ax_mask.set_title('{}'.format("Predicted Mask: " + str(image_index)), fontsize = 20)
        rgb_mask = mask_channels_to_rgb(mask)
        plt.imshow(rgb_mask)
        #plt.imshow(mask[:, :, 6], cmap='gray')
    return test_mosaic
    plt.show()
    plt.close()

"""## Load and predict dataset"""

# Load images
examples_to_load = 3
normal_images, print_and_scan_images = load_images_printscan_batches(morph_folder_base, image_size, examples_to_load)
print("Loaded {} normal and p&s images, eachone grouped in {} morphing examples".format(len(normal_images), examples_to_load))

# Normalize
normal_images = normal_images / 255.0
print_and_scan_images = print_and_scan_images / 255.0

# Predict
images_predicted = inference_model.predict(normal_images)

# Show result
normal_images_mosaic = show_images_mosaic("Test segmentation on morphed DB", normal_images, images_predicted)
print_and_scan_images_mosaic = show_images_mosaic("Test segmentation on p&s morphed DB", print_and_scan_images, images_predicted)



wandb.log({"Mosaics": [wandb.Image(normal_images_mosaic, caption="Test on morphed DB"), wandb.Image(print_and_scan_images_mosaic, caption="Test on p&s morphed DB")]}, commit=True)

wandb.finish()
if delete_run:
    api = wandb.Api()
    run = api.run("{}/{}/{}".format("Nini94", project_name, run.id))
    run.delete()