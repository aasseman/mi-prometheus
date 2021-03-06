#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2017 Sean Robertson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# --------------------------------------------------------------------------------
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

"""text_to_text_problem.py: abstract base class for text to text sequential problems, e.g. machine translation
    Inspiration taken from the corresponding Pytorch tutorial.
    See https://pytorch.org/tutorials/intermediate/seq2seq_translation_tutorial.html """
__author__ = "Vincent Marois"

import collections
import unicodedata
import re
import torch
import torch.nn as nn
from problems.seq_to_seq.seq_to_seq_problem import SeqToSeqProblem

_TextAuxTuple = collections.namedtuple(
    'TextAuxTuple',
    ('inputs_text',
     'outputs_text',
     'input_lang',
     'output_lang'))


class TextAuxTuple(_TextAuxTuple):
    """
    Tuple used for storing batches of data by text to text sequential problems.
    Contains four elements:

    - text input sentence (e.g. string in input language for translation)
    - text output sentence (e.g. string in output language for translation
    - Lang() instance of the input language
    - Lang() instance of the output language

    """
    __slots__ = ()


# global tokens
PAD_token = 0
SOS_token = 1
EOS_token = 2


class TextToTextProblem(SeqToSeqProblem):
    """
    Base class for text to text sequential problems.

    Provides some basic functionality useful in all problems of such
    type

    """

    def __init__(self, params):
        """
        Initializes problem object. Calls base constructor. Sets nn.NLLLoss()
        as default loss function.

        :param params: Dictionary of parameters (read from configuration file).

        """
        super(TextToTextProblem, self).__init__(params)

        # set default loss function - negative log likelihood and ignore
        # padding elements.
        self.loss_function = nn.NLLLoss(size_average=True, ignore_index=0)

    def compute_BLEU_score(self, data_tuple, logits, aux_tuple):
        """
        Compute BLEU score in order to evaluate the translation quality
        (equivalent of accuracy) Reference paper:
        http://www.aclweb.org/anthology/P02-1040.pdf Implementation inspired
        from https://machinelearningmastery.com/calculate-bleu-score-for-text-
        python/ To deal with the batch, we accumulate the individual bleu score
        for each pair of sentences and average over the batch size.

        :param data_tuple: DataTuple(input_tensors, target_tensors)
        :param logits: predictions of the model
        :param aux_tuple: TextAuxTuple('inputs_text', 'outputs_text', 'input_lang', 'output_lang')

        :return: Average BLEU Score for the batch ( 0 < BLEU < 1)

        """
        # get most probable words indexes for the batch
        _, top_indexes = logits.topk(k=1, dim=-1)
        logits = top_indexes.squeeze()
        batch_size = logits.shape[0]

        from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

        # retrieve target sentences from TextAuxTuple
        targets_text = []
        for sentence in aux_tuple.outputs_text:
            targets_text.append(sentence.split())

        # retrieve text sentences from the logits (which should be tensors of
        # indexes)
        logits_text = []
        for logit in logits:
            logits_text.append(
                [aux_tuple.output_lang.index2word[index.item()]
                 for index in logit])

        bleu_score = 0
        for i in range(batch_size):
            # compute bleu score and use a smoothing function
            bleu_score += sentence_bleu([targets_text[i]],
                                        logits_text[i],
                                        smoothing_function=SmoothingFunction().method1)

        return round(bleu_score / batch_size, 4)

    def evaluate_loss(self, data_tuple, logits, aux_tuple):
        """
        Computes loss.
        By default, the loss function is the Negative Log Likelihood function.
        The input given through a forward call is expected to contain log-probabilities (LogSoftmax) of each class.
        The input has to be a Tensor of size either (batch_size, C) or (batch_size, C, d1, d2,...,dK) with K ≥ 2 for the
        K-dimensional case.
        The target that this loss expects is a class index (0 to C-1, where C = number of classes).

        :param data_tuple: Data tuple containing inputs and targets.
        :param logits: Logits being outputs of the model.
        :param aux_tuple: Auxiliary tuple containing mask.
        :return: loss
        """
        loss = self.loss_function(logits.transpose(1, 2), data_tuple.targets)

        return loss

    def set_max_length(self, max_length):
        """
        Sets maximum sequence lenth (property).

        :param max_length: Length to be saved as max.

        """
        self.max_sequence_length = max_length

    def add_statistics(self, stat_col):
        """
        Add BLEU score to collector.

        :param stat_col: Statistics collector.

        """
        stat_col.add_statistic('bleu_score', '{:4.5f}')

    def collect_statistics(self, stat_col, data_tuple, logits, aux_tuple):
        """
        Collects BLEU score.

        :param stat_col: Statistics collector.
        :param data_tuple: Data tuple containing inputs and targets.
        :param logits: Logits being output of the model.
        :param aux_tuple: auxiliary tuple (aux_tuple).

        """

        stat_col['bleu_score'] = self.compute_BLEU_score(
            data_tuple, logits, aux_tuple)

    def show_sample(self, data_tuple, aux_tuple, sample_number=0):
        """
        Shows the sample (both input and target sequences) using matplotlib.
        Elementary visualization.

        :param data_tuple: Data tuple.
        :param aux_tuple: Auxiliary tuple.
        :param sample_number: Number of sample in a batch (DEFAULT: 0)

        """
        # TODO
        pass

    # ----------------------
    # The following are helper functions for data pre-processing in the case
    # of a translation task

    def unicode_to_ascii(self, s):
        """
        Turn a Unicode string to plain ASCII. See:
        http://stackoverflow.com/a/518232/2809427.

        :param s: Unicode string.
        :return: plain ASCII string.

        """
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        )

    def normalize_string(self, s):
        """
        Lowercase, trim, and remove non-letter characters in string s.

        :param s: string.
        :return: normalized string.

        """
        s = self.unicode_to_ascii(s.lower().strip())
        s = re.sub(r"([.!?])", r" \1", s)
        s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
        return s

    def indexes_from_sentence(self, lang, sentence, max_seq_length):
        """
        Construct a list of indexes using a 'vocabulary index' from a specified
        Lang instance for the specified sentence (see Lang class below). Also
        pad this list of indexes so that its length will be equal to
        max_seq_length (needed for batch support).

        :param lang: instance of the class Lang, having a word2index dict.
        :param sentence: string to convert word for word to indexes, e.g. "The black cat is eating."
        :param max_seq_length: Maximum length for the list of indexes.

        :return: padded list of indexes.

        """
        seq = [lang.word2index[word]
               for word in sentence.split(' ')] + [EOS_token]
        seq += [PAD_token for _ in range(max_seq_length - len(seq))]
        return seq

    def tensor_from_sentence(self, lang, sentence, max_seq_length):
        """
        Reuses indexes_from_sentence() to create a tensor of indexes with the
        EOS token.

        :param lang: instance of the Lang class, having a word2index dict.
        :param sentence: string to convert word for word to indexes, e.g. "The black cat is eating."
        :param max_seq_length: Maximum length for the list of indexes (passed to indexes_from_sentence())

        :return: tensor of indexes, terminated by the EOS token.

        """
        indexes = self.indexes_from_sentence(lang, sentence, max_seq_length)

        return torch.tensor(indexes).type(self.app_state.LongTensor)

    def tensors_from_pair(self, pair, input_lang, output_lang, max_seq_length):
        """
        Creates a tuple of tensors of indexes from a pair of sentences.

        :param pair: tuple of input & output languages sentences
        :param input_lang: instance of the class Lang, having a word2index dict, representing the input language.
        :param output_lang: instance of the class Lang, having a word2index dict, representing the output language.
        :param max_seq_length: Maximum length for the list of indexes (passed to indexes_from_sentence())

        :return: tuple of tensors of indexes.

        """
        input_tensor = self.tensor_from_sentence(
            input_lang, pair[0], max_seq_length)
        target_tensor = self.tensor_from_sentence(
            output_lang, pair[1], max_seq_length)

        return [input_tensor, target_tensor]

    def tensors_from_pairs(self, pairs, input_lang,
                           output_lang, max_seq_length):
        """
        Returns a list of tuples of tensors of indexes from a list of pairs of
        sentences. Reuses tensors_from_pair.

        :param pairs: list of sentences pairs
        :param input_lang: instance of the class Lang, having a word2index dict, representing the input language.
        :param output_lang: instance of the class Lang, having a word2index dict, representing the output language.
        :param max_seq_length: Maximum length for the list of indexes (passed to indexes_from_sentence())

        :return: list of tensors of indexes.

        """
        return [self.tensors_from_pair(
            pair, input_lang, output_lang, max_seq_length) for pair in pairs]


