import PySimpleGUI as sg
from PIL import Image, ImageTk, ImageGrab, ImageWin
import win32gui
import io
import os, sys
import numpy as np
import cv2
import imutils

class UI:
    def __init__(self, preview_size=(960,540)):
        self.preview_size = preview_size

    def refresh_listfiles(self, folder_path):
        listFiles = []
        for file in os.listdir(folder_path):
            filename, file_extension = os.path.splitext(file)
            file_extension = file_extension.lower()
            if(file_extension == ".jpg" or file_extension==".jpeg" or file_extension==".png" or file_extension==".bmp"):
                listFiles.append(file)

        self.update_filelist(listFiles)

    def save_graph_as_file(self, filename):
        """
        Saves any element as an image file.  Element needs to have an underlyiong Widget available (almost if not all of them do)
        :param element: The element to save
        :param filename: The filename to save to. The extension of the filename determines the format (jpg, png, gif, ?)
        """
        window = self.window
        element = window["-img_preview-"]
        widget = element.Widget
        box = (widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_rootx() + widget.winfo_width(), widget.winfo_rooty() + widget.winfo_height())
        grab = ImageGrab.grab(bbox=box)
        grab.save(filename)

    def create_window(self, win_title, resizable):

        self.win_title = win_title
        self.resizable = resizable
        self.main_layout = self.layout_theme1()
        self.window = sg.Window(win_title, self.main_layout, resizable=resizable)

        return self.window

    def get_resize(self, img, resize):
        (w,h) = img.size
        ratio = resize[0]/w
        nw = resize[0]
        nh = int(h * ratio)
        if nh>resize[1]:
            ratio = resize[1]/h
            nh = resize[1]
            nw = int(w * ratio)

        self.img_size = (nw,nh)
        self.img_orgsize = (w,h)
        self.resize_ratio = (w/nw, h/nh)
        #self.preview_size = (w,h)

        return img.resize((nw,nh), Image.ANTIALIAS)


    def update_preview_img(self, img_path, first=True):
        window = self.window
        '''
        window['-img_preview-'].update(data=self.get_img_data(img_path, re_size, first=True))
        '''

        graph = window.Element("-img_preview-")
        graph.Erase()

        graph.DrawImage(data=self.get_img_data(img_path, self.preview_size, first=True), location=(0, self.preview_size[1]))
        #graph.DrawImage(data=self.get_img_data(img_path, self.img_orgsize, first=True), location=(0, self.img_orgsize[1]))
        #window['-img_preview-'].set_size(self.preview_size)

    def update_filelist(self, lists):
        window = self.window
        window["-FILE_LIST-"].update(lists)

    def get_img_data(self, f, re_size, first=False):

        img = Image.open(f)
        img = self.get_resize(img, re_size)
        #img.thumbnail(re_size)
        #(w,h) = (img.size)
        
        #img = img.resize(re_size, Image.ANTIALIAS)
        if first:                     # tkinter is inactive the first time
            bio = io.BytesIO()
            img.save(bio, format="PNG")
            del img
            return bio.getvalue()

        return ImageTk.PhotoImage(img)

    def set_status(self, objID, status):
        window = self.window
        window[objID].update(disabled=status)


    #choose folder --> key="-FOLDER_PATH-"
    #img_filelist --> key="-FOLDER_PATH-" 
    #preview img --> key='-img_preview-'
    def layout_theme1(self):
        preview_size=self.preview_size

        folder_choose = [ 
            [sg.Text("缺陷相片資料夾")],
            [sg.In(size=(25, 1), enable_events=True, key="-FOLDER_PATH-"), sg.FolderBrowse()],
            [sg.Listbox( values=[], enable_events=True, size=(35, 30), key="-FILE_LIST-" )],
            [sg.Button('自動辨識' ,key='-AUTO_LABEL-'), sg.Button('完成' ,key='-Finished-')]
        ]


        #left_col = [folder_choose , sg.Text('_'  * 150), file_list ]
        preview = [ [sg.Text("圖片張數:          ", key="-COUNTS-")],
                    [sg.Graph(
                        canvas_size=preview_size,
                        graph_bottom_left=(0, 0),
                        graph_top_right=self.preview_size,
                        key="-img_preview-",
                        enable_events=True,
                        background_color='black',
                        drag_submits=True,
                        right_click_menu=[[],['Erase item',]]
                        )]
                    #[sg.Image(data=self.get_img_data('images/empty.png', re_size=self.preview_size, first=True), enable_events=True, key='-img_preview-')]
                ]


        layout = [ [ sg.Column(folder_choose, vertical_alignment='top', justification='center') ,sg.Column(preview, vertical_alignment='top', justification='center')   ]]

        return layout

