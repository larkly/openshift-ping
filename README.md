# Openshift S2I demo site for pinging other pods

The desired multitenancy functionality has been delivered if pods in different project are unable to communicate with each other. This test could be done by retrieving pod IP addresses with `oc get endpoints`, logging on to any container with `oc rsh` and trying to ping ip addresses.

However, this tool is set up in two projects, ping1 and ping2, using the commands

```
for project in ping1 ping2; do oc new-project $project; \
oc new-app python:3.4~https://github.com/larkly/openshift-ping.git \
--name=$project -n $project; done
```

The build can be monitored with the `oc log` output shown.

In order to verify that we cannot ping pods allocated to different projects, go to the webpage

 http://ping1.apps.domain.name/ping/ping1.ping1.endpoints.cluster.local

A successful ping output should be the result. Now go to

 http://ping2.apps.domain.name/ping/ping1.ping1.endpoints.cluster.local

The ping output should indicate that zero packets were received at ping2 from ping1.

## Configuration

The following environment variables can be set:

| Variable | Default | Description |
|----------|---------|-------------|
| `PING_TARGET` | *(none)* | When set, visiting `/ping/` without a host argument will ping this target automatically (issue #5). |
| `target` | *(none)* | Fallback for `PING_TARGET` (checked only if `PING_TARGET` is unset). |
| `FLASK_DEBUG` | `0` | Set to `1`, `true`, or `yes` to enable Flask debug mode (local development only). Debug mode is **off** by default for security. |

## OpenShift Environment Noise

On OpenShift, the `LD_PRELOAD=libnss_wrapper.so` setting produces a harmless but
misleading warning in `stderr` on every subprocess invocation.  This application
automatically filters that warning from ping output so users see clean results
(issue #6).

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m unittest discover -s . -p "test_*.py" -v

# Lint
ruff check .

# Run the app locally (debug mode off by default)
python app.py
# Or with debug mode:
FLASK_DEBUG=1 python app.py
```

