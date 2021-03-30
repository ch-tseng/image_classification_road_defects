# -*- coding: utf-8 -*-
from libMain import UI
from libMain import LABELING
import PySimpleGUI as sg
import io
import os, sys
import glob
from yoloOpencv import opencvYOLO
import cv2
import numpy as np
import win32gui
import shutil

win_preview_size = (1024,768)
finished_path = r'D:\wait\road_finished'

#AI Model
model_cfg = r'AI\cfg.road_server2\yolov3.cfg'
model_names = r'AI\cfg.road_server2\obj.names'
model_weights = r'AI\cfg.road_server2\weights\yolov3_151000.weights'
model_size = (608, 608)
class_list = { 'D00': '縱向裂縫輪痕', 'D01': '縱向裂縫施工', 'D10': '橫向裂縫間隔', 'D11': '橫向裂縫施工', \
    'D12': '縱橫裂縫', 'D20': '龜裂', 'D21': '人孔破損', 'D30': '車轍', 'D31': '路面隆起', \
    'D40': '坑洞', 'D41': '人孔高差', 'D42': '薄層剝離', 'D50': '人孔缺失', 'D51': '正常人孔' }

#----------------------------------------------------------------------------------

finished_path = finished_path.replace('\\', '/')

def checkenv():
    if not os.path.exists(finished_path):
        os.makedirs(finished_path)

def get_mode_classes():
    classes = []
    with open(model_names, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.replace('\n', '')
            classes.append(line)

    return classes

def rgb2hex(rgb):
    (r, g, b) = rgb
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)

#------------------------------------------------------------------------------------
checkenv()

winUI = UI(preview_size=win_preview_size)
window = winUI.create_window(win_title="道路缺陷-初期分類", resizable=True)

model_cfg = model_cfg.replace('\\', '/')
model_names = model_names.replace('\\', '/')
model_weights = model_weights.replace('\\', '/')

yolo = opencvYOLO(imgsize=model_size, \
    objnames=model_names, \
    weights=model_weights,\
    cfg=model_cfg, score=0.25, nms=0.5)

path_preview_img, filename_preview = '', ''  #for selected file
objects = get_mode_classes()
classColors = []
for i in range(0, len(class_list)):
    classColors.append(np.random.choice(range(256), size=3).tolist())

option_classes = []
for  i, cname in enumerate(class_list):
        option_classes.append('{}_{}_{}'.format(i,cname,cname+'/'+class_list[cname]))


#dragging = False
#start_point = end_point = prior_rect = None
while True:

    event, values = window.read() 


    if event == sg.WIN_CLOSED:  # if the X button clicked, just exit
        break

    elif event == "-FOLDER_IMAGE-":
        path_img_dataset = values["-FOLDER_PATH-"]

    elif event == "-FOLDER_PATH-":  # A file was chosen from the listbox
        winUI.refresh_listfiles(values["-FOLDER_PATH-"])
        

    elif event == "-FILE_LIST-":  # A file was chosen from the listbox
        if len(values["-FILE_LIST-"])>0:
            img_bboxes, img_rects = [], []
            filename_preview = values["-FILE_LIST-"][0]
            path_preview_img = os.path.join(values["-FOLDER_PATH-"], values["-FILE_LIST-"][0])
            winUI.update_preview_img(img_path=path_preview_img, first=True)
            aiLABEL = LABELING(classColors, option_classes)

    elif event == "-AUTO_LABEL-":
        if os.path.exists(path_preview_img):
            img_predict = cv2.imread(path_preview_img)
            print('img_predict', img_predict.shape)
            yolo.getObject(img_predict, labelWant=objects, drawBox=True, bold=2, textsize=1.2, bcolor=(255,255,255), tcolor=classColors)
            print(yolo.labelNames)
            cv2.imwrite('predicted.png', aiLABEL.rectangle(img=img_predict, bboxes=yolo.bbox, color=(255,0,0)))
            winUI.update_preview_img(img_path='predicted.png', first=True)

            #for id, box in enumerate(yolo.bbox):
            #    print(' yolo box',  box)
            #    aiLABEL.add_rect(box, window["-img_preview-"], yolo.classIds[id], winUI.img_size, winUI.img_orgsize)

    elif event == '-Finished-':
        if os.path.exists(path_preview_img):
            winUI.save_graph_as_file('graph.png')
            os.rename(path_preview_img , os.path.join(finished_path, filename_preview))
            base_name, ext_name = filename_preview.split('.')[0], filename_preview.split('.')[-1]
            #os.rename('graph.png' , os.path.join(finished_path, base_name+'_ans.'+ext_name))
            shutil.copyfile('graph.png' , os.path.join(finished_path, base_name+'_ans.'+ext_name))
            winUI.refresh_listfiles(values["-FOLDER_PATH-"])

    elif event == '-img_preview-':
        # https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Graph_Drag_Rectangle.py
        x, y = values["-img_preview-"]
        print('x,y', x,y)
        aiLABEL.start_drag(values, window["-img_preview-"])
        '''
        x, y = values["-img_preview-"]
        graph = window["-img_preview-"]
        if not dragging:
            start_point = (x, y)
            dragging = True
        else:
            end_point = (x, y)

        if prior_rect:
            graph.delete_figure(prior_rect)
        

        if None not in (start_point, end_point):
            prior_rect = graph.draw_rectangle(start_point, end_point, line_color='red')
        '''

    elif event.endswith('+UP'):  # The drawing has ended because mouse up
        aiLABEL.end_drag(window["-img_preview-"], winUI.img_size)
        '''
        print(start_point, end_point)
        if start_point == end_point:
            continue

        
        
        class_event, class_values = sg.Window('Choose an class', [[sg.Text('Class name ->'), sg.Listbox(option_classes, size=(20, 6), \
            key='class_choose')],  [sg.Button('Ok'), sg.Button('Cancel')]]).read(close=True)

        #刪除rectangle
        if prior_rect:
            graph.delete_figure(prior_rect)

        #popup menu for class: https://stackoverflow.com/questions/62559454/how-do-i-make-a-pop-up-window-with-choices-in-python
        if class_event == 'Ok':
            selection = class_values["class_choose"][0].split('_')
            color_c = classColors[int(selection[0])]
            print(start_point, end_point)
            class_rect = graph.draw_rectangle(start_point, end_point, line_color=rgb2hex(color_c))
            graph.DrawText(selection[2], start_point, font=("Courier New", 12), color=rgb2hex(color_c), \
                text_location=sg.TEXT_LOCATION_TOP_LEFT)
            #sg.popup(f'You chose {class_values["class_choose"][0]}')
            img_bboxes.append([start_point[0], winUI.img_size[1]-start_point[1], abs(end_point[0]-start_point[0]), abs(end_point[1]-start_point[1])])
            img_rects.append(prior_rect)
            print('img size', winUI.img_size)
            print('img_bboxes', img_bboxes)
            print('img_rects', img_rects)

        
            
        start_point, end_point = None, None  # enable grabbing a new rect
        dragging = False
        '''
    else:
        print("unhandled event", event, values)            
