import os.path
import torch
from src import safetensors_hack
from safetensors.torch import save_file

def write_lora_metadata(model_path, updates):
  if model_path.startswith("\"") and model_path.endswith("\""):             # trim '"' at start/end
    model_path = model_path[1:-1]
  if not os.path.exists(model_path):
    return None

  from safetensors.torch import save_file

  metadata = None
  tensors = {}
  if os.path.splitext(model_path)[1] == '.safetensors':
    tensors, metadata = safetensors_hack.load_file(model_path, "cpu")

    for k, v in updates.items():
      metadata[k] = str(v)

    save_file(tensors, model_path, metadata)
    print(f" Model saved: {model_path}")

def convert_pt_to_safetensors(f):
    print(f"Convert .pt: {f}")
    ext = os.path.splitext(f)[1]
    fn = f"{f.replace(ext, '')}.safetensors"

    with torch.no_grad():
        weights = torch.load(f, map_location=torch.device("cpu"))
        fn = f"{f.replace(ext, '')}.safetensors"
        print(f'Saving {fn}...')
        save_file(weights, fn)

    return fn
