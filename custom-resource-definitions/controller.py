import requests
import base64
import json

from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Load Kubernetes configuration
config.load_kube_config()

# Define the API and CRD details
API_URL = "https://console.redhat.com/api/insights-results-aggregator/v2/cluster/{cluster_id}/reports"
GET_DISABLED = "false"
IO_HASH = "567fcb7672182f825069b6dfd33b14ad7e9dec3f"


def get_cluster_id():
    v1 = client.CustomObjectsApi()
    cluster_info = v1.get_cluster_custom_object(
        "config.openshift.io", "v1", "clusterversions", "version"
    )
    return cluster_info["spec"]["clusterID"]


def fetch_recommendations():
    # Get the token to authenticate in the API
    token = get_auth_token()
    cluster_id = get_cluster_id()
    # Fetch the data
    response = requests.get(
        API_URL.format(cluster_id=cluster_id),
        headers={
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
            # this user-agent is mandatory when authenticating with the pull-secret
            "User-Agent": f"insights-operator/{IO_HASH} cluster/{cluster_id}",
        },
        params={"get_disabled": GET_DISABLED},
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch recommendations: {response.text}")

    return response.json()


def get_auth_token():
    # Create a Kubernetes client
    api_instance = client.CoreV1Api()

    # Retrieve the pull-secret from the specified namespace
    namespace = "openshift-config"  # Change as needed
    secret_name = "pull-secret"

    try:
        secret = api_instance.read_namespaced_secret(secret_name, namespace)
        # Decode the token from the secret data
        token_data = secret.data[".dockerconfigjson"]
        token_json = base64.b64decode(token_data).decode("utf-8")

        # Extract the token using json parsing
        token_dict = json.loads(token_json)
        token = token_dict["auths"]["cloud.openshift.com"]["auth"]

        return token
    except ApiException as e:
        raise Exception("Failed to retrieve the authentication token") from e
    except KeyError:
        raise Exception("Token not found in the pull-secret.") from e


def create_recommendation_crd(recommendation):
    # Create a Kubernetes client
    api_instance = client.CustomObjectsApi()

    # Define the CRD object
    crd_body = {
        "apiVersion": "monitoring.openshift.io/v1",
        "kind": "Recommendation",
        "metadata": {
            "name": recommendation["rule_id"].replace(
                "_", "-"
            ),  # You cannot use underscores
        },
        "spec": {
            "ruleID": recommendation["rule_id"],
            "description": recommendation["description"],
            "created_at": recommendation["created_at"],
            "details": recommendation["details"],
            "disable_feedback": recommendation["disable_feedback"],
            "disabled": recommendation["disabled"],
            "disabled_at": (
                recommendation["disabled_at"]
                if len(recommendation["disabled_at"]) > 0
                else None
            ),
            "extra_data": recommendation["extra_data"],
            "internal": recommendation["internal"],
            "reason": recommendation["reason"],
            "resolution": recommendation["resolution"],
            "tags": recommendation["tags"],
            "total_risk": recommendation["total_risk"],
            "user_vote": recommendation["user_vote"],
        },
        "status": {"createdAt": recommendation["created_at"]},
    }

    try:
        api_instance.create_cluster_custom_object(
            group="monitoring.openshift.io",
            version="v1",
            plural="recommendations",
            body=crd_body,
        )
        print(f"Created Recommendation: {recommendation['rule_id']}")
    except ApiException as e:
        raise Exception("Exception when creating CRD") from e


def delete_existing_crds():
    api_instance = client.CustomObjectsApi()
    try:
        existing_crds = api_instance.list_cluster_custom_object(
            group="monitoring.openshift.io", version="v1", plural="recommendations"
        )

        for crd in existing_crds.get("items", []):
            rule_id = crd["metadata"]["name"]
            api_instance.delete_cluster_custom_object(
                group="monitoring.openshift.io",
                version="v1",
                plural="recommendations",
                name=rule_id,
                body=client.V1DeleteOptions(),
            )
            print(f"Deleted existing Recommendation: {rule_id}")
    except ApiException as e:
        raise Exception("Exception when deleting CRDs") from e


if __name__ == "__main__":
    # Fetch new recommendations
    recommendations = fetch_recommendations()

    # Clean up existing CRDs if everything went fine
    delete_existing_crds()

    for rec in recommendations["report"]["data"]:
        create_recommendation_crd(rec)
