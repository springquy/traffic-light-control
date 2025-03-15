# NScamera.py
import cv2
import numpy as np
import time
from ultralytics import YOLO

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Open the video file 
cap = cv2.VideoCapture("NScamera.mp4")
if not cap.isOpened():
    print("Cannot open video.")
    exit()

# Set of allowed detection labels
allowed_labels = {"car", "bus", "truck", "motorcycle"}

# Define lane ROI polygons
lane1_polygon = np.array([
    [0, 30],
    [1280, 470],
    [1280, 650],
    [0, 80]
], dtype=np.int32)

lane2_polygon = np.array([
    [0, 90],
    [1280, 650],
    [590, 720],
    [0, 250]
], dtype=np.int32)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Draw lane boundaries on the frame
    cv2.polylines(frame, [lane1_polygon], isClosed=True, color=(0, 255, 255), thickness=2)
    cv2.polylines(frame, [lane2_polygon], isClosed=True, color=(255, 0, 255), thickness=2)

    # Initialize vehicle counts for each lane
    counts_lane1 = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0}
    counts_lane2 = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0}

    # Run inference on the current frame
    start_time = time.time()
    results = model(frame, verbose=False)
    processing_time = time.time() - start_time

    # Process detections and count vehicles in each lane
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            label = model.names[cls_id]

            if label in allowed_labels:
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                in_lane1 = cv2.pointPolygonTest(lane1_polygon, (center_x, center_y), False) >= 0
                in_lane2 = cv2.pointPolygonTest(lane2_polygon, (center_x, center_y), False) >= 0

                if in_lane1 or in_lane2:
                    if in_lane1:
                        counts_lane1[label] += 1
                    if in_lane2:
                        counts_lane2[label] += 1

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Display vehicle counts for each lane on the frame
    text_lane1 = (f"N | Car: {counts_lane1['car']} Bus: {counts_lane1['bus']} "
                  f"Truck: {counts_lane1['truck']} Motorcycle: {counts_lane1['motorcycle']}")
    cv2.putText(frame, text_lane1, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    text_lane2 = (f"S | Car: {counts_lane2['car']} Bus: {counts_lane2['bus']} "
                  f"Truck: {counts_lane2['truck']} Motorcycle: {counts_lane2['motorcycle']}")
    cv2.putText(frame, text_lane2, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Show and write the processed frame
    cv2.imshow("Video", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
