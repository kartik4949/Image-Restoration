# -*- coding: utf-8 -*-
"""Copy of Rephrase Research Engineer Problem

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1fqIpWggEW2E_-Y-YYOS3rn2kCuJW5PgR

# Problem Statement

You are given the original and degraded versions of a few images. Your task is to write a GAN which can fix the degraded images.

Complete the function `fix` at the end of the "Evaluation" block so that it can take a degraded image, and return a fixed image (that looks as much like the original non-degraded version as possible).

Before submission, get this notebook in a state such that the `fix` function can directly be called on an image.

#Setup

## Intended Structure after Setup

Run the blocks in this section to get the following directory structure:
```
/content
│
└───rephrase-pubfig831
    │
    └───correct
    │   │
    │   └───train
    │   │   │
    │   │   └───Adam Sandler
    │   │   │   │   train__000001-000000.jpg
    │   │   │   │   train__000001-000001.jpg
    │   │   │   │   train__000001-000002.jpg
    │   │   │   │   ...
    │   │   │
    │   │   └───Alec Baldwin
    │   │   │   │   train__000002-000000.jpg
    │   │   │   │   train__000002-000001.jpg
    │   │   │   │   ...
    │   │   │
    │   │   └───Angelina Jolie
    │   │   │   │   train__000003-000000.jpg
    │   │   │   │   train__000003-000001.jpg
    │   │   │   │   ...
    │   │   │
    │   │   │ ...
    │   │
    │   └───test
    │       │
    │       └───Adam Sandler
    │       │   │   test__000001-000000.jpg
    │       │   │   test__000001-000001.jpg
    │       │   │   ...
    │       │
    │       └───Alec Baldwin
    │       │   │   test__000002-000000.jpg
    │       │   │   ...
    │       │
    │       └───Angelina Jolie
    │       │   │   test__000003-000000.jpg
    │       │   │   ...
    │       │
    │       │ ...
    │
    │
    └───degraded
        │   <Same directory structure as 'correct'>
```

Every image in the degraded directory is a degraded version of the image with the same name in the correct directory. e.g. `/content/rephrase-pubfig831/degraded/Adam Sandler/train__000001-000002.jpg` is the degraded version of `/content/rephrase-pubfig831/correct/Adam Sandler/train__000001-000002.jpg`

## Installation (pip etc)
Add any other installation commands you want to in this block.
"""

!pip install GPUtil
!pip install tqdm
!ln -sf /opt/bin/nvidia-smi /usr/bin/nvidia-smi

"""## Downloading and Generating Dataset
Run this block only once. Do not modify it.
"""

import os
from glob import glob

import cv2
import numpy as np
from tqdm import tqdm

def degrade(path: str) -> None:
    """Load image at `input_path`, distort and save as `output_path`"""
    SHIFT = 2
    image = cv2.imread(path)
    to_swap = np.random.choice([False, True], image.shape[:2], p=[.8, .2])
    swap_indices = np.where(to_swap[:-SHIFT] & ~to_swap[SHIFT:])
    swap_vals = image[swap_indices[0] + SHIFT, swap_indices[1]]
    image[swap_indices[0] + SHIFT, swap_indices[1]] = image[swap_indices]
    image[swap_indices] = swap_vals
    cv2.imwrite(path, image)

!wget http://briancbecker.com/files/downloads/pubfig83lfw/pubfig83lfw_raw_in_dirs.zip
!unzip -q pubfig83lfw_raw_in_dirs.zip
!rm pubfig83lfw_raw_in_dirs.zip
!mkdir rephrase-pubfig831
!mv pubfig83lfw_raw_in_dirs rephrase-pubfig831/correct
!rm -r rephrase-pubfig831/correct/distract
!cp -r rephrase-pubfig831/correct rephrase-pubfig831/degraded

for image_path in tqdm(glob('rephrase-pubfig831/degraded/*/*/*.jpg')):
  degrade(image_path)

"""# **Checking Free Memory**
This block is just so that you can have an idea of the resources you have at hand on the Google Collab system.
"""

