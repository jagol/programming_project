import os
import argparse
import csv

from predict import load_model, load_config, get_num_examples
from corpus_parser import Parser, Cleaner
from swiss_char_checker import *
from neural_models import *

# General Pipeline: specify model -> specify test set -> specify if with char-checker -> specify if written to file

def parse_cmd_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--model", type=str, help="Path to model.")
    parser.add_argument('-i', '--path_in', type=str, help='Path to input file.')
    parser.add_argument('-t', '--type', type=str, help='Either "torch" or "sklearn".')
    parser.add_argument("-c", "--config", type=str, help="Path to hyperparamter/config file (json).")
    parser.add_argument("-cc", "--charchecker", action="store_true", default=True, help="Do pre-elimination with char-checker.")
    parser.add_argument("-w", "--write", action="store_true", default=False, help="Write to file (name automatically generated.")
    parser.add_argument("-o", "--outfile", type=str, help="Path to outfile to write to.")
    return parser.parse_args()


def predict_on_input(model, model_type, path_in, config, char_checker, device):
    """Make prediction on the input data with the given model.

    Args:
        model: either torch.nn.Model or sklearn-model
        model_type: str
        path_in: str
        config: dict
        device: str
    Return:
        list
    """
    char_to_idx = load_char_to_idx()
    max_length = load_max_len() if 'max_length_text' not in config else config['max_length_text']
    predictions = []
    if model_type == 'torch':
        reader = csv.reader(open(path_in, 'r', encoding='utf8'))
        next(reader)
        for row in reader:
            tweet_id, text = row[0], Cleaner.clean(Cleaner.mask(row[1])[0])
            if char_checker == True:
                if check_sentences(text) == False:
                    predictions.append((tweet_id, 1, 0.99))
                    continue
            tweet_idxs = [char_to_idx.get(char, char_to_idx['unk']) for char in text][:max_length]
            x = np.zeros(max_length)
            for j, idx in enumerate(tweet_idxs):
                x[j] = idx
            output_raw = model(torch.LongTensor([x]).to(device))
            output = torch.squeeze(output_raw)
            max_prob, prediction = torch.max(output, 0)
            pred_binary = prediction.item() if prediction.item() <= 1 else 1
            predictions.append((tweet_id, pred_binary, np.exp(max_prob.tolist())))
    return predictions

def write_to_file(preds, outfile):
    """Write to outfile

    Args:
        preds: list
        outfile: str
    Return:
        None
    """
    with open(outfile, "w", encoding="utf8") as f:
        csv_writer = csv.writer(f)
        for item in preds:
            csv_writer.writerow(item)


def main():
    print("Reading in command-line args...")
    args = parse_cmd_args()
    config = load_config(args.config)
    model = load_model(args.model, args.type, device="cpu")
    print("Evaluate on test set...")
    results = predict_on_input(model, args.type, args.path_in, config, args.charchecker, "cpu")
    if args.write == True:
        print("Writing to file {}.".format(args.outfile))
        write_to_file(results, args.outfile)
    print("Done.")

if __name__ == "__main__":
        main()
