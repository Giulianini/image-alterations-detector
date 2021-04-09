# -*- coding: utf-8 -*-
"""SemanticSegmentationUnet.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1i-NCJ8d34vfbDZHq6bsTUZ9Ak3TMkUu1

# Semantic Segmentation with U-Net

## Notebook configuration
"""

########################################## CONFIGURATION ####################################
# Dataset variables
total_images = 30000
images_to_load = 10000
image_size = 256
augmentation = 0.5
# Net variables
noisy_student_weights_path_b3 = "/content/efficientnet-b3_noisy-student_notop.h5" 
noisy_student_weights_path_b4 = "/content/efficientnet-b4_noisy-student_notop.h5"
architecture = 'UNet'
backbone = 'efficientnetb3'
backbone_weights = noisy_student_weights_path_b3
frozen_epochs = 10
fine_tune_epochs = 50
batch_size = 32
min_lr = 0.0001
max_lr = 0.001
classes_to_segment = {'skin': True, 'nose': True, 'eye': True, 'brow': True, 'ear': True, 'mouth': True, 
                      'hair': True, 'neck': True, 'cloth': False}

"""## GPU Info"""

gpu_info = !nvidia-smi
gpu_info = '\n'.join(gpu_info)
if gpu_info.find('failed') >= 0:
  print('Select the Runtime > "Change runtime type" menu to enable a GPU accelerator, ')
  print('and then re-execute this cell.')
else:
  print("GPU T4 or P100")
  print(gpu_info)

"""## Global imports and unzipping dataset"""

!pip install segmentation_models -q
!pip install -U git+https://github.com/albu/albumentations --no-cache-dir -q
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
# Connecting to W&B
wandb.login()
# Connecting to google drive
drive.mount('/content/drive')
# Unzipping dataset
if not os.path.isdir("/content/CelebAMask-HQ"):
  !unzip -q "/content/drive/MyDrive/MasterThesis/CelebAMask-HQ.zip"
  !cp "/content/drive/MyDrive/MasterThesis/efficientnet-b4_noisy-student_notop.h5" "efficientnet-b4_noisy-student_notop.h5"
  !cp "/content/drive/MyDrive/MasterThesis/efficientnet-b3_noisy-student_notop.h5" "efficientnet-b3_noisy-student_notop.h5"

"""## Folder configuration
Preparing output folders:
  - **../output/**
"""

import time
############# OUTPUT CONFIGURATION ###########
def create_new_folder(directory):
    if not os.path.exists(directory):
        try:
            os.mkdir(directory)
        except:
            print("Could not create {} directory".format(directory))
output_directory = r"../output/"
figure_directory = output_directory + r"figures/"
models_directory = output_directory + r"models/"
classifiers_directory = output_directory + r"classifiers/"
logs_directory = output_directory + r"logs/"
model_directory = models_directory + time.strftime('%Y-%m-%d %H-%M-%S') + "/"
log_directory = logs_directory + time.strftime('%Y-%m-%d %H-%M-%S') + "/"

create_new_folder(output_directory)
create_new_folder(figure_directory)
create_new_folder(models_directory)
create_new_folder(logs_directory)
create_new_folder(model_directory)
create_new_folder(classifiers_directory)
create_new_folder(log_directory)

def clean_models_directory():
  import shutil
  shutil.rmtree(models_directory, ignore_errors=True)
  create_new_folder(models_directory)
  create_new_folder(model_directory)

print("Output folders created under:", output_directory)

"""## Segmentation configuration"""

from itertools import compress
IN_CLOUD = True
root_folder = "./" if not IN_CLOUD else "/content/CelebAMask-HQ/"
folder_images = root_folder + "CelebA-HQ-img"
folder_masks = root_folder + "CelebAMask-HQ-mask-anno"

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

"""## Show maks channels in RGB
Merge and convert stacked masks to single RGB image according to color mapping.
"""

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