import psutil
import humanize
import os
import GPUtil as GPU
gpu = GPU.getGPUs()[0]
process = psutil.Process(os.getpid())
print(f"Gen RAM: Free {humanize.naturalsize(psutil.virtual_memory().available)} | Proc size {humanize.naturalsize(process.memory_info().rss)}")
print(f"GPU RAM: Free {gpu.memoryFree:.0f}MB | Used {gpu.memoryUsed:.0f}MB | Util {gpu.memoryUtil*100:.0f}% | Total {gpu.memoryTotal:.0f}MB")

!pip install tensorflow-gpu==2.0.0

import os
from glob import glob

import cv2
import numpy as np
from tqdm import tqdm

"""# **Main Code**

## Data Loading

Details of Implementation.


>>>As I have a fulltime job so cant really give my 100% for this question.
So,here what i have done is used GAN with Content Loss according to paper

>>>I have used MISH activation which is state of the art activation at this moment,Later performance is boosted!!


>>>Tensorflow 2.0 is used due to Autograph , Autodiff and Tf.Data effeciency


>>>Tf.function are essential for performance boost

>>>Input PipeLine can be improved (Prefetch can boost training but more ram is required ).
"""

import os
import matplotlib.pyplot as plt
import cv2
import tensorflow as tf
print(tf.__version__)
AUTOTUNE = tf.data.experimental.AUTOTUNE


class DataGenerator:
  def __init__(self,batch_size):
    self.train_path_original = '/content/rephrase-pubfig831/correct/train/'
    self.train_path_degraded = '/content/rephrase-pubfig831/degraded/train/'
    self.train_original = []
    self.train_degraded = []
    self.batch_size = batch_size
    self.dataset_size = 0

  def prepare_for_training(self, ds, cache=True, shuffle_buffer_size=1000):
        '''if cache:
            if isinstance(cache, str):
                ds = ds.cache(cache)
            else:
                ds = ds.cache()'''
        ds = ds.shuffle(buffer_size=shuffle_buffer_size)
        ds = ds.batch(self.batch_size)
        #ds = ds.prefetch(buffer_size=AUTOTUNE)
        return ds

  def preprocess(self,image):
    return  (image - 127.5) / 127.5
    return image


  def generate(self):
    
    for i,j,k in os.walk(self.train_path_original):
      for files in k:
        self.train_original.append(i+'/'+files)
    for i,j,k in os.walk(self.train_path_degraded):
      for files in k:
        self.train_degraded.append(i+'/'+files)
      
    tf_data = tf.data.Dataset.from_tensor_slices(
            (sorted(self.train_original),sorted(self.train_degraded))
        )
    self.dataset_size = len(self.train_degraded)
    
    def read(batch_o, batch_d):
            image_path_o = tf.io.read_file(batch_o)
            batch_image_o = tf.io.decode_jpeg(image_path_o)
            image_path_d = tf.io.read_file(batch_d)
            batch_image_d = tf.io.decode_jpeg(image_path_d)
            batch_image_d = tf.image.convert_image_dtype(batch_image_d, dtype=tf.float32)
            batch_image_o = tf.image.convert_image_dtype(batch_image_o, dtype=tf.float32)
            #batch_image_d = self.preprocess(batch_image_d)
            #batch_image_o = self.preprocess(batch_image_o)
            return batch_image_o,batch_image_d

    tf_csv_stream = tf_data.map(read, num_parallel_calls=AUTOTUNE)
    train = self.prepare_for_training(tf_csv_stream)
    return train

#gc.collect()



import tensorflow
print(tensorflow.__version__)

"""## Structure

### **Constants and Hyperparemeters**
"""



"""### Generator Model"""

from tensorflow.python.ops import math_ops
from tensorflow.python.framework import ops
import tensorflow as tf

@tf.function
def mish(x):
    return x*tf.math.tanh(tf.math.softplus(x))


"""
Instance Normalization can boost training stability i have to implement it correctly!
"""
@tf.function
def instance_norm(name, x):

    mean, variance = tf.nn.moments(x, axes = [1, 2])
    x = (x - mean) / ((variance + BN_epsilon) ** 0.5)
    
    if affine :
        beta = tf.get_variable(name = name + "beta", shape = dim, dtype = tf.float32,
                               initializer = tf.constant_initializer(0.0, tf.float32))
        gamma = tf.get_variable(name + "gamma", dim, tf.float32, 
                                initializer = tf.constant_initializer(1.0, tf.float32))
        x = gamma * x + beta 
    
    return x



