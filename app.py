from flask import Flask
from flask import render_template
from flask import redirect
import subprocess

app = Flask(__name__)


def filter_output(proc, host: str, time_limit: int=None) -> str:
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
    """Root index for this Flask webapp. Simply redirects to /ping."""
    return redirect("/ping", code=302)


@app.route('/ping')
@app.route('/ping/<string:host>')
def ping(host: string=None):
    """Main function where the 'magic' happens!..."""
    if not host:
        return render_template(
            'results.html',
            return_data=(
                'You need to enter an IP address at the end of the URL,'
                ' like <domain>/ping/8.8.8.8'))

    # Default time_limit of hardcoded 16 seconds.
    #   (It's a 4-packet ping for crying out loud...)
    time_limit, cmd = 16, ["ping", "-c", "4", str(host)]
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
