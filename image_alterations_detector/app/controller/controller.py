from typing import Optional

import cv2
import numpy as np

from image_alterations_detector.app.utils.general_utils import show_message_box
from image_alterations_detector.app.view.view import View
from image_alterations_detector.dataset.altered_dataset.test_altered_dataset import test_two_images
from image_alterations_detector.descriptors.double_image_alteration_descriptors.triangle_descriptor_visualization import \
    draw_delaunay_alterations
from image_alterations_detector.face_morphology.landmarks_prediction.visualization import \
    visualize_facial_landmarks_points, visualize_facial_landmarks_areas
from image_alterations_detector.face_transform.face_alignment.face_aligner import FaceAligner
from image_alterations_detector.segmentation.face_segmenter import compute_general_iou, \
    denormalize_and_convert_rgb, compute_iou_per_mask, FaceSegmenter


class Controller:
    def __init__(self):
        self.ui: Optional[View] = None
        self.img_source: Optional[np.ndarray] = None
        self.img_target: Optional[np.ndarray] = None
        self.face_aligner = FaceAligner()
        self.face_segmenter = FaceSegmenter()
        self.img_source_aligned: Optional[np.ndarray] = None
        self.img_target_aligned: Optional[np.ndarray] = None
        self.landmarks_source: Optional[np.ndarray] = None
        self.landmarks_target: Optional[np.ndarray] = None

    def check_images(self):
        return self.img_source is None or self.img_target is None

    def load_image_form_path(self, img_path, img_type):
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if img_type == 'source':
            self.img_source = img
            self.ui.tab1.set_image1(self.img_source)
        else:
            self.img_target = img
            self.ui.tab1.set_image2(self.img_target)

    def take_webcam_photo(self):
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        cam.release()
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.img_source = img
        self.ui.tab1.set_image1(self.img_source)

    def align_images(self):
        if self.check_images():
            show_message_box('please load both images', 'warning')
        else:
            self.img_source_aligned, self.landmarks_source = self.face_aligner.align(self.img_source)
            self.img_target_aligned, self.landmarks_target = self.face_aligner.align(self.img_target)
            # Get alignment view
            visual_source = visualize_facial_landmarks_points(self.img_source_aligned, self.landmarks_source)
            visual_target = visualize_facial_landmarks_points(self.img_target_aligned, self.landmarks_target)
            visual_source = visualize_facial_landmarks_areas(visual_source, self.landmarks_source, alpha=0.5)
            visual_target = visualize_facial_landmarks_areas(visual_target, self.landmarks_target, alpha=0.5)
            self.ui.tab1.show_aligned(visual_source, visual_target)

    def analyze_images(self, animate):
        if self.check_images():
            show_message_box('please load both images', 'warning')
        else:
            draw_delaunay_alterations(self.img_source, self.img_target, animate=animate,
                                      show_function=lambda img1, img2: self.ui.tab2.set_triangulation_images(img1,
                                                                                                             img2))
            res = test_two_images(self.img_source, self.img_target)
            self.ui.tab2.show_result(res)

    def segment_images(self):
        if self.check_images():
            show_message_box('please load both images', 'warning')
        else:
            segmented = self.face_segmenter.segment_images([self.img_source_aligned, self.img_target_aligned])
            rgb_images = denormalize_and_convert_rgb(segmented)
            general_iou = compute_general_iou(segmented[0], segmented[1])
            masks_iou = compute_iou_per_mask(segmented[0], segmented[1])
            self.ui.tab3.set_segmentation_infos(rgb_images[0], rgb_images[1], general_iou, masks_iou)

    def set_ui(self, ui):
        self.ui = ui

    def start(self):
        self.ui.show()
