import json
import sys

from typing import Annotated
from fastapi import FastAPI, Response, status, Header
from pydantic import BaseModel
import os
import requests

app = FastAPI()


class Image(BaseModel):
	title: str
	name: str
	description: str | None = None
	r_version: list[str] | None = None
	py_version: list[str] | None = None
	quarto_version: list[str] | None = None
	# r_path: list[str] | None = None
	# py_path: list[str] | None = None
	# quarto_path: list[str] | None = None


class ConnectImageInstallationEntry(BaseModel):
	path: str
	version: str


class ConnectImageInstallation(BaseModel):
	installations: list[ConnectImageInstallationEntry] = []


class ConnectImage(BaseModel):
	title: str
	description: str | None = None
	cluster_name: str = "Kubernetes"
	name: str
	matching: str = "exact"
	supervisor: str | None = None
	python: ConnectImageInstallation = ConnectImageInstallation()
	quarto: ConnectImageInstallation = ConnectImageInstallation()
	r: ConnectImageInstallation = ConnectImageInstallation()


connect = os.getenv("CONNECT_SERVER")
api_key = os.getenv("CONNECT_API_KEY")
content_guid = os.getenv("CONNECT_CONTENT_GUID", "unknown")

if not connect or connect == "":
	raise Exception("Connect server must be specified using the CONNECT_SERVER env var")

if not api_key or api_key == "":
	raise Exception("ERROR: Connect API Key must be specified using the CONNECT_API_KEY env var")


# @app.get("/")
# async def root():
# 	return {"message": "Hello World"}


# @app.get("/image")
# async def get_image():
# 	return {"message": "Hello World"}


# TODO: allow a GET for just images maintained by this instance, and owned by this user

# TODO: allow a DELETE for just images maintained by this instance, and owned by this user... by GUID? by Image name?

@app.post("/image")
async def post_image(
		img: Image, response: Response, rstudio_connect_credentials: Annotated[str | None, Header()] = None
		) -> dict | str:

	cimg = ConnectImage(title=img.title, name=img.name)
	cimg.description = img.description

	# prepare credentials of requesting user
	print(rstudio_connect_credentials, file=sys.stderr)
	req_user = 'unknown'
	if rstudio_connect_credentials:
		creds = json.loads(rstudio_connect_credentials)
		req_user = creds['user']

	cimg.description = json.dumps({
		'description': img.description,
		'user': req_user,
		'managed-by': content_guid,
	})

	# check that at least one install is provided
	if (not img.r_version or len(img.r_version) == 0) and \
		(not img.py_version or len(img.py_version) == 0) and \
		(not img.quarto_version or len(img.quarto_version) == 0):
		response.status_code = status.HTTP_400_BAD_REQUEST
		return {'message': 'Invalid request body. Must provide R, Python, or Quarto installations'}

	if img.r_version and len(img.r_version) != 0:
		for r in img.r_version:
			cimg.r.installations.append(ConnectImageInstallationEntry(version=r, path=f'/opt/R/{r}/bin/R'))

	if img.py_version and len(img.py_version) != 0:
		for py in img.py_version:
			cimg.python.installations.append(ConnectImageInstallationEntry(version=py, path=f'/opt/python/{py}/bin/python'))

	if img.quarto_version and len(img.quarto_version) != 0:
		for q in img.quarto_version:
			cimg.quarto.installations.append(ConnectImageInstallationEntry(version=q, path=f'/opt/quarto/{q}/bin/quarto'))

	# prep request upstream to connect host
	json_body = cimg.model_dump_json()
	# print(json_body)

	res = requests.post(
		f'{connect}/__api__/v1/environments',
		data=json_body,
		headers={
			'Authorization': f'Key {api_key}',
		}
	)
	res_json = res.json()

	# print(res_json)
	# print(res.status_code)

	response.status_code = res.status_code
	return res_json


if __name__ == "__main__":
	print("Run this file with `uvicorn main:app --reload`")
