from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from collections import defaultdict, Counter

import numpy as np
import cv2
import os
import gc
import math
import asyncio

import time

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
  allow_credentials=True
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def health():
  print("Health Checked")
  return { "status": "ok" }

@app.post("/core-helper/")
async def core_helper(images: list[UploadFile] = File(...), selected_job_class: str = Form(...)):
  try:
    processed = await asyncio.wait_for(process(images, selected_job_class), timeout=300.0)
    if processed.get("message") is not None:
      return JSONResponse(content={
          "success": processed.get("success", False),
          "message": processed.get("message", "")
      })
    elif processed.get("core_skill_names") is not None:
      return JSONResponse(content={
          "success": processed.get("success", False),
          "core_skill_names": processed.get("core_skill_names", [])
      })
  except asyncio.TimeoutError:
    return JSONResponse(status_code=500, content={
      "success": False,
      "message": "요청 시간이 초과되었어요.\n같은 현상이 반복되면 관리자에게 문의해 주세요."
    })
  except Exception as e:
    import traceback
    traceback.print_exc()

    return JSONResponse(status_code=500, content={
      "success": False,
      "message": "서버에 오류가 발생했어요.\n같은 현상이 반복되면 관리자에게 문의해 주세요."
    })

async def process(images: list[UploadFile] = File(...), selected_job_class: str = Form(...)):
  start_time = time.time()
  print(f"요청 - 직업: [{selected_job_class}], 이미지: [{len(images)}]")

  # 경로 설정
  base_path = "static"
  job_class_path = os.path.join(base_path, "skills", selected_job_class)
  skills = get_job_skills(job_class_path)

  icons = []
  upper_color = [180, 255, 35]
  for image in images:
    content = await image.read()
    np_img = np.frombuffer(content, np.uint8)
    display = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    if display is None:
      continue

    cores = find_core_candidates(display, color=upper_color)
    # print(f"cores: {len(cores)}")
    if not cores:
      continue

    enhanced_cores = filter_enhanced_core_candidates(cores)
    # print(f"enhanced_cores: {len(enhanced_cores)}")
    if not enhanced_cores:
      continue

    core_icons = extract_core_icon_candidates(enhanced_cores, color=upper_color)
    # print(f"core_icons: {len(core_icons)}")
    if not core_icons:
      continue

    valid_core_icons = filter_valid_core_icons(core_icons, color=upper_color)
    # print(f"valid_core_icons: {len(valid_core_icons)}")
    if valid_core_icons:
      icons.extend(valid_core_icons)

    del cores
    del enhanced_cores
    del core_icons
    del valid_core_icons
    del content
    del np_img
    del display
    gc.collect()
  find_cores = time.time()
  print(f"경과 시간[코어 탐색]: {find_cores - start_time:.3f}초, 탐색된 코어: {len(icons)}개")

  detected_cores = []
  for icon in icons:
    detected_skill_names = analyze_icon(icon, skills)
    if detected_skill_names:
      detected_cores.append(detected_skill_names)
  analyze_cores = time.time()
  print(f"경과 시간[코어 분석]: {analyze_cores - find_cores:.3f}초, 분석된 코어: {len(detected_cores)}개")
  print(f"소요 시간: {analyze_cores - start_time:.3f}초")

  if not icons and not detected_cores:
    return {
      "success": False,
      "message": "이미지 화질이 낮아 코어 인식이 어려워요.\n게임 내 그래픽 설정을 높인 뒤 다시 시도해 주세요."
    }
  elif not detected_cores:
    return {
      "success": False,
      "message": "코어가 분석되지 않았어요.\n게임 내 그래픽 설정을 높인 뒤 다시 시도해 주세요."
    }
  else:
    return {
      "success": True,
      "core_skill_names": detected_cores
    }

def get_job_skills(job_class_path):
  skills = []
  for file_name in os.listdir(job_class_path):
    if file_name.lower().endswith(".png"):
      path = os.path.join(job_class_path, file_name)
      icon = cv2.imread(path)
      outlined_icon = outline_icon(icon)
      name = file_name[:-4]
      skills.append({"icon": outlined_icon, "name": name})
  return skills

def split_grouping_targets(contours):
  grouping_targets = []
  standalone_targets = []

  for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    area = w * h

    if area < 24:
      continue
    elif len(c) < 2:
      continue

    aspect_ratio = float(w) / h if h != 0 else 0

    if 0.8 <= aspect_ratio <= 1.2:
      standalone_targets.append(c)
    else:
      grouping_targets.append(c)
  return grouping_targets, standalone_targets

def get_center(rect):
  x, y, w, h = rect
  return (x + w/2, y + h/2)

