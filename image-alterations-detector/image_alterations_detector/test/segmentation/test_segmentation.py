from face_transform.face_alignment.face_aligner import FaceAligner
from file_system.path_utilities import get_image_path, get_model_path
from segmentation.configuration.keras_backend import set_keras_backend


def main():
    set_keras_backend()
    import cv2
    import matplotlib.pyplot as plt
    import segmentation.configuration.color_configuration as color_conf
    import segmentation.conversions as conversions
    import segmentation.model as model

    # Configuration
    image_size = 512
    aligner = FaceAligner(desired_face_width=image_size)
    classes_to_segment = {'skin': True, 'nose': True, 'eye': True, 'brow': True, 'ear': True, 'mouth': True,
                          'hair': True, 'neck': True, 'cloth': False}
    classes_list, colors_values_list = color_conf.get_classes_colors(classes_to_segment)

    # Images
    img1 = cv2.imread(get_image_path('img1.jpg'), cv2.IMREAD_COLOR)
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
    img1 = aligner.align(img1, )
    img1 = img1.reshape((1, img1.shape[0], img1.shape[1], img1.shape[2])).astype('float')
    img1_normalized = img1 / 255.0

    # Predict
    inference_model = model.load_model(get_model_path('unet.h5'))

    images_predicted = inference_model.predict(img1_normalized)
    predicted = conversions.denormalize(images_predicted[0])
    predicted_rgb = conversions.mask_channels_to_rgb(predicted, 8, image_size, colors_values_list)
    plt.imshow(predicted_rgb)
    plt.show()


if __name__ == '__main__':
    main()