"""## Class distribution and weight definition
Segmentation classes (masks) are not equally distributed through all images. The distribution can vary according to:
  - Frequence
  - Pixels belonging to each class

Algorithm:
  
  1. Create a vector of pixel sums (**classes_pixel_sum**) for each class (mask)
  2. Iterate over n sample images (200)
  3. Iterate over all masks (18)
  4. For each mask sum all **foreground pixels** 
  5. Add the pixel sum (**sum_pixels_mask**) of the mask to the corresponding bin of (**classes_pixel_sum**) vector
  6. Divide the sum for the number of images (200) optaining a vector of mean per bin (**classes_pixel_mean**)
  7. Normalize with **norm L1** the vector so that each bin represents a the probability to find pixels of the corresponding mask
  8. The probability vector corresponds to classes (mask) weight

"""

'''
Take the number of classes with background and compute distribution
'''
def compute_class_distribution(masks, samples_number, n_classes):
    from sklearn import preprocessing
    classes_pixel_sum = np.zeros(n_classes + 1)
    label_list_background = list(classes_list)
    label_list_background.append('background')

    for i in range(samples_number):
        image_masks = masks[i]
        # Computing on label list
        for idx, label in enumerate(label_list_background):
            mask = image_masks[:,:,idx]
            sum_pixels_mask = mask[mask > 128].sum()
            classes_pixel_sum[idx] += sum_pixels_mask

    classes_pixel_mean = (classes_pixel_sum/samples_number).astype(int)
    classes_weight = preprocessing.normalize([classes_pixel_mean], norm='l1')
    classes_weight = np.reshape(classes_weight, (n_classes + 1))

    # for (label, weight) in zip(label_list_background, classes_weight):
    #     print("{:10s} : {:5f}".format(label, weight))

    # print("Total :", classes_weight.sum())

    # Pie chart, where the slices will be ordered and plotted counter-clockwise
    global figure_distribution
    figure_distribution = plt.figure(figsize=(20, 15))
    plt.suptitle("Classes distribution", fontsize = 35)
    colors = [tuple(np.array(col)/255) for col in colors_values_list]
    plt.gca().axis("equal")
    pie = plt.pie(classes_weight, shadow=True, startangle=90, colors=colors, labels=label_list_background, rotatelabels=False, textprops={'fontsize': 25})
    #draw circle
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    #Legend
    plt.legend(
        title="Classes",
        title_fontsize=30, 
        labels=['%s, %1.1f%%' % (l, (float(s)) * 100) for l, s in zip(label_list_background, classes_weight)],
        bbox_to_anchor=(1,0.5), 
        loc="center right", 
        fontsize=25, 
        bbox_transform=plt.gcf().transFigure
    )
    plt.subplots_adjust(left=0.0, bottom=0.1, right=0.7)
    plt.show()
    return classes_weight

"""## Load and preprocess images and masks
Masks are optained stacking single gray-images toghether depthwise then appended to a list.

Example with image_size = 512 and 18 classes:

- U-Net Mask:
  1. Gray mask shape: **(512, 512, 1)**
  2. NClasses = 18 
  3. Merge mask shape = **(512, 512, 18)**
  4. Stack background = **(512, 512, 19)**

Images are just appended to a list.
- Image rgb:
  1. Image shape: **(512, 512, 3)**
"""

from IPython.display import clear_output

def assemble_mask_levels(mask_file):
    masks_stack = np.zeros((image_size, image_size, 1)) # Base to stack
    masks_foreground = np.zeros((image_size, image_size, 1), 'uint8') # Sum of all masks foreground
    # Assembling sub-labels for each class definend by user. For example [EYE, NOSE, ...] are assembled together
    for idx, class_name in enumerate(classes_list):
        # Sum of all masks' labels of the same class
        class_mask = np.zeros((image_size, image_size, 1), 'uint8') 
        class_labels = class_labels_mapping[class_name]
        # Iterate over sub-labels and create a unique mask level for class. For example EYE = [r_eye, l_eye, ...] are assembled together
        for label in class_labels:
            filename = mask_file + '_' + label + '.png'
            if os.path.exists(filename):
                im = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
                im = cv2.resize(im, (image_size, image_size))
                class_mask[im != 0] = 255
        # Stack to other masks
        masks_stack = class_mask if idx == 0 else np.dstack((masks_stack, class_mask)) # Not stack the first
        # Increase total foreground pixels
        masks_foreground[class_mask != 0] = 255

    # Adding background mask at the end
    background_mask = (255 - masks_foreground)
    masks_stack = np.dstack((masks_stack, background_mask))
    return masks_stack

