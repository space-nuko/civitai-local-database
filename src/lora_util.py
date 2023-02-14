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


def load_ckpt_weights(checkpoint_path):
    try:
        # Load the weights from the checkpoint file, without computing gradients
        with torch.no_grad():
            weights = torch.load(checkpoint_path, map_location=torch.device('cpu'))
            # Check if the weights are contained in a "state_dict" key
            if "state_dict" in weights:
                weights = weights["state_dict"]
                # If the weights are nested in another "state_dict" key, remove it
                if "state_dict" in weights:
                    weights.pop("state_dict")
            return weights

    except Exception as e:
        if isinstance(e, (RuntimeError, EOFError)):
            print(" FAIL TO LOAD CHECKPOINT: Corrupted file")
        elif isinstance(e, FileNotFoundError):
            print(" File Not Found")
        elif isinstance(e, (AttributeError, KeyError)):
            print(" FILE NOT SUPPORTED")
        else:
            print(f'Error: {e}')

def convert_pt_to_safetensors(f):
    print(f"Convert .pt: {f}")
    ext = os.path.splitext(f)[1]
    fn = f"{f.replace(ext, '')}.safetensors"

    with torch.no_grad():
        weights = load_ckpt_weights(f)
        fn = f"{f.replace(ext, '')}.safetensors"
        print(f'Saving {fn}...')
        save_file(weights, fn)

    return fn