class _Conv_BN_(tf.keras.layers.Layer):
    def __init__(self,n_filters,activation='relu'):
        super().__init__()
        self.n_filters = n_filters
        self.n_feats = 64
        self.activation = activation
        '''if(activation=='mish'):
          self.mish  = tf.keras.layers.Activation(activation=mish)'''
        self.conv1 = tf.keras.layers.Conv2DTranspose(kernel_size = 3 ,filters = n_filters // 2,strides = 2 ,padding="SAME")
        self.bn = tf.keras.layers.BatchNormalization()
    def call(self,x,training=None):
        x = self.conv1(x)
        x = self.bn(x)
        if(self.activation == 'mish'):
          x = mish(x)
        else:
          x = tf.nn.relu(x)
        return x


class _transConv_bn(tf.keras.layers.Layer):
    def __init__(self,n_filters,activation='relu'):
        super().__init__()
        self.n_filters = n_filters
        self.n_feats = 64
        self.activation = activation
        self.conv1 = tf.keras.layers.Conv2D(kernel_size = 3 ,filters = n_filters*2,strides = 2 ,padding="SAME")
        self.bn = tf.keras.layers.BatchNormalization()
    def call(self,x,training=None):
        x = self.conv1(x)
        x = self.bn(x)
        if(self.activation == 'mish'):
          x = mish(x)
        else:
          x = tf.nn.relu(x)
        

        return x




class res_block(tf.keras.layers.Layer):
    def __init__(self,n_filters,activation = 'relu'):
        super().__init__()
        self.n_filters = n_filters
        self.activation = activation
        self.n_feats = 64
        self.conv1 = tf.keras.layers.Conv2D(kernel_size = 3 ,filters = n_filters,strides = 1 ,padding="VALID")
        self.conv2 = tf.keras.layers.Conv2D(kernel_size = 3 ,filters = n_filters,strides = 1 ,padding="VALID")
        self.add = tf.keras.layers.Add()
        self.bn1 = tf.keras.layers.BatchNormalization()
        self.bn2 = tf.keras.layers.BatchNormalization()
    def call(self,x,training=None):
        _res = x
        x = tf.pad(x, [[0,0],[1,1],[1,1],[0,0]], mode = 'REFLECT')
        x = self.bn1(x)
        x = self.conv1(x)

        if(self.activation == 'mish'):
          x = mish(x)
        else:
          x = tf.nn.relu(x)
        
        x = tf.pad(x, [[0,0],[1,1],[1,1],[0,0]], mode = 'REFLECT')
        x = self.bn2(x)
        x = self.conv2(x)
        x = self.add([x  , _res])
        return x


"""
I have to try if squeeze and Excitation can work and improve results between every block e.g down ,up and res

"""

class Squeeze_and_E(tf.keras.Model):
  def __init__(self,ch,ratio=16):
    super().__init__()
    f1 = ch//ratio 
    f2 = ch
    self.model = tf.keras.Sequential([tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dense(f1, activation='relu'),
    tf.keras.layers.Dense(f2, activation='sigmoid')])
    self.multiply_l = tf.keras.layers.Multiply()
  def call(self,x ,training = None):
    _x = x
    x = self.model(x)
    x = self.multiply_l([_x , x])
    return x


class Generator(tf.keras.Model):
    def __init__(self, activation='relu',Squeeze = False):
        super().__init__()
        self.channel  = 3
        self.num_of_down_scale = 2
        self.gen_resblocks = 1
        self.base_f = 32
        self.Squeeze = Squeeze
        self.activation = activation
        self.conv1 = tf.keras.layers.Conv2D(filters=self.base_f,kernel_size=(7,7) , strides=(1,1),padding = 'VALID')
        self.bn = tf.keras.layers.BatchNormalization()
        self.down_block = tf.keras.Sequential()
        for i in range(self.num_of_down_scale):
            self.down_block.add(_transConv_bn(self.base_f * (i + 1),activation=activation ))
        
        
        self.res_block_model = tf.keras.Sequential()
        for i in range(self.gen_resblocks):
            self.res_block_model.add(res_block(self.base_f * (2 ** self.num_of_down_scale),activation=activation))
        self.up_block = tf.keras.Sequential()
        for i in range(self.num_of_down_scale):
            self.up_block.add(_Conv_BN_(self.base_f * (2 ** (self.num_of_down_scale - i)),activation=activation))
        self.conv_out = tf.keras.layers.Conv2D(kernel_size = 7,filters = self.channel,strides=1,padding = "VALID")
        self.conv_out_1 = tf.keras.layers.Conv2D(kernel_size = 3,filters = self.channel,strides=1,padding = "VALID")
        self.add = tf.keras.layers.Add()
        
    def call(self,x,training=None):
        _res = x
        x = tf.pad(x, [[0,0],[3,3],[3,3],[0,0]], mode = 'REFLECT')
        x = self.conv1(x)

        x = self.bn(x)
        if(self.activation == 'mish'):
          x = mish(x)
        else:
          x = tf.nn.relu(x)
        x = self.down_block(x)
        x = self.res_block_model(x)
        x = self.up_block(x)
        if(self.Squeeze):
          se = Squeeze_and_E(x.shape[-1] )
          se.build(input_shape = x.shape)
          x = se(x)

        x = tf.pad(x, [[0,0],[3,3],[3,3],[0,0]], mode = 'REFLECT')
        x = self.conv_out_1(x)
        x = self.conv_out(x)
        x = tf.nn.tanh(x)
        x = self.add([x ,_res])
        x = tf.clip_by_value(x, -1.0, 1.0)  
        return x



#print(model.predict(input_img).shape)

"""### Discriminator Model"""

class Discriminator(tf.keras.Model):
	def __init__(self,filters,kernel_size,strides,sz,channels,leak):
		super().__init__()
		self.filters = filters
		self.kernel_size = kernel_size
		self.strides = strides
		self.sz = sz
		self.channels = channels
		self.leak = leak
		self.model_disc = tf.keras.Sequential([
			tf.keras.layers.Conv2D(self.filters, self.kernel_size, self.strides,  padding="same"),
			tf.keras.layers.LeakyReLU(self.leak),
			tf.keras.layers.Conv2D(2*self.filters, self.kernel_size, self.strides,  padding="same"),
			tf.keras.layers.BatchNormalization(),
	        tf.keras.layers.LeakyReLU(self.leak ),
	        tf.keras.layers.Conv2D(4*self.filters, self.kernel_size, self.strides, padding="same",),
	        tf.keras.layers.BatchNormalization(),
	        tf.keras.layers.LeakyReLU(self.leak ),
	        tf.keras.layers.Conv2D(8*self.filters, self.kernel_size, self.strides, padding="same",),
	        tf.keras.layers.BatchNormalization(),
	        tf.keras.layers.LeakyReLU(self.leak ),
	        tf.keras.layers.Flatten(),
	        tf.keras.layers.Dense(1),
			])
	def call(self,x,training=None):
		x = self.model_disc(x,training=True)
		return x

"""
CHANGE ACTIVATION TO 'relu', IF RESULTS ARE UNSTABLE AS I HAVENT TRIED WITH MISH YET

"""


ACTIVATION = 'mish'

generator = Generator(activation=ACTIVATION)
generator.build(input_shape = (None,250,250,3))
generator.summary()

discriminator = Discriminator(32,(3,3),(2,2),250,3,0.2)
discriminator.build(input_shape = (None,250,250,3))
discriminator.summary()




"""
In case keras is used later when i implement it in keras to need this model for dat!!!

"""
class G_D(tf.keras.Model):
  def __init__(self,train=True):
    super().__init__()
    self.g = Generator()
    self.train = train
    self.d = Discriminator(64,(3,3),(2,2),250,3,0.2)
    self.d.trainable = train
  def call(self,x,training = None):
    self.g.build(input_shape = x.shape)
    x = self.g(x)
    self.d.trainable = self.train
    self.d.build(input_shape = x.shape)
    x = self.d(x)
    return x


model = G_D()
model.build(input_shape = (None,250,250,3))
model.summary()

"""### Loss Functions"""



def perceptual_loss(y_true, y_pred,loss_model):
    loss_model.trainable = False
    return 100*tf.reduce_mean(tf.square(loss_model(y_true) - loss_model(y_pred)))


def wasserstein_loss(image_originals,generated_images,discriminator ):
    epsilon = tf.random.uniform(shape = [8, 1, 1, 1], minval = 0.0, maxval = 1.0)
    interpolated_input = epsilon * image_originals + (1 - epsilon) * generated_images
    gradient = tf.gradients(discriminator(interpolated_input), [interpolated_input])[0]
    disc_loss =  tf.reduce_mean(tf.square(tf.sqrt(tf.reduce_mean(tf.square(gradient), axis = [1, 2, 3])) - 1))
    return disc_loss

"""### Optimizer"""

learning_rate = 0.0001
d_optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate, beta_1=0.5)
g_optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate, beta_1=0.5)

