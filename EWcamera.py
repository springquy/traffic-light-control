# EWcamera.py
import cv2
import numpy as np
import time
from ultralytics import YOLO

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Open video source
cap = cv2.VideoCapture("EWcamera.mp4")
if not cap.isOpened():
    print("Cannot open video.")
    exit()

# Allowed detection labels
allowed_labels = {"car", "bus", "truck", "motorcycle"}

# Define lane boundary polygons (ROI)
lane1_polygon = np.array([
    [0, 150],
    [1280, 420],
    [1280, 650],
    [0, 260]
], dtype=np.int32)

lane2_polygon = np.array([
    [0, 220],
    [1280, 620],
    [400, 700],
    [0, 420]
], dtype=np.int32)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Draw lane ROI boundaries
    cv2.polylines(frame, [lane1_polygon], isClosed=True, color=(0, 255, 255), thickness=2)
    cv2.polylines(frame, [lane2_polygon], isClosed=True, color=(255, 0, 255), thickness=2)

    # Initialize vehicle counts for each lane
    counts_lane1 = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0}
    counts_lane2 = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0}

    # Perform inference on the current frame
    start_time = time.time()
    results = model(frame, verbose=False)
    processing_time = time.time() - start_time

    # Process detection results
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            label = model.names[cls_id]

            if label in allowed_labels:
                # Calculate the center of the bounding box
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                # Count vehicle if its center lies inside one of the lane polygons
                if cv2.pointPolygonTest(lane1_polygon, (center_x, center_y), False) >= 0:
                    counts_lane1[label] += 1
                elif cv2.pointPolygonTest(lane2_polygon, (center_x, center_y), False) >= 0:
                    counts_lane2[label] += 1

                # Draw bounding box and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Display vehicle counts on the frame
    text_lane1 = (f"E | Car: {counts_lane1['car']}  Bus: {counts_lane1['bus']}  "
                  f"Truck: {counts_lane1['truck']}  Motorcycle: {counts_lane1['motorcycle']}")
    cv2.putText(frame, text_lane1, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    text_lane2 = (f"W | Car: {counts_lane2['car']}  Bus: {counts_lane2['bus']}  "
                  f"Truck: {counts_lane2['truck']}  Motorcycle: {counts_lane2['motorcycle']}")
    cv2.putText(frame, text_lane2, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Show and save the processed frame
    cv2.imshow("East-West Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
