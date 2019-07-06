from symnet import AbstractModel
from symnet.image import normalize_images
from symnet.data_utils import read_data

from keras.utils import to_categorical
from keras.callbacks import LearningRateScheduler, ModelCheckpoint
from keras.preprocessing.image import ImageDataGenerator

import pandas as pd

import os


class AbstractImageClassificationModel(AbstractModel):
    """
    An abstract class meant as a base class for all image classifiers. Concrete
    classes subclassing this should implement specific architectures like ResNet
    or DenseNet. This should not be used directly.
    """

    def __init__(self, path: str, label_column: str = None, header: int = 0, augment_data: bool = True,
                 normalize: bool = True, balance: bool = True, *args, **kwargs):

        super(AbstractImageClassificationModel, self).__init__(path, *args, **kwargs)

        self.label_column = label_column
        self.augment_data = augment_data

        self.datagen = None

        x_train, x_test, y_train, y_test = \
            read_data(path, label_column, header, balance=balance, train_size=self.train_size)

        self.train_df = pd.concat([x_train, y_train], axis=1)
        self.test_df = pd.concat([x_test, y_test], axis=1)

        if normalize:
            self.x_train, self.x_test = normalize_images(self.x_train, self.x_test)

        self.input_shape = self.x_train.shape[1:]

        self.y_train = to_categorical(self.y_train, self.n_classes)
        self.y_test = to_categorical(self.y_test, self.n_classes)

    def fit(self, finish_fit: bool = True):
        """
        Fits the model. The value of finish_fit here does not matter: it will be forced
        to True.
        :param finish_fit: Useless parameter
        :return: None
        """

        if not self.augment_data:
            # TODO: Fix this
            super(AbstractImageClassificationModel, self).fit()
        else:
            super(AbstractImageClassificationModel, self).fit(False)

            # Augment the data and call fit() ourselves.
            self.datagen = ImageDataGenerator(
                # set input mean to 0 over the dataset
                featurewise_center=False,
                # set each sample mean to 0
                samplewise_center=False,
                # divide inputs by std of dataset
                featurewise_std_normalization=False,
                # divide each input by its std
                samplewise_std_normalization=False,
                # apply ZCA whitening
                zca_whitening=False,
                # epsilon for ZCA whitening
                zca_epsilon=1e-06,
                # randomly rotate images in the range (deg 0 to 180)
                rotation_range=0,
                # randomly shift images horizontally
                width_shift_range=0.1,
                # randomly shift images vertically
                height_shift_range=0.1,
                # set range for random shear
                shear_range=0.,
                # set range for random zoom
                zoom_range=0.,
                # set range for random channel shifts
                channel_shift_range=0.,
                # set mode for filling points outside the input boundaries
                fill_mode='nearest',
                # value used for fill_mode = "constant"
                cval=0.,
                # randomly flip images
                horizontal_flip=True,
                # randomly flip images
                vertical_flip=False,
                # set rescaling factor (applied before any other transformation)
                rescale=None,
                # set function that will be applied on each input
                preprocessing_function=None,
                # image data format, either "channels_first" or "channels_last"
                data_format=None,
                # fraction of images reserved for validation (strictly between 0 and 1)
                validation_split=0.0)

            lr_scheduler = LearningRateScheduler(self._lr_schedule)
            # Prepare callbacks for model saving and for learning rate adjustment.
            save_dir = os.path.join(os.getcwd(), 'saved_models')
            model_name = 'model.{epoch:03d}.h5'

            # Prepare model model saving directory.
            if not os.path.isdir(save_dir):
                os.makedirs(save_dir)

            filepath = os.path.join(save_dir, model_name)
            checkpoint = ModelCheckpoint(filepath=filepath,
                                         monitor='val_acc',
                                         verbose=1,
                                         save_best_only=True)
            callbacks = [lr_scheduler, checkpoint]

            # Fit the model on the batches generated by datagen.flow().
            self.model.fit_generator(self.datagen.flow_from_dataframe(self.train_df,
                                                                      directory=os.getcwd(),
                                                                      x_col=self.train_df.columns[0],
                                                                      y_col=self.train_df.columns[1],
                                                                      batch_size=self.bs),
                                     validation_data=(self.x_test, self.y_test),
                                     epochs=self.epochs, verbose=1, workers=4,
                                     callbacks=callbacks)

    def score(self):
        return self.model.evaluate_generator(self.datagen.flow_from_dataframe(self.test_df,
                                                                              directory=os.getcwd(),
                                                                              x_col=self.train_df.columns[0],
                                                                              y_col=self.train_df.columns[1],
                                                                              batch_size=self.bs))
