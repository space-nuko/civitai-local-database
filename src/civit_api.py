import requests
from src.models import Creator, Model, ModelVersion, Tag, ModelVersionFile, ModelVersionImage
import json
from datetime import datetime
import dateutil.parser

def _request_creators(limit=20, page=1, query=None) -> dict:
    """_request_creators _summary_

    Args:
        limit (int, optional): _description_. Defaults to 20.
        page (int, optional): _description_. Defaults to 1.
        query (_type_, optional): _description_. Defaults to None.

    Returns:
        dict: _description_
    """
    endpoint = "https://civitai.com/api/v1/creators"
    params = {"limit": limit, "page": page, "query": query}
    response = requests.get(endpoint, params=params, timeout=30)
    print(str(response))
    print(response.json())
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_creators(
    limit:int=20,
    page:int=1, query:str=None,
    save:bool=False
) -> tuple[dict, list[Creator]]:
    """get_creators _summary_

    Args:
        limit (int, optional): _description_. Defaults to 20.
        page (int, optional): _description_. Defaults to 1.
        query (str, optional): _description_. Defaults to None.
        save (bool, optional): If True then save results to database. Defaults to False.

    Returns:
        tuple[dict, list[Creator]]: _description_
    """
    data = _request_creators(limit, page, query)
    print(f'data: {data}')
    # access the response metadata
    metadata = data["metadata"]  # totalItems,currentPage,pageSize,totalPages,nextPage

    # Create a list of Creator objects from the data
    creators = []
    for item in data["items"]:
        creator = Creator(
            username=item["username"], model_count=item["modelCount"], link=item["link"]
        )
        creators.append(creator)
    return metadata, creators


