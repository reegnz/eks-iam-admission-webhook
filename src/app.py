from flask import Flask, request, Response, jsonify
import ssl
import json
import base64
app = Flask(__name__)

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.verify_mode = ssl.CERT_REQUIRED
context.load_verify_locations = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

marker_annotation = 'eks.amazonaws.com/iam-role'

@app.route('/', methods=['POST'])
def mutate_pods():
    default_response = {
        "response":  {
            "allowed": True
        }
    }
    admission_review = request.get_json()
    obj = admission_review["request"]["object"]
    if not should_mutate(obj):
        return jsonify(default_response)
    role = get_annotation(obj, marker_annotation)

    params = {
        "envs": [
            {
                "name": "AWS_IAM_ROLE",
                "value": role
            },
            {
                "name": "AWS_WEB_IDENTITY_TOKEN_FILE",
                "value": "/var/run/secrets/eks.amazonaws.com/serviceaccount/token"
            }
        ],
        "volumeMounts": [
            {
                "name": "aws-iam-token",
                "readOnly": True,
                "mountPath": "/var/run/secrets/eks.amazonaws.com/serviceaccount"
            }
        ],
        "volumes": [
            {
                "name": "aws-iam-token",
                "projected": {
                    "sources": [
                        {
                            "serviceAccountToken": {
                                "audience": "sts.amazonaws.com",
                                "expirationSeconds": 86400,
                                "path": "token",
                            }
                        }
                    ]
                }
            }
        ]
    }

    patches = patch_pod(obj, params)
    res = {
        "apiVersion": "admission.k8s.io/v1beta1",
        "kind": "AdmissionReview",
        "request": admission_review["request"],
        "response": {
            "uid": admission_review["request"]["uid"],
            "allowed": True,
            "patch": base64.b64encode(json.dumps(patches).encode('UTF-8')).decode('ASCII')
        }
    }
    app.logger.info(json.dumps(res))
    return jsonify(res)


def patch_pod(obj: dict, params: dict) -> list:

    patches = []
    patches += patch_all('containers', obj, params)
    patches += patch_all('initContainers', obj, params)
    if 'volumes' not in obj['spec']:
        patches += create_volumes()
        volumes = []
    else:
        volumes = obj['spec']['volumes']
    patches += patch_volumes(volumes, params["volumes"])

    return patches


def patch_all(containerType: str, obj: dict, params: dict):
    patches = []
    if containerType not in obj["spec"]:
        return patches

    for count in range(len(obj["spec"][containerType])):
        container = obj["spec"][containerType][count]
        if 'env' not in container:
            patches += create_env(containerType, count)
            env = []
        else:
            env = container["env"]
        patches += patch_container_env(env, containerType,
                                       count, params["envs"])
        if 'volumeMounts' not in container:
            patches += create_volume_mounts(containerType, count)
            volumeMounts = []
        else:
            volumeMounts = container["volumeMounts"]
        patches += patch_volume_mounts(volumeMounts, containerType,
                                       count, params["volumeMounts"])
    return patches


def create_env(containerType: str, count: int):
    return [
        {
            'op': 'add',
            'path': f'/spec/{containerType}/{count}/env',
            'value': []
        }
    ]


def should_mutate(obj: dict):
    return has_annotation(obj, marker_annotation)


def has_annotation(obj: dict, name: str):
    metadata = obj['metadata']
    if 'annotations' not in metadata:
        return False
    annotations = metadata['annotations']
    if name not in annotations:
        return False
    return True


def get_annotation(obj: dict, name: str):
    return obj['metadata']['annotations'][name]


def patch_container_env(containerEnv: dict, containerType: str, count: int, envs: list) -> list:
    return [
        {
            'op': 'add',
            'path': f'/spec/{containerType}/{count}/env/-',
            'value': env
        }
        for env in envs
    ]


def create_volume_mounts(containerType: str, count: int):
    return [
        {
            'op': 'add',
            'path': f'/spec/{containerType}/{count}/volumeMounts',
            'value': []
        }
    ]


def patch_volume_mounts(containerMounts: dict, containerType: str, count: int, volumeMounts: list) -> list:
    return [
        {
            'op': 'add',
            'path': f'/spec/{containerType}/{count}/volumeMounts/-',
            'value': mount
        }
        for mount in volumeMounts
    ]


def create_volumes():
    return [
        {
            'op': 'add',
            'path': '/spec/volumes',
            'value': []
        }
    ]


def patch_volumes(containerVolumes: dict, volumes: list):
    return [
        {
            'op': 'add',
            'path': '/spec/volumes/-',
            'value': volume
        }
        for volume in volumes
    ]