def load_dataset_batch(start, stop):
    print("Loading dataset time complex")
    batch_size = stop - start
    loaded_images = np.empty((batch_size, image_size, image_size, 3), dtype='uint8')
    loaded_masks = np.empty((batch_size, image_size, image_size, n_classes + 1), dtype='uint8')
    
    print("Loading and stacking masks")
    for k in range(start, stop):
        folder_num = k // 2000
        mask_file = os.path.join(folder_masks, str(folder_num), str(k).rjust(5, '0'))
      
        # Appending mask stack
        loaded_masks[k] = assemble_mask_levels(mask_file)

        # Compute progress bar
        percentage_loaded = (k / batch_size) * 100
        if percentage_loaded % 10 == 0: 
          print(percentage_loaded, "%")

    print("Loading images")
    for i in range(start, stop):
        image = cv2.imread("{}/{}.jpg".format(folder_images, i), cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (image_size, image_size))      
        
        # Appending image stack
        loaded_images[i] = image

        # Compute progress bar
        percentage_loaded = (i / batch_size) * 100
        if percentage_loaded % 10 == 0: 
          print(percentage_loaded, "%")

    clear_output()
    return loaded_images, loaded_masks

"""## Load dataset"""

def load_data(start, stop, show_example):
    images, masks = load_dataset_batch(start, stop)

    if show_example:
        # Show augmentation
        global figure_sample 
        figure_sample = plt.figure(figsize=(20, 8))
        plt.suptitle("Image example", fontsize = 30)

        plt.subplot(1, 3, 1)
        plt.axis('off')
        plt.title('{}'.format("Image"), fontsize = 20)
        plt.imshow(images[0])

        plt.subplot(1, 3, 2)
        plt.axis('off')
        plt.title('{}'.format("Mask"), fontsize = 20)
        rgb_mask = mask_channels_to_rgb(masks[0])
        plt.imshow(rgb_mask)

        plt.subplot(1, 3, 3)
        plt.axis('off')
        plt.title('{}'.format("Background"), fontsize = 20)
        plt.imshow(masks[0][:,:,-1], cmap='gray')

        plt.show()
    return images, masks

# Load dataset
images, masks = load_data(0, images_to_load, show_example=True)

"""## Split dataset

*   Load images in batch
*   Compute class distribution on sample list
*   Split dataset
"""

def shuffle_arrays(arrays, set_seed=-1):
    assert all(len(arr) == len(arrays[0]) for arr in arrays)
    seed = np.random.randint(0, 2**(32 - 1) - 1) if set_seed < 0 else set_seed
    for arr in arrays:
        rstate = np.random.RandomState(seed)
        rstate.shuffle(arr)

# Shuffling dataset
shuffle_arrays([images, masks])

# Train test splitting using pythn views on dataset
x_train_start = images[:int(0.8 * len(images))]
y_train_start = masks[:int(0.8 * len(masks))]
x_test = images[len(x_train_start):]
y_test = masks[len(y_train_start):]

x_train = x_train_start[:int(0.8 * len(x_train_start))]
y_train = y_train_start[:int(0.8 * len(y_train_start))]
x_val = x_train_start[len(x_train): len(x_train_start)]
y_val = y_train_start[len(y_train): len(y_train_start)]

