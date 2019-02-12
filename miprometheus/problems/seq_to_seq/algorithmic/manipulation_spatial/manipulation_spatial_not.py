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

__author__ = "Tomasz Kornuta"

import torch
import numpy as np
from miprometheus.problems.seq_to_seq.algorithmic.algorithmic_seq_to_seq_problem import AlgorithmicSeqToSeqProblem


class ManipulationSpatialNot(AlgorithmicSeqToSeqProblem):
    """
    Class generating sequences of random bit-patterns with inverted targets, so\
    the system is supposed to learn NOT logical operation, i.e. y(0) = !x(0), y(1) = !x(1), ... 

    .. figure:: ../img/algorithmic/manipulation_spatial/manipulation_spatial_not.png
        :scale: 80 %
        :align: center

        Exemplary sequence generated by the Manipulation Spatial Not problem (without additional command lines).

    1. There are two control markers, indicating:

        - beginning of first subsequence (i.e. sequence to be memorized),
        - beginning of second subsequence ("dummy").

    2. For other elements of the input sequence the control bits are set to zero. \
    However, the second ("dummy") subsequence might contain (random) command lines (when number of control bits is > 2).

    3. Generator returns a mask, which (by default) is used for masking the unimportant elements of the target sequence \
    (i.e. only outputs related to the second subsequence are taken into consideration)
    """

    def __init__(self, params):
        """
        Constructor - stores parameters. Calls parent class ``AlgorithmicSeqToSeqProblem``\
         initialization.

        :param params: Dictionary of parameters (read from configuration ``.yaml`` file).
        """
        # Set default number of bits for a given problem.
        # This has to be done before calling base class constructor!
        params.add_default_params({
            'control_bits': 2,
            'data_bits': 8 })
        # Call parent constructor - sets e.g. the loss function, dtype.
        # Additionally it extracts "standard" list of parameters for
        # algorithmic tasks, like batch_size, numbers of bits, sequences etc.
        super(ManipulationSpatialNot, self).__init__(params)
        self.name = 'ManipulationSpatialNot'

        assert self.control_bits >= 2, "Problem requires at least 2 control bits (currently %r)" % self.control_bits
        assert self.data_bits >= 1, "Problem requires at least 1 data bit (currently %r)" % self.data_bits


    def generate_batch(self, batch_size):
        """
        Generates a batch of samples of size ''batch_size'' on-the-fly.

        .. note::

            The sequence length is drawn randomly between ``self.min_sequence_length`` and \
            ``self.max_sequence_length``.

        .. warning::
            All the samples within the batch will have the same sequence length.

        :param batch_size: Size of the batch to be returned. 

        :return: DataDict({'sequences', 'sequences_length', 'targets', 'masks', 'num_subsequences'}), with:

            - sequences: [BATCH_SIZE, 2*SEQ_LENGTH+2, CONTROL_BITS+DATA_BITS]
            - sequences_length: [BATCH_SIZE, 1] (the same random value between self.min_sequence_length and self.max_sequence_length)
            - targets: [BATCH_SIZE, , 2*SEQ_LENGTH+2, DATA_BITS]
            - masks: [BATCH_SIZE, 2*SEQ_LENGTH+2, 1]
            - num_subsequences: [BATCH_SIZE, 1]
        """
        # Control part containing (or not) control lines, depending on the settings.
        ctrl_aux = self.generate_ctrl_aux(2)

        # Set sequence length
        seq_length = np.random.randint(
            self.min_sequence_length, self.max_sequence_length + 1)

        # Generate batch of random bit sequences [BATCH_SIZE x SEQ_LENGTH X
        # DATA_BITS]
        bit_seq = np.random.binomial(
            1, self.bias, (batch_size, seq_length, self.data_bits))

        # Generate input:  [BATCH_SIZE, 2*SEQ_LENGTH+2, CONTROL_BITS+DATA_BITS]
        inputs = np.zeros([batch_size,
                           2 * seq_length + 2,
                           self.control_bits + self.data_bits],
                          dtype=np.float32)

        # Set start control marker.
        inputs[:, 0, 0] = 1  # Memorization bit.

        # Set bit sequence.
        inputs[:, 1:seq_length + 1,
        self.control_bits:self.control_bits + self.data_bits] = bit_seq

        # Set end control marker.
        inputs[:, seq_length + 1, 1] = 1  # Recall bit.

        # Set control lines for recall items.   
        inputs[:,seq_length + 2:2 * seq_length + 2,0:self.control_bits] = np.tile(
            ctrl_aux,(batch_size,seq_length,1))


        # Generate target:  [BATCH_SIZE, 2*SEQ_LENGTH+2, DATA_BITS] (only data
        # bits!)
        targets = np.zeros([batch_size, 2 * seq_length + 2,
                            self.data_bits], dtype=np.float32)

        # Set target bit sequence - logical not.
        targets[:, seq_length + 2:, :] = np.logical_not(bit_seq)

        # Generate target mask: [BATCH_SIZE, 2*SEQ_LENGTH+2, 1]
        ptmask = torch.zeros([batch_size, 2 * seq_length + 2, 1]).type(self.app_state.ByteTensor)
        ptmask[:, seq_length + 2:] = 1

        # PyTorch variables.
        ptinputs = torch.from_numpy(inputs).type(self.app_state.dtype)
        pttargets = torch.from_numpy(targets).type(self.app_state.dtype)

        # Return data_dict.
        data_dict = self.create_data_dict()
        data_dict['sequences'] = ptinputs
        data_dict['sequences_length'] = seq_length
        data_dict['targets'] = pttargets
        data_dict['masks'] = ptmask
        data_dict['num_subsequences'] = 1

        return data_dict


if __name__ == "__main__":
    """ Tests sequence generator - generates and displays a random sample"""

    # "Loaded parameters".
    from miprometheus.utils.param_interface import ParamInterface

    params = ParamInterface()
    params.add_config_params({'control_bits': 2,
                              'data_bits': 8,
                              'min_sequence_length': 1,
                              'max_sequence_length': 10,
                              'size': 1000
                              })
    batch_size = 64
    num_workers = 0

    # Create problem object.
    problem = ManipulationSpatialNot(params)

    # Create dataloader object.
    from torch.utils.data import DataLoader
    loader = DataLoader(dataset=problem, batch_size=batch_size, collate_fn=problem.collate_fn,
                         shuffle=False, num_workers=num_workers, worker_init_fn=problem.worker_init_fn)

    # Measure generation time.
    #print("Measuring generation time. Please wait...") 
    #import time
    #s = time.time()
    #for i, batch in enumerate(loader):
    #    #print('Batch # {} - {}'.format(i, type(batch)))
    #    pass
    #print('Number of workers: {}'.format(loader.num_workers))
    #print('Time taken to exhaust a dataset of size {}, with a batch size of {}: {}s'
    #      .format(len(problem), batch_size, time.time() - s))

    # Display single sample (0) from batch.
    batch = next(iter(loader))
    problem.show_sample(batch, 0)

