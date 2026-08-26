# Future Live Recognition Pipeline Design

## Current System
Frame → MediaPipe → Random Forest → Prediction

Suitable for static alphabet gestures only.

## Proposed Architecture for Continuous Sign Recognition

### 1. Webcam Stream
- **Responsibility**: Captures continuous video frames from the webcam
- **Input**: Camera device feed
- **Output**: Raw video frames (BGR images)
- **Why needed**: Source of real-time visual data for the entire pipeline

### 2. Frame Capture
- **Responsibility**: Samples frames at a consistent rate (e.g. 30 FPS)
- **Input**: Raw video stream
- **Output**: Individual frames with timestamps
- **Why needed**: Controls the rate of processing to avoid overloading the system

### 3. MediaPipe
- **Responsibility**: Detects hands and extracts 21 landmark points per frame
- **Input**: Single video frame
- **Output**: 21 x 3 landmark coordinates (x, y, z)
- **Why needed**: Converts raw pixels into structured numerical data

### 4. Landmark Extraction
- **Responsibility**: Normalizes and flattens landmarks into a 63-dimensional feature vector
- **Input**: 21 raw landmark coordinates
- **Output**: Normalized 63-value feature vector
- **Why needed**: Ensures position/scale invariance before feeding into any model

### 5. Temporal Buffer
- **Responsibility**: Stores the last N frames of landmark vectors (e.g. N=30)
- **Input**: Single frame feature vector
- **Output**: Sequence of N feature vectors
- **Why needed**: Signs are movements, not single frames. A buffer captures motion over time

### 6. Sequence Generator
- **Responsibility**: Formats the buffered frames into a tensor suitable for sequence models
- **Input**: N x 63 matrix from temporal buffer
- **Output**: Formatted sequence tensor (batch_size, timesteps, features)
- **Why needed**: Sequence models like LSTM require specific input shapes

### 7. Sequence Model (Future: LSTM / GRU / Transformer)
- **Responsibility**: Learns patterns of gesture evolution across time
- **Input**: Sequence tensor (N frames of landmarks)
- **Output**: Probability distribution over gesture classes
- **Why needed**: Static models can't distinguish signs that look similar mid-gesture but differ in motion

### 8. Gesture / Word Prediction
- **Responsibility**: Converts model output to human-readable gesture label
- **Input**: Probability distribution
- **Output**: Predicted sign + confidence score
- **Why needed**: Final classification step

### 9. Sentence Formation
- **Responsibility**: Combines individual sign predictions into meaningful phrases
- **Input**: Stream of gesture predictions
- **Output**: Complete sentences in natural language
- **Why needed**: Real communication requires word sequences, not isolated signs

## Key Difference from Current System
Current system treats each frame independently.
Future system treats gestures as sequences across time — enabling word-level and sentence-level recognition using the WLASL dataset already integrated.