# Openshift S2I demo site for pinging other pods


oc new-app python:2.7~https://github.com/larkly/openshift-ping.git --name=ping1 --env=APP_FILE=flaskping.py -n ping1

oc new-app python:2.7~https://github.com/larkly/openshift-ping.git --name=ping2 --env=APP_FILE=flaskping.py -n ping2
