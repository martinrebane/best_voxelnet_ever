#!/usr/bin/env python
# -*- coding:UTF-8 -*-

import glob
import argparse
import os
import time
import tensorflow as tf

from config import cfg
from model import RPN3D

from utils import *
from utils.kitti_loader import iterate_data, sample_test_data



parser = argparse.ArgumentParser(description='testing')
parser.add_argument('-n', '--tag', type=str, nargs='?', default='pre_trained_car',
                    help='set log tag')
parser.add_argument('-d', '--decrease', type=bool, nargs='?', default=False,
                    help='set the flag to True if decrease model')
parser.add_argument('-m', '--minimize', type=bool, nargs='?', default=False,
                    help='set the flag to True if minimize model')
parser.add_argument('-t', '--data-tag', type=str, nargs='?', default='000000',
                    help='set data tag')
parser.add_argument('-o', '--output-path', type=str, nargs='?',default='./predictions',
                    help='results output dir')
parser.add_argument('-v', '--vis', type=bool, nargs='?', default=True,
                    help='set the flag to True if dumping visualizations')
args = parser.parse_args()


dataset_dir = cfg.DATA_DIR
test_dir = os.path.join(dataset_dir, 'testing')
print("dir", test_dir)
res_dir = os.path.join('.', args.output_path)
save_model_dir = os.path.join('.', 'save_model', args.tag)
    
os.makedirs(res_dir, exist_ok=True)
os.makedirs(os.path.join(res_dir, 'data'), exist_ok=True)
if args.vis:
    os.makedirs(os.path.join(res_dir, 'vis'), exist_ok=True)

def main(_):
    
    with tf.Graph().as_default():

        gpu_options = tf.GPUOptions(
            per_process_gpu_memory_fraction=cfg.GPU_MEMORY_FRACTION,
            visible_device_list=cfg.GPU_AVAILABLE,
            allow_growth=True
        )

        config = tf.ConfigProto(
            gpu_options=gpu_options,
            device_count={"GPU": cfg.GPU_USE_COUNT,},
            allow_soft_placement=True,
        )

        with tf.Session(config=config) as sess:
            model = RPN3D(
                cls=cfg.DETECT_OBJ,
                decrease=args.decrease,
                minimize=args.minimize,
                single_batch_size=1,
                avail_gpus=cfg.GPU_AVAILABLE.split(',')
            )
            
            # param init/restore
            if tf.train.get_checkpoint_state(save_model_dir):
                print("Reading model parameters from %s" % save_model_dir)
                model.saver.restore(sess, tf.train.latest_checkpoint(save_model_dir))
            
            
            batch = sample_single_data(test_dir, args.data_tag)
            
            if args.vis:
                tags, results, front_images, bird_views, heatmaps = model.predict_step(sess, batch, summary=False, vis=True)
            else:
                tags, results = model.predict_step(sess, batch, summary=False, vis=False)
            
            for tag, result in zip(tags, results):
                of_path = os.path.join(res_dir, 'data', tag + '.txt')
                with open(of_path, 'w+') as f:
                    labels = box3d_to_label([result[:, 1:8]], [result[:, 0]], [result[:, -1]], coordinate='lidar')[0]
                    for line in labels:
                        f.write(line)
                    print('write out {} objects to {}'.format(len(labels), tag))
                    
            # dump visualizations
            if args.vis:
                for tag, front_image, bird_view, heatmap in zip(tags, front_images, bird_views, heatmaps):
                    front_img_path = os.path.join(res_dir, 'vis', tag + '_front.jpg')
                    bird_view_path = os.path.join(res_dir, 'vis', tag + '_bv.jpg')
                    heatmap_path = os.path.join(res_dir, 'vis', tag + '_heatmap.jpg')
                    cv2.imwrite(front_img_path, front_image)
                    cv2.imwrite(bird_view_path, bird_view)
                    cv2.imwrite(heatmap_path, heatmap)


if __name__ == '__main__':
    tf.app.run(main)