# Compute class weights
print("Dataset dimensions: [{}, {}] \ntrain: {} \nvalid: {} \ntest: {}".format(images.shape, masks.shape, len(x_train), len(x_val), len(x_test)))
distribution_masks_samples = np.array(y_test[0:200])
classes_weight = compute_class_distribution(distribution_masks_samples, distribution_masks_samples.shape[0], n_classes)

"""## Prepare generators"""

import albumentations as A
from keras.utils.data_utils import Sequence

class Dataloader(Sequence):
    def __init__(self, x_set, y_set, batch_size, augmentations, shuffle=False):
        self.x, self.y = x_set, y_set
        self.batch_size = batch_size
        self.augment = augmentations
        self.shuffle = shuffle
        self.indexes = np.arange(len(x_set))
        self.batch_shape_x = (self.batch_size, self.x.shape[1], self.x.shape[2], self.x.shape[3])
        self.batch_shape_y = (self.batch_size, self.y.shape[1], self.y.shape[2], self.y.shape[3])
        self.on_epoch_end()

    def __len__(self):
        return int(np.ceil(len(self.x) / float(self.batch_size)))

    def __getitem__(self, idx):
        indexes = self.indexes[idx * self.batch_size:(idx + 1) * self.batch_size]
        
        batch_x_out = np.empty(self.batch_shape_x, dtype='float32')
        batch_y_out = np.empty(self.batch_shape_y, dtype='float32')
        
        for i, random_index in enumerate(indexes):
            transformed = self.augment(image=self.x[random_index], mask=self.y[random_index])
            batch_x_out[i] = transformed['image']
            batch_y_out[i] = transformed['mask']
        return batch_x_out, batch_y_out

    def on_epoch_end(self):
        if self.shuffle:
            self.indexes = np.random.permutation(self.indexes)

def get_training_augmentation():
    return A.Compose([
        A.RandomSizedCrop((image_size - 80, image_size - 80), image_size, image_size, interpolation=cv2.INTER_LANCZOS4, p=0.3),
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=30, p=0.5),
        A.OneOf([
            A.ElasticTransform(alpha=200, sigma=200 * 0.15, alpha_affine=200 * 0.05, p=0.3),
            A.OpticalDistortion(distort_limit=0.5, shift_limit=0.5, p=0.3),
            A.GridDistortion(p=0.5),
        ], p=0.3),
        A.ToFloat(max_value=255, always_apply=True),
    ], additional_targets={'mask': 'image'}, p=augmentation)

def get_validation_augmentation():
    return A.Compose([
        A.ToFloat(max_value=255),
    ], additional_targets={'mask': 'image'})

def get_preprocessing(preprocessing_fn):
    _transform = [
        A.Lambda(image=preprocessing_fn),
    ]
    return A.Compose(_transform)

# Create generators
train_generator = Dataloader(x_train, y_train, batch_size, get_training_augmentation(), shuffle=True)
val_generator = Dataloader(x_val, y_val, batch_size, get_validation_augmentation())
test_generator = Dataloader(x_test, y_test, batch_size, get_validation_augmentation())

# Show augmentation
augmentation_mosaic = plt.figure(figsize=(30, 20))
plt.suptitle("Augmentation", fontsize = 30)
for batch in train_generator:
  for idx in range(0, len(batch[0]), 2):
      row = 4
      col = 6
      if idx > (col * row) - 1:
        break
      plt.subplot(row, col, idx + 1)
      plt.axis('off')
      plt.title('{}'.format("Image: " + str(int(idx / 2))), fontsize = 20)
      img = denormalize(batch[0][idx])
      fig = plt.imshow(img)

      plt.subplot(row, col, idx + 2)
      plt.axis('off')
      plt.title('{}'.format("Mask: " + str(int(idx / 2))), fontsize = 20)
      mask = denormalize(batch[1][idx])
      rgb_mask = mask_channels_to_rgb(mask)
      plt.imshow(rgb_mask)
  break
plt.show()

"""## Defining callbacks"""

#@title Callback module
from keras.callbacks import Callback
from keras import backend as K
import numpy as np


