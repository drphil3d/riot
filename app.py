from chalice import Chalice
import boto3
import json
from botocore.exceptions import ClientError
from chalice import NotFoundError
from boto3.dynamodb.conditions import Key, Attr

REGION = 'us-east-1'

app = Chalice(app_name='riot')
app.debug = True
ddb = boto3.resource('dynamodb', region_name=REGION)


def dict_or(d, k1, k2):
    """used for conditional assignment on a dictionary"""
    if k1 in d:
        return d[k1]
    elif k2 in d:
        return d[k2]
    return None


def ddb_query(table, response_key, partition_key, partition_value, sort_key, params=None, metric=None):
    """DynamoDb query using partition key and sort key plus gt, gte, lt, lte, and between"""
    p_key = Key(partition_key).eq(partition_value)
    if params is not None:
        if ('gt' in params or 'gte' in params) and ('lt' in params or 'lte' in params):
            p_key = p_key & Key(sort_key).between(dict_or(params, 'gt', 'gte'), dict_or(params, 'lt', 'lte'))
        else:
            if 'gt' in params:
                p_key = p_key & Key(sort_key).gt(params['gt'])
            if 'gte' in params:
                p_key = p_key & Key(sort_key).gte(params['gte'])
            if 'lt' in params:
                p_key = p_key & Key(sort_key).lt(params['lt'])
            if 'lte' in params:
                p_key = p_key & Key(sort_key).lte(params['lte'])
    if metric is not None:
        response = table.query(
            KeyConditionExpression=p_key,
            FilterExpression=Attr('payload.state.reported.' + metric).exists(),
            ExpressionAttributeNames={"#src": "source", "#ts": "timestamp", "#pl": "payload", "#st": "state",
                                      "#rpt": "reported", "#v": metric},
            ProjectionExpression="#src, #ts, #pl.#st.#rpt.#v"
        )
    else:
        response = table.query(
            KeyConditionExpression=p_key
        )
    if response_key in response:
        return response[response_key]
    else:
        return []


@app.route('/things', methods=['GET'])
def get_things():
    iot = boto3.client('iot', region_name=REGION)
    request = app.current_request
    if request.method == 'GET':
        try:
            response = iot.list_things()
            return response["things"]
        except ClientError as e:
            raise NotFoundError()


@app.route('/things/{thing}', methods=['GET'])
def get_thing(thing):
    iot_data = boto3.client('iot-data', region_name=REGION)
    request = app.current_request
    if request.method == 'GET':
        try:
            response = iot_data.get_thing_shadow(thingName=thing)
            body = response["payload"]
            return json.loads(body.read())
        except ClientError as e:
            raise NotFoundError(thing)


@app.route('/introspect')
def introspect():
    return app.current_request.to_dict()


@app.route('/metrics/{thing}/{metric}', methods=['GET'])
def get_metrics(thing, metric):
    request = app.current_request
    params = app.current_request.query_params
    if request.method == 'GET':
        try:
            return ddb_query(ddb.Table('sensors'), 'Items', 'source', thing, 'timestamp', params, metric)
        except ClientError as e:
            raise NotFoundError()
