from flask import Flask, request
from flask_cors import CORS, cross_origin
from Query import Query
from Indexer import Indexer
 
 
app = Flask(__name__)
CORS(app)

i = Indexer()
q = Query(i)

@app.route('/search', methods=["GET"])
def search():
    args = request.args
    try:
        query_string = args.get('q')
    except:
        return []
    return {'data' : q.search(query_string),
    'query': query_string}

if __name__=='__main__':
    app.run( host='127.0.0.1', port=5000)