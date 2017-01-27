import boto3

SNAPSHOTS = 'snapshots.snerted.com'


def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        raise TypeError


def lambda_handler(event, context):
    s3 = boto3.client('s3')
    results = []
    for obj in s3.list_objects_v2(Bucket=SNAPSHOTS)['Contents']:
        o = dict()
        o['name'] = obj['Key']
        o['url'] = s3.generate_presigned_url('get_object', Params={'Bucket': SNAPSHOTS, 'Key': obj['Key']})
        o['timestamp'] = date_handler(obj['LastModified'])
        results.append(o)
    return results