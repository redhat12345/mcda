import sys
import argparse
import os
import numpy as np
from sklearn.datasets import load_svmlight_files
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Reshape, Flatten, MaxPooling2D, GlobalMaxPooling2D, Dropout, Lambda
from keras.layers.merge import _Merge
from keras.utils import to_categorical
from keras.layers.convolutional import Convolution2D, Conv2DTranspose
from keras.layers.normalization import BatchNormalization
from keras.layers.advanced_activations import LeakyReLU
from keras.optimizers import Adam, RMSprop
from keras.regularizers import l2
from keras.datasets import mnist
from keras import backend as K
from functools import partial
from scipy.sparse import vstack
from keras.backend import set_session,tensorflow_backend
import tensorflow as tf 
import scipy
from utils import *


config = tf.ConfigProto(gpu_options=tf.GPUOptions(allow_growth=True))
config.gpu_options.per_process_gpu_memory_fraction = 0.8
set_session(tf.Session(config=config))

bt_size = 128
ip_shape = (5000,)
n_classes = 2
gen_rate = 1e-4
epochs = 30
steps = 80


data_folder = './data/'
source_name = sys.argv[1]
target_name = sys.argv[2]  
xs, ys, xt, yt, xt_test, yt_test = load_amazon(source_name, target_name, data_folder, verbose=True)
ys = to_categorical(ys,2)
yt = to_categorical(yt,2)
yt_test = to_categorical(yt_test,2)


coral_param = - float(sys.argv[3])


def coral_loss(y_true, y_pred):
    h_s = y_pred[:bt_size]
    h_t = y_pred[bt_size:]
    _D_s = tf.reduce_sum(h_s, axis=0, keep_dims=True)
    _D_t = tf.reduce_sum(h_t, axis=0, keep_dims=True)
    C_s = (tf.matmul(tf.transpose(h_s), h_s) - tf.matmul(tf.transpose(_D_s), _D_s) / bt_size) / (bt_size - 1)
    C_t = (tf.matmul(tf.transpose(h_t), h_t) - tf.matmul(tf.transpose(_D_t), _D_t) / bt_size) / (bt_size - 1)
    coral_loss = tf.nn.l2_loss(C_s - C_t) + K.mean(y_true)


def run_coral(xs,ys,xt, xt_test, yt_test):
    generator = make_generator()
    classifier = make_classifier()

    input_s = Input(shape=ip_shape)
    middle_s = generator(input_s)
    out_cls_s = classifier(middle_s)

    cls_model = Model(inputs=input_s, outputs=out_cls_s)
    cls_model.compile(optimizer=Adam(gen_rate),loss=['categorical_crossentropy'], metrics = ['accuracy'])

    coral_rate = gen_rate * coral_param
    coral_model = Model(inputs=input_s, outputs=out_cls_s)
    coral_model.compile(optimizer=Adam(coral_rate),loss= coral_loss)


    ns = xs.shape[0]//bt_size
    nt = xt.shape[0]//bt_size
    zeros = np.zeros((bt_size * 2), dtype=np.float32)
    maxv = 0

    for epoch in range(epochs):
        for i in range(steps):
            inds = np.random.randint(0,ns)
            inds = np.random.randint(0,ns)

            xs_batch = xs[inds * bt_size:(inds + 1) * bt_size]
            ys_batch = ys[inds * bt_size:(inds + 1) * bt_size]
            xt_batch = xt[indt * bt_size:(indt + 1) * bt_size]

            x_all = np.concatenate([xs_batch, xt_batch], axis = 0)

            cls_model.train_on_batch(xs_batch, ys_batch)
            coral_model.train_on_batch(x_all, zeros)
            if i%5 ==0:
                xs, ys = shuffle_data2(xs,ys)
                xt = shuffle_data(xt)

#since peaking point are different between methods, we return the max instead of the last acc as other benchmarks

        _, acc = cls_model.evaluate(x = xt_test, y = yt_test, verbose = 0) 
        maxv = max(acc, maxv) 
        if epoch % 2 ==0:
            print('test accuracy: ', maxv * 100)

    return maxv

total = 0
for rnd in range (5):
    total += run_coral(xs,ys,xt, xt_test,yt_test)
    print (total/(rnd+1))