# from ddtrace import tracer, config, patch_all # STEP 02
# tracer.configure(hostname='agent', port=8126) # STEP 02 
# config.flask['service_name'] = 'taster' # STEP 02

# patch_all(flask=True) # STEP 02
from flask import Flask, request, jsonify

# patch_all(logging=True) # STEP 04
import logging

FORMAT = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
          #'[dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] ' # STEP 04
          '- %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)
log.level = logging.INFO

import random

#------------------------------#

app = Flask(__name__)

@app.route("/taste")
def taste():
    beer = request.args.get("beer")

    if beer == 'stout':
        score = random.randint(10, 0)
    else:
        score = random.randint(1, 10)

    log.info('Tasting, giving it a '+str(score))

    return jsonify(score=score)
