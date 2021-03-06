import tkinter as tk
from tkinter.ttk import Notebook
from typing import Optional, List, Tuple

from image_alterations_detector.app.utils.conversion import convert_to_tk_image, \
    image_resize_with_border
from image_alterations_detector.app.utils.layout_utils import create_text_label, set_img_label_layout


class Tab3:
    def __init__(self, view, tab_control: Notebook):
        from image_alterations_detector.app.view.view import View
        # Init tab
        self.view: View = view
        self.tab_control = tab_control
        self.tab_root = tk.ttk.Frame(self.tab_control)
        # Tab root
        self.tab_root.grid(row=0, column=0, sticky='nsew')
        self.tab_control.add(self.tab_root, text='Segmentation')
        self.tab_root.columnconfigure(0, weight=1)
        self.tab_root.rowconfigure(0, weight=1)
        self.tab_root.rowconfigure(1, weight=0)

        # -------------------- Images panel
        self.images_panel = tk.Frame(self.tab_root)
        self.images_panel.grid(row=0, column=0, sticky='new')
        self.images_panel.columnconfigure(0, weight=1)
        self.images_panel.columnconfigure(1, weight=1)
        # Images
        self.image2_label: Optional[tk.Label] = tk.Label(self.images_panel)
        self.image1_label: Optional[tk.Label] = tk.Label(self.images_panel)

        # -------------------- Info panel
        self.info_panel = tk.Frame(self.tab_root, relief=tk.RAISED, bd=1)
        self.info_panel.grid(row=1, column=0, sticky='nsew')
        self.info_panel.columnconfigure(0, weight=1)

        # Title
        self.title_label: Optional[tk.Label] = tk.Label(self.info_panel, text='IOU values', font=("Times", 35))
        self.title_label.grid(row=0, column=0, sticky='new')

        # Result panel
        self.result_panel = tk.Frame(self.info_panel, relief=tk.RAISED, bd=1)
        self.result_panel.grid(row=1, column=0, sticky='nsew')
        self.result_panel.columnconfigure(0, weight=1)
        self.result_panel.columnconfigure(1, weight=1)

    def set_segmentation_infos(self, img1, img2, general_iou: float, masks_iou: List[Tuple[str, float]]):
        size = int(self.tab_control.winfo_height() - 350)
        img1 = convert_to_tk_image(image_resize_with_border(img1, size)[0])
        img2 = convert_to_tk_image(image_resize_with_border(img2, size)[0])
        set_img_label_layout(self.image1_label, img1, 0, 0, 'w')
        set_img_label_layout(self.image2_label, img2, 0, 1, 'e')
        masks_iou = sorted(masks_iou, key=lambda tup: tup[1], reverse=True)
        # General iou
        create_text_label(self.result_panel, 'General:', 25, 0, 0, 'nw')
        create_text_label(self.result_panel, '{}%'.format(int(round(general_iou, 2) * 100)), 25, 0, 1, 'nw')
        # Masks iou
        for idx, iou_tuple in enumerate(masks_iou):
            create_text_label(self.result_panel, iou_tuple[0], 20, idx + 1, 0, 'nw')
            create_text_label(self.result_panel, '{}%'.format(int(round(iou_tuple[1], 2) * 100)), 20, idx + 1, 1, 'nw')