class CyclicLR(Callback):
    """This callback implements a cyclical learning rate policy (CLR).
    The method cycles the learning rate between two boundaries with
    some constant frequency.
    # Arguments
        base_lr: initial learning rate which is the
            lower boundary in the cycle.
        max_lr: upper boundary in the cycle. Functionally,
            it defines the cycle amplitude (max_lr - base_lr).
            The lr at any cycle is the sum of base_lr
            and some scaling of the amplitude; therefore
            max_lr may not actually be reached depending on
            scaling function.
        step_size: number of training iterations per
            half cycle. Authors suggest setting step_size
            2-8 x training iterations in epoch.
        mode: one of {triangular, triangular2, exp_range}.
            Default 'triangular'.
            Values correspond to policies detailed above.
            If scale_fn is not None, this argument is ignored.
        gamma: constant in 'exp_range' scaling function:
            gamma**(cycle iterations)
        scale_fn: Custom scaling policy defined by a single
            argument lambda function, where
            0 <= scale_fn(x) <= 1 for all x >= 0.
            mode paramater is ignored
        scale_mode: {'cycle', 'iterations'}.
            Defines whether scale_fn is evaluated on
            cycle number or cycle iterations (training
            iterations since start of cycle). Default is 'cycle'.
    The amplitude of the cycle can be scaled on a per-iteration or
    per-cycle basis.
    This class has three built-in policies, as put forth in the paper.
    "triangular":
        A basic triangular cycle w/ no amplitude scaling.
    "triangular2":
        A basic triangular cycle that scales initial amplitude by half each cycle.
    "exp_range":
        A cycle that scales initial amplitude by gamma**(cycle iterations) at each
        cycle iteration.
    For more detail, please see paper.
    # Example for CIFAR-10 w/ batch size 100:
        ```python
            clr = CyclicLR(base_lr=0.001, max_lr=0.006,
                                step_size=2000., mode='triangular')
            model.fit(X_train, Y_train, callbacks=[clr])
        ```
    Class also supports custom scaling functions:
        ```python
            clr_fn = lambda x: 0.5*(1+np.sin(x*np.pi/2.))
            clr = CyclicLR(base_lr=0.001, max_lr=0.006,
                                step_size=2000., scale_fn=clr_fn,
                                scale_mode='cycle')
            model.fit(X_train, Y_train, callbacks=[clr])
        ```
    # References
      - [Cyclical Learning Rates for Training Neural Networks](
      https://arxiv.org/abs/1506.01186)
    """

    def __init__(
            self,
            base_lr=0.001,
            max_lr=0.006,
            step_size=2000.,
            mode='triangular',
            gamma=1.,
            scale_fn=None,
            scale_mode='cycle'):
        super(CyclicLR, self).__init__()

        if mode not in ['triangular', 'triangular2',
                        'exp_range']:
            raise KeyError("mode must be one of 'triangular', "
                           "'triangular2', or 'exp_range'")
        self.base_lr = base_lr
        self.max_lr = max_lr
        self.step_size = step_size
        self.mode = mode
        self.gamma = gamma
        if scale_fn is None:
            if self.mode == 'triangular':
                self.scale_fn = lambda x: 1.
                self.scale_mode = 'cycle'
            elif self.mode == 'triangular2':
                self.scale_fn = lambda x: 1 / (2.**(x - 1))
                self.scale_mode = 'cycle'
            elif self.mode == 'exp_range':
                self.scale_fn = lambda x: gamma ** x
                self.scale_mode = 'iterations'
        else:
            self.scale_fn = scale_fn
            self.scale_mode = scale_mode
        self.clr_iterations = 0.
        self.trn_iterations = 0.
        self.history = {}

        self._reset()

    def _reset(self, new_base_lr=None, new_max_lr=None,
               new_step_size=None):
        """Resets cycle iterations.
        Optional boundary/step size adjustment.
        """
        if new_base_lr is not None:
            self.base_lr = new_base_lr
        if new_max_lr is not None:
            self.max_lr = new_max_lr
        if new_step_size is not None:
            self.step_size = new_step_size
        self.clr_iterations = 0.

    def clr(self):
        cycle = np.floor(1 + self.clr_iterations / (2 * self.step_size))
        x = np.abs(self.clr_iterations / self.step_size - 2 * cycle + 1)
        if self.scale_mode == 'cycle':
            return self.base_lr + (self.max_lr - self.base_lr) * \
                np.maximum(0, (1 - x)) * self.scale_fn(cycle)
        else:
            return self.base_lr + (self.max_lr - self.base_lr) * \
                np.maximum(0, (1 - x)) * self.scale_fn(self.clr_iterations)

    def on_train_begin(self, logs={}):
        logs = logs or {}

        if self.clr_iterations == 0:
            K.set_value(self.model.optimizer.lr, self.base_lr)
        else:
            K.set_value(self.model.optimizer.lr, self.clr())

    def on_batch_end(self, epoch, logs=None):

        logs = logs or {}
        self.trn_iterations += 1
        self.clr_iterations += 1
        K.set_value(self.model.optimizer.lr, self.clr())

        self.history.setdefault(
            'lr', []).append(
            K.get_value(
                self.model.optimizer.lr))
        self.history.setdefault('iterations', []).append(self.trn_iterations)

        for k, v in logs.items():
            self.history.setdefault(k, []).append(v)

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        logs['lr'] = K.get_value(self.model.optimizer.lr)

