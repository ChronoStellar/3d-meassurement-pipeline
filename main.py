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

# <-- *** MODIFICATION 1 *** -->
# Renamed from pkl2ply to results_to_ply
# Now accepts the vibe_data dictionary and output_folder directly
def results_to_ply(vibe_data: dict, output_folder: str):
    """
    Converts a VIBE results dictionary to a .ply mesh.
    Saves the .ply in the specified output_folder and returns the path.
    """
    print(f"\n--- 2. CONVERTING VIBE data TO PLY ---")
    smpl_model_path = 'data/vibe_data'
    
    # Save the .ply file in the output folder
    output_ply_path = os.path.join(output_folder, "result.ply")
    os.makedirs(output_folder, exist_ok=True)

    try:
        # The data is already a dictionary, no joblib.load needed
        output = vibe_data
        person_ids = list(output.keys())
        if not person_ids:
            print(f"Error: No people found in vibe_data dictionary")
            return None
            
        first_person_id = person_ids[0]
        print(f"Extracting data for person ID: {first_person_id}")
        
        all_vertices = output[first_person_id]['verts']
    except Exception as e:
        print(f"Error reading vibe_data dictionary: {e}.")
        print("Attempting to load as list (legacy format)...")
        try:
            # Legacy format check (just in case, though vibe_data is dict)
            all_vertices = vibe_data[1]['verts']
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


# <-- *** MODIFICATION 2 *** -->
# Updated to capture the returned dictionary from run_vibe
def process_video_endpoint(video_path):
    """
    Runs VIBE on a video and returns the path to the output .pkl file.
    """
    print(f"\n--- 1. STARTING VIBE PROCESSING for {video_path} ---")
    output_folder = 'output' 
    
    # This path is still used by VIBE to save the .pkl, but
    # we won't use it for loading anymore.
    pkl_save_path = os.path.join(output_folder, "vibe_output.pkl")

    # Run VIBE and get the results dictionary directly
    vibe_data = run_vibe(
        vid_file=video_path,
        output_folder=output_folder, 
        run_smplify=True,
        smooth=True,
        no_render=True
    )
    
    # Check if data was returned, not if a file exists
    if vibe_data:
        print(f"--- VIBE SUCCESS. Results returned in-memory. ---")
        # Return the data dictionary and the folder path for saving the .ply
        return {"status": "success", "data": vibe_data, "output_folder": output_folder}
    else:
        print(f"--- VIBE FAILED. No data returned from run_vibe. ---")
        return {"status": "error", "message": f"Processing failed. VIBE returned no data."}

# ===================================================================
# =================== MAIN API FUNCTION =============================
# ===================================================================

# <-- *** MODIFICATION 3 *** -->
# Updated to handle the new return value from process_video_endpoint
# and call the new results_to_ply function
def run_full_pipeline(input_video_path):
    """
    This is the main function your API will call.
    It takes a video file path, runs the full process, and returns
    a dictionary with the final measurements or an error.
    """
    
    # --- STAGE 1: Process Video (Video -> VIBE data dict) ---
    vibe_results = process_video_endpoint(input_video_path)
    
    if vibe_results['status'] == 'error':
        return vibe_results # Pass the error dictionary up
    
    # Get the data and save location from the results
    vibe_data = vibe_results['data']
    output_folder = vibe_results['output_folder']
    
    # --- STAGE 2: Convert VIBE data to PLY (dict -> PLY) ---
    ply_file_path = results_to_ply(vibe_data, output_folder)
    
    if ply_file_path is None:
        return {"status": "error", "message": "Failed to convert VIBE data to PLY"}
    
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
    video_to_process = "sample_video.mp4" 
    
    if os.path.exists(video_to_process):
        
        # Call the main API-ready function
        final_result = run_full_pipeline(video_to_process)
        
        print("\n================= FINAL RESULT =================")
        print(final_result)
        print("================================================")
        
    else:
        print(f"--- FAILED: Test video not found at: {video_to_process} ---")