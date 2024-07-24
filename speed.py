import numpy as np
import torch
import cv2
from pathlib import Path

model = torch.hub.load('ultralytics/yolov5', 'yolov5s')

previous_positions = {}
frame_time = 0.033
speed_threshold = 5
traffic_threshold = 10
meters_per_pixel = 0.05

def calculate_speed(previous_pos, current_pos, frame_time, meters_per_pixel):
    distance_pixels = np.linalg.norm(np.array(current_pos) - np.array(previous_pos))
    distance_meters = distance_pixels * meters_per_pixel
    speed_m_per_sec = distance_meters / frame_time
    speed_km_per_h = speed_m_per_sec * 3.6
    return speed_km_per_h

def process_results(frame_idx, detections, names, im0):
    global previous_positions

    current_positions = {}
    frame_object_detect = []
    traffic_jam_detected = False

    for detection in detections:
        x1, y1, x2, y2, conf, cls = detection
        label = names[int(cls)]
        if label not in current_positions:
            current_positions[label] = []
        x_center = (x1 + x2) / 2
        y_center = (y1 + y2) / 2
        current_positions[label].append((x_center, y_center))

    for label, positions in current_positions.items():
        for idx, current_pos in enumerate(positions):
            object_id = f"{label}_{idx}"
            if object_id in previous_positions:
                speed_km_per_h = calculate_speed(previous_positions[object_id], current_pos, frame_time, meters_per_pixel)
                if speed_km_per_h < 300:
                    print(f"Object ID: {object_id}, Speed: {speed_km_per_h:.2f} km/h")
                    if label == 'car' and speed_km_per_h < speed_threshold and len(positions) > traffic_threshold:
                        traffic_jam_detected = True

    previous_positions = {f"{label}_{idx}": pos for label, pos_list in current_positions.items() for idx, pos in enumerate(pos_list)}

    if traffic_jam_detected:
        cv2.putText(im0, 'Traffic Jam', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

def run(video_path, output_path):
    cap = cv2.VideoCapture(video_path)
    assert cap.isOpened(), "Error reading video file"
    w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

    video_writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    while cap.isOpened():
        success, im0 = cap.read()
        if not success:
            print("Video frame is empty or video processing has been successfully completed.")
            break

        results = model(im0)
        detections = results.xyxy[0].cpu().numpy()

        process_results(None, detections, model.names, im0)

        video_writer.write(im0)

    cap.release()
    video_writer.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    video_path = "highway_short.mp4"
    output_path = "speed_estimation.avi"  
    run(video_path, output_path)
