#!/usr/bin/env bash

mkdir -p data
cd data
gdown "https://drive.google.com/uc?id=1untXhYOLQtpNEy4GTY_0fL_H-k6cTf_r"
unzip vibe_data.zip
rm vibe_data.zip
cd ..
mv data/vibe_data/sample_video.mp4 .
mkdir -p $HOME/.torch/models/
mv data/vibe_data/yolov3.weights $HOME/.torch/models/

gdown "https://drive.google.com/uc?id=1PLUUsB2w7EOc4Zr6QviQuLOL6NVFN_BI" -O data/smpl/SMPL_NEUTRAL.pkl
# gdown "https://drive.google.com/uc?id=1tVgCkqRVNsW8BtLKYeuqNUfT2PSxE6GL" -O data/smplx/SMPLX_NEUTRAL.pkl