class LABELING:
    def __init__(self, classColors, option_classes):
        self.classColors = classColors
        self.option_classes = option_classes
        self.dragging = False
        self.drag_start = None
        self.drag_end = None
        self.prior_rect = None
        self.img_bboxes = []
        self.img_rects = []

    def rectangle(self, img, bboxes, color):
        
        for box in bboxes:
            left, top, right, bottom = box[0], box[1], box[0]+box[2], box[1]+box[3]
            cv2.rectangle(img, (left, top), (right, bottom), color, 2)

        return img

    def rgb2hex(self, rgb):
        (r, g, b) = rgb
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)

    def start_drag(self, values, desktop):
        x, y = values["-img_preview-"]

        if not self.dragging :
            self.drag_start = (x, y)
            self.dragging = True
        else:
            self.drag_end = (x, y)

        if self.prior_rect:
            desktop.delete_figure(self.prior_rect)
        

        if None not in (self.drag_start, self.drag_end):
            self.prior_rect = desktop.draw_rectangle(self.drag_start, self.drag_end, line_color='red')


    def end_drag(self, desktop, img_size):
        if self.drag_start == self.drag_end:
            return

        classColors = self.classColors
        option_classes = self.option_classes

        class_event, class_values = sg.Window('Choose an class', [[sg.Text('Class name ->'), sg.Listbox(option_classes, size=(20, 6), \
            key='class_choose')],  [sg.Button('Ok'), sg.Button('Cancel')]]).read(close=True)

        #刪除rectangle
        if self.prior_rect:
            desktop.delete_figure(self.prior_rect)

        #popup menu for class: https://stackoverflow.com/questions/62559454/how-do-i-make-a-pop-up-window-with-choices-in-python
        

        if class_event == 'Ok':
            img_bboxes = self.img_bboxes
            img_rects = self.img_rects
            selection = class_values["class_choose"][0].split('_')
            color_c = classColors[int(selection[0])]

            if(self.drag_end[1]>self.drag_start[1]):  #由下方往上拉矩形, 故值需交換
                tmp = self.drag_start
                self.drag_start = self.drag_end
                self.drag_end= tmp

            print(self.drag_start, self.drag_end)
            class_rect = desktop.draw_rectangle(self.drag_start, self.drag_end, line_color=self.rgb2hex(color_c))
            desktop.DrawText(selection[2], self.drag_start, font=("Courier New", 12), color=self.rgb2hex(color_c), \
                text_location=sg.TEXT_LOCATION_TOP_LEFT)
            #sg.popup(f'You chose {class_values["class_choose"][0]}')
            img_bboxes.append([self.drag_start[0], img_size[1]-self.drag_start[1], \
                abs(self.drag_end[0]-self.drag_start[0]), abs(self.drag_end[1]-self.drag_start[1])])
            img_rects.append(self.prior_rect)
            print('img size', img_size)
            print('img_bboxes', img_bboxes)
            print('img_rects', img_rects)

            self.img_bboxes = img_bboxes
            self.img_rects = img_rects
            
        self.drag_start, self.drag_end = None, None  # enable grabbing a new rect
        self.dragging = False

    def add_rect(self, bbox, desktop, class_id, img_size, org_imgsize):
        #ratio_x = img_size[0] / org_imgsize[0]
        #ratio_y = img_size[1] / org_imgsize[1]

        #bbox = (int(sbox[0]*ratio_x), int(sbox[1]*ratio_y), \
        #   int(sbox[2]*ratio_x), int(sbox[3]*ratio_y))
        #print('--->restore ', bbox)

        img_bboxes = self.img_bboxes
        img_rects = self.img_rects
        self.drag_start = (bbox[0], bbox[1])
        self.drag_end = (bbox[0]+bbox[2], (bbox[1]+bbox[3]))
        classes = self.option_classes[class_id].split('_')
        print(self.drag_start, self.drag_end)
        color_c = self.classColors[class_id]
        rect = desktop.draw_rectangle(self.drag_start, self.drag_end, line_color=self.rgb2hex(color_c))
        desktop.DrawText(classes[2], self.drag_start, font=("Courier New", 12), color=self.rgb2hex(color_c), \
                text_location=sg.TEXT_LOCATION_TOP_LEFT)

        img_bboxes.append(bbox)
        img_rects.append(rect)

        self.img_bboxes = img_bboxes
        self.img_rects = img_rects