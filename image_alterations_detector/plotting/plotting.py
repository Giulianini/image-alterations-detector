import matplotlib.pyplot as plt


def get_images_mosaic_no_labels(title, images, rows, cols) -> plt.Figure:
    """
    Construct an image mosaic from a list of tuples

    :param title: the title of the mosaic
    :param images: a list of images
    :param rows: mosaic rows
    :param cols: mosaic cols
    :return: a matplotlib figure
    :raise: indexError if number of mosaic cells is less than images to show
    """
    figure_mosaic = plt.figure(1, figsize=(20, 10))
    figure_mosaic.suptitle(title, fontsize=30)
    rows = rows
    cols = cols
    if rows * cols < len(images):
        raise IndexError("Number of images grater than number of mosaic cells")
    for idx, image in enumerate(images):
        # Subplot RGB
        ax_image = figure_mosaic.add_subplot(rows, cols, idx + 1)
        ax_image.axis('off')
        ax_image.set_title(idx, fontsize=20)
        plt.imshow(image)
    return figure_mosaic


def get_images_mosaic_with_label(title, images_labels_data, rows, cols) -> plt.Figure:
    """
    Construct an image mosaic from a list of tuples

    :param title: the title of the mosaic
    :param images_labels_data: a list of tuples (image, caption)
    :param rows: mosaic rows
    :param cols: mosaic cols
    :return: a matplotlib figure
    :raise: indexError if number of mosaic cells is less than images to show
    """
    figure_mosaic = plt.figure(1, figsize=(20, 10))
    figure_mosaic.suptitle(title, fontsize=30)
    rows = rows
    cols = cols
    if rows * cols < len(images_labels_data):
        raise IndexError("Number of images grater than number of mosaic cells")
    for idx, image_label_data in enumerate(images_labels_data):
        # Subplot RGB
        image = image_label_data[0]
        caption = image_label_data[1]
        ax_image = figure_mosaic.add_subplot(rows, cols, idx + 1)
        ax_image.axis('off')
        ax_image.set_title(caption, fontsize=20)
        plt.imshow(image)
    return figure_mosaic
