import utils
import time
from utils import np, plt, load_tiff_image, load_SAR_image, compute_metrics, data_augmentation, unet, normalization, \
RGB_image, extract_patches, patch_tiles, bal_aug_patches, extrac_patch2, test_FCN, pred_recostruction, \
weighted_categorical_crossentropy, mask_no_considered, tf, Adam, prediction, load_model, confusion_matrix, \
EarlyStopping, ModelCheckpoint, identity_block, ResNet50, color_map

root_path = './DATASETS/'

# Load images
img_t1 = load_tiff_image(root_path+'images/18_08_2017_image'+'.tif').astype(np.float32)
img_t1 = img_t1.transpose((1,2,0))
img_t2 = load_tiff_image(root_path+'images/21_08_2018_image'+'.tif').astype(np.float32)
img_t2 = img_t2.transpose((1,2,0))

# Concatenation of images
image_array1 = np.concatenate((img_t1, img_t2), axis = -1).astype(np.float32)
h_, w_, channels = image_array1.shape
print(image_array1.shape)

# Normalization
type_norm = 1
image_array = normalization(image_array1, type_norm)
print(np.min(image_array), np.max(image_array))

# Load reference
image_ref1 = load_tiff_image(root_path+'images/REFERENCE_2018_EPSG4674'+'.tif')
image_ref = image_ref1[:1700,:1440]

past_ref1 = load_tiff_image(root_path+'images/PAST_REFERENCE_FOR_2018_EPSG4674'+'.tif')
unique, counts = np.unique(past_ref1, return_counts=True)
counts_dict = dict(zip(unique, counts))
print('='*50)
print(counts_dict)
past_ref = past_ref1[:1700,:1440]

#  Creation of buffer
buffer = 2
final_mask = mask_no_considered(image_ref, buffer, past_ref)
#plt.imshow(final_mask)

# Mask with tiles
tile_number = np.ones((340,480))
mask_c_1 = np.concatenate((tile_number, 2*tile_number, 3*tile_number), axis=1)
mask_c_2 = np.concatenate((4*tile_number, 5*tile_number, 6*tile_number), axis=1)
mask_c_3 = np.concatenate((7*tile_number, 8*tile_number, 9*tile_number), axis=1)
mask_c_4 = np.concatenate((10*tile_number, 11*tile_number, 12*tile_number), axis=1)
mask_c_5 = np.concatenate((13*tile_number, 14*tile_number, 15*tile_number), axis=1)
mask_tiles = np.concatenate((mask_c_1, mask_c_2, mask_c_3 , mask_c_4, mask_c_5), axis=0)

mask_tr_val = np.zeros((mask_tiles.shape))
tr1 = 1
tr2 = 6
tr3 = 7
tr4 = 13
val1 = 5
val2 = 12

mask_tr_val[mask_tiles == tr1] = 1
mask_tr_val[mask_tiles == tr2] = 1
mask_tr_val[mask_tiles == tr3] = 1
mask_tr_val[mask_tiles == tr4] = 1
mask_tr_val[mask_tiles == val1] = 2
mask_tr_val[mask_tiles == val2] = 2

total_no_def = 0
total_def = 0

total_no_def += len(image_ref[image_ref==0])
total_def += len(image_ref[image_ref==1])
# Print number of samples of each class
print('Total no-deforestaion class is {}'.format(len(image_ref[image_ref==0])))
print('Total deforestaion class is {}'.format(len(image_ref[image_ref==1])))
print('Percentage of deforestaion class is {:.2f}'.format((len(image_ref[image_ref==1])*100)/len(image_ref[image_ref==0])))
#%% Patches extraction
patch_size = 128
stride = patch_size//8

# Percent of class deforestation
percent = 5
# 0 -> No-DEf, 1-> Def, 2 -> No considered
number_class = 3

# Trainig tiles
tr_tiles = [tr1, tr2, tr3, tr4]
patches_tr, patches_tr_ref = patch_tiles(tr_tiles, mask_tiles, image_array, final_mask, patch_size, stride)
patches_tr_aug, patches_tr_ref_aug = bal_aug_patches(percent, patch_size, patches_tr, patches_tr_ref)
patches_tr_ref_aug_h = tf.keras.utils.to_categorical(patches_tr_ref_aug, number_class)

# Validation tiles
val_tiles = [val1, val2]
patches_val, patches_val_ref = patch_tiles(val_tiles, mask_tiles, image_array, final_mask, patch_size, stride)
patches_val_aug, patches_val_ref_aug = bal_aug_patches(percent, patch_size, patches_val, patches_val_ref)
patches_val_ref_aug_h = tf.keras.utils.to_categorical(patches_val_ref_aug, number_class)

#%%
start_time = time.time()
exp = 1
rows = patch_size
cols = patch_size
adam = Adam(lr = 0.0001 , beta_1=0.9)
batch_size = 8

weights = [0.5, 0.5, 0]
loss = weighted_categorical_crossentropy(weights)
model = unet((rows, cols, channels))
model.compile(optimizer=adam, loss=loss, metrics=['accuracy'])
# print model information
model.summary()
filepath = 'models/'
# define early stopping callback
earlystop = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=10, verbose=1, mode='min')
checkpoint = ModelCheckpoint(filepath+'unet_exp_'+str(exp)+'.h5', monitor='val_loss', verbose=1, save_best_only=True, mode='min')
callbacks_list = [earlystop, checkpoint]
# train the model
start_training = time.time()
model_info = model.fit(patches_tr_aug, patches_tr_ref_aug_h, batch_size=batch_size, epochs=100, callbacks=callbacks_list, verbose=2, validation_data= (patches_val_aug, patches_val_ref_aug_h) )
end_training = time.time() - start_time
#%% Test model
# Creation of mask with test tiles
mask_ts_ = np.zeros((mask_tiles.shape))
ts1 = 2
ts2 = 3
ts3 = 4
ts4 = 8
ts5 = 9
ts6 = 10
ts7 = 11
ts8 = 14
ts9 = 15
mask_ts_[mask_tiles == ts1] = 1
mask_ts_[mask_tiles == ts2] = 1
mask_ts_[mask_tiles == ts3] = 1
mask_ts_[mask_tiles == ts4] = 1
mask_ts_[mask_tiles == ts5] = 1
mask_ts_[mask_tiles == ts6] = 1
mask_ts_[mask_tiles == ts7] = 1
mask_ts_[mask_tiles == ts8] = 1
mask_ts_[mask_tiles == ts9] = 1

#% Load model
model = load_model(filepath+'unet_exp_'+str(exp)+'.h5', compile=False)
area = 11
# Prediction
ref_final, pre_final, prob_recontructed, ref_reconstructed, mask_no_considered_, mask_ts, time_ts = prediction(model, image_array, image_ref, final_mask, mask_ts_, patch_size, area)

# Metrics
cm = confusion_matrix(ref_final, pre_final)
metrics = compute_metrics(ref_final, pre_final)
print('Confusion  matrix \n', cm)
print('Accuracy: ', metrics[0])
print('F1score: ', metrics[1])
print('Recall: ', metrics[2])
print('Precision: ', metrics[3])

# Alarm area
total = (cm[1,1]+cm[0,1])/len(ref_final)*100
print('Area to be analyzed',total)

print('training time', end_training)
print('test time', time_ts)

#%% Show the results
# prediction of the whole image
fig1 = plt.figure('whole prediction')
plt.imshow(prob_recontructed)
# Show the test tiles
fig2 = plt.figure('prediction of test set')
plt.imshow(prob_recontructed*mask_ts)