def _request_models(
    limit=100,
    page=1,
    query=None,
    tag=None,
    username=None,
    model_type=None,
    sort=None,
    period=None,
    rating=None,
) -> dict:
    """_request_models _summary_

    Args:
        limit (int, optional): _description_. Defaults to 100.
        page (int, optional): _description_. Defaults to 1.
        query (_type_, optional): _description_. Defaults to None.
        tag (_type_, optional): _description_. Defaults to None.
        username (_type_, optional): _description_. Defaults to None.
        model_type (_type_, optional): _description_. Defaults to None.
        sort (_type_, optional): _description_. Defaults to None.
        period (_type_, optional): _description_. Defaults to None.
        rating (_type_, optional): _description_. Defaults to None.

    Returns:
        dict: _description_
    """
    endpoint = "https://civitai.com/api/v1/models"
    params = {
        "limit": limit,
        "page": page,
        "query": query,
        "tag": tag,
        "username": username,
        "types": model_type,
        "sort": sort,
        "period": period,
        "rating": rating,
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_models(
    limit=100,
    page=1,
    query=None,
    tag=None,
    username=None,
    model_type=None,
    sort=None,
    period=None,
    rating=None,
    save:bool=False
) -> tuple[dict, list[Model]]:
    """get_models _summary_

    Args:
        limit (int, optional): _description_. Defaults to 100.
        page (int, optional): _description_. Defaults to 1.
        query (_type_, optional): _description_. Defaults to None.
        tag (_type_, optional): _description_. Defaults to None.
        username (_type_, optional): _description_. Defaults to None.
        model_type (_type_, optional): _description_. Defaults to None.
        sort (_type_, optional): _description_. Defaults to None.
        period (_type_, optional): _description_. Defaults to None.
        rating (_type_, optional): _description_. Defaults to None.
        save (bool, optional): If True then save results to database. Defaults to False.

    Returns:
        tuple[dict, list[Model]]: _description_
    """
    data = _request_models(
        limit, page, query, tag, username, model_type, sort, period, rating
    )
    # access the response metadata
    metadata = data["metadata"]  # totalItems,currentPage,pageSize,totalPages,nextPage

    # Create a list of Model objects from the data
    models = []
    modelVersions = []
    modelVersionFiles = []
    modelVersionImages = []
    import json
    for item in data["items"]:
        model = Model(
            id=int(item["id"]),
            name=item["name"],
            description=item["description"],
            type=item["type"],
            nsfw=item["nsfw"],
            tags=json.dumps(item["tags"]),
            creator_username=item["creator"]["username"],
            creator_image=item["creator"]["image"],
        )
        models.append(model)
        for data in item["modelVersions"]:
            model_version = ModelVersion(
                id=int(data["id"]),
                name=data["name"],
                description=data["description"],
                base_model=data["baseModel"],
                created_at=dateutil.parser.parse(data["createdAt"]),
                download_url=data["downloadUrl"],
                trained_words=json.dumps(data["trainedWords"]),
                parent_id=model.id
                )
            modelVersions.append(model_version)

            for file in data["files"]:
                version_file = ModelVersionFile(
                    id=int(file["id"]),
                    name=file["name"],
                    size_kb=file["sizeKB"],
                    type=file["type"],
                    format=file["format"],
                    pickle_scan_result=file["pickleScanResult"],
                    virus_scan_result=file["virusScanResult"],
                    scanned_at=dateutil.parser.parse(file["scannedAt"]) if file["scannedAt"] else datetime.min,
                    parent_id=model_version.id
                )
                modelVersionFiles.append(version_file)

            for image in data["images"]:
                version_image = ModelVersionImage(
                    url=image["url"],
                    nsfw=image["nsfw"],
                    width=image["width"],
                    height=image["height"],
                    hash=image["hash"],
                    meta=json.dumps(image["meta"]),
                    parent_id=model_version.id
                )
                modelVersionImages.append(version_image)
    return metadata, models, modelVersions, modelVersionFiles, modelVersionImages


def _request_model_version(model_versions_id: str) -> dict:
    """_request_model_version _summary_

    Args:
        model_versions_id (str): _description_

    Returns:
        dict: _description_
    """    
    endpoint = f"https://civitai.com/api/v1/model-versions/{model_versions_id}"
    response = requests.get(endpoint)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_model_version(model_versions_id: str, save:bool=False) -> ModelVersion:
    """get_model_version _summary_

    Args:
        model_versions_id (str): _description_
        save (bool, optional): If True then save results to database. Defaults to False.

    Returns:
        ModelVersion: _description_
    """
    data = _request_model_version(model_versions_id)
    # access the response metadata
    metadata = data["metadata"]  # totalItems,currentPage,pageSize,totalPages,nextPage

    model_version = ModelVersion(
        name=data["name"],
        model_name=data["model"]["name"],
        model_type=data["model"]["type"],
        model_nsfw=data["model"]["nsfw"],
        model_poi=data["model"]["poi"],
        model_id=data["modelId"],
        created_at=data["createdAt"],
        download_url=data["downloadUrl"],
        trained_words=data["trainedWords"],
        files_size_kb=data["files"]["sizeKb"],
        files_format=data["files"]["format"],
        files_pickle_scan_result=data["files"]["pickleScanResult"],
        files_virus_scan_result=data["files"]["virusScanResult"],
        files_scanned_at=data["files"]["scannedAt"],
        images_url=data["images"]["url"],
        images_nsfw=data["images"]["nsfw"],
        images_width=data["images"]["width"],
        images_height=data["images"]["height"],
        images_hash=data["images"]["hash"],
        images_meta=data["images"]["meta"],
    )
    return model_version


def _request_tags(limit=20, page=1, query=None) -> dict:
    """_request_tags _summary_

    Args:
        limit (int, optional): _description_. Defaults to 20.
        page (int, optional): _description_. Defaults to 1.
        query (_type_, optional): _description_. Defaults to None.

    Returns:
        dict: _description_
    """    
    endpoint = "https://civitai.com/api/v1/tags"
    params = {"limit": limit, "page": page, "query": query}
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_tags(limit:int=20, page:int=1, query:str=None, save:bool=False) -> tuple[dict, list[Tag]]:
    """get_tags _summary_

    Args:
        limit (int, optional): _description_. Defaults to 20.
        page (int, optional): _description_. Defaults to 1.
        query (str, optional): _description_. Defaults to None.
        save (bool, optional): If True then save results to database. Defaults to False.

    Returns:
        tuple[dict, list[Tag]]: _description_
    """
    data = _request_tags(limit, page, query)
    # access the response metadata
    metadata = data["metadata"]  # totalItems,currentPage,pageSize,totalPages,nextPage


def download_model():
    """download_model _summary_

    Raises:
        Exception: _description_
    """    
    raise Exception('NOT IMPLEMENTED')
    # content-disposition
    url = "http://example.com/download"
    headers = {
        "Content-Disposition": "attachment; filename=example.zip",
        "User-Agent": "MyApp/1.0"
    }
    response = requests.get(url, headers=headers)