from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, EarlyStopping
##################### SETTINGS CALLBACKS ####################
model_file = model_directory + "best_model.hdf5"
# define callbacks for learning rate scheduling and best checkpoints saving
callbacks = [
    ModelCheckpoint(model_file, save_weights_only=True, save_best_only=True, mode='min'),
    ReduceLROnPlateau(),
]

checkpoint = ModelCheckpoint(
    model_file,
    monitor='val_iou_score',
    mode='max',
    save_best_only=True)

early_stopping = EarlyStopping(
    monitor='val_iou_score',
    mode='max',
    min_delta=0.01,
    patience=10,
    verbose=1,
    restore_best_weights=True)

reduce_lr = ReduceLROnPlateau(
    monitor='val_loss',
    min_lr=0.00001,
    cooldown=5,
    factor=0.5,
    patience=10,
    verbose=1)

clr_fn = lambda x: 1/(5**(x*0.0001))
clr_traingular_decay = CyclicLR(
    base_lr=min_lr, 
    max_lr=max_lr,
    step_size=4.0 * len(train_generator), 
    scale_fn=clr_fn,
    mode='exp_range',
    scale_mode='iterations')

clr_traingular_2 = CyclicLR(
    base_lr=min_lr, 
    max_lr=max_lr,
    step_size=5.0 * len(train_generator), 
    mode='triangular2')

"""## Fine tuning"""

from segmentation_models.utils import set_trainable
from wandb.keras import WandbCallback
from datetime import datetime, timezone
import pytz

# initialize W&B with your project name and optionally with configutations.
tz = pytz.timezone('Europe/Rome')
italy_now = datetime.now(tz)
run = wandb.init(project='FaceParsingUNet', job_type="training", name="{}-{}-{}".format(architecture, backbone, italy_now.strftime("%d/%m/%y-%H:%M")),
           config={
              "framework": "keras",
              "dataset": "CelebAMask-HQ",
              'loaded_images': images_to_load,
              "image_size": image_size,
              "backbone": backbone,
              "architecture": architecture,
              "learning_rate": "cyclic_triangular_decay",
              "frozen_epochs": frozen_epochs,
              "fine_tune_epochs": fine_tune_epochs,
              "min_lr": min_lr,
              "max_lr": max_lr,
              "batch_size": batch_size,
              "augmentation": augmentation,
              "loss_function": "dice_loss + jackard_loss",
              "metrics:": "iou_score, f_score"
           })

