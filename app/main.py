from flask import Flask, request, send_file
import requests
from loguru import logger
import os
import PIL.Image
from io import BytesIO
import uuid 

app = Flask(__name__)
TARGET_HOST = os.environ['TARGET_HOST']

logger.info(f"Current Target Tile Host: {TARGET_HOST}")

# Based on https://stackoverflow.com/a/10170635
def serve_pil_image(pil_img, mimetype):
    img_io = BytesIO()
    pil_img.save(img_io, mimetype.split("/")[1].upper())
    img_io.seek(0)
    return send_file(img_io, mimetype=mimetype)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
  current_process = uuid.uuid1()

  if isinstance(request.query_string, str):
    target_url = f"{TARGET_HOST}{path}?{request.query_string}"
  else:
    target_url = f"{TARGET_HOST}{path}?{request.query_string.decode()}"

  logger.info(f"|{current_process}| Requesting : {target_url}")
  res = requests.get(target_url)

  logger.info(f"|{current_process}| Requested: {res.status_code}")
  original_mimetype = res.headers['Content-type'].split(";")[0]
  original_type_of_res = original_mimetype.split("/")[0]
  logger.info(f"|{current_process}| Response mimetype: {original_mimetype}")

  if original_type_of_res != "image" or "VND.MICROSOFT.ICON" in original_mimetype.upper():
        logger.warning(f"|{current_process}| Content non-supported")
        return (f'Non-Supported Content Type: {original_mimetype}', 204)

  image_stream = BytesIO(res.content)
  image = PIL.Image.open(image_stream)
  image_bw = image.convert('LA')
  logger.info(f"|{current_process}| Image transformed, ready to response")
  return serve_pil_image(image_bw, original_mimetype)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080)