import cv2

from image_alterations_detector.file_system.path_utilities import get_image_path


def load_img(image_name):
    img = cv2.imread(get_image_path(get_image_path(image_name)), cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img