"""## Preprocessing

### Setting device to use for tensor operations
"""



"""### Initializing weights (if required)"""



"""## Training"""

@tf.function
def train_step(image_originals , image_degradeds,loss_model,shift=True):
    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
      generated_images = generator(image_degradeds, training=True)
      
      real_output = discriminator(image_originals, training=True)
      
      fake_output = discriminator(generated_images, training=True)
      d_loss_real = - tf.reduce_mean(real_output)
      d_loss_fake = tf.reduce_mean(fake_output)

      if(shift):
        disc_loss = d_loss_real + d_loss_fake + 10.0* wasserstein_loss(image_originals,generated_images,discriminator )
      else:
        disc_loss = d_loss_real + d_loss_fake 

      
      gen_loss = -d_loss_fake + perceptual_loss(image_originals,generated_images,loss_model)


    gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)

    g_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
    d_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))
    return gen_loss,disc_loss

import gc

def train( epochs):
  vgg = tf.keras.applications.VGG16(include_top=False, weights='imagenet', input_shape=(250,250,3))
  loss_model = tf.keras.Model(inputs=vgg.input, outputs=vgg.get_layer('block3_conv3').output)
  for epoch in range(epochs):
    batch_size = 8
    d = DataGenerator(batch_size)
    dataset = iter(d.generate())
    dataset_size = d.dataset_size
    training_steps = int(dataset_size/batch_size)
    for image_batch_o,image_batch_d in tqdm(dataset , total=training_steps):
      gen_loss,disc_loss = train_step(image_batch_o,image_batch_d,loss_model)
      gc.collect()
    print("Epochs === {}\t\tGen_loss {} \t\t Disc_loss{}\t\t".format(epoch , gen_loss , disc_loss))

