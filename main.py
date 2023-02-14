"""Civit.AI Local Database

Usage:
  main.py creators [options]
  main.py models [options] (get|download)
  main.py version [options]
  main.py tags [options]
  main.py sync [options]
  main.py dump [options]
  main.py (-h | --help)
  main.py --version

Options:
    -i ID, --id ID              Model versions ID
    -l LIMIT, --limit LIMIT     Limit items returned
    --period PERIOD             Something???
    -q QUERY, --query QUERY     Text query
    -p PAGE, --page PAGE        Pagination offset
    -r RATING, --rating RATING  Search by model ratings
    -s SORT, --sort SORT        Sort results by
    --save                      Save results to database
    -t TAG, --tag TAG           Tag search
    -t TYPE, --type TYPE        Model type
    -u USER, --username USER    Model creator username

    -v --verbose    Increase verbosity
    -h --help       Show this screen.
    --version       Show version.
"""
from sqlalchemy import create_engine, select, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import os.path
import io
import json
import tqdm
import traceback
from PIL import PngImagePlugin, Image
import markdownify
from pathvalidate import sanitize_filepath
from docopt import docopt
import requests
import base64

from src.models import Base, Model, ModelVersion, ModelVersionFile, ModelVersionImage
from src.civit_api import get_creators, get_models, get_model_version,  get_tags
from src import safetensors_hack, lora_util, sd_models

DATABASE_NAME = os.getenv("DATABASE_NAME","civitai_default_db")

#if os.path.isfile(DATABASE_NAME + ".db"):
#    from datetime import datetime
#    import shutil
#    today = datetime.now()
#    path = today.strftime('%Y_%m_%d_%H-%M-%S')
#    os.makedirs(path)
#    shutil.copy(DATABASE_NAME + ".db", path)
#    os.remove(DATABASE_NAME + ".db")

