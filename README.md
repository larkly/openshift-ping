# Openshift S2I demo site for pinging other pods

oc new-project ping1; oc new-project ping2;

oc new-app python:2.7~https://github.com/larkly/openshift-ping.git --name=ping1 --env=APP_FILE=flaskping.py -n ping1

oc new-app python:2.7~https://github.com/larkly/openshift-ping.git --name=ping2 --env=APP_FILE=flaskping.py -n ping2

The desired multitenancy functionality has been delivered if pods in different project are unable to communicate with each other. This test could be done by retrieving pod IP addresses with `oc get endpoints`, logging on to any container with `oc rsh` and trying to ping ip addresses.

However, this tool is set up in two projects, ping1 and ping2, using the command `for project in ping1 ping2; do oc new-app python:2.7~https://github.com/larkly/openshift-ping.git --name=$project --env=APP_FILE=flaskping.py -n $project`.

The build can be monitored with the `oc log` output shown.

In order to verify that we cannot ping pods allocated to different projects, go to the webpage

 http://ping1.<routename>/ping/ping1.ping1.endpoints.cluster.local

A successful ping output should be the result. Now go to

 http://ping2.<routename>/ping/ping1.ping1.endpoints.cluster.local

The ping output should indicate that zero packets were received at ping2 from ping1.
