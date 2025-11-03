import sys, os
import torch
import trimesh
import numpy as np
import smplx
import joblib
import json
from measure import MeasureBody
from measurement_definitions import STANDARD_LABELS
from VIBE import run_vibe

def measure_json(model_path = 'output/result.ply'):
    mesh = trimesh.load(model_path, force='mesh')
    verts_np = np.array(mesh.vertices, dtype=np.float32)

    n_verts = verts_np.shape[0]
    if n_verts == 6890:
        model_type = 'smpl'
    elif n_verts == 10475:
        model_type = 'smplx'
    else:
        raise ValueError(f'Unexpected vertex count {n_verts}.')

    measurer = MeasureBody(model_type)
    measurer.from_verts(verts=torch.from_numpy(verts_np))

    measurer.measure(measurer.all_possible_measurements)
    measurer.label_measurements(STANDARD_LABELS)

    print('\n=== LABELLED MEASUREMENTS (cm) ===')
    for label, val in measurer.labeled_measurements.items():
        print(f'{label}: {val:.2f} cm')

    def _get(name: str):
        if name not in measurer.measurements:
            raise KeyError(f"Measurement '{name}' not computed.")
        val = measurer.measurements[name]
        return float(round(val, 2))

    arm_left  = _get("arm left length")
    arm_right = _get("arm right length")
    arms_avg  = round((arm_left + arm_right) / 2.0, 2)

    payload = {
        "height":               round(_get("height"),0),
        "chest_circumference":  round(_get("chest circumference"),0),
        "waist_circumference":  round(_get("waist circumference"),0),
        "torso_length":         round(_get("torso back length"),0),
        "arms_length":          arms_avg
    }

    json_str = json.dumps(payload, indent=2)
    print("\n=== JSON OUTPUT ===")
    print(json_str)

    return json_str

def pkl2ply(file):
    pkl_path = file

    smpl_model_path = 'data/vibe_data'

    output_ply_path = 'output/result.ply'
    os.makedirs(os.path.dirname(output_ply_path), exist_ok=True)

    output = joblib.load(pkl_path)

    all_vertices = output[1]['verts']

    frame_idx = 0
    vertices = all_vertices[frame_idx]
    print(f"Loaded vertices for frame {frame_idx}. Shape: {vertices.shape}")

    model = smplx.SMPL(smpl_model_path)
    faces = model.faces
    print(f"Loaded SMPL faces. Shape: {faces.shape}")

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    mesh.export(output_ply_path)

    print(f"Successfully saved {output_ply_path}")

def process_video_endpoint(video_path):
    video_name = os.path.basename(video_path).split('.')[0]
    output_dir = f"./vibe_results/{video_name}_output"

    run_vibe(
        vid_file=video_path,
        output_folder='output',
        tracking_method='pose', 
        run_smplify=True,
        smooth=True,
        no_render=True
    )
    
    result_path = os.path.join(output_dir, "vibe_output.pkl")
    
    if os.path.exists(result_path):
        return {"status": "success", "result_file": result_path}
    else:
        return {"status": "error", "message": "Processing failed"}

# --- Example Usage ---
# if __name__ == '__main__':
    # This simulates an API call
    # video_to_process = "path/to/your/video.mp4"
    # if os.path.exists(video_to_process):
    #     results = process_video_endpoint(video_to_process)
    #     print(results)
    # else:
        # print(f"Video file not found: {video_to_process}")