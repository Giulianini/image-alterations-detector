import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_root_folder_path(file, folder_path_from_root):
    """ Get the path to a sub-root folder

    :param file: the file
    :param folder_path_from_root: the sub-root folder
    :return: the absolute path
    """
    file_path = os.path.join(ROOT_DIR, folder_path_from_root, file)
    if not os.path.exists(file_path):
        raise FileNotFoundError('Check if file exists')
    else:
        return file_path


def get_model_path(model_file) -> str:
    """ Get the path to the model file

    :param model_file: the model file
    :return: the absolute path
    """
    return get_root_folder_path(model_file, 'models')


def get_image_path(image_file) -> str:
    """ Get the path to the image file

        :param image_file: the image file
        :return: the absolute path
        """
    return get_root_folder_path(image_file, 'images')