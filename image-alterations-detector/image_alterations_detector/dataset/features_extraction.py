import numpy as np
from keras import models
from scipy.stats import stats
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import normalize
from sklearn.svm import SVC
from tensorflow.python.keras.layers import Dense, Dropout, BatchNormalization

from dataset.dataset_utils import load_altered_dataset
from double_image_features.triangles_measures import compute_mean_triangles_area, compute_mean_centroids_distances, \
    compute_mean_angles_distances, compute_mean_affine_matrices_distances, compute_face_lbp_difference
from face_morphology.face_detection.face_detector import FaceDetector
from face_morphology.landmarks_prediction.landmark_predictor import LandmarkPredictor
from face_morphology.landmarks_triangulation.conversions import triangulation_indexes_to_points
from face_morphology.landmarks_triangulation.delaunay import compute_triangulation_indexes
from face_transform.face_alignment.face_aligner import FaceAligner
from handcrafted_features.local_binary_pattern.local_binary_pattern import LocalBinaryPattern

if __name__ == '__main__':
    dataset_path = '/Users/luca/Desktop/altered'
    mean_area = []
    centroids = []
    angles = []
    matrices = []
    lbps = []

    dataset = []
    labels = []
    genuine, altered = load_altered_dataset(dataset_path)
    genuine_1, genuine_5, genuine_14 = genuine
    beauty_a, beauty_b, beauty_c = altered
    extractor = LandmarkPredictor("../../models/shape_predictor_68_face_landmarks.dat")
    detector = FaceDetector()
    lbp = LocalBinaryPattern(24, 8)
    aligner = FaceAligner(desired_face_width=genuine_1[0].shape[0])
    # Extract indexes from one of the two
    points = extractor.get_2d_landmarks(genuine_1[0])
    triangles_indexes = compute_triangulation_indexes(genuine_1[0], points)
    for idx in range(0, len(genuine_1)):
        img_genuine_1 = genuine_1[idx]
        img_genuine_5 = genuine_5[idx]
        img_genuine_14 = genuine_14[idx]
        img_beauty_a = beauty_a[idx]
        img_beauty_b = beauty_b[idx]
        img_beauty_c = beauty_c[idx]
        # Extract landmark indexes
        img_genuine_1_points = extractor.get_2d_landmarks(img_genuine_1)
        img_genuine_5_points = extractor.get_2d_landmarks(img_genuine_5)
        img_genuine_14_points = extractor.get_2d_landmarks(img_genuine_14)
        img_beauty_a_points = extractor.get_2d_landmarks(img_beauty_a)
        img_beauty_b_points = extractor.get_2d_landmarks(img_beauty_b)
        img_beauty_c_points = extractor.get_2d_landmarks(img_beauty_c)
        # Align face_detection
        img_genuine_1 = aligner.align(img_genuine_1, img_genuine_1_points)
        img_genuine_5 = aligner.align(img_genuine_5, img_genuine_5_points)
        img_genuine_14 = aligner.align(img_genuine_14, img_genuine_14_points)
        img_beauty_a = aligner.align(img_beauty_a, img_beauty_a_points)
        img_beauty_b = aligner.align(img_beauty_b, img_beauty_b_points)
        img_beauty_c = aligner.align(img_beauty_c, img_beauty_c_points)
        # Extract landmark indexes
        img_genuine_1_points = extractor.get_2d_landmarks(img_genuine_1)
        img_genuine_5_points = extractor.get_2d_landmarks(img_genuine_5)
        img_genuine_14_points = extractor.get_2d_landmarks(img_genuine_14)
        img_beauty_a_points = extractor.get_2d_landmarks(img_beauty_a)
        img_beauty_b_points = extractor.get_2d_landmarks(img_beauty_b)
        img_beauty_c_points = extractor.get_2d_landmarks(img_beauty_c)

        # Extract indexes from one of the two
        img_genuine_1_tri_points = triangulation_indexes_to_points(img_genuine_1_points, triangles_indexes)
        img_genuine_5_tri_points = triangulation_indexes_to_points(img_genuine_5_points, triangles_indexes)
        img_genuine_14_tri_points = triangulation_indexes_to_points(img_genuine_14_points,
                                                                    triangles_indexes)
        img_beauty_a_tri_points = triangulation_indexes_to_points(img_beauty_a_points, triangles_indexes)
        img_beauty_b_tri_points = triangulation_indexes_to_points(img_beauty_b_points, triangles_indexes)
        img_beauty_c_tri_points = triangulation_indexes_to_points(img_beauty_c_points, triangles_indexes)

        # Compute area
        mean_area_difference1_14 = compute_mean_triangles_area(img_genuine_1_tri_points, img_genuine_14_tri_points)
        mean_area_difference1_5 = compute_mean_triangles_area(img_genuine_1_tri_points, img_genuine_5_tri_points)
        mean_area_difference1_a = compute_mean_triangles_area(img_genuine_1_tri_points, img_beauty_a_tri_points)
        mean_area_difference1_b = compute_mean_triangles_area(img_genuine_1_tri_points, img_beauty_b_tri_points)
        mean_area_difference1_c = compute_mean_triangles_area(img_genuine_1_tri_points, img_beauty_c_tri_points)

        mean_area.extend(
            [mean_area_difference1_14, mean_area_difference1_5, mean_area_difference1_a, mean_area_difference1_b,
             mean_area_difference1_c])

        # Compute centroid
        centroid_distances1_14 = compute_mean_centroids_distances(img_genuine_1_tri_points, img_genuine_14_tri_points)
        centroid_distances1_5 = compute_mean_centroids_distances(img_genuine_1_tri_points, img_genuine_5_tri_points)
        centroid_distances1_a = compute_mean_centroids_distances(img_genuine_1_tri_points, img_beauty_a_tri_points)
        centroid_distances1_b = compute_mean_centroids_distances(img_genuine_1_tri_points, img_beauty_b_tri_points)
        centroid_distances1_c = compute_mean_centroids_distances(img_genuine_1_tri_points, img_beauty_c_tri_points)

        centroids.extend(
            [centroid_distances1_14, centroid_distances1_5, centroid_distances1_a, centroid_distances1_b,
             centroid_distances1_c])

        # Compute cosine similarity
        angles_distances1_14 = compute_mean_angles_distances(img_genuine_1_tri_points, img_genuine_14_tri_points)
        angles_distances1_5 = compute_mean_angles_distances(img_genuine_1_tri_points, img_genuine_5_tri_points)
        angles_distances1_a = compute_mean_angles_distances(img_genuine_1_tri_points, img_beauty_a_tri_points)
        angles_distances1_b = compute_mean_angles_distances(img_genuine_1_tri_points, img_beauty_b_tri_points)
        angles_distances1_c = compute_mean_angles_distances(img_genuine_1_tri_points, img_beauty_c_tri_points)

        angles.extend(
            [angles_distances1_14, angles_distances1_5, angles_distances1_a, angles_distances1_b,
             angles_distances1_c])

        # Matrix distances
        affine_matrices_distances1_14 = compute_mean_affine_matrices_distances(img_genuine_1_tri_points,
                                                                               img_genuine_14_tri_points)
        affine_matrices_distances1_5 = compute_mean_affine_matrices_distances(img_genuine_1_tri_points,
                                                                              img_genuine_5_tri_points)
        affine_matrices_distances1_a = compute_mean_affine_matrices_distances(img_genuine_1_tri_points,
                                                                              img_beauty_a_tri_points)
        affine_matrices_distances1_b = compute_mean_affine_matrices_distances(img_genuine_1_tri_points,
                                                                              img_beauty_b_tri_points)
        affine_matrices_distances1_c = compute_mean_affine_matrices_distances(img_genuine_1_tri_points,
                                                                              img_beauty_c_tri_points)
        matrices.extend(
            [affine_matrices_distances1_14, affine_matrices_distances1_5, affine_matrices_distances1_a,
             affine_matrices_distances1_b,
             affine_matrices_distances1_c])

        # LBP
        lbp_features1_14 = compute_face_lbp_difference(img_genuine_1, img_genuine_14, detector, lbp)
        lbp_features1_5 = compute_face_lbp_difference(img_genuine_1, img_genuine_5, detector, lbp)
        lbp_features1_a = compute_face_lbp_difference(img_genuine_1, img_beauty_a, detector, lbp)
        lbp_features1_b = compute_face_lbp_difference(img_genuine_1, img_beauty_b, detector, lbp)
        lbp_features1_c = compute_face_lbp_difference(img_genuine_1, img_beauty_c, detector, lbp)

        lbps.extend([lbp_features1_14, lbp_features1_5, lbp_features1_a, lbp_features1_b, lbp_features1_c])

        labels.extend([0, 0, 1, 1, 1])

    mean_area = np.array(mean_area).astype('float32')
    centroids = np.array(centroids).astype('float32')
    angles = np.array(angles).astype('float32')
    matrices = np.array(matrices).astype('float32')
    lbps = np.array(lbps).astype('float32')

    # Normalize
    mean_area = normalize(mean_area, norm='max')
    centroids = normalize(centroids, norm='max')
    angles = normalize(angles, norm='max')
    matrices = normalize(matrices, norm='max')
    # lbps = normalize(lbps, norm='max')

    dataset = np.column_stack([mean_area, matrices])
    labels = np.array(labels)

    print(mean_area.shape, centroids.shape, angles.shape, matrices.shape, lbps.shape)

    x_train_mean_area, x_test_mean_area, y_train_mean_area, y_test_mean_area = train_test_split(lbps, labels,
                                                                                                test_size=0.2,
                                                                                                random_state=23)
    x_train_matrices, x_test_matrices, y_train_matrices, y_test_matrices = train_test_split(matrices, labels,
                                                                                            test_size=0.2,
                                                                                            random_state=23)

    # Multi-classifier
    svm_mean_area = SVC(C=1, kernel='linear')
    rf_mean_area = RandomForestClassifier(max_depth=7, random_state=0)  # 7

    multi_mean_area = VotingClassifier(estimators=[
        ('svm', svm_mean_area), ('rf', rf_mean_area)],
        voting='hard', weights=[1, 1],
        flatten_transform=True, n_jobs=-1)
    multi_mean_area.fit(x_train_mean_area, y_train_mean_area)
    predicted_mean_area = multi_mean_area.predict(x_test_mean_area)
    print("SVM/RF mean area accuracy score:", accuracy_score(y_test_mean_area, predicted_mean_area))

    svm_matrices = SVC(C=1, kernel='linear')
    rf_matrices = RandomForestClassifier(max_depth=7, random_state=0)  # 7

    multi_matrices = VotingClassifier(estimators=[
        ('svm', svm_matrices), ('rf', rf_matrices)],
        voting='hard', weights=[1, 1],
        flatten_transform=True, n_jobs=-1)
    multi_matrices.fit(x_train_matrices, y_train_matrices)
    predicted_matrices = multi_matrices.predict(x_test_matrices)
    print("SVM/RF matrices accuracy score:", accuracy_score(y_test_matrices, predicted_matrices))

    print("\nFINAL EVALUATION")
    mean_area_matrices_predicted = np.column_stack((predicted_mean_area, predicted_matrices))
    mean_area_matrices_predicted = stats.mode(mean_area_matrices_predicted, axis=1)[0]
    print("\nMulti classifier accuracy score:", accuracy_score(y_test_mean_area, mean_area_matrices_predicted))

    print("Testing keras")
    # Configuration options
    feature_vector_length = 678
    # y_train = to_categorical(y_train_matrices, 1)
    # y_test = to_categorical(y_test_matrices, 1)
    # Set the input shape
    input_shape = (feature_vector_length,)
    print(f'Feature shape: {input_shape}')
    # Create the model
    model = models.Sequential()
    model.add(Dense(350, input_shape=input_shape))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))

    model.add(Dense(100, activation='tanh'))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))

    model.add(Dense(10, activation='tanh'))
    model.add(BatchNormalization())
    model.add(Dropout(0.2))

    model.add(Dense(1, activation='sigmoid'))
    # Configure the model and start training
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    model.fit(x_train_matrices, y_train_matrices, epochs=200, batch_size=128, verbose=1, validation_split=0.2)
    # Test the model after training
    test_results = model.evaluate(x_test_matrices, y_test_matrices, verbose=1)
    print(f'Test results - Loss: {test_results[0]} - Accuracy: {test_results[1]}')