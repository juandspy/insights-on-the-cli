# Insights on the CLI

- [Insights on the CLI](#insights-on-the-cli)
  - [Using plugins](#using-plugins)
    - [Making use of already existing CRDs](#making-use-of-already-existing-crds)
    - [Making use of the console.redhat.com API](#making-use-of-the-consoleredhatcom-api)
      - [Extra: exporting to CSV](#extra-exporting-to-csv)
  - [Using Custom Resource Definitions](#using-custom-resource-definitions)

This repo researches different ways of achieving an `oc get recommendations`
command to show the OCP Advisor recommendations on the CLI.

## Using plugins

Writing plugins is quite straightforward, but cannot be automatically shipped
to all customers using `oc`. You just need to place an executable like
`oc-foo-bar` or `kubectl-foo-bar` and you will be able to call `oc foo bar`.
There is a limitation for the naming so we won't be able to create an
`oc-get-recommendations` plugin. The workaround is to use `oc-recommendations`
for example.

These plugins need to be placed in the `$PATH` of your system, so you may want
to run `export PATH=$PATH:$(pwd)/plugins` or copy these executables somewhere in your
`$PATH`.

See more information about plugins [here](https://kubernetes.io/docs/tasks/extend-kubectl/kubectl-plugins/).

### Making use of already existing CRDs

Luckily for us, the Insights Operator already defines some [HelathChecks](https://github.com/openshift/api/blob/25d2eecae482743bb3bbb30e0e6a34a8bcdb1a36/operator/v1/types_insights.go#L86)
on each cluster that kind of represent the recommendations. However, they just
contain some basic information.

You can access these objects with

```sh
$ oc get insightsoperators -o json | jq '.items[0].status.insightsReport.healthChecks'
```
```json
[
  {
    "advisorURI": "https://console.redhat.com/openshift/insights/advisor/clusters/3105ebec-8b14-4c8e-b3d7-3875bf1c3271?first=ccx_rules_ocp.external.rules.operator_unmanaged%7COPERATOR_UNMANAGED",
    "description": "OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state",
    "state": "Enabled",
    "totalRisk": 2
  }
]
```

We can easily convert this into a plugin. Please check [oc-recommendations](oc-recommendations).
This way you can run:

```
❯ oc recommendations
NAME    DESCRIPTION     STATE   TOTAL_RISK      ADVISOR_URI
====    ===========     =====   ==========      ===========
OPERATOR_UNMANAGED      OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state   Enabled 2       https://console.redhat.com/openshift/insights/advisor/clusters/3105ebec-8b14-4c8e-b3d7-3875bf1c3271?first=ccx_rules_ocp.external.rules.operator_unmanaged%7COPERATOR_UNMANAGED
```

### Making use of the console.redhat.com API

We can use the `pull-secret` to make calls to the console.redhat.com API.

```
❯ oc extract secret/pull-secret \
    -n openshift-config --to=- |\
    jq '.auths."cloud.openshift.com"'
{
  "auth": "XXX",
  "email": "jdiazsua@redhat.com"
}
```

See how it works with:

```
❯ oc recommendations api
Rule_ID                                                 Created_At            Total_Risk  Disabled
=======                                                 ==========            ==========  ========
ccx_rules_ocp.external.rules.operator_unmanaged.report  2021-01-11T16:00:00Z  2           false
```

```
❯ oc recommendations api details
Rule_ID                                                 Created_At            Description  Details  Reason  Resolution  Total_Risk  Disabled
=======                                                 ==========            ===========  =======  ======  ==========  ==========  ========
ccx_rules_ocp.external.rules.operator_unmanaged.report  2021-01-11T16:00:00Z  OpenShift    cluster  can     get         damaged     when      an  operator  is  configured  to  'Unmanaged'  state  OpenShift  cluster  can  get  damaged  when  an  operator  is  configured  to  'Unmanaged'  state.  {{?pydata.unmanaged_operators.length  >  1}}The  following  operators  have  the  `managementState`  parameter  set  to  `Unmanaged`.  {{??}}The  following  operator  has  the  `managementState`  parameter  set  to  `Unmanaged`.  {{?}}Some  Operators  might  not  support  this  management  state  as  it  might  damage  the  cluster  and  require  manual  recovery.\n\n**Operator  Name:**\n{{~pydata.unmanaged_operators:item}}\n-  {{=item}}\n{{~}}\n  Red  Hat  recommends  that  you  configure  the  operator  parameter  `managementState`  to  `Managed`.\n\nExample:\n{{~pydata.unmanaged_operators:item}}\n~~~\n#  oc  patch  oc/{{=item}}  --type='merge'  -p  '{"Spec":{"managementState":  "Managed"}}'\n~~~\n{{~}}\n  2  false
```

#### Extra: exporting to CSV

I wrote an extra plugin to store all this info as a CSV file:

```
❯ oc recommendations api csv > /tmp/recommendations.csv
```

Would look like:

| Rule_ID                                                | Created_At           | Description                                                                                                                                                                       | Details                                                                                            | Reason                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Resolution                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Total_Risk | Disabled |
| ------------------------------------------------------ | -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------- |
| ccx_rules_ocp.external.rules.operator_unmanaged.report | 2021-01-11T16:00:00Z | OpenShift  cluster    can         get           damaged         when       an                                operator        is         configured         to  'Unmanaged'  state | OpenShift  cluster  can  get  damaged  when  an  operator  is  configured  to  'Unmanaged'  state. | ```{{?pydata.unmanaged_operators.length  >  1}}The  following  operators  have  the  `managementState`  parameter  set  to  `Unmanaged`.  {{??}}The  following  operator  has  the  `managementState`  parameter  set  to  `Unmanaged`.  {{?}}Some  Operators  might  not  support  this  management  state  as  it  might  damage  the  cluster  and  require  manual  recovery. **Operator                                                                                  Name:** {{~pydata.unmanaged_operators:item}} -                                                                                           {{=item}} {{~}}``` | ```Red                                                                                      Hat        recommends  that          you             configure  the                               operator        parameter  `managementState`  to  `Managed`. Example: {{~pydata.unmanaged_operators:item}} ~~~ #                                                                                           oc         patch       oc/{{=item}}  --type='merge'  -p         '{"Spec":{"managementState":  "Managed"}}' ~~~ {{~}}``` | 2          | false    |

## Using Custom Resource Definitions

The idea is to populate a CRD called `Recommendations` so that you can use
all the built-in features of `oc`, including `oc get recommendations`.

You can create these CRDs with

```
❯ oc create -f custom-resource-definitions/
```

And run a controller (after installing the [requirements](requirements.txt)):

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

that could run periodically to fetch the latest recommendations and populating
the CRDs:

```
export PYTHONWARNINGS="ignore:Unverified HTTPS request"
python custom-resource-definitions/controller.py
```

Then you may:

<details>
<summary>1. List basic information</summary>
<br>

```
❯ oc get recommendations
NAME                                                     CREATED AT             TOTAL RISK
ccx-rules-ocp.external.rules.operator-unmanaged.report   2021-01-11T16:00:00Z   2
```

</details>

<details>
<summary>2. Get more information</summary>
<br>

```
❯ oc get recommendations -o wide
NAME                                                     DESCRIPTION                                                                             CREATED AT             TOTAL RISK   DETAILS
ccx-rules-ocp.external.rules.operator-unmanaged.report   OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state   2021-01-11T16:00:00Z   2            OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state.
```

</details>

<details>
<summary>3. Get all the information</summary>
<br>

```
❯ oc describe recommendations/ccx-rules-ocp.external.rules.operator-unmanaged.report
Name:         ccx-rules-ocp.external.rules.operator-unmanaged.report
Namespace:    
Labels:       <none>
Annotations:  <none>
API Version:  monitoring.openshift.io/v1
Kind:         Recommendation
Metadata:
  Creation Timestamp:  2024-11-21T10:20:50Z
  Generation:          1
  Resource Version:    1468352
  UID:                 c66042c1-79e3-41a6-8cbe-6d6061040d72
Spec:
  created_at:        2021-01-11T16:00:00Z
  Description:       OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state
  Details:           OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state.
  disable_feedback:  
  Disabled:          false
  extra_data:
    error_key:  OPERATOR_UNMANAGED
    Type:       rule
  Internal:     false
  Reason:       {{?pydata.unmanaged_operators.length > 1}}The following operators have the `managementState` parameter set to `Unmanaged`. {{??}}The following operator has the `managementState` parameter set to `Unmanaged`. {{?}}Some Operators might not support this management state as it might damage the cluster and require manual recovery.

**Operator Name:**
{{~pydata.unmanaged_operators:item}}
- {{=item}}
{{~}}

  Resolution:  Red Hat recommends that you configure the operator parameter `managementState` to `Managed`.

Example:
{{~pydata.unmanaged_operators:item}}
~~~
# oc patch oc/{{=item}} --type='merge' -p '{"Spec":{"managementState": "Managed"}}'
~~~
{{~}}

  Tags:
    service_availability
  total_risk:  2
  user_vote:   0
Events:        <none>
```

</details>

<details>
<summary>4. Get the information as YAML</summary>
<br>

```
❯ oc get recommendations/ccx-rules-ocp.external.rules.operator-unmanaged.report -o yaml
apiVersion: monitoring.openshift.io/v1
kind: Recommendation
metadata:
  creationTimestamp: "2024-11-21T10:20:50Z"
  generation: 1
  name: ccx-rules-ocp.external.rules.operator-unmanaged.report
  resourceVersion: "1468352"
  uid: c66042c1-79e3-41a6-8cbe-6d6061040d72
spec:
  created_at: "2021-01-11T16:00:00Z"
  description: OpenShift cluster can get damaged when an operator is configured to
    'Unmanaged' state
  details: OpenShift cluster can get damaged when an operator is configured to 'Unmanaged'
    state.
  disable_feedback: ""
  disabled: false
  extra_data:
    error_key: OPERATOR_UNMANAGED
    type: rule
  internal: false
  reason: |
    {{?pydata.unmanaged_operators.length > 1}}The following operators have the `managementState` parameter set to `Unmanaged`. {{??}}The following operator has the `managementState` parameter set to `Unmanaged`. {{?}}Some Operators might not support this management state as it might damage the cluster and require manual recovery.

    **Operator Name:**
    {{~pydata.unmanaged_operators:item}}
    - {{=item}}
    {{~}}
  resolution: |
    Red Hat recommends that you configure the operator parameter `managementState` to `Managed`.

    Example:
    {{~pydata.unmanaged_operators:item}}
    ~~~
    # oc patch oc/{{=item}} --type='merge' -p '{"Spec":{"managementState": "Managed"}}'
    ~~~
    {{~}}
  tags:
  - service_availability
  total_risk: 2
  user_vote: 0
```

</details>

<details>
<summary>5. Get the information as JSON</summary>
<br>

```
❯ oc get recommendations/ccx-rules-ocp.external.rules.operator-unmanaged.report -o json
{
    "apiVersion": "monitoring.openshift.io/v1",
    "kind": "Recommendation",
    "metadata": {
        "creationTimestamp": "2024-11-21T10:20:50Z",
        "generation": 1,
        "name": "ccx-rules-ocp.external.rules.operator-unmanaged.report",
        "resourceVersion": "1468352",
        "uid": "c66042c1-79e3-41a6-8cbe-6d6061040d72"
    },
    "spec": {
        "created_at": "2021-01-11T16:00:00Z",
        "description": "OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state",
        "details": "OpenShift cluster can get damaged when an operator is configured to 'Unmanaged' state.",
        "disable_feedback": "",
        "disabled": false,
        "extra_data": {
            "error_key": "OPERATOR_UNMANAGED",
            "type": "rule"
        },
        "internal": false,
        "reason": "{{?pydata.unmanaged_operators.length \u003e 1}}The following operators have the `managementState` parameter set to `Unmanaged`. {{??}}The following operator has the `managementState` parameter set to `Unmanaged`. {{?}}Some Operators might not support this management state as it might damage the cluster and require manual recovery.\n\n**Operator Name:**\n{{~pydata.unmanaged_operators:item}}\n- {{=item}}\n{{~}}\n",
        "resolution": "Red Hat recommends that you configure the operator parameter `managementState` to `Managed`.\n\nExample:\n{{~pydata.unmanaged_operators:item}}\n~~~\n# oc patch oc/{{=item}} --type='merge' -p '{\"Spec\":{\"managementState\": \"Managed\"}}'\n~~~\n{{~}}\n",
        "tags": [
            "service_availability"
        ],
        "total_risk": 2,
        "user_vote": 0
    }
}
```

</details>

<details>
<summary>6. Get a specific field</summary>
<br>

```
❯ oc get recommendations/ccx-rules-ocp.external.rules.operator-unmanaged.report -o json | jq .spec.tags
[
  "service_availability"
]
```

</details>