engine = create_engine(f"sqlite:///{DATABASE_NAME}.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

VERBOSE = False
MAX_COVER_IMAGES = 3

def convert_civitai_meta(meta):
    if meta is None:
        return None

    meta = json.loads(meta)
    if meta is None:
        return None

    prompt = meta.pop("prompt", "")
    neg_prompt = meta.pop("negativePrompt", None)
    seed = meta.pop("seed", "-1")
    steps = meta.pop("steps", "20")
    sampler = meta.pop("sampler", "Euler a")
    cfgScale = meta.pop("cfgScale", "7")

    meta["Seed"] = seed
    meta["Steps"] = steps
    meta["Sampler"] = sampler
    meta["CFG Scale"] = cfgScale

    generation_params_text = ", ".join([k if k == v else f'{k}: {v}' for k, v in meta.items() if v is not None])
    negative_prompt_text = "\nNegative prompt: " + neg_prompt if neg_prompt else ""
    return f"{prompt}{negative_prompt_text}\n{generation_params_text}".strip()

if __name__ == '__main__':
    arguments = docopt(
        __doc__,
        version=f'Civit.AI Local Database {os.getenv("PROGRAM_VERSION","0.0.1")}'
    )
    print(arguments)

    if arguments['--verbose']:
        VERBOSE = True

    if arguments["creators"]:
        passed_args = {}
        if arguments['--limit']:
            passed_args["limit"]=arguments['--limit']
        if arguments['--page']:
            passed_args["page"]=arguments['--page']
        if arguments['--query']:
            passed_args["query"]=arguments['--query']
        if arguments['--save']:
            passed_args["save"]=arguments['--save']
        get_creators(**passed_args)
    elif arguments["models"]:
        if arguments["get"]:
            passed_args = {}
            if arguments['--limit']:
                passed_args["limit"]=arguments['--limit']
            if arguments['--page']:
                passed_args["page"]=arguments['--page']
            if arguments['--query']:
                passed_args["query"]=arguments['--query']
            if arguments['--tag']:
                passed_args["tag"]=arguments['--tag']
            if arguments['--username']:
                passed_args["username"]=arguments['--username']
            if arguments['--type']:
                passed_args["type"]=arguments['--type']
            if arguments['--sort']:
                passed_args["sort"]=arguments['--sort']
            if arguments['--period']:
                passed_args["period"]=arguments['--period']
            if arguments['--rating']:
                passed_args["rating"]=arguments['--rating']
            if arguments['--save']:
                passed_args["save"]=arguments['--save']

            max_pages = 9999
            page = 1
            passed_args["page"] = page

            while page <= max_pages:
                metadata, models, modelVersions, modelVersionFiles, modelVersionImages = get_models(**passed_args)
                max_pages = metadata["totalPages"]

                import json
                print(json.dumps(metadata))
                session = Session()
                # session.add_all(models)
                # session.add_all(modelVersions)
                # session.add_all(modelVersionFiles)
                # session.add_all(modelVersionImages)
                for m in models + modelVersions + modelVersionFiles + modelVersionImages:
                    session.merge(m)
                session.commit()
                page += 1
                passed_args["page"] = page

        elif arguments["download"]:
            raise Exception('Not Implemented Yet!')
    elif arguments["version"]:
        passed_args = {}
        if arguments['--id']:
            passed_args["model_versions_id"]=arguments['--id']
        if arguments['--save']:
            passed_args["save"]=arguments['--save']
        get_model_version(**passed_args)
    elif arguments["tags"]:
        passed_args = {
            "limit":arguments['--limit'],
            "page":arguments['--page'],
            "query":arguments['--query'],
            "save":arguments['--save']
        }
        get_tags(**passed_args)
    elif arguments["sync"]:
        raise Exception('Not Implemented Yet!')
    elif arguments["dump"]:
        path = "D:\\stable-diffusion\\models\\lora-torrent\\LoRAs\\CivitAI"
        assert os.path.isdir(path)

        print(f"Saving models to {path}...")
        failures = []

        stmt = select(Model).where(Model.type == "LORA")
        with Session() as session:
            total = session.query(Model).filter(Model.type == "LORA").with_entities(func.count()).scalar()
            for row in tqdm.tqdm(session.execute(stmt), total=total):
                model = row[0]
                for version in model.versions:
                    try:
                        print(f"{version.id}")
                        formats = {f.format: True for f in version.files if f.type == "Model"}
                        has_safetensors = "SafeTensor" in formats
                        format = "SafeTensor"
                        if not has_safetensors:
                            format = "PickleTensor"

                        file = next(filter(lambda f: f.type == "Model" and f.format == format, version.files))
                        if file is None:
                            raise Exception(f"No file! {model.id} {model.name}")

                        parent_path = sanitize_filepath(os.path.join(path, f"{model.id} - {model.name}"), platform="Windows")

                        cover_images = []
                        for i, image in enumerate(version.images):
                            basename = os.path.splitext(file.name)[0]
                            suffix = "preview"
                            if i > 0:
                                suffix = f"preview.{i}"
                            outpath = sanitize_filepath(os.path.join(parent_path, f"{basename}.{suffix}.png"), platform="Windows")
                            if os.path.exists(outpath):
                                print(f"Path already exists, skipping: {outpath}")
                                continue

                            os.makedirs(os.path.dirname(outpath), exist_ok=True)
                            resp = requests.get(image.url)
                            pil = Image.open(io.BytesIO(resp.content))

                            with io.BytesIO() as output_bytes:
                                metadata = PngImagePlugin.PngInfo()
                                meta = convert_civitai_meta(image.meta)
                                if meta:
                                    metadata.add_text("parameters", meta)
                                pil.save(output_bytes, "PNG", pnginfo=(metadata))
                                bytes_data = output_bytes.getvalue()

                            with open(outpath, "wb") as f:
                                f.write(bytes_data)

                            if len(cover_images) < MAX_COVER_IMAGES:
                                cover_images.append(base64.b64encode(bytes_data).decode("ascii"))

                        outpath = sanitize_filepath(os.path.join(parent_path, f"{file.name}"), platform="Windows")
                        os.makedirs(os.path.dirname(outpath), exist_ok=True)

                        model_path = outpath
                        bn, ext = os.path.splitext(outpath)
                        if ext != ".safetensors":
                            model_path = f"{bn}.safetensors"

                        if os.path.exists(model_path):
                            print(f"Path already exists, skipping: {outpath}")
                            continue
                        print(f"Saving: {outpath}")

                        if not os.path.isfile(outpath):
                            response = requests.get(version.download_url + f"?type={file.type}&format={file.format}", stream=True)
                            total_size_in_bytes = int(response.headers.get('content-length', 0))
                            progress_bar = tqdm.tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
                            try:
                                with open(outpath, "wb") as f:
                                    for chunk in response.iter_content(1024):
                                        progress_bar.update(len(chunk))
                                        f.write(chunk)
                                    progress_bar.close()
                            except KeyboardInterrupt:
                                progress_bar.close()
                                print(f"*** DELETING partial file: {outpath}")
                                os.unlink(outpath)
                                print("Interrupted, exiting.")
                                exit(1)
                        else:
                            print("Using model file on disk.")

                        if ext != ".safetensors":
                            legacy_hash = sd_models.model_hash(outpath) # use .pt legacy hash
                            outpath = lora_util.convert_pt_to_safetensors(outpath)
                        else:
                            legacy_hash = safetensors_hack.legacy_hash_file(outpath)

                        assert os.path.splitext(outpath)[1] == ".safetensors"

                        description = model.description or ""
                        if version.description:
                            description += "<hr>"
                            description += version.description

                        model_hash = safetensors_hack.hash_file(outpath)
                        metadata = {
                            "ssmd_cover_images": json.dumps(cover_images),
                            "ssmd_display_name": f"{model.name}",
                            "ssmd_author": model.creator_username,
                            "ssmd_version": version.name,
                            "ssmd_source": f"https://civitai.com/models/{model.id}",
                            "ssmd_keywords": ", ".join(json.loads(version.trained_words)),
                            "ssmd_description": markdownify.markdownify(description, heading_style="ATX"),
                            "ssmd_rating": "0",
                            "ssmd_tags": ", ".join(json.loads(model.tags)),
                            "sshs_model_hash": model_hash,
                            "sshs_legacy_hash": legacy_hash
                           }
                        lora_util.write_lora_metadata(outpath, metadata)
                    except Exception as ex:
                        exs = ''.join(traceback.TracebackException.from_exception(ex).format())
                        print(f"Failed saving model: {exs}")
                        failures.append({"model_id": model.id, "version_id": version.id, "exception": str(exs)})

        with open("failures.json", "w") as f:
            json.dump(failures, f)
    else:
        raise Exception("Arguments parsing failed")
