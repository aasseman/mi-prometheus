#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) IBM Corporation 2018
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""problem.py: contains base class for all problems"""
__author__ = "Tomasz Kornuta"


import collections
from abc import ABCMeta, abstractmethod
from utils.app_state import AppState

_DataTuple = collections.namedtuple('DataTuple', ('inputs', 'targets'))


class DataTuple(_DataTuple):
    """
    Tuple used by storing batches of data by problems.
    """
    __slots__ = ()


_MaskAuxTuple = collections.namedtuple('MaskAuxTuple', ('mask'))


class MaskAuxTuple(_MaskAuxTuple):
    """
    Tuple used by storing batches of data by sequential problems using mask.

    Contains one element: mask that might be used for evaluation of the
    loss function.

    """
    __slots__ = ()


_LabelAuxTuple = collections.namedtuple('LabelAuxTuple', ('label'))


class LabelAuxTuple(_LabelAuxTuple):
    """
    Tuple used by storing batches of labels in classification problems.
    """
    __slots__ = ()


class Problem(metaclass=ABCMeta):
    """
    Class representing base class for all Problems.
    """

    def __init__(self, params):
        """
        Initializes problem object.

        :param params: Dictionary of parameters (read from configuration file).

        """
        # Set default loss function.
        self.loss_function = None

        # Store pointer to params.
        self.params = params

        # Get access to AppState.
        self.app_state = AppState()

        # "Default" problem name.
        self.name = 'Problem'


    def set_loss_function(self, loss_function):
        """
        Sets loss function.

        :param criterion: Loss function (e.g. nn.CrossEntropyLoss()) that will be set as optimization criterion.

        """
        self.loss_function = loss_function


    @abstractmethod
    def generate_batch(self):
        """
        Generates batch of sequences of given length.

        Abstract - to be defined in derived classes.

        """

    def return_generator(self):
        """
        Returns a generator yielding a batch  of size [BATCH_SIZE,
        2*SEQ_LENGTH+2, CONTROL_BITS+DATA_BITS]. Additional elements of
        sequence are  start and stop control markers, stored in additional
        bits.

        : returns: A tuple: input with shape [BATCH_SIZE, 2*SEQ_LENGTH+2, CONTROL_BITS+DATA_BITS], output

        """
        # Create "generator".
        while True:
            yield self.generate_batch()

    def evaluate_loss(self, data_tuple, logits, _):
        """
        Calculates loss between the predictions/logits and targets (from
        data_tuple) using the selected loss function.

        :param logits: Logits being output of the model.
        :param data_tuple: Data tuple containing inputs and targets.
        :param _: auxiliary tuple (aux_tuple) is not used in this function.

        """
        # Unpack tuple.
        (_, targets) = data_tuple

        # Compute loss using the provided loss function.
        loss = self.loss_function(logits, targets)

        return loss

    def add_statistics(self, stat_col):
        """
        Add statistics to collector.

        EMPTY - To be redefined in inheriting classes.

        :param stat_col: Statistics collector.

        """
        pass

    def collect_statistics(self, stat_col, data_tuple, logits, _):
        """
        Base statistics collection.

        EMPTY - To be redefined in inheriting classes.

        :param stat_col: Statistics collector.
        :param data_tuple: Data tuple containing inputs and targets.
        :param logits: Logits being output of the model.
        :param _: auxiliary tuple (aux_tuple) is not used in this function.

        """
        pass

    def turn_on_cuda(self, data_tuple, aux_tuple):
        """ Enables computations on GPU - copies the input and target matrices (from DataTuple) to GPU.
        This method has to be overwritten in derived class if one decides to copy other matrices as well.

        :param data_tuple: Data tuple.
        :param aux_tuple: Auxiliary tuple (WARNING: Values stored in that variable will remain in CPU)
        :returns: Pair of Data and Auxiliary tuples (Data on GPU, Aux on CPU).
        """
        # Unpack tuples and copy data to GPU.
        gpu_inputs = data_tuple.inputs.cuda()
        gpu_targets = data_tuple.targets.cuda()

        # Pack matrices to tuples.
        data_tuple = DataTuple(gpu_inputs, gpu_targets)

        return data_tuple, aux_tuple

    def plot_preprocessing(self, data_tuple, aux_tuple, logits):
        """
        Allows for some data preprocessing before the model creates a plot for
        visualization during training or inference. To be redefined in
        inheriting classes.

        :param data_tuple: Data tuple.
        :param aux_tuple: Auxiliary tuple.
        :param logits: Logits being output of the model.
        :return: data_tuplem aux_tuple, logits after preprocessing.

        """
        return data_tuple, aux_tuple, logits

    def curriculum_learning_initialize(self, curriculum_params):
        """
        Initializes curriculum learning - simply saves the curriculum params.
        This method can be overwriten in the derived classes.

        :curriculum_params: Interface to parameters accessing curriculum learning view of the registry tree.
        """
        # Save params.
        self.curriculum_params = curriculum_params

    def curriculum_learning_update_params(self, episode):
        """
        Updates problem parameters according to curriculum learning. There is
        no general solution to curriculum learning. This method should be
        overwriten in the derived classes.

        :param episode: Number of the current episode.
        :returns: True informing that CL wasn't active at all (i.e. is finished).

        """
        return True