class Lang(object):
    """
    Simple helper class allowing to represent a language in a translation task.
    It will contain for instance a vocabulary index (word2index dict) & keep
    track of the number of words in the language.

    This class is useful as each word in a language will be represented as a one-hot vector: a giant vector of zeros
    except for a single one (at the index of the word). The dimension of this vector is potentially very high, hence it
    is generally useful to trim the data to only use a few thousand words per language.

    The inputs and targets of the associated sequence to sequence networks will be sequences of indexes, each item
    representing a word. The attributes of this class (word2index, index2word, word2count) are useful to keep track of
    this.

    """

    def __init__(self, name):
        """
        Constructor.

        :param name: string to name the language (e.g. french, english)

        """
        self.name = name
        self.word2index = {"PAD": 0, "SOS": 1, "EOS": 2}  # dict 'word': index
        # keep track of the occurrence of each word in the language. Can be
        # used to replace
        self.word2count = {}
        # rare words.
        # dict 'index': 'word', initializes with PAD, EOS, SOS tokens
        self.index2word = {0: "PAD", 1: "SOS", 2: "EOS"}
        # Number of words in the language. Start by counting PAD, EOS, SOS
        # tokens.
        self.n_words = 3

    def add_sentence(self, sentence):
        """
        Process a sentence using add_word().

        :param sentence: sentence to be added to the language.
        :return: None.

        """
        for word in sentence.split(' '):
            self.add_word(word)

    def add_word(self, word):
        """
        Add a word to the vocabulary set: update word2index, word2count,
        index2words & n_words.

        :param word: word to be added.
        :return: None.

        """

        if word not in self.word2index:  # if the current word has not been seen before
            # create a new entry in word2index
            self.word2index[word] = self.n_words
            self.word2count[word] = 1  # count first occurrence of this word
            # create a new entry in index2word
            self.index2word[self.n_words] = word
            self.n_words += 1  # increment total number of words in the language

        else:  # this word has been seen before, simply update its occurrence
            self.word2count[word] += 1