def group_nearby_contours(contours, threshold=70):
  rects = [cv2.boundingRect(c) for c in contours]
  centers = [get_center(r) for r in rects]
  used = [False] * len(contours)
  groups = []

  for i in range(len(contours)):
    if used[i]:
      continue
    group = [contours[i]]
    used[i] = True
    for j in range(i+1, len(contours)):
      if used[j]:
        continue
      dist = np.linalg.norm(np.array(centers[i]) - np.array(centers[j]))
      if dist < threshold:
        group.append(contours[j])
        used[j] = True
    groups.append(group)
  return groups

def is_reasonable_box(x, y, w, h, min_area=250, aspect_range=(0.8, 1.2)):
  if w * h < min_area:
    return False
  aspect_ratio = float(w) / h if h != 0 else 0
  return aspect_range[0] <= aspect_ratio <= aspect_range[1]

def find_core_candidates(display, color=[180, 255, 50]):
  lower_color = np.array([0, 0, 0])
  upper_color = np.array(color)

  hsv = cv2.cvtColor(display, cv2.COLOR_BGR2HSV)
  smoothed = cv2.bilateralFilter(hsv, d=5, sigmaColor=10, sigmaSpace=10)
  masked = cv2.inRange(smoothed, lower_color, upper_color)
  contours, _ = cv2.findContours(masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  if not contours:
    return []

  core_candidates = []
  padding = 20
  height, width = display.shape[:2]

  grouping_targets, standalone_targets = split_grouping_targets(contours)
  groups = group_nearby_contours(grouping_targets)

  contour_groups = [group for group in groups if len(group) > 0] + [[c] for c in standalone_targets]

  for group in contour_groups:
    merged = np.vstack(group)
    x, y, w, h = cv2.boundingRect(merged)

    if not is_reasonable_box(x, y, w, h):
      continue

    # 패딩 포함 영역 계산
    x1 = max(x - padding, 0)
    y1 = max(y - padding, 0)
    x2 = min(x + w + padding, width)
    y2 = min(y + h + padding, height)

    crop = display[y1:y2, x1:x2]
    core_candidates.append(crop)

  return core_candidates

def filter_enhanced_core_candidates(cores):
  lower_color = np.array([0, 0, 0])
  upper_color = np.array([94, 115, 113])

  enhanced_core_candidates = []
  for core in cores:
    masked = cv2.inRange(core, lower_color, upper_color)

    h, w = masked.shape
    x = w // 6
    y = (h // 2) - 5

    # 강화코어 후보(흰색 많음)
    counter = Counter()
    for i in range(10):
      counter[f"{masked[y+i, x]}"] += 1
    if counter['255'] > counter['0']:
      enhanced_core_candidates.append(core)
  return enhanced_core_candidates

def extract_core_icon_candidates(cores, color=[180, 255, 50]):
  size = 32

  lower_color = np.array([0, 0, 0])
  upper_color = np.array(color)

  core_icon_candidates = []
  for core in cores:
    hsv = cv2.cvtColor(core, cv2.COLOR_BGR2HSV)
    smoothed = cv2.bilateralFilter(hsv, d=5, sigmaColor=10, sigmaSpace=10)
    masked = cv2.inRange(smoothed, lower_color, upper_color)

    contours, _ = cv2.findContours(masked, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
      continue

    grouping_targets, standalone_targets = split_grouping_targets(contours)
    groups = group_nearby_contours(grouping_targets)

    contour_groups = [group for group in groups if len(group) > 0] + [[c] for c in standalone_targets]

    best_crop = None
    best_area = 0
    for group in contour_groups:
      merged = np.vstack(group)
      x, y, w, h = cv2.boundingRect(merged)

      if not is_reasonable_box(x, y, w, h):
        continue

      area = w * h
      if area > best_area:
        best_area = area
        best_crop = core[y:y+h, x:x+w]
    if best_crop is not None:
      best_crop = cv2.resize(best_crop, (size, size))
      core_icon_candidates.append(best_crop)
  return core_icon_candidates

def filter_valid_core_icons(icons, color=[180, 255, 50]):
  lower_color = np.array([0, 0, 0])
  upper_color = np.array(color)

  core_icons = []
  for icon in icons:
    hsv = cv2.cvtColor(icon, cv2.COLOR_BGR2HSV)
    smoothed = cv2.bilateralFilter(hsv, d=9, sigmaColor=20, sigmaSpace=20)
    masked = cv2.inRange(smoothed, lower_color, upper_color)
    edges = np.concatenate([masked[0, :], masked[-1, :], masked[:, 0], masked[:, -1]])

    # 스킬 후보(모서리에 흰색이 42 ~ 124)
    counter = Counter()
    counter.update(map(str, edges))
    if 42 <= counter["255"] <= 124:
      core_icons.append(icon)
  return core_icons

def outline_icon(icon):
  size = 32
  icon = cv2.resize(icon, (size, size))

  outer_color = [221, 221, 204]
  inner_color = [255, 255, 255]
  border_color = [0, 0, 0]

  def draw_horizontal(y, color):
    icon[y, 1:31] = color

  def draw_vertical(x, color):
    icon[2:30, x] = color

  # 바깥 테두리
  draw_horizontal(1, outer_color)   # 위
  draw_horizontal(30, outer_color)  # 아래

  # 안쪽 테두리
  draw_horizontal(2, inner_color)   # 위
  draw_horizontal(29, inner_color)  # 아래

  # 바깥 테두리
  draw_vertical(1, outer_color)     # 왼쪽
  draw_vertical(30, outer_color)    # 오른쪽

  # 안쪽 테두리
  draw_vertical(2, inner_color)     # 왼쪽
  draw_vertical(29, inner_color)    # 오른쪽

  # 외곽 경계선
  icon[0, 0:32] = border_color       # 최상단
  icon[31, 0:32] = border_color      # 최하단
  icon[0:32, 0] = border_color       # 최좌측
  icon[0:32, 31] = border_color      # 최우측

  return icon

def split_icon(icon):
  size = 32
  icon = cv2.resize(icon, (size, size))

  triangle_mask = np.zeros((size, size), dtype=np.uint8)
  pts = np.array([[0, 0], [31, 0], [16, 16]], np.int32)
  pts = pts.reshape((-1, 1, 2))
  cv2.fillPoly(triangle_mask, [pts], 255)

  canvas1, canvas2, canvas3 = (np.zeros_like(icon) for _ in range(3))
  for y in range(size):
    for x in range(size):
      if triangle_mask[y, x] == 0:
        (canvas1 if x < 16 else canvas3)[y, x] = icon[y, x]
  canvas2 = np.where(triangle_mask == 255, icon, canvas2)
  return [canvas1, canvas2, canvas3]

def merge_icon_parts(parts):
  size = 32

  triangle_mask = np.zeros((size, size), dtype=np.uint8)
  pts = np.array([[0, 0], [31, 0], [16, 16]], np.int32)
  pts = pts.reshape((-1, 1, 2))
  cv2.fillPoly(triangle_mask, [pts], 255)

  canvas = np.zeros_like(parts[0])
  for y in range(size):
    for x in range(size):
      if triangle_mask[y, x] == 0:
        (canvas if x < 16 else canvas)[y, x] = (parts[0] if x < 16 else parts[2])[y, x]
  for center in range(3):
    canvas[:, :, center] = np.where(triangle_mask == 255, parts[1][:, :, center], canvas[:, :, center])
  return canvas

def mask_icon(sample, icon):
  mask = sample != 0
  canvas = np.zeros_like(sample)
  canvas[mask] = icon[mask]
  return canvas

def analyze_icon(icon, skills):
  gray_icon = cv2.cvtColor(icon, cv2.COLOR_BGR2GRAY)
  icon_parts = split_icon(gray_icon)
  matched_skills = []
  for icon_part in icon_parts:
    match_results = []
    for skill in skills:
      if matched_skills:
        skill_names = [skill["name"] for skill in matched_skills]
        if skill["name"] in skill_names:
          continue
      gray_skill = cv2.cvtColor(skill["icon"], cv2.COLOR_BGR2GRAY)
      masked = mask_icon(icon_part, gray_skill)
      result = cv2.matchTemplate(icon_part, masked, cv2.TM_CCOEFF_NORMED)
      _, max_val, _, _ = cv2.minMaxLoc(result)
      match_results.append({"score": max_val, "skill": skill})
      del result
    skills = [result["skill"] for result in match_results]
    scores = [result["score"] for result in match_results]
    max_score = max(scores)
    if max_score < 0.625:
      return []

    max_score_index = scores.index(max_score)
    matched_skills.append(skills[max_score_index])
    del match_results
  
  skill_parts = [skill["icon"] for skill in matched_skills]
  skill_names = [skill["name"] for skill in matched_skills]
  merged_icon = merge_icon_parts(skill_parts)
  outlined_icon = outline_icon(merged_icon)

  result = cv2.matchTemplate(icon, outlined_icon, cv2.TM_CCOEFF_NORMED)
  _, max_val, _, _ = cv2.minMaxLoc(result)

  detected_skill_names = skill_names if max_val > 0.625 else []
  del result

  gc.collect()
  return detected_skill_names