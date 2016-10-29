from flask import Flask
from flask import render_template
from flask import redirect
import platform

from sys import version_info

# Due to timeout not existing before Python 3.3:
if version_info.major == 2 or version_info.minor <= 3:
    import pip
    pip.main(["install", "subprocess32"])
    # from __future__ import unicode_literals   # Not sure if necessary
    import subprocess32 as subprocess
else:
    import subprocess

app = Flask(__name__)


def filter_output(proc, host, time_limit=None):
    # type: (Popen, str, int) -> str
    # http://stackoverflow.com/a/35230792
    """Function for getting output from process executed."""
    try:
        stdout, stderr = proc.communicate(timeout=time_limit)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate(timeout=time_limit)
    return_data = "{} {}".format(host, stdout)

    if not stderr:  # => if stderr != "":
        # Everything is jolly good, ignore stderr
        return return_data

    return_data += "\n\nstderr:\n{}".format(stderr)
    return return_data


@app.route('/')
def index():
    # type: () -> render_template
    """Root index for this Flask webapp. Simply redirects to /ping."""
    return redirect("/ping", code=302)


@app.route('/ping/')
@app.route('/ping/<string:host>/')
@app.route('/ping/<string:host>/<int:count>/')
def ping(host=None, count=4):
    # type: (str, int) -> render_template
    """Main function where the 'magic' happens!..."""
    if not host:
        return render_template(
            'results.html',
            return_data=(
                'You need to enter an IP address at the end of the URL,'
                ' like <domain>/ping/8.8.8.8'))

    # Default time_limit of hardcoded 16 seconds.
    #   (It's a 4-packet ping for crying out loud...)
    time_limit = 16

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
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
