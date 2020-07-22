import math
import numpy as np
import cv2
from utils.trackableobject import TrackableObject

def track_objects(objects, trackableObjects, orientation, coord, inDirection):

	totals = [0,0]

	for (objectID, centroid) in objects.items():
			
		to = trackableObjects.get(objectID, None)
						
		if to is None:
			to = TrackableObject(objectID, centroid)
			
		else:
			
			x = [c[0] for c in to.centroids]
			y = [c[1] for c in to.centroids]
			delta_x = centroid[0] - np.mean(x)
			delta_y = centroid[1] - np.mean(y)
			
			to.centroids.append(centroid)	

			# check to see if the object has been counted or not
			# store total in total in total[0]
			if not to.counted:				
				if orientation == "H":
					if inDirection == "UP":
						if delta_y < 0 and centroid[1] < coord:
							totals[0] += 1
							to.counted = True
						elif delta_y > 0 and centroid[1] > coord:
							totals[1] += 1
							to.counted = True
					elif inDirection == "DOWN":
						if delta_y < 0 and centroid[1] < coord:
							totals[1] += 1
							to.counted = True
						elif delta_y > 0 and centroid[1] > coord:
							totals[0] += 1
							to.counted = True

				if orientation == "V":
					if inDirection == "LEFT":
						if delta_x < 0 and centroid[0] < coord:
							totals[0] += 1
							to.counted = True
						elif delta_x > 0 and centroid[0] > coord:
							totals[1] += 1	
							to.counted = True
					if inDirection == "RIGHT":
						if delta_x < 0 and centroid[0] < coord:
							totals[1] += 1
							to.counted = True
						elif delta_x > 0 and centroid[0] > coord:
							totals[0] += 1	
							to.counted = True
	
		# store the trackable object in our dictionary
		trackableObjects[objectID] = to
	
	return trackableObjects, totals

def draw_bounding_boxes(obj, labels, frame, rects):

	label_text_color = (255, 255, 255)

	box = obj.bounding_box.flatten().tolist()
	box_left, box_top,   = int(box[0]), int(box[1]) 
	box_right, box_bottom = int(box[2]), int(box[3])
	
	#Set bounding box colour:
	if obj.label_id == 0:
		box_color = (0, 0, 255)
	elif obj.label_id == 1:
		box_color = (0, 255, 0)
	
	cv2.rectangle(frame, (box_left, box_top),
								(box_right, box_bottom), box_color, 1)

	label_text = labels[obj.label_id]
	
	label_size = cv2.getTextSize(
		label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
	label_left = box_left
	
	label_top = box_top - label_size[1]
	
	if (label_top < 1):
		label_top = 1
	label_right = label_left + label_size[0]
	label_bottom = label_top + label_size[1]
	cv2.rectangle(frame, (label_left - 1, label_top - 1),
				(label_right + 1, label_bottom + 1), box_color, -1)
	cv2.putText(frame, label_text, (label_left, label_bottom),
				cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_text_color, 1)

	
	rects.append((box_left, box_top, box_right, box_bottom))
	
	return rects, frame