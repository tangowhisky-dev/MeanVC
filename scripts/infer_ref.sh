export PYTHONPATH=$PYTHONPATH:$PWD

# All checkpoints live in assets/ — run download_ckpt.py first to populate.
model_path=assets/ckpt/model_200ms.safetensors
vocoder_path=assets/ckpt/vocos.pt
asr_path=assets/ckpt/fastu2++.pt
sv_path=assets/wavLM/wavlm_large_finetune.pth
source_path=path/to/source_dir
reference_path=path/to/reference.wav
output_dir=src/outputs

mkdir -p $output_dir


python3 src/infer/infer_ref.py \
    --model-config src/config/config_200ms.json \
    --ckpt-path ${model_path} \
    --vocoder-ckpt-path ${vocoder_path} \
    --asr-ckpt-path ${asr_path} \
    --sv-ckpt-path ${sv_path} \
    --source-path ${source_path} \
    --reference-path ${reference_path} \
    --output-dir ${output_dir} \
    --chunk-size 20 \
    --steps 2