# Loss
print("Applying class weights to loss:", ["%.2f"%item for item in classes_weight])
dice_loss = sm.losses.DiceLoss(class_weights=classes_weight)
jackard_loss = sm.losses.JaccardLoss(class_weights=classes_weight)
total_loss = dice_loss + jackard_loss
# Metrics
metrics = [sm.metrics.IOUScore(threshold=0.7), sm.metrics.FScore(threshold=0.7)]
# Callbacks
callbacks = [checkpoint, 
             early_stopping, 
             clr_traingular_decay,
             WandbCallback()]
# Model
model = sm.Unet(backbone, encoder_weights=backbone_weights, classes=n_classes + 1, activation='sigmoid', encoder_freeze=True)
model.compile('Adam', loss=total_loss, metrics=metrics)

# Pretrain model decoder
history_frozen = model.fit(train_generator, 
                            validation_data=val_generator, 
                            epochs=frozen_epochs, 
                            steps_per_epoch=len(train_generator), 
                            validation_steps=len(val_generator),
                            callbacks=callbacks)

# Release all layers for training
for layer in model.layers:
    layer.trainable = True
model.compile(keras.optimizers.Adam(lr=0.01), loss=total_loss, metrics=metrics)

history_fine_tune = model.fit(train_generator, 
                    validation_data=val_generator,
                    initial_epoch=frozen_epochs,
                    epochs=fine_tune_epochs,
                    steps_per_epoch=len(train_generator), 
                    validation_steps=len(val_generator),
                    callbacks=callbacks)

# Merging histories
history = dict()
for some_key in history_frozen.history.keys():
    current_values = [] # to save values from all three hist dicts
    for hist_dict in [history_frozen.history, history_fine_tune.history]:
        current_values += hist_dict[some_key]
    history[some_key] = current_values

"""## Evaluation"""

import matplotlib.pyplot as plt
################## EVALUATE ####################

# Plot training & validation iou_score values
figure_iou_score = plt.figure(figsize=(30, 8))
figure_iou_score.suptitle("Model Evaluation", fontsize = 30)
plt.subplot(121)
plt.plot(history['iou_score'])
plt.plot(history['val_iou_score'])
plt.title('Model iou_score', fontsize = 20)
plt.ylabel('iou_score', fontsize = 15)
plt.xlabel('Epoch', fontsize = 15)
plt.legend(['Train', 'Test'], loc='upper left')

# Plot training & validation loss values
plt.subplot(122)
plt.plot(history['loss'])
plt.plot(history['val_loss'])
plt.title('Model loss', fontsize = 20)
plt.ylabel('Loss', fontsize = 15)
plt.xlabel('Epoch', fontsize = 15)
plt.legend(['Train', 'Test'], loc='upper left')
plt.savefig(figure_directory + "iou_score_loss_graph.pdf")

# Plot learning rate history
figure_clr = plt.figure(figsize=(30, 8))
figure_clr.suptitle("Ciclic Learning Rate", fontsize = 30)
plt.subplot(1, 2, 1)
plt.plot(clr_traingular_decay.history['iterations'], clr_traingular_decay.history['lr'])
plt.title('CLR - Custom Iteration-Policy', fontsize = 20)
plt.ylabel('Learning Rate', fontsize = 15)
plt.xlabel('Training Iterations', fontsize = 15)

plt.subplot(1, 2, 2)
plt.suptitle("Cyclic Learning Rate", fontsize = 30)
plt.plot(clr_traingular_decay.history['iterations'], clr_traingular_decay.history['iou_score'])
plt.title('CLR - Learning Rate vs IOU Score', fontsize = 20)
plt.ylabel('IOU Score', fontsize = 15)
plt.xlabel('Training Iterations', fontsize = 15)
plt.savefig(figure_directory + "cyclic_learning_rate.pdf")
plt.show()

"""## Metrics"""

