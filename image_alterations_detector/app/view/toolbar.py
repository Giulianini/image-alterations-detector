import tkinter as tk
from threading import Thread
from tkinter import filedialog


class Toolbar:
    def __init__(self, view, parent):
        from image_alterations_detector.app.view.view import View
        self.view: View = view
        self.tab_root = parent
        self.dialog = tk.filedialog
        self.toolbar = tk.Frame(self.tab_root, relief=tk.RAISED, bd=2)
        btn_open_source = tk.Button(self.toolbar, text="Load source image",
                                    command=lambda: self.load_image('source'))
        btn_open_doc = tk.Button(self.toolbar, text="Load target image",
                                 command=lambda: self.load_image('target'))
        btn_open_webcam = tk.Button(self.toolbar, text="Source image from webcam",
                                    command=lambda: self.load_image('webcam'))
        btn_align = tk.Button(self.toolbar, text="Align images",
                              command=lambda: self.align_images())
        btn_analyze = tk.Button(self.toolbar, text="Analyze images",
                                command=lambda: self.analyze_images())
        self.animate_var = tk.BooleanVar()
        checkbox = tk.Checkbutton(self.toolbar, text="Animate", variable=self.animate_var, onvalue=True, offvalue=False)
        btn_segment = tk.Button(self.toolbar, text="Segment images",
                                command=lambda: self.segment_images())
        # Position
        self.toolbar.grid(row=0, column=0, sticky="nsw")
        btn_open_source.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        btn_open_doc.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        btn_open_webcam.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        btn_align.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        btn_analyze.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        checkbox.grid(row=5, column=0, sticky="ew", padx=20, pady=0)
        btn_segment.grid(row=6, column=0, sticky="ew", padx=5, pady=5)

    def load_image(self, img_type):
        def load_file():
            filepath = self.dialog.askopenfilename(
                filetypes=[("Png files", "*.png"), ("Jpg files", "*.jpg"), ("Jpeg files", "*.jpeg")]
            )
            return filepath

        if img_type != 'webcam':
            img_path = load_file()
            if not img_path:
                return
            self.view.controller.load_image_form_path(img_path, img_type)
        else:
            self.view.controller.take_webcam_photo()

    def align_images(self):
        Thread(name='image align', target=lambda: self.view.controller.align_images()).start()

    def analyze_images(self):
        Thread(name='image analyze', target=lambda: self.view.controller.analyze_images(self.animate_var.get())).start()

    def segment_images(self):
        Thread(name='image segment', target=lambda: self.view.controller.segment_images()).start()
