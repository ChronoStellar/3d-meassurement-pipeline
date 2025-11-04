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

def measure_json(model_path):
    """
    Loads a .ply mesh, calculates body measurements, and returns a JSON string.
    """
    print(f"\n--- 3. MEASURING BODY from: {model_path} ---")
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

    # Return the JSON string for the API
    return json_str

def pkl2ply(pkl_path):
    """
    Converts a VIBE .pkl output file to a .ply mesh.
    Saves the .ply in the same directory as the .pkl and returns the path.
    """
    print(f"\n--- 2. CONVERTING PKL TO PLY: {pkl_path} ---")
    smpl_model_path = 'data/vibe_data'
    
    # Save the .ply file in the *same folder* as the .pkl file
    # This keeps results grouped by video
    output_ply_path = os.path.join(os.path.dirname(pkl_path), "result.ply")
    
    os.makedirs(os.path.dirname(output_ply_path), exist_ok=True)

    try:
        output = joblib.load(pkl_path)
        person_ids = list(output.keys())
        if not person_ids:
            print(f"Error: No people found in pkl file: {pkl_path}")
            return None
            
        first_person_id = person_ids[0]
        print(f"Extracting data for person ID: {first_person_id}")
        
        all_vertices = output[first_person_id]['verts']
    except Exception as e:
        print(f"Error loading {pkl_path}: {e}. Is it a VIBE pkl file?")
        print("Attempting to load as list (legacy format)...")
        try:
            output = joblib.load(pkl_path)
            all_vertices = output[1]['verts'] # Try original structure
        except Exception as e2:
            print(f"Legacy load failed: {e2}")
            return None

    frame_idx = 0 # Use the first frame
    vertices = all_vertices[frame_idx]
    print(f"Loaded vertices for frame {frame_idx}. Shape: {vertices.shape}")

    model = smplx.SMPL(smpl_model_path)
    faces = model.faces
    print(f"Loaded SMPL faces. Shape: {faces.shape}")

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.export(output_ply_path)

    print(f"Successfully saved {output_ply_path}")
    # Return the path to the new .ply file
    return output_ply_path


def process_video_endpoint(video_path):
    """
    Runs VIBE on a video and returns the path to the output .pkl file.
    """
    print(f"\n--- 1. STARTING VIBE PROCESSING for {video_path} ---")
    # video_name = os.path.basename(video_path).split('.')[0] # No longer needed for path
    output_folder = 'output' 
    
    # This is the new, simplified path you requested
    result_path = os.path.join(output_folder, "vibe_output.pkl")

    run_vibe(
        vid_file=video_path,
        output_folder=output_folder, 
        run_smplify=True,
        smooth=True,
        no_render=True
    )
    
    if os.path.exists(result_path):
        print(f"--- VIBE SUCCESS. Output saved to: {result_path} ---")
        return {"status": "success", "result_file": result_path}
    else:
        print(f"--- VIBE FAILED. Expected file not found at: {result_path} ---")
        return {"status": "error", "message": f"Processing failed. Expected file not found at: {result_path}"}

# ===================================================================
# =================== MAIN API FUNCTION =============================
# ===================================================================

def run_full_pipeline(input_video_path):
    """
    This is the main function your API will call.
    It takes a video file path, runs the full process, and returns
    a dictionary with the final measurements or an error.
    """
    
    # --- STAGE 1: Process Video (Video -> PKL) ---
    vibe_results = process_video_endpoint(input_video_path)
    
    if vibe_results['status'] == 'error':
        return vibe_results # Pass the error dictionary up
    
    # Use the path returned from the previous step
    pkl_file = vibe_results['result_file']
    
    # --- STAGE 2: Convert PKL to PLY (PKL -> PLY) ---
    ply_file_path = pkl2ply(pkl_file)
    
    if ply_file_path is None:
        return {"status": "error", "message": "Failed to convert PKL to PLY"}
    
    # --- STAGE 3: Measure Body (PLY -> JSON) ---
    try:
        json_measurements = measure_json(ply_file_path)
        print(f"\n--- 4. FULL PROCESS COMPLETE ---")
        return {"status": "success", "data": json_measurements}
    except Exception as e:
        print(f"Error during measurement: {e}")
        return {"status": "error", "message": f"Failed during measurement: {e}"}


# --- This block is for testing your script directly ---
if __name__ == '__main__':
    
    # You can change this path to test different videos
    video_to_process = "./sample_video.mp4" 
    
    if os.path.exists(video_to_process):
        
        # Call the main API-ready function
        final_result = run_full_pipeline(video_to_process)
        
        print("\n================= FINAL RESULT =================")
        print(final_result)
        print("================================================")
        
    else:
        print(f"--- FAILED: Test video not found at: {video_to_process} ---")