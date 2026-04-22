import sys, os
from tqdm import tqdm
import jiwer
from zhon.hanzi import punctuation
import string
import numpy as np
import soundfile as sf
import scipy
import zhconv
from funasr import AutoModel
import glob

punctuation_all = punctuation + string.punctuation

def load_zh_model():
    model = AutoModel(model="paraformer-zh")
    return model

def process_one(hypo, truth):
    for x in punctuation_all:
        if x == '\'':
            continue
        truth = truth.replace(x, '')
        hypo = hypo.replace(x, '')

    truth = truth.replace('  ', ' ')
    hypo = hypo.replace('  ', ' ')

    truth = " ".join([x for x in truth])
    hypo = " ".join([x for x in hypo])

    result = jiwer.process_words(truth, hypo)
    wer = result.wer
    return wer