train(100)

"""## Evaluation"""

img = cv2.imread('/content/rephrase-pubfig831/degraded/test/Adam Sandler/test__000001-000000.jpg')
img = np.asarray([img[:,:,[2,1,0]]])/255.
img = generator(img)
"""
THIS IS THE CORRECTED /FIXED IMAGE (FIRST ONE)


"""
plt.imshow(img[0])
plt.show()
img = cv2.imread('/content/rephrase-pubfig831/degraded/test/Adam Sandler/test__000001-000000.jpg')
plt.imshow(img[:,:,[2,1,0]])
plt.show()

def fix(image: np.ndarray) -> np.ndarray:
    """
    This function should take a degraded image in BGR format as a 250x250x3
    numpy array, and return its fixed version in the same format.
    """
    img = np.asarray([image[:,:,[2,1,0]]])/255.
    img = generator(img)
    return img[0]

"""# Results
Run this block after done to look at some of the results of the fix function yourself.
"""

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline

import os
import random
from glob import glob

import cv2
import matplotlib.pyplot as plt
import numpy as np

NUM_DISPLAY = 5

files = glob('/content/rephrase-pubfig831/correct/test/*/*')
grid = []

for path in random.sample(files, NUM_DISPLAY):
  correct = cv2.imread(path)
  split = path.split('/')
  degraded = cv2.imread('/'.join([*split[:3], 'degraded', *split[4:]]))
  fixed = fix(degraded)
  degraded = np.asarray(degraded,dtype='float32')/255.
  correct = np.asarray(correct,dtype='float32')/255.
  grid.append(np.column_stack([degraded[...,[2,1,0]], fixed, correct[...,[2,1,0]]]))

image = np.row_stack(grid)
#dpi = float(plt.rcParams['figure.dpi'])
figsize = image.shape[1] / dpi, image.shape[0] / dpi
ax = plt.figure(figsize=figsize).add_axes([0, 0, 1, 1])
ax.axis('off')
ax.imshow(image)
plt.show()