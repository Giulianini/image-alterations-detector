import os

import segmentation_models as sm
import tensorflow
from tensorflow import keras
from tensorflow.python.keras.models import Model

from image_alterations_detector.file_system.path_utilities import ROOT_DIR


def load_model(model_path):
    """ Load the model from path

    :param model_path: the path to the model .h5 file
    :return: the Keras model
    """
    dice_loss = sm.losses.DiceLoss()
    jaccard_loss = sm.losses.JaccardLoss()
    total_loss = dice_loss + jaccard_loss
    inference_model = keras.models.load_model(
        model_path,
        custom_objects={
            'dice_loss_plus_jaccard_loss': total_loss,
            'iou_score': sm.metrics.IOUScore(
                threshold=0.7),
            'f1-score': sm.metrics.FScore(
                threshold=0.7)
        }
    )
    return inference_model


def serialize_tflite_model(model: Model, image_size):
    # Convert the model.
    model.input.set_shape((1, image_size, image_size, 3))
    converter = tensorflow.lite.TFLiteConverter.from_keras_model(model)
    converter.experimental_new_converter = True
    converter.experimental_new_quantizer = True
    quantized_and_pruned_tflite_model = converter.convert()
    with open(os.path.join(ROOT_DIR, 'models', 'unet-{}.tflite'.format(image_size)), 'wb') as f:
        f.write(quantized_and_pruned_tflite_model)
