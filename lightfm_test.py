
import numpy as np

from lightfm.datasets import fetch_stackexchange

data = fetch_stackexchange('crossvalidated',
                           test_set_fraction=0.1,
                           indicator_features=False,
                           tag_features=True)

train = data['train']
test = data['test']

import matplotlib.pylab as pl
import scipy.sparse as sps
import scipy.io
import matplotlib.pylab as plt
import scipy.sparse as sps

exit()

print('The dataset has %s users and %s items, '
      'with %s interactions in the test and %s interactions in the training set.'
      % (train.shape[0], train.shape[1], test.getnnz(), train.getnnz()))

# Import the model
from lightfm import LightFM

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
model = model.fit(train, epochs=NUM_EPOCHS, num_threads=NUM_THREADS)

# Import the evaluation routines
from lightfm.evaluation import auc_score

# Compute and print the AUC score
train_auc = auc_score(model, train, num_threads=NUM_THREADS).mean()
print('Collaborative filtering train AUC: %s' % train_auc)


# We pass in the train interactions to exclude them from predictions.
# This is to simulate a recommender system where we do not
# re-recommend things the user has already interacted with in the train
# set.
test_auc = auc_score(model, test, train_interactions=train, num_threads=NUM_THREADS).mean()
print('Collaborative filtering test AUC: %s' % test_auc)


# Set biases to zero
model.item_biases *= 0.0

test_auc = auc_score(model, test, train_interactions=train, num_threads=NUM_THREADS).mean()
print('Collaborative filtering test AUC: %s' % test_auc)


item_features = data['item_features']
tag_labels = data['item_feature_labels']

print('There are %s distinct tags, with values like %s.' % (item_features.shape[1], tag_labels[:3].tolist()))

# Define a new model instance
model = LightFM(loss='warp',
                item_alpha=ITEM_ALPHA,
                no_components=NUM_COMPONENTS)

# Fit the hybrid model. Note that this time, we pass
# in the item features matrix.
model = model.fit(train,
                item_features=item_features,
                epochs=NUM_EPOCHS,
                num_threads=NUM_THREADS)

# Don't forget the pass in the item features again!
train_auc = auc_score(model,
                      train,
                      item_features=item_features,
                      num_threads=NUM_THREADS).mean()
print('Hybrid training set AUC: %s' % train_auc)

test_auc = auc_score(model,
                     test,
                     train_interactions=train,
                     item_features=item_features,
                     num_threads=NUM_THREADS).mean()
print('Hybrid test set AUC: %s' % test_auc)


def get_similar_tags(model, tag_id):
    # Define similarity as the cosine of the angle
    # between the tag latent vectors

    # Normalize the vectors to unit length
    # norm = np.linalg.norm(model.item_embeddings, axis=1)
    norm = np.apply_along_axis(np.linalg.norm,1,model.item_embeddings)
    tag_embeddings = (model.item_embeddings.T
                      / norm).T  #np.linalg.norm(model.item_embeddings, axis=1))

    query_embedding = tag_embeddings[tag_id]
    similarity = np.dot(tag_embeddings, query_embedding)
    most_similar = np.argsort(-similarity)[1:4]

    return most_similar


for tag in (u'bayesian', u'regression', u'survival'):
    tag_id = tag_labels.tolist().index(tag)
    print('Most similar tags for %s: %s' % (tag_labels[tag_id],
                                            tag_labels[get_similar_tags(model, tag_id)]))