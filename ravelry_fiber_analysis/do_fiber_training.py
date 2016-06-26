import json, numpy as np
import matplotlib.pylab as pl
import scipy.sparse as sps
import scipy.io
import matplotlib.pylab as plt
import scipy as sp
import scipy.sparse as sps
import pickle
import os

from ravelry_fiber_analysis import ravelry_api_common as rc

from lightfm import LightFM
from lightfm.evaluation import auc_score

def do_fiber_training(visualization = False):

    if not os.path.isfile(rc.RECOMMENDER_TRAINING) or not os.path.isfile(rc.RECOMMENDER_MODEL):

        yarn_data_matrix = pickle.load(open( rc.YARN_DATA_MATRIX, "rb" ))
        yarn_data_train = sps.coo_matrix(
                                yarn_data_matrix[:int(len(yarn_data_matrix)*0.5)]
                        ) > 0
        yarn_data_test = sps.coo_matrix(
                                yarn_data_matrix[int(len(yarn_data_matrix)*0.5):]
                        ) > 0
        if visualization:
            print yarn_data_train.shape[0],yarn_data_test.shape[0], len(yarn_data_matrix)

        # Taken from: https://github.com/lyst/lightfm/blob/master/examples/stackexchange/hybrid_crossvalidated.ipynb
        # Set the number of threads; you can increase this
        # ify you have more physical cores available.
        NUM_THREADS = 2
        NUM_COMPONENTS = 30
        NUM_EPOCHS = 3
        ITEM_ALPHA = 1e-6

        # Let's fit a WARP model: these generally have the best performance.
        model = LightFM(loss='warp',
                        item_alpha=ITEM_ALPHA,
                       no_components=NUM_COMPONENTS)

        # Run 3 epochs and time it.
        model = model.fit(yarn_data_train, epochs=NUM_EPOCHS, num_threads=NUM_THREADS)



        # Compute and print the AUC score
        train_auc = auc_score(model, yarn_data_train, num_threads=NUM_THREADS).mean()
        print('Collaborative filtering train AUC: %s' % train_auc)


        # We pass in the train interactions to exclude them from predictions.
        # This is to simulate a recommender system where we do not
        # re-recommend things the user has already interacted with in the train
        # set.
        test_auc = auc_score(model, yarn_data_test, train_interactions=yarn_data_train, num_threads=NUM_THREADS).mean()
        print('Collaborative filtering test AUC: %s' % test_auc)

        pickle.dump(yarn_data_matrix,open(rc.RECOMMENDER_TRAINING, 'wb'))
        pickle.dump(model,open(rc.RECOMMENDER_MODEL, 'wb'))
    else:
        yarn_data_matrix = pickle.load(open(rc.RECOMMENDER_TRAINING, 'rb'))
        model = pickle.load(open(rc.RECOMMENDER_MODEL, 'rb'))


    translation_dict = pickle.load(open(rc.YARN_TRANSLATION_DATA, 'rb'))
    print len(yarn_data_matrix)
    for matrix_id in xrange(0,len(yarn_data_matrix)):
        print matrix_id
        predictions = model.predict(matrix_id,yarn_data_matrix[matrix_id])
        matches = []
        predictions += abs(np.min(predictions)) # make non-negative
        _max = np.max(predictions) # find max for normalization
        predictions /= _max # Normalize predictions
        for prediction in xrange(0,len(predictions)):

            if predictions[prediction] > 0.9:
                matches.append([translation_dict[prediction],prediction,predictions[prediction]])

        print translation_dict[matrix_id],matches