# Force MKL (CPU BLAS) to use one core, faster
import os
os.environ["OMP_NUM_THREADS"] = '1'

import torch
import torch.nn.functional as F
import argparse
import yaml
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Force MKL (CPU BLAS) to use one core, faster
os.environ["OMP_NUM_THREADS"] = '1'

# Import problems and problem factory.
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'problems'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
from problems.problem_factory import ProblemFactory
from models.model_factory import ModelFactory

from misc.app_state import AppState


def show_sample(prediction, target, mask, sample_number=0):
    """ Shows the sample (both input and target sequences) using matplotlib."""
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    # Set ticks.
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Set labels.
    ax1.set_title('Prediction')
    ax1.set_ylabel('Data bits')
    ax2.set_title('Target')
    ax2.set_ylabel('Data bits')
    # ax2.set_ylabel('Data bits')
    ax2.set_xlabel('Item number')

    # Set data.
    ax1.imshow(np.transpose((prediction[sample_number, :, :]).detach().numpy(), [1, 0]))
    ax2.imshow(np.transpose((target[sample_number, :, :]).detach().numpy(), [1, 0]))

    plt.show()

    # Plot!

if __name__ == '__main__':
    app_state = AppState()

    # Create parser with list of  runtime arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', type=str, default='', dest='input_dir',
                        help='Input path, containing the saved parameters as well as the yaml file')
    parser.add_argument('-v', action='store_true', dest='visualize',
                        help='Activate visualization')

    # Parse arguments.
    FLAGS, unparsed = parser.parse_known_args()

    # Test
    print("Testing")

    # Check if config file was selected.
    if FLAGS.input_dir == '':
        print('Please pass input path folder as -i parameter')
        exit(-1)

    if FLAGS.visualize:
        app_state.visualize = True

    # Check it file exists.
    if not os.path.isdir(FLAGS.input_dir):
        print('Input path {} does not exist'.format(FLAGS.input_dir))
        exit(-2)

    # Read YAML file
    with open(FLAGS.input_dir + "/train_settings.yaml", 'r') as stream:
        config_loaded = yaml.load(stream)

    # set seed
    if config_loaded["settings"]["seed_torch"] != -1:
        torch.manual_seed(config_loaded["settings"]["seed_torch"])

    if config_loaded["settings"]["seed_numpy"] != -1:
        np.random.seed(config_loaded["settings"]["seed_numpy"])

    # Build new problem
    problem = ProblemFactory.build_problem(config_loaded['problem_test'])

    # Build model
    model = ModelFactory.build_model(config_loaded['model'])

    # load the trained model
    model.load_state_dict(
        torch.load(FLAGS.input_dir + "/model_parameters",
                   map_location=lambda storage, loc: storage)  # This is to be able to load CUDA-trained model on CPU
    )

    for inputs, targets, mask in problem.return_generator():
        # apply the trained model
        output = F.sigmoid(model(inputs))

        if config_loaded['settings']['use_mask']:
            output = output[:, mask[0], :]
            targets = targets[:, mask[0], :]

        # test accuracy
        output = torch.round(output)
        acc = 1 - torch.abs(output-targets)
        accuracy = acc.mean()
        print("Accuracy: %.6f" % (accuracy * 100) + "%")
        # plot data
        # show_sample(output, targets, mask)

        if app_state.visualize:
            is_closed = model.plot_sequence(inputs[0].detach(), output[0].detach(), targets[0].detach())
            if is_closed:
                break
        else:
            break