################ METRICS ###################
print(len(test_generator))
test_metrics = model.evaluate(test_generator, verbose=1, steps=len(test_generator))
print()
print(f'LOSS : {test_metrics[0]}')
print(f'IOU SCORE : {test_metrics[1]}')
print(f'F1 SCORE : {test_metrics[2]}')
# Update W&B accuracy to best
wandb.run.summary['val_loss'] = min(history['val_loss'])
wandb.run.summary['val_iou_score'] = max(history['val_iou_score'])
wandb.run.summary['val_f1-score'] = max(history['val_f1-score'])
wandb.run.summary['iou_score'] = max(history['iou_score'])
wandb.run.summary['f1-score'] = max(history['f1-score'])
# Logging test evaluations
wandb.run.summary['test_loss'] = test_metrics[0]
wandb.run.summary['test_iou_score'] = test_metrics[1]
wandb.run.summary['test_f1-score'] = test_metrics[2]
# Saving model
model_name = "{}-{}-iou_{:.2f}".format(architecture, backbone, test_metrics[1])
save_model_dir = "/content/save_model/"
model.save(save_model_dir)
# Load artifact model
model_artifact = wandb.Artifact(model_name, type="model", description="Trained on CelebAMask-HQ", metadata=dict(wandb.config))
model_artifact.add_dir(save_model_dir)
run.log_artifact(model_artifact)

"""## Test"""

# Show test images
test_mosaic = plt.figure(1, figsize=(30, 20))
plt.suptitle("Test segmentation", fontsize = 30)

for batch in test_generator:
  batch_predicted = model.predict(batch[0])
  for idx in range(0, len(batch_predicted), 2):
      row = 4
      col = 6
      if idx > (col * row) - 1:
        break
      image_to_predict = batch[0][idx]
      plt.subplot(row, col, idx + 1)
      plt.axis('off')
      plt.title('{}'.format("Image: " + str(int(idx / 2))), fontsize = 20)
      img = denormalize(image_to_predict)
      plt.imshow(img)

      plt.subplot(row, col, idx + 2)
      plt.axis('off')
      plt.title('{}'.format("Predicted Mask: " + str(int(idx / 2))), fontsize = 20)
      mask = denormalize(batch_predicted[idx])
      rgb_mask = mask_channels_to_rgb(mask)
      plt.imshow(rgb_mask)
      #plt.imshow(mask[:, :, 6], cmap='gray')
  break
plt.show()
plt.savefig(figure_directory + "test_images.pdf")


wandb.log({"Training charts": [wandb.Image(figure_iou_score, caption="iou_score_loss_graph"), wandb.Image(figure_clr, caption="cyclic_learning_rate")]}, commit=False)
wandb.log({"Mosaics": [wandb.Image(augmentation_mosaic, caption="Augmentation"), wandb.Image(test_mosaic, caption="Test segmentation")]}, commit=False)
wandb.log({"Figures": [wandb.Image(figure_colors, caption="Class to colors"), wandb.Image(figure_sample, caption="Image example"), wandb.Image(figure_distribution, caption="Classes distribution")]}, commit=True)

wandb.finish()

"""## Test on my photo"""

# Show augmentation
plt.figure(1, figsize=(10, 5))
plt.suptitle("Test me segmented")
plt.axis('off')

im = cv2.imread(output_directory + 'luca.jpg', cv2.IMREAD_COLOR)
im = cv2.resize(im, (image_size, image_size), cv2.INTER_LANCZOS4)
im = np.array(im, 'float32') / 255.
im = np.expand_dims(im, 0)

im_predicted = model.predict(im)
im_predicted = np.squeeze(im_predicted, axis=0)

im = np.squeeze(im, axis=0)

plt.subplot(1, 2, 1)
plt.title('Image')
im = denormalize(im)
plt.imshow(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))

plt.subplot(1, 2, 2)
plt.title('Mask')
im_predicted = denormalize(im_predicted)
im_predicted = mask_channels_bgr(im_predicted)
plt.imshow(cv2.cvtColor(im_predicted, cv2.COLOR_BGR2RGB))

plt.savefig(figure_directory + "Me_segmented.pdf")
plt.show()