GET_DISABLED=false

# Get the token to authenticate in the API
token=$(oc extract secret/pull-secret \
    -n openshift-config --to=- |\
    jq '.auths."cloud.openshift.com".auth' |\
    sed -e 's/^"//' -e 's/"$//')

# Get the CLUSTER ID to use as parameter to the API call
cluster_id=$(oc get clusterversion -o jsonpath='{.items[].spec.clusterID}')
io_hash=$(git ls-remote https://github.com/openshift/insights-operator.git HEAD |cut -f1)

# Fetch the data
recommendations=$(curl -s \
  https://console.redhat.com/api/insights-results-aggregator/v2/cluster/$cluster_id/reports?get_disabled=$GET_DISABLED \
  -H 'accept: application/json' \
  -H "User-Agent: insights-operator/${io_hash} cluster/${cluster_id}" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${token}")