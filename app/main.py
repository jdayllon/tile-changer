from flask import Flask, Response, request, send_file
from werkzeug.wsgi import FileWrapper
from flask_caching import Cache
import requests
from loguru import logger
import os
import PIL.Image
from io import BytesIO
import uuid 
import logging

#### 
def env_var_load(name, default_value):
    if name in os.environ:
          res = type(default_value) (os.environ[name])
          logger.info(f"ENV '{name}' Found: {res}")
          return res
    else:
          logger.warning(f"ENV '{name}' NOT Found: {default_value}")
          return default_value

# Initial env prepare
DEBUG = env_var_load("DEBUG",True)
CACHE_TYPE = env_var_load("CACHE_TYPE",'simple')
CACHE_DEFAULT_TIMEOUT = env_var_load("CACHE_DEFAULT_TIMEOUT",300)
TARGET_HOST = env_var_load('TARGET_HOST','')

config = {
    "DEBUG": DEBUG,          # some Flask specific configs
    "CACHE_TYPE": CACHE_TYPE, # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": CACHE_DEFAULT_TIMEOUT
}

if CACHE_TYPE == 'redis':  
  config['CACHE_REDIS_HOST'] = env_var_load("CACHE_REDIS_HOST", 'localhost')
  config['CACHE_REDIS_PORT'] = env_var_load("CACHE_REDIS_PORT", 6379)
  config['CACHE_REDIS_PASSWORD'] = env_var_load("CACHE_REDIS_PASSWORD",'')
  config['CACHE_REDIS_DB'] = env_var_load("CACHE_REDIS_DB",'')
  
app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)
####
# Partial disable Requests logging
logging.getLogger("requests").setLevel(logging.WARNING)

# Based on https://stackoverflow.com/a/10170635
# https://www.pythonanywhere.com/forums/topic/13570/
def serve_pil_image(pil_img, mimetype):
    img_io = BytesIO()
    pil_img.save(img_io, mimetype.split("/")[1].upper())
    img_io.seek(0)
    # Original response from Github uses send_file method
    # but I have problems with pickle and uwsgi, changed send_file
    # for direct uwsgi filewraper and Response from Flask
    # --> return send_file(img_io, mimetype=mimetype)
    w = FileWrapper(img_io)
    return Response(w, mimetype=mimetype, direct_passthrough=True)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@cache.cached(timeout=24*60*60, query_string=True)
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
  logger.info(f"|{current_process}| Image transformed, sending...")

  return serve_pil_image(image_bw, original_mimetype)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080)