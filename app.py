from flask import Flask
from flask import render_template
from flask import redirect
import os
import subprocess
import platform

# Environment variable name for default ping target.
# When set, visiting /ping/ without a host argument will ping this target.
DEFAULT_TARGET_ENV = 'PING_TARGET'

app = Flask(__name__)


def _filter_stderr(stderr):
    """Remove known OpenShift environment noise from stderr.

    OpenShift sets LD_PRELOAD=libnss_wrapper.so which produces a harmless
    warning on every subprocess invocation.  This cleans it up so users
    don't see confusing noise in their ping output (issue #6).
    """
    if not stderr:
        return stderr
    noise_markers = [
        "libnss_wrapper.so",
        "LD_PRELOAD",
    ]
    lines = stderr.splitlines()
    filtered = [
        line for line in lines
        if not any(marker in line for marker in noise_markers)
    ]
    return '\n'.join(filtered) if filtered else ''


def filter_output(proc, host, time_limit=None):
    """Function for getting output from process executed."""
    try:
        stdout, stderr = proc.communicate(timeout=time_limit)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=time_limit)
    return_data = "{} {}".format(host, stdout)

    stderr = _filter_stderr(stderr)
    if not stderr:
        # Everything is jolly good, ignore stderr
        return return_data

    return_data += "\n\nstderr:\n{}".format(stderr)
    return return_data


@app.route('/')
def index():
    """Root index for this Flask webapp. Simply redirects to /ping."""
    return redirect("/ping", code=302)


@app.route('/ping/')
@app.route('/ping/<string:host>/')
@app.route('/ping/<string:host>/<int:count>/')
def ping(host=None, count=4):
    """Main function where the 'magic' happens!...

    If no host is given in the URL, falls back to the PING_TARGET
    environment variable (issue #5).  If that is also unset, an
    instruction message is displayed.
    """
    if not host:
        # Fall back to default target from environment variable (issue #5)
        host = os.environ.get(DEFAULT_TARGET_ENV) or os.environ.get('target')

    if not host:
        return render_template(
            'results.html',
            return_data=(
                'You need to enter an IP address at the end of the URL,'
                ' like <domain>/ping/8.8.8.8'
                ' or set the {} environment variable.'.format(
                    DEFAULT_TARGET_ENV)))

    # Default time_limit of hardcoded 16 seconds.
    #   (It's a 4-packet ping for crying out loud...)
    time_limit = 2 * count

    if platform.system() == "Windows":
        cmd = ["ping", "-n", str(count), str(host)]
    else:
        cmd = ["ping", "-c", str(count), str(host)]

    proc = subprocess.Popen(
        args=cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True)

    return_data = filter_output(proc=proc, host=host, time_limit=time_limit)
    return render_template('results.html', return_data=return_data)


if __name__ == '__main__':
    # Only enable debug mode when explicitly requested via env var.
    # Previously hard-coded to True, which exposed the Werkzeug debugger
    # (remote code execution risk) in production.
    app.debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=8080)
