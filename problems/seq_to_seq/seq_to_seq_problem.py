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

"""problem.py: contains base class for all seq2seq problems"""
__author__ = "Tomasz Kornuta"

from problems.problem import Problem


class SeqToSeqProblem(Problem):
    """
    Class representing base class for all sequential problems.
    """

    def __init__(self, params):
        """
        Initializes problem object. Calls base constructor.

        :param params: Dictionary of parameters (read from configuration file).

        """
        super(SeqToSeqProblem, self).__init__(params)

        # Check if predictions/targets should be masked.
        if 'use_mask' not in params:
            # TODO: Set false as default!
            params.add_default_params({'use_mask': True})
        self.use_mask = params["use_mask"]

    def evaluate_loss(self, data_tuple, logits, aux_tuple):
        """ Calculates accuracy equal to mean number of correct predictions in a given batch.
        WARNING: Applies mask (from aux_tuple) to both logits and targets!

        :param logits: Logits being output of the model.
        :param data_tuple: Data tuple containing inputs and targets.
        :param aux_tuple: Auxiliary tuple containing mask.
        """
        # Check if mask should be is used - if so, use the correct loss
        # function.
        if (self.use_mask):
            loss = self.loss_function(
                logits, data_tuple.targets, aux_tuple.mask)
        else:
            loss = self.loss_function(logits, data_tuple.targets)

        return